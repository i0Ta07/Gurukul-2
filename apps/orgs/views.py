from django.http import HttpResponse, HttpResponseBadRequest
from apps.orgs.mixins import TeacherRequiredMixin,OrgMembershipRequiredMixin,OwnerAdminRequired,OwnerRequired
from django.views import View
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render,get_object_or_404
from apps.orgs.models import OrgAdmin, OrgInvitation, OrgMembership, Organization
from apps.users.models import User
from django.core.exceptions import ValidationError
from apps.orgs.forms import CreateChildOrgForm,CreateRootOrgForm,CreateOrgConfigForm,SendInvitationForm,CreateAdminForm
from django.db import transaction
from config.utils import create_message_and_redirect
from apps.orgs.utils import (
    UserRole,
    get_user_role,validate_child_org,validate_root_org,
    build_breadcrumbs,build_slug,resolve_org_path,get_emails_from_excel,
    build_membership_slug,annotate_memberships,generate_numeric_otp,
    delete_root_org_otp_key
    )
from django.core.cache import cache
from django.contrib.auth.hashers import make_password,check_password
from config.utils import send_email

class ViewRootOrgs(LoginRequiredMixin, TeacherRequiredMixin,View):
    template_name = "orgs/view_orgs_and_classrooms.html"

    def get(self, request, *args, **kwargs):
            created_orgs = Organization.get_root_nodes().filter(config__owner = request.user)
            memberships = annotate_memberships(
                OrgMembership.objects.filter(teacher= request.user).select_related("org")
            )
            orgs = [
                *build_slug(instance= created_orgs,role=UserRole.OWNER),
                *build_membership_slug(instance=memberships),
            ]
            context = {"orgs": orgs,"root_org_view":True}
            if request.htmx:
                    return render(request, "orgs/view_orgs_and_classrooms.html#view-org",context)
            return render(request, self.template_name, context)

# should only show the TLD orgs the user has created
class ViewChildOrgs(LoginRequiredMixin, TeacherRequiredMixin, View):
    template_name = "orgs/view_orgs_and_classrooms.html"

    def get(self, request, *args, **kwargs):
        org_path = kwargs.get("org_path")
        slugs = [slug for slug in org_path.strip("/").split("/") if slug]
        root_node = get_object_or_404(Organization.get_root_nodes(), slug = slugs[0]) # Get root node
        org_role = get_user_role(root = root_node,user= request.user) # Check if user has access to root node
        if org_role:            
            current_node = resolve_org_path(root_node =root_node,slugs=slugs)
            children = current_node.get_children().order_by("name")
            template = root_node.config.template()
            current_depth = current_node.get_depth()
            node_label = template[current_depth -1]
            classrooms = current_node.classrooms.order_by('name')
            context = {
                "org_role":org_role,
                "orgs":build_slug(children,org_path),
                "classrooms":build_slug(classrooms,org_path),
                "current_org_name": current_node.name,
                "parent_org_id": current_node.id,
                "parent_org_path":org_path,
                "breadcrumbs": build_breadcrumbs(org_path), 
                "child_org_view": not classrooms.exists() and current_depth != len(template),
                "classroom_view": not children.exists()  and current_depth  == len(template),
                "node_label":node_label,
            }
            if request.htmx:
                return render(request, "orgs/view_orgs_and_classrooms.html#view-org",context)
                
            return render(request, self.template_name, context)
        return create_message_and_redirect(request,message="You are not part of this organization",url="users-dashboard",code="error")

class CreateChildOrg(LoginRequiredMixin,TeacherRequiredMixin,OwnerAdminRequired,View):
    template_name = "orgs/partials/create_child_org.html"
    form_class = CreateChildOrgForm

    def get(self,request, *args, **kwargs):
        form = self.form_class()
        return render(request, self.template_name, {"form":form,**kwargs,})

    
    def post(self, request, *args, **kwargs):
        parent_id = kwargs['org_id']
        parent = get_object_or_404(Organization, pk=parent_id)

        # Load post data into the form
        form = self.form_class(request.POST)
        form_context = {"form":form,**kwargs,}
        if not form.is_valid():
            return render(request, self.template_name,form_context)
        org = form.save(commit=False) # need id of the created obj, henc form.save(commit = False), not Organization(**cleaned_data)
        org.created_by = request.user
        try:
            validate_child_org(parent_node = parent, instance=org)
        except ValidationError as e:
            form.add_error(field=None,error=e.message)
            return render(request, self.template_name,form_context)
        parent.add_child(instance=org)
        row_context = {
            "org":build_slug(instance=org,parent_path=kwargs['org_path']),"parent_org_path":kwargs['org_path']
        }
        messages.success(request,message="Organization created successfully.")
        response = render(request, "orgs/view_orgs_and_classrooms.html#org-row",row_context)
        response['HX-Trigger'] = 'child-org-created'
        return response

class CreateRootOrgAndConfig(LoginRequiredMixin,TeacherRequiredMixin,View):
    template_name = "orgs/partials/create_root_and_config_org.html"
    root_form = CreateRootOrgForm
    config_form = CreateOrgConfigForm

    def get(self,request, *args, **kwargs):
        root_form = self.root_form()
        config_form = self.config_form()
        return render(request, self.template_name, {"root_form":root_form,"config_form":config_form})
    
    def post(self, request, *args, **kwargs):
        def render_error():
            response = render(
                request,
                self.template_name,
                {
                    "root_form": root_form,
                    "config_form": config_form,
                },
            )
            response["HX-Retarget"] = "#modal_container" # Change the target to inside modal from main-list if there is an error
            response["HX-Reswap"] = "innerHTML" # Change the swap method to innerHTML from afterbegin inside the target container
            return response

        root_form = self.root_form(request.POST)
        config_form = self.config_form(request.POST)

        if not root_form.is_valid() or not config_form.is_valid():
            return render_error()
        
        org = root_form.save(commit=False) # Need commit= False because we need id in building slug
        org.created_by = request.user

        try:
            validate_root_org(instance=org)
        except ValidationError as e:
            root_form.add_error(field=None,error=e.message)
            return render_error()
        
        org_config = config_form.save(commit=False)  # Need commit= False to later save.
        org_config.org = org
        org_config.owner = request.user

        with transaction.atomic(): # either both root and config are created or none
            Organization.add_root(instance = org)
            org_config.save()

        messages.success(request,"Organization created successfully")
        response = render(request,"orgs/view_orgs_and_classrooms.html#org-row", {
            "org": build_slug(instance= org, role= UserRole.OWNER),
            "root_org_view":True,
            }
        )
        response['HX-Trigger'] = 'root-org-created'
        return response

class SendInvitations(LoginRequiredMixin,TeacherRequiredMixin,OwnerAdminRequired,View):
    template_name = "orgs/send_invitations.html"
    form_class = SendInvitationForm

    def get(self,request,*args, **kwargs):
        form = self.form_class()
        context = {'form':form, **kwargs}
        if request.htmx:
            return render(request,template_name="orgs/send_invitations.html#send-invitations",context=context)
        return render(request,template_name=self.template_name,context=context)       

    def post(self,request, *args, **kwargs):
        form = self.form_class(request.POST, request.FILES)
        if not form.is_valid():
            return render(request,template_name="orgs/send_invitations.html#send-invitations",context={'form':form, **kwargs})
        # If email is provided
        email = form.cleaned_data['email']
        
        if email:
            try:
                user = User.objects.get(email = email)
            except User.DoesNotExist:
                form.add_error("email","No such user exists. Kindly recheck the email.")
                return render(request,template_name="orgs/send_invitations.html#send-invitations",context={'form':form, **kwargs})
            root_org = self.get_root_org()
            invitation = OrgInvitation(to_user=user,from_user=request.user,org=root_org,)
            try:
                invitation.full_clean()   
                invitation.save()
            except ValidationError as e:
                form.add_error(None,e)
                return render(request,template_name="orgs/send_invitations.html#send-invitations",context={'form':form, **kwargs})

            messages.success(request,"Request sent successfully")
            # Render a fresh form
            return render(request,template_name="orgs/send_invitations.html#send-invitations",context={'form':self.form_class(), **kwargs})
        else:
            file =  form.cleaned_data['file']
            data = get_emails_from_excel(file)
            response = render(request,template_name="orgs/send_invitations.html#render-emails-from-files",context={"data":data, **kwargs})
            response['HX-Retarget'] = '#file_email_container'
            return response

class SendBulkInvitations(LoginRequiredMixin,TeacherRequiredMixin,OwnerAdminRequired,View):
    def post(self,request, *args, **kwargs):
        root_org = self.get_root_org()      
        email_ids = set(request.POST.getlist("emails"))
        users = (
            User.objects
            .filter(email__in=email_ids)
            .exclude(pk=request.user.pk) # 1. user is not inviting himself.
            .exclude(org_membership__org=root_org) # 2. requested user are not already part of the org.
            .exclude(received_invitation__org=root_org) # 3. If there is already an invitation
            .distinct()
        )
        created_invitations = OrgInvitation.objects.bulk_create(
            [
                OrgInvitation(
                    to_user=user,
                    from_user=request.user,
                    org=root_org,
                )
                for user in users
            ]
        )
        messages.success(request,f"Sent {len(created_invitations)} invitations.")
        return render(request,template_name="orgs/send_invitations.html#send-invitations",context={'form':SendInvitationForm(),**kwargs})

class ViewInvitations(LoginRequiredMixin,TeacherRequiredMixin,View):
    template_name = "orgs/view_invitations.html"

    def get(self,request, *args, **kwargs):
        pending_invitations = OrgInvitation.objects.filter(to_user = request.user).order_by('-created_at')
        context = {"pending_invitations":pending_invitations,"count":len(pending_invitations)}
        if request.htmx:
            return render(request,template_name="orgs/view_invitations.html#view-invitations",context=context)
        return render(request,template_name=self.template_name,context=context)

    def post(self,request, *args, **kwargs):
        inv_id = kwargs['invitation_id']
        inv_obj = get_object_or_404(OrgInvitation,pk=inv_id)
        action = request.POST.get("action")

        if action == "accept":
            membership = OrgMembership(org = inv_obj.org, teacher = inv_obj.to_user, created_by = inv_obj.from_user)
            try:
                membership.full_clean()
            except ValidationError as e:
                messages.error(request,e)
                return render(request,"partials/messages.html")
            membership.save()
            messages.success(request,f"You are now part of {membership.org.name}.")
        elif action == "reject":
            messages.warning(request,f"Request from {inv_obj.from_user.get_full_name()} to join {inv_obj.org.name} has been rejected.")
        else:
            return HttpResponseBadRequest("Invalid action")
        
        inv_obj.delete()
        response = render(request,"partials/messages.html")
        response['HX-Trigger'] = "invitation-removed"
        return response
        
class CreateAdmins(LoginRequiredMixin,TeacherRequiredMixin,OwnerAdminRequired,View):
    template_name = "orgs/create_admin.html"
    form_class = CreateAdminForm

    def get(self,request, *args, **kwargs):
        root_org = self.get_root_org()
        form = self.form_class(root_org= root_org)
        context = {'form':form,"org_name":root_org.name,**kwargs}
        if request.htmx:
            return render(request,template_name="orgs/create_admin.html#create-admin",context=context)
        return render(request,template_name=self.template_name,context=context)
    
    def post(self,request, *args, **kwargs):
        root_org = self.get_root_org()
        form = self.form_class(request.POST,root_org= root_org)
        error_context = {'form':form,"org_name":root_org.name,**kwargs}

        if not form.is_valid():
            return render(request,template_name="orgs/create_admin.html#create-admin",context = error_context)
        membership_obj = form.cleaned_data['teachers']
        instance = OrgAdmin(membership = membership_obj,created_by = request.user)
        try:
            instance.full_clean()
        except ValidationError as e:
            form.add_error(None,e)
            return render(request,template_name="orgs/create_admin.html#create-admin",context = error_context)
        instance.save()
        messages.success(request,"Admin created successfully")
        # Render fresh form
        context = {'form':self.form_class(root_org = root_org),"org_name":root_org.name,**kwargs}
        return render(request,template_name="orgs/create_admin.html#create-admin",context = context)

class ViewRootOrgConfig(LoginRequiredMixin,TeacherRequiredMixin,OrgMembershipRequiredMixin,View):
    template_name = "orgs/view_root_config.html"

    def get(self,request, *args, **kwargs):
        root_org = self.get_root_org()
        owner = root_org.config.owner
        memberships = OrgMembership.objects.filter(org=root_org)

        admins = [
            m.teacher
            for m in memberships.filter(admin__isnull=False)
        ]

        teachers = [
            m.teacher
            for m in memberships.filter(admin__isnull=True)
        ]
        role = get_user_role(root=root_org,user= request.user)

        context = {"owner":owner,"admins":admins,"teachers":teachers,"root_org_name":root_org.name,"root_org_id":root_org.id,"role":role}
        if request.htmx:
            return render(request,template_name="orgs/view_root_config.html#view-root-config",context=context)
        return render(request,self.template_name,context)

class DeleteRootOrgSendOTP(LoginRequiredMixin,TeacherRequiredMixin,OwnerRequired,View):
    def post(self,request, *args, **kwargs,):
        """User selected Yes on confirmation modal. Generate OTP, send it and save it in redis."""
        root_org =self.get_root_org()
        key= delete_root_org_otp_key(user_id=request.user.id,org_id=root_org.id)
        if cache.get(key=key):
            messages.success(request,"An OTP has already been sent to your registered email.")
            return render(request, 'orgs/partials/delete_root_org_verify_otp.html', {"org_name":root_org.name,**kwargs})             
        otp = generate_numeric_otp(length=6)
        hash = make_password(otp,salt=str(request.user.last_login))
        cache.set(
            key=key,
            value={
                "hash":hash,
                "attempts":0
            },
            timeout=300
        )
        owner = root_org.config.owner
        send_email(
            email_template_name="orgs/delete_root_org_otp_email.txt",
            html_email_template_name="orgs/delete_root_org_otp_email.html",
            subject=f"Request for Deletion: {root_org.name}",
            receiver=owner.email,
            context={"otp":otp,"org_name":root_org.name,"user_full_name":owner.get_full_name()}
        )
        return render(request, 'orgs/partials/delete_root_org_verify_otp.html', {"org_name":root_org.name,**kwargs})        

class DeleteRootOrg(LoginRequiredMixin,TeacherRequiredMixin,OwnerRequired,View):
    def get(self,request,*args,**kwargs):
        """Show confirmation modal"""
        root_org = self.get_root_org()
        return render(request, 'orgs/partials/delete_root_org.html', {"org_name":root_org.name,**kwargs})

    def post(self,request,*args,**kwargs):
        """Hanlde OTP submission"""
        root_org = self.get_root_org()
        key = delete_root_org_otp_key(user_id=request.user.id, org_id=root_org.id)
        data = cache.get(key)
        if not data:
            return create_message_and_redirect(request,"OTP expired",url='users-dashboard',code="error")
        data['attempts'] += 1

        if check_password(password=request.POST.get("otp"),encoded=data['hash']):
            cache.delete(key)
            root_org.delete()
            response = HttpResponse("", status=200)
            response['HX-Trigger'] = "otp-verified" # Close the modal
            return response
        elif data['attempts'] >= 3:
            cache.delete(key)
            return create_message_and_redirect(request,"Maximum 3 attempts. Try again later.",url='users-dashboard',code="error")
        else:
            messages.error(request,message=f"Incorrect OTP. Attempts Remaining: {(3 - data['attempts'])}")
            cache.set(key=key,value=data)
            # Render the same form again.
            response = render(request,'orgs/partials/delete_root_org_verify_otp.html',context={"org_name":root_org.name,**kwargs})
            # With different target and swap.
            response["HX-Retarget"] = "#modal_container"
            response["HX-Reswap"] = "innerHTML"
            return response
            

class DeleteChildOrg(LoginRequiredMixin,TeacherRequiredMixin,OwnerAdminRequired,View):
    def get(self,request,*args,**kwargs):
        org = get_object_or_404(Organization,pk=kwargs['org_id'])
        return render(request, 'orgs/partials/delete_child_org.html', {"org_name":org.name,**kwargs})

    def post(self,request,*args,**kwargs):
        org = get_object_or_404(Organization,pk=kwargs['org_id'])
        org.delete()
        return  HttpResponse("", status=200)


class ViewOrgDetails(LoginRequiredMixin,TeacherRequiredMixin,OrgMembershipRequiredMixin,View):
    template_name = 'orgs/partials/view_org_details.html'
    def get(self,request,*args,**kwargs):
        org = get_object_or_404(Organization,pk=kwargs['org_id'])
        return render(request,self.template_name,{'org':org})
        