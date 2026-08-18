from django.http import HttpResponse, HttpResponseBadRequest
from apps.orgs.mixins import TeacherRequiredMixin,OrgMembershipRequiredMixin,OwnerAdminRequired,OwnerRequired
from django.views import View
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render,get_object_or_404
from apps.orgs.models import OrgAdmin, OrgInvitation, OrgMembership, Organization
from apps.users.models import User
from django.core.exceptions import ValidationError
from apps.orgs.forms import OrgNameForm,CreateRootOrgForm,CreateOrgConfigForm,SendInvitationForm,CreateAdminForm
from django.db import transaction
from config.utils import create_message_and_redirect
from apps.orgs.utils import ( UserRole,
    validata_create_child_org,validate_create_root_org,build_slug,
    resolve_parent_path_and_build_breadcrumbs,get_emails_from_excel,
    build_membership_slug,annotate_memberships,generate_numeric_otp,
    delete_root_org_otp_key,validate_rename_org,render_error_inside_modal
    )
from django.core.cache import cache
from django.contrib.auth.hashers import make_password,check_password
from config.utils import send_email
from config.settings import EMAIL_EXPIRY_DURATION

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
class ViewChildOrgs(LoginRequiredMixin, TeacherRequiredMixin, OrgMembershipRequiredMixin, View):
    template_name = "orgs/view_orgs_and_classrooms.html"

    def get(self, request, *args, **kwargs):
        role = self.role
        if role:
            root_node = self.get_root_org()
            org_path = kwargs.get("org_path")
            slugs = [slug for slug in org_path.strip("/").split("/") if slug]
            parent_node,breadcrumbs = resolve_parent_path_and_build_breadcrumbs(root_node =root_node,slugs=slugs)
            children = parent_node.get_children().order_by("name")
            template = root_node.config.template()
            current_depth = parent_node.get_depth()
            label = template[current_depth -1]
            classrooms = parent_node.classrooms.order_by('name')
            context = {
                "role":role,
                "orgs":build_slug(children,org_path),
                "classrooms":build_slug(classrooms,org_path),
                "parent_org_name": parent_node.name,
                "parent_org_id": parent_node.id,
                "parent_org_path":org_path,
                "breadcrumbs": breadcrumbs, 
                "child_org_view": not classrooms.exists() and current_depth != len(template),
                "classroom_view": not children.exists()  and current_depth  == len(template),
                "label":label,
            }
            if request.htmx:
                return render(request, "orgs/view_orgs_and_classrooms.html#view-org",context)
                
            return render(request, self.template_name, context)
        return create_message_and_redirect(request,message="You are not part of this organization",url="users-dashboard",code="error")

class CreateChildOrg(LoginRequiredMixin,TeacherRequiredMixin,OwnerAdminRequired,View):
    template_name = "orgs/partials/create_child_org.html"
    form_class = OrgNameForm

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
            validata_create_child_org(parent = parent, instance=org)
        except ValidationError as e:
            form.add_error(field=None,error=e.message)
            return render(request, self.template_name,form_context)
        parent.add_child(instance=org)
        parent_org_path = kwargs['org_path']
        row_context = {
            "org":build_slug(instance=org,parent_org_path=parent_org_path),"parent_org_path":parent_org_path,
            "child_org_view":True, 'role': self.role
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
        root_form = self.root_form(request.POST)
        config_form = self.config_form(request.POST)

        if not root_form.is_valid() or not config_form.is_valid():
            return render_error_inside_modal(request=request,template_name=self.template_name,context={
                "root_form": root_form,
                "config_form": config_form,                
            })
        
        org = root_form.save(commit=False) # Need commit= False because we need id in build_slug
        org.created_by = request.user

        try:
            validate_create_root_org(instance=org)
        except ValidationError as e:
            root_form.add_error(field=None,error=e.message)
            return render_error_inside_modal(request=request,template_name=self.template_name,context={
                "root_form": root_form,
                "config_form": config_form,                
            })
        
        org_config = config_form.save(commit=False)  # Need commit= False to later save.
        org_config.org = org
        org_config.owner = request.user

        with transaction.atomic(): # either both root and config are created or none
            Organization.add_root(instance = org)
            org_config.save()

        messages.success(request,"Root Organization created successfully")
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
            response = render(request,template_name="orgs/send_invitations.html#render-emails-from-file",context={"data":data, **kwargs})
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
        context = {'form':form,"root_org_name":root_org.name,**kwargs}
        if request.htmx:
            return render(request,template_name="orgs/create_admin.html#create-admin",context=context)
        return render(request,template_name=self.template_name,context=context)
    
    def post(self,request, *args, **kwargs):
        root_org = self.get_root_org()
        form = self.form_class(request.POST,root_org= root_org)
        error_context = {'form':form,"root_org_name":root_org.name,**kwargs}

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
        context = {'form':self.form_class(root_org = root_org),"root_org_name":root_org.name,**kwargs}
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
        role = self.role
        is_admin_or_owner,is_owner,is_admin_or_teacher = False,False,False

        if role == UserRole.OWNER:
            is_owner = True
        if role in [UserRole.ADMIN, UserRole.OWNER]:
            is_admin_or_owner = True
        if role in [UserRole.ADMIN, UserRole.TEACHER]:
            is_admin_or_teacher = True

        context = {"owner":owner,"admins":admins,"teachers":teachers,"root_org_name":root_org.name,"root_org_id":root_org.id,"is_admin_or_owner":is_admin_or_owner,"is_owner":is_owner,"is_admin_or_teacher":is_admin_or_teacher}
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
            return render(request, 'orgs/partials/delete_root_org_verify_otp.html', {"root_org_name":root_org.name,**kwargs})             
        otp = generate_numeric_otp(length=6)
        hash = make_password(otp,salt=str(request.user.last_login))
        cache.set(
            key=key,
            value={
                "hash":hash,
                "attempts":0
            },
            timeout=EMAIL_EXPIRY_DURATION
        )
        owner = root_org.config.owner
        send_email(
            email_template_name="orgs/delete_root_org_otp_email.txt",
            html_email_template_name="orgs/delete_root_org_otp_email.html",
            subject=f"Request for Deletion: {root_org.name}",
            receiver=[owner.email],
            context={"otp":otp,"root_org_name":root_org.name,"user_full_name":owner.get_full_name()}
        )
        return render(request, 'orgs/partials/delete_root_org_verify_otp.html', {"root_org_name":root_org.name,**kwargs})        

class DeleteRootOrg(LoginRequiredMixin,TeacherRequiredMixin,OwnerRequired,View):
    def get(self,request,*args,**kwargs):
        """Show confirmation modal"""
        root_org = self.get_root_org()
        return render(request, 'orgs/partials/delete_root_org.html', {"root_org_name":root_org.name,**kwargs})

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
            cache.set(key=key,value=data,timeout=300)
            return  render_error_inside_modal(request=request,template_name='orgs/partials/delete_root_org_verify_otp.html',
                context={"root_org_name":root_org.name,**kwargs}
            )

class DeleteChildOrg(LoginRequiredMixin,TeacherRequiredMixin,OwnerAdminRequired,View):
    def get(self,request,*args,**kwargs):
        org = get_object_or_404(Organization,pk=kwargs['org_id'])
        return render(request, 'orgs/partials/delete_child_org.html', {"org_name":org.name,**kwargs})

    def post(self,request,*args,**kwargs):
        org = get_object_or_404(Organization,pk=kwargs['org_id'])
        org.delete()
        return HttpResponse("", status=200)

class ViewOrgDetails(LoginRequiredMixin,TeacherRequiredMixin,OrgMembershipRequiredMixin,View):
    template_name = 'orgs/partials/view_org_details.html'
    def get(self,request,*args,**kwargs):
        org = get_object_or_404(Organization,pk=kwargs['org_id'])
        return render(request,self.template_name,{'org':org})

class RevokeOrgMembership(LoginRequiredMixin,TeacherRequiredMixin,OwnerAdminRequired,View):
    def get(self,request,*args, **kwargs):
        first_name, last_name = get_object_or_404(
            User.objects.values_list("first_name", "last_name"), # Return first_name and last_name inside a tuple, rather than whole user instance.
            pk=kwargs["teacher_id"], 
        )
        teacher_name = f"{first_name} {last_name}"
        return render(request,template_name="orgs/partials/revoke_org_membership.html",context={**kwargs,"teacher_name":teacher_name})

    
    def post(self,request,*args, **kwargs):
        root_org = self.get_root_org()
        # In DB, a ForeignKey field like teacher is stored as a teacher_id column containing the primary key of the related User,
        #  so in OrgMembership table we have something like org_id, teacher_id
        mem_obj = get_object_or_404(OrgMembership,teacher_id = kwargs['teacher_id'],org = root_org) 
        mem_obj.delete()
        return HttpResponse("", status=200)

class RevokeOrgAdmin(LoginRequiredMixin,TeacherRequiredMixin,OwnerRequired,View):
    def get(self, request, *args, **kwargs):
        first_name, last_name = get_object_or_404(
            User.objects.values_list('first_name','last_name'),
            pk=kwargs['admin_id']
        )
        admin_name = f"{first_name} {last_name}"
        return render(request,"orgs/partials/revoke_org_admin.html",{**kwargs,"admin_name":admin_name})

    def post(self,request,*args, **kwargs):
        root_org = self.get_root_org()
        admin_obj = get_object_or_404(
            OrgAdmin,
            membership__teacher_id=kwargs["admin_id"],
            membership__org=root_org,
        )
        admin_obj.delete()
        return HttpResponse("", status=200)

class RenameOrg(LoginRequiredMixin,TeacherRequiredMixin,OwnerAdminRequired,View):
    form_class = OrgNameForm
    template_name = "orgs/partials/rename_org.html"
    def get(self,request, *args, **kwargs):
        org = get_object_or_404(Organization,pk=kwargs['org_id'])
        form  = self.form_class(initial={'name':org.name})
        if self.get_root_org() == org:
            context = {**kwargs,"form":form, "root_org_view":True,}
        else:
            context = {**kwargs,"form":form,"child_org_view":True}
        return render(request,self.template_name,context)

    def post(self, request, *args, **kwargs):
        org = get_object_or_404(Organization,pk=kwargs['org_id'])
        form = self.form_class(request.POST)
        if not form.is_valid():
            return render_error_inside_modal(request=request,template_name=self.template_name,context={
                **kwargs,"form":form
            })
        parent_org_path = kwargs.get('parent_org_path')
        is_root = False
        if not parent_org_path:
            if self.get_root_org() != org:
                return create_message_and_redirect(request,"Invalid rename request","users-dashboard","error",)
            is_root = True
        if is_root and self.role != 'Owner':
            return create_message_and_redirect(request,"Only Owners can rename root organizations","users-dashboard","error",) 

        org.name = form.cleaned_data['name']

        try:
            if is_root:
                validate_rename_org(instance=org)
            else:
                validate_rename_org(instance=org, parent=org.get_parent())
        except ValidationError as e:
            form.add_error(field=None,error=e.message)
            return render_error_inside_modal(request=request,template_name=self.template_name,context={
                **kwargs,"form":form,"root_org_view":is_root, "child_org_view":not(is_root)
            })        
        org.save()
        
        if is_root:
            row_context = {
            "org":build_slug(instance=org,parent_org_path=parent_org_path,role=UserRole.OWNER),"parent_org_path":parent_org_path,
            "root_org_view":True,
            }
        else:
            row_context = {
            "org":build_slug(instance=org,parent_org_path=parent_org_path),"parent_org_path":parent_org_path,
            "child_org_view": True, 'role': self.role
            }            
        response = render(request, "orgs/view_orgs_and_classrooms.html#org-row",row_context)
        response['HX-Trigger'] = 'org-renamed'
        return response