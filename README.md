# Gurukul

## To start the application run each command in different terminal

```Python

python manage.py runserver

# Start tailwind watcher
python manage.py tailwind start 

# Celery worker
celery -A config worker -P threads -E -l info
```

## To check for updates for tailwind npm packages and update them use

```Python
python manage.py tailwind check-updates
python manage.py tailwind update
```

### Problems Solved

* Custom User Model, User Manager
* Used django TreeBeard for Organization stucture to avoid recursive lookups
* Email Change using Cryptographic signing and redis
* Social Auth Custom pipeline for user_type
* Used HTMX for AJAX (making POST requests without reload).
* Added celery to send async emails
* Change from bootstrap to  tailwind CDN to django_tailwind for responsive designs
* Use Alpine for frontend UI

### Pending decisons

* Decide whether to keep the bio, phone and DOB. Since this is not a social website we will not need show profiles of user. We may add a chat feature for teachers in a organization. For that we will need a username. Even if chat is added we dont need to show bio, phone and DOB.

* To remove title from individual pages, since we have to update the title in every htmx request seperately. We can just use **Gurukul** as a title for every page.

### Remember

* During a htmx POST request and returning the partial from the backend view that includes form, form.errors and some messages (success or business logic) only, you have to include both the form-erorrs and message partails in the container that is being swapped in the POST request. Refer: profile.html

* Use `class="page-container" id="page-container"`, since we are swapping the page-container for HTMX get on each page, to move between different pages partials. Make sure the view render both the reload and request.htmx. Always push URL to change the URL.
