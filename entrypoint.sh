#!/bin/sh

# Собираем статику
python manage.py collectstatic --noinput

# Запускаем Gunicorn
exec gunicorn RecipeAPI.wsgi:application --bind 0.0.0.0:8000