# Gurukul

## To start the application run each command in different terminal

```Python
# django
python manage.py runserver

# Start tailwind watcher
python manage.py tailwind start 

# Celery worker
celery -A config worker -P threads -E -l info

# Start Celery Beat
celery -A config beat -l INFO 
```

### To check for updates for tailwind npm packages and update them use

```Python
python manage.py tailwind check-updates
python manage.py tailwind update
```

## Problems Solved

* Custom User Model, User Manager
* Used django TreeBeard for Organization stucture to avoid recursive lookups
* Email Change using Cryptographic signing and redis
* Social Auth Custom pipeline for user_type
* Used HTMX for AJAX (making POST requests without reload).
* Added celery to send async emails
* Change from bootstrap to  tailwind CDN to django_tailwind for responsive designs
* Use Alpine for frontend UI
* Render a new form using hx-get on button click and submit it using hx-post.
* Created a cron-job that deletes the expired invitations using django-celery-beat.

## Workings

### Login

Right now the user can register himself and login using the credentials. If an existing user with credentials use o-auth, then his account will automatically be linked with the account with credentials. Then he can use o-auth directly to login.

### Register Email

User enters an email, we will check if it is already taken if not we will save the (email + inc_TTL(bool)) inside Redis with a 5 min TTL. Then we will create a a secret token and sent it to the user email. We are using celery for sending email asynchronously. When user clicks the link, we will check if the value exists in the cache and increase the TTL to 15 minutes and  then `set inc_TTL = True` rendering the rest of the register form. When user sends the POST request we again check if the cache exist and if it does we take the email from redis and attach it to the instance and create the user.

### Change Email

The working is very similar to how django implement forgot password. We will render the profile form that will also contain the email. If the POST request does not contain the email field we will not do anything but if it does we will save the old email for now and save the new email in redis. Now we will use the user_id and convert it to base64 and use `TimestampSigner` to sign and send it to the user's new email. This is because if the user clicks on the link again it will be automatically invalidated since the salt is now the new email. When the user clicks the link we will extract the give user id and try to unsign the string with the extracted user's current email. If the link has been tampered with, we will get a error during unsign. If this all was successful we will get the new email from the redis and update. We have to check for race conditions, if in between user created an account with this email. We then delete the key from the cache and logout him from all devices.

### Form Rendering inside a page (replacing the form in place)

The create-child-org button is clicked and a hx-get request to the form url. The form is rendered on the start of the main-list. The form has been rendered with autofocus ON at the start(afterbegin) of main-list. When the form is submitted it will make a hx-post request to the view. If there are any errors, the form will be re-rendered along with the errors. If the form has no errors the view will return a newly created organization. The form will be replaced by this new organization using hx-swap. Finally add  apline's `@click.outside="$el.remove()"` to remove the form. To stop the user from making hx-get when the form is already rendered on the page, create a new `x-data = "formOpen = false"` variable and when the button is clicked, change it to true and disable the button and when user clicks outside the form enable the button. Use this for all forms rendered on the page. If there is any form on the page the user cannot press any button.

### Form Rendering inside a page (in a modal)

Create a empty modal at the end of the page. Click a button which will make a hx-get request to the view. The view will return a form that will be rendered inside the modal. The user will fill the form, if there are any errors the form will be re-rendered on the modal. If there are no errors the #main-list will get updated with the newly created org. To handle different hx-target based on whether the forms has errors we will use `error_response['HX-Retarget'] = '#modal_form_container'` and `error_response['HX-Reswap'] = 'innerHTML'`. We will remove the form after the modal is closed everytime using `x-data @close="modal_form_container.innerHTML = '';"` and a new get request will be each time the modal is opened. To handle the successful POST request and close the modal we will trigger the success using `success_response['HX-Trigger'] = 'root-org-created'` and in the modal we will listen to it and close the modal `@root-org-created="$el.close();"`. To show the errors outside the modal we have used `hx-swap-oob="true"` to update #message-container (another part of DOM) in a single POST request apart from the default `hx-target` element. This wasy error were behind the dialog and sicne dialog is the top element we cannot push them back. then we decided to show the errors inside the modal by leaving some pre-allocatted space at the bottom for errors using `h-15`, not the most effcient soln but will be okay for now.

> We have create the form_errors as a partial so that it can be used with different form names because sometimes we have more than 1 form in a single tempalte and all cannot be called `form`. So we can use `{% include "partials/form_errors.html#form-errors" with form=root_form %}`.

### Authorization

Current authorization allows the user to access any part of an organization if he has access to the root organization. But he can only add teachers or admin if he is the owner or an admin. User can create a classroom if he is a member of the organization and a teacher. Here member means owner, admin and teacher.

### Delete Invitations

Added `django-celery-beat` and then migrate. Defined a cron job and attached the given task(delete_expired_invitations) to it using the admin panel.

## Rules

* Classes cannot co-exist with organization. They must be present at the leaf node.

## To do list

* Handle messages and errors in smaller screens.

## Pending decisons

* Decide whether to keep the bio, phone and DOB. Since this is not a social website we will not need show profiles of user. We may add a chat feature for teachers in a organization. For that we will need a username. Even if chat is added we dont need to show bio, phone and DOB.

* To remove title from individual pages, since we have to update the title in every htmx request seperately. We can just use **Gurukul** as a title for every page.

* Should the password reset form use celery to send emails?

## Remember

* Use the custom CSS attributes such as form-label, form-input, base-button, hyperlink, bordered card and page-container.

* During a htmx POST request and returning the partial from the backend view that includes form, form.errors and some messages (success or business logic) only, you have to include both the form-erorrs and message partails in the container that is being swapped in the POST request. Refer: profile.html

* Use `class="page-container" id="page-container"`, since we are swapping the page-container for HTMX get requests on each page, to move between different pages partials. Make sure the view render both the reload and request.htmx. Always push URL to change the URL.

* We have to render both request.htmx and request(if the user directly access the page).

* Model.objects.create save the object in the DB, use Model(kwargs) to create instance, then full_clean() and then save.
