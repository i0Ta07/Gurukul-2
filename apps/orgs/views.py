
from apps.orgs.mixins import TeacherRequiredMixin,OrgMembershipRequiredMixin,OwnerAdminRequired
from django.views import View
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render,get_object_or_404
from apps.orgs.models import OrgInvitation, Organization
from apps.users.models import User
from django.core.exceptions import ValidationError
from apps.orgs.forms import CreateChildOrgForm,CreateRootOrgForm,CreateOrgConfig,SendInvitation
from django.db import transaction
from config.utils import create_message_and_redirect
from apps.orgs.utils import (
    UserRole,
    validate_root_access,validate_child_org,validate_root_org,get_memberships,
    build_breadcrumbs,build_slug,resolve_org_path,get_emails_from_excel
    )

class ViewRootOrgs(LoginRequiredMixin, TeacherRequiredMixin,View):
    template_name = "orgs/list_orgs.html"

    def get(self, request, *args, **kwargs):
            created_orgs = Organization.get_root_nodes().filter(config__owner = request.user)
            memberships = get_memberships(user = request.user)
            orgs = [
                *(
                    {
                        "name": org.name,
                        "path": f"{org.slug}",
                        "role": UserRole.OWNER.value,
                    }
                    for org in created_orgs
                ),
                *(
                    {
                        "name": membership.org.name,
                        "path": f"{membership.org.slug}",
                        "role": UserRole.ADMIN.value if membership.has_admin else UserRole.TEACHER.value,
                    }
                    for membership in memberships
                ),
            ]
            context = {"orgs": orgs,"root_org_view":True}
            if request.htmx:
                    return render(request, "orgs/list_orgs.html#view-org",context)
            return render(request, self.template_name, context)

# should only show the TLD orgs the user has created
class ViewChildOrgs(LoginRequiredMixin, TeacherRequiredMixin, View):
    template_name = "orgs/list_orgs.html"

    def get(self, request, *args, **kwargs):
        org_path = kwargs.get("org_path")
        slugs = [slug for slug in org_path.strip("/").split("/") if slug]
        root_node = get_object_or_404(Organization.get_root_nodes(), slug = slugs[0]) # Get root node
        org_role = validate_root_access(root = root_node,user= request.user) # Check if user has access to root node
        if org_role:            
            current_node = resolve_org_path(root_node =root_node,slugs=slugs)
            children = current_node.get_children().order_by("name")
            template = root_node.config.template()
            current_depth = current_node.get_depth()
            if template:
                node_label = template[current_depth -1]
            else:
                node_label = "Organization"
            classrooms = current_node.classrooms.order_by('name')
            context = {
                "org_role":org_role,
                "orgs":build_slug(children,org_path),
                "classrooms":build_slug(classrooms,org_path),
                "current_org_name": current_node.name,
                "current_org_id": current_node.id,
                "current_org_path":org_path,
                "breadcrumbs": build_breadcrumbs(org_path), 
                "child_org_view": not classrooms.exists() and current_depth != len(template),
                "classroom_view": not children.exists()  and current_depth  == len(template),
                "node_label":node_label,
            }
            if request.htmx:
                return render(request, "orgs/list_orgs.html#view-org",context)
                
            return render(request, self.template_name, context)
        return create_message_and_redirect(request,message="You are not part of this organization",url="users-dashboard",code="error")


class CreateChildOrg(LoginRequiredMixin,TeacherRequiredMixin,OrgMembershipRequiredMixin,View):
    template_name = "orgs/partials/create_child_org.html"
    form_class = CreateChildOrgForm

    def get(self,request, *args, **kwargs):
        form = self.form_class()
        return render(request, self.template_name, {"form":form,"org_id":kwargs['org_id'],"org_path":kwargs['org_path']})

    
    def post(self, request, *args, **kwargs):
        parent_id = kwargs['org_id']
        parent_path = kwargs['org_path']

        parent = get_object_or_404(Organization, pk=parent_id)

        # Load post data into the form
        form = self.form_class(request.POST)
        form_context = {"form":form,"org_id":kwargs['org_id'],"org_path":kwargs['org_path']}
        if not form.is_valid():
            return render(request, self.template_name,form_context)
        org = form.save(commit=False)
        org.created_by = request.user
        try:
            validate_child_org(parent_node = parent, instance=org)
        except ValidationError as e:
            form.add_error(field=None,error=e.message)
            return render(request, self.template_name,form_context)
        parent.add_child(instance=org)
        path = f"{parent_path}/{org.slug}" if parent_path else org.slug
        row_context = {
            "org":{ "name":org.name,"path":path}
        }
        messages.success(request,message="Organization created successfully.")
        response = render(request, "orgs/list_orgs.html#org-row",row_context)
        response['HX-Trigger'] = 'child-org-created'
        return response

class CreateRootOrgAndConfig(LoginRequiredMixin,TeacherRequiredMixin,View):
    template_name = "orgs/partials/create_root_and_config_org.html"
    root_form = CreateRootOrgForm
    config_form = CreateOrgConfig

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
        
        org = root_form.save(commit=False)
        org.created_by = request.user

        try:
            validate_root_org(instance=org)
        except ValidationError as e:
            root_form.add_error(field=None,error=e.message)
            return render_error()
        
        org_config = config_form.save(commit=False)
        org_config.org = org
        org_config.owner = request.user

        with transaction.atomic(): # either both root and config are created or none
            Organization.add_root(instance = org)
            org_config.save()

        messages.success(request,"Organization created successfully")
        response = render(request,"orgs/list_orgs.html#org-row", {
            "org":{"name":org.name, "path":f"{org.slug}","role":UserRole.OWNER.value},
            "root_org_view":True,
            }
        )
        response['HX-Trigger'] = 'root-org-created'
        return response

class SendInvitations(LoginRequiredMixin,TeacherRequiredMixin,OwnerAdminRequired,View):
    template_name = "orgs/send_invitations.html"
    form_class = SendInvitation

    def get(self,request,*args, **kwargs):
        form = self.form_class()
        context = {'form':form,"org_id":kwargs['org_id']}
        if request.htmx:
            return render(request,template_name="orgs/send_invitations.html#send-invitations",context=context)
        return render(request,template_name=self.template_name,context=context)       

    def post(self,request, *args, **kwargs):
        form = self.form_class(request.POST, request.FILES)
        if not form.is_valid():
            return render(request,template_name="orgs/send_invitations.html#send-invitations",context={'form':form,"org_id":kwargs['org_id']})
        # If email is provided
        email = form.cleaned_data['email']
        org_id = kwargs['org_id']
        org = Organization.objects.get(pk= org_id).get_root()
        if email:
            try:
                user = User.objects.get(email = email)
            except User.DoesNotExist:
                form.add_error("email","No such user exists. Kindly recheck the email.")
                return render(request,template_name="orgs/send_invitations.html#send-invitations",context={'form':form,"org_id":kwargs['org_id']})
            invitation = OrgInvitation(to_user=user,from_user=request.user,org=org,)
            try:
                invitation.full_clean()   
                invitation.save()
            except ValidationError as e:
                form.add_error(None,e)
                return render(request,template_name="orgs/send_invitations.html#send-invitations",context={'form':form,"org_id":kwargs['org_id']})

            messages.success(request,"Request sent successfully")
            # Render a fresh form
            return render(request,template_name="orgs/send_invitations.html#send-invitations",context={'form':self.form_class(),"org_id":kwargs['org_id']})
        else:
            file =  form.cleaned_data['file']
            data = get_emails_from_excel(file)
            response = render(request,template_name="orgs/send_invitations.html#render-emails-from-files",context={"data":data,"org_id":kwargs['org_id']})
            response['HX-Retarget'] = '#file_email_container'
            return response

class SendBulkInvitations(LoginRequiredMixin,TeacherRequiredMixin,OwnerAdminRequired,View):
    def post(self,request, *args, **kwargs):
        org = Organization.objects.get(pk=  kwargs['org_id']).get_root()        
        email_ids = set(request.POST.getlist("emails"))
        users = (
            User.objects
            .filter(email__in=email_ids)
            .exclude(pk=request.user.pk) # 1. user is not inviting himself.
            .exclude(org_membership__org=org) # 2. requested user are not part of the org.
            .exclude(received_invitation__org=org) # 3. If there is already an invitation
            .distinct()
        )
        created_invitations = OrgInvitation.objects.bulk_create(
            [
                OrgInvitation(
                    to_user=user,
                    from_user=request.user,
                    org=org,
                )
                for user in users
            ],
            ignore_conflicts=True,
        )
        messages.success(request,f"Sent {len(created_invitations)} invitations.")
        return render(request,template_name="orgs/send_invitations.html#send-invitations",context={'form':SendInvitation(),"org_id":kwargs['org_id']})

        