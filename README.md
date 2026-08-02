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

## Rules

* Classes cannot co-exist with organization. They must be present at the leaf node.

* Root Organizations can be deleted by owner after OTP authentication.

## To do list

* Handle messages and errors in smaller screens.

* Add guardrails to email like max 3 attempts, resend button and cooldown periods.

## Pending decisons

* Decide whether to keep the bio, phone and DOB. Since this is not a social website we will not need show profiles of user. We may add a chat feature for teachers in a organization. For that we will need a username. Even if chat is added we dont need to show bio, phone and DOB.

* To remove title from individual pages, since we have to update the title in every htmx request seperately. We can just use **Gurukul** as a title for every page.

* Should the password reset form use celery to send emails?

* There are repeated business checks inside the Model's clean methods that are already checked in the View. Should be removed?

## Remember

* Use the custom CSS attributes such as form-label, form-input, base-button, hyperlink, bordered card and page-container.

* During a htmx POST request and returning the partial from the backend view that includes form, form.errors and some messages (success or business logic) only, you have to include both the form-erorrs and message partails in the container that is being swapped in the POST request. Refer: profile.html

* Use `class="page-container" id="page-container"`, since we are swapping the page-container for HTMX get requests on each page, to move between different pages partials. Make sure the view render both the reload and request.htmx. Always push URL to change the URL.

* We have to render both request.htmx and request(if the user directly access the page).

* Model.objects.create save the object in the DB, use Model(kwargs) to create instance, then full_clean() and then save.

* No need to add `{% csrf_token %}` on **HTMX post requests**, since we added `<body hx-headers='{"x-csrftoken": "{{ csrf_token }}"}'>` inside our base.html, we only have specify csrf token on normal django POST forms. If you are adding a fallback method="post" method then you have to specify `{% csrf_token %}`.

## For Production

* Setup tailwind.

* Download alpine offline.

* Setup python-magic for linux in pyproject.toml.

* Set DEBUG = False and handle static directories.
