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
