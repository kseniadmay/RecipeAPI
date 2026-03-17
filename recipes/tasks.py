import time
from celery import shared_task
from django.core.mail import send_mail
from django.contrib.auth import get_user_model
from django.conf import settings

from .models import Recipe


User = get_user_model()


@shared_task
def send_welcome_email(user_id):
    """Отправление приветственного письма новому пользователю"""

    try:
        user = User.objects.get(id=user_id)

        subject = f'Добро пожаловать в Recipe API, {user.username}!'
        message = f"""
Привет, {user.username}!

Спасибо за регистрацию в Recipe API!

Теперь ты можешь:
- Создавать свои рецепты
- Добавлять рецепты в избранное
- Делиться рецептами с друзьями

Начни с создания своего первого рецепта!

API: http://localhost:8000/api/
Документация: http://localhost:8000/docs/

С уважением,
Команда Recipe API
        """

        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL if hasattr(settings,
                                                              'DEFAULT_FROM_EMAIL') else 'noreply@recipeapi.com',
            recipient_list=[user.email],
            fail_silently=False,
        )

        print(f"Приветствие отправлено пользователю {user.username} ({user.email})")
        return f"Email sent to {user.email}"

    except User.DoesNotExist:
        print(f"Пользователь с ID {user_id} не найден")
        return f"User {user_id} not found"
    except Exception as e:
        print(f"Ошибка отправки email: {str(e)}")
        raise


@shared_task
def generate_recipe_thumbnail(recipe_id):
    """
    Генерация превью изображения для рецепта

    Args:
        recipe_id: ID рецепта

    """

    try:
        from PIL import Image
        import os

        recipe = Recipe.objects.get(id=recipe_id)

        # Проверяем, что у рецепта есть изображение
        if not recipe.image:
            print(f"У рецепта {recipe_id} нет изображения")
            return f"Recipe {recipe_id} has no image"

        # Путь к оригинальному изображению
        image_path = recipe.image.path

        # Создаём директорию для thumbnails если её нет
        thumbnail_dir = os.path.join(settings.MEDIA_ROOT, 'thumbnails')
        os.makedirs(thumbnail_dir, exist_ok=True)

        # Путь для thumbnail
        thumbnail_filename = f"thumb_{os.path.basename(image_path)}"
        thumbnail_path = os.path.join(thumbnail_dir, thumbnail_filename)

        # Открываем изображение и создаём превью
        print(f"Создаю thumbnail для рецепта '{recipe.title}'...")

        with Image.open(image_path) as img:
            # Создаём превью 300x300 (сохраняя пропорции)
            img.thumbnail((300, 300), Image.Resampling.LANCZOS)
            img.save(thumbnail_path, quality=85)

        print(f"Thumbnail создан: {thumbnail_path}")
        return f"Thumbnail created for recipe {recipe_id}"

    except Recipe.DoesNotExist:
        print(f"Рецепт с ID {recipe_id} не найден")
        return f"Recipe {recipe_id} not found"
    except Exception as e:
        print(f"Ошибка создания thumbnail: {str(e)}")
        raise


@shared_task
def send_daily_recipe_digest():
    """
    Отправка ежедневного дайджеста со случайным рецептом
    всем пользователям (периодическая задача)
    """

    try:
        # Получаем случайный рецепт
        recipe = Recipe.objects.order_by('?').first()

        if not recipe:
            print("Нет рецептов для отправки дайджеста")
            return "No recipes available"

        # Получаем всех пользователей с email
        users = User.objects.exclude(email='').exclude(email__isnull=True)

        subject = '🍳 Рецепт дня от Recipe API!'

        emails_sent = 0
        for user in users:
            message = f"""
Привет {user.username}!

Сегодняшний рецепт дня: {recipe.title}

{recipe.description}

Время приготовления: {recipe.cook_time} минут
Порций: {recipe.servings}
Калорий: {recipe.calories}

Попробуй приготовить!

Смотреть рецепт: http://localhost:8000/api/recipes/{recipe.id}/

С уважением,
Команда Recipe API
            """

            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL if hasattr(settings,
                                                                  'DEFAULT_FROM_EMAIL') else 'noreply@recipeapi.com',
                recipient_list=[user.email],
                fail_silently=True,
            )
            emails_sent += 1

        print(f"Дайджест отправлен {emails_sent} пользователям. Рецепт: '{recipe.title}'")
        return f"Digest sent to {emails_sent} users"

    except Exception as e:
        print(f"Ошибка отправки дайджеста: {str(e)}")
        raise


@shared_task
def cleanup_old_cache():
    """
    Очистка старого кэша (периодическая задача)
    Можно запускать раз в день
    """

    from django.core.cache import cache

    try:
        # Пример: удаляем все ключи старше определённого времени
        # В реальности Redis сам удаляет по TTL
        print("🧹 Запуск очистки старого кэша...")

        # Здесь может быть логика очистки
        # Например, удаление неиспользуемых ключей

        print("Очистка кэша завершена")
        return "Cache cleanup completed"

    except Exception as e:
        print(f"Ошибка очистки кэша: {str(e)}")
        raise


@shared_task
def demo_long_task(duration=10):
    """
    Демо-задача для тестирования (имитирует долгую работу)

    Args:
        duration: сколько секунд "работать"
    """

    print(f"Начинаю долгую задачу на {duration} секунд...")

    for i in range(duration):
        time.sleep(1)
        print(f"  Прогресс: {i + 1}/{duration} секунд")

    print(f"Долгая задача завершена!")
    return f"Task completed after {duration} seconds"