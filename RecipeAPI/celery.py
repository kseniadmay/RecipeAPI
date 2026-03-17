import os
from celery import Celery
from celery.schedules import crontab

# Устанавливаем переменную окружения для Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'RecipeAPI.settings')

# Создаём экземпляр Celery
app = Celery('RecipeAPI')

# Загружаем конфигурацию из Django settings
# namespace='CELERY' означает что все настройки Celery в settings.py 
# должны начинаться с 'CELERY_'
app.config_from_object('django.conf:settings', namespace='CELERY')

# Автоматически находим tasks.py в каждом приложении
app.autodiscover_tasks()

# Периодические задачи (расписание)
app.conf.beat_schedule = {
    # Отправка дайджеста каждый день в 10:00
    'send-daily-recipe-digest': {
        'task': 'recipes.tasks.send_daily_recipe_digest',
        'schedule': crontab(hour=10, minute=0),  # Каждый день в 10:00
    },
}

@app.task(bind=True)
def debug_task(self):
    """Тестовая задача для проверки"""

    print(f'Request: {self.request!r}')