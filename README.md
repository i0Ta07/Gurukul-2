# Gurukul

## To start the application run each command in different terminal

```Python

python manage.py runserver

# Start tailwind wacther
python manage.py tailwind start 

# Celery worker
celery -A config worker -P threads -E -l info 
```

## To check for updates for tailwind npm packages and update them use

```Python
python manage.py tailwind check-updates
python manage.py tailwind update
```
