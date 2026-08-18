# Organizations

## Workings

### Form Rendering inside a page (replacing the form in place)

The create-child-org button is clicked and a hx-get request to the form url. The form is rendered on the start of the main-list. The form has been rendered with autofocus ON at the start(afterbegin) of main-list. When the form is submitted it will make a hx-post request to the view. If there are any errors, the form will be re-rendered along with the errors. If the form has no errors the view will return a newly created organization. The form will be replaced by this new organization using hx-swap. Finally add  apline's `@click.outside="$el.remove()"` to remove the form. To stop the user from making hx-get when the form is already rendered on the page, create a new `x-data = "formOpen = false"` variable and when the button is clicked, change it to true and disable the button and when user clicks outside the form enable the button. Use this for all forms rendered on the page. If there is any form on the page the user cannot press any button.

### Form Rendering inside a page (in a modal)

Create a empty modal at the end of the page. Click a button which will make a hx-get request to the view. The view will return a form that will be rendered inside the modal. The user will fill the form, if there are any errors the form will be re-rendered on the modal. If there are no errors the #main-list will get updated with the newly created org. To handle different hx-target based on whether the forms has errors we will use `error_response['HX-Retarget'] = '#modal_form_container'` and `error_response['HX-Reswap'] = 'innerHTML'`. We will remove the form after the modal is closed everytime using `x-data @close="modal_form_container.innerHTML = '';"` and a new get request will be each time the modal is opened. To handle the successful POST request and close the modal we will trigger the success using `success_response['HX-Trigger'] = 'root-org-created'` and in the modal we will listen to it and close the modal `@root-org-created="$el.close();"`. To show the errors outside the modal we have used `hx-swap-oob="true"` to update #message-container (another part of DOM) in a single POST request apart from the default `hx-target` element. This wasy error were behind the dialog and sicne dialog is the top element we cannot push them back. then we decided to show the errors inside the modal by leaving some pre-allocatted space at the bottom for errors using `h-15`, not the most effcient soln but will be okay for now.

> We have create the form_errors as a partial so that it can be used with different form names because sometimes we have more than 1 form in a single tempalte and all cannot be called `form`. So we can use `{% include "partials/form_errors.html#form-errors" with form=root_form %}`.

### Authorization

Current authorization allows the user to access any part of an organization if he has access to the root organization. But he can only add teachers or admin if he is the owner or an admin. User can create a classroom if he is a member of the organization and a teacher. Here member means owner, admin and teacher.

### Delete Invitations

Added `django-celery-beat` and then migrate. Defined a cron job and attached the given task(delete_expired_invitations) to it using the admin panel.

> Most of the organization views requires the root org_id, therefore after extracting the root_id from given current org_id using `self.get_root_org` defined in RootOrganization mixin (Both Permission mixin inherits from this), we send the root_id to the frontend. There will be no less but the lookup will be fast as compared to going down the tree.

### Scrollbar

Inside `base.html` we have `min-h-screen md:h-dvh`. For devices larger than `md`, `h-dvh` sets a strict, explicit height that dynamically adjusts with the browser's viewport (for example, when the mobile address bar expands or collapses). Because the height is fixed to the viewport, the scrollable area can sometimes become very small, making the scrollbar frustrating to use on smaller screens.

This is where `min-h-screen` helps. It sets a static minimum height equal to the viewport, ensuring the element is at least the height of the screen while still allowing it to grow if its content overflows in smaller devices.

For scrollable containers, however, you should define an explicit height (for example, `h-[200px]`) to create a predictable scroll area. This ensures the scrollbar has enough space to be usable.

To make a div scrollable add `flex-auto min-h-0` to each parent and add `overflow-y-auto flex-auto min-h-0` to the div that should be scrollable.

### Delete Child Organization

When the user selects the delete button from the dropdown, send a GET request to show the modal. If pressed yes, hx-target="#org{{ org_id }}" hx-swap="delete" and return HttpResponse("",status=200). This will delete the organization from the frontend.

### Delete Root Organization

When the owner clicks the delete button and we show a confirmation. IF pressed Yes, we send a POST request to /verify-otp that generates a 6 digits numeric OTP using `secrets`. This OTP's hash is created using the make_password from `django.contrib.auth.hashers` with the salt = user's last login. We save the hash and attempts in redis with 15 minutes TTL and send the email to the user. the delete-root-org GET request shows the confirmation modal and it's POST request handles the OTP submission. We check if the OTP does not expire, if not we use `check_password` to verify the OTP. If incorrect `data['attampts] += 1`. Max attempts are 3 and then redirect.

> There should be a cooldown period that will be implemented later like one user can have 3 emails sent to him in an hour to do a specific task.

### Transfer Ownership

We will show the owner the list of admins in which he can select an admin. We will verify the operation using OTP first. After verification the previous owner will be demoted to admin and the selected admin will be promoted to owner.

### Show Invitation Count

DaisyUI came in clutch with the `indicator` class, we will hx-trigger="every 60s" to fetch the number of invitations pending.

### Rename Org

Open the prefilled form inside the modal and perform validations. If failed re-render the form inside the modal.

## To do

* Add Rename to orgs and classrooms.

* Change `org_path` to `parent_org_path` and `org_id` to `parent_org_id`. Some `org_id` remain `org_id`, only those of parent will change.

* In several views we could get specific attributes from the object instead of the whole instance.

## Remember

* Inside the database, a `ForeignKey` field is stored as the primary key of the related model in the table of the model that defines the foreign key. For example, the `OrgMembership` model has two foreign key fields: `org` and `teacher`. In the `OrgMembership` table, these are stored as `org_id` and `teacher_id`, which contain the primary keys (`id`) of the corresponding `Organization` and `User` records.

This is why filtering with `teacher_id=5` is more direct than `teacher__id=5`: the `teacher_id` value already exists in the `OrgMembership` table, so Django can filter on that column without traversing the relationship using joins.

* @click, x-show, x-model, x-bind and all other Alpine dependent components will only work if one of the ancestors contain x-data.
