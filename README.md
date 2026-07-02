# Gurukul

## To start the application run each command in different terminal

```Python

python manage.py runserver
pyhton manage.py tailwind start # Start tailwind wacther
celery -A config worker -P threads -E -l info # Celery worker
```

## To check for updates for tailwind npm packages and update them use

```Python
python manage.py tailwind check-updates
python manage.py tailwind update
```
