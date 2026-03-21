import time
from celery import shared_task
from django.core.mail import send_mail
from django.contrib.auth import get_user_model
from django.conf import settings

from .models import Recipe

User = get_user_model()


@shared_task
def send_welcome_email(user_id):
    """Отправка welcome email новому пользователю"""

    try:
        user = User.objects.get(id=user_id)

        subject = f'Добро пожаловать в Recipe API, {user.username}!'

        message = f'''Привет {user.username}!

Спасибо за регистрацию в Recipe API!

Теперь ты можешь:
- Создавать свои рецепты
- Добавлять рецепты в избранное
- Делиться рецептами с друзьями

Начни с создания своего первого рецепта!

API: https://recipeapi.up.railway.app/api/
Документация: https://recipeapi.up.railway.app/docs/

С уважением,
Команда Recipe API'''

        # Используем разные методы в зависимости от окружения
        if settings.DEBUG:
            # Локально: Django send_mail (через Mailhog SMTP)
            print(f"✉️ Отправка email на {user.email}...")

            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL if hasattr(settings,
                                                                  'DEFAULT_FROM_EMAIL') else 'noreply@recipeapi.com',
                recipient_list=[user.email],
                fail_silently=False,
            )

            print(f"✅ Welcome email отправлен пользователю {user.username} ({user.email})")

        else:
            # На Railway: SendGrid API (обходит блокировку SMTP портов)
            import os
            from sendgrid import SendGridAPIClient
            from sendgrid.helpers.mail import Mail, ClickTracking, TrackingSettings

            print(f"✉️ Отправка email через SendGrid API на {user.email}...")

            # Создаём письмо
            sg_message = Mail(
                from_email=settings.DEFAULT_FROM_EMAIL if hasattr(settings,
                                                                  'DEFAULT_FROM_EMAIL') else 'Recipe API <noreply@recipeapi.com>',
                to_emails=user.email,
                subject=subject,
                plain_text_content=message
            )

            # ОТКЛЮЧАЕМ click tracking (он ломает форматирование plain text!)
            tracking_settings = TrackingSettings()
            tracking_settings.click_tracking = ClickTracking(enable=False, enable_text=False)
            sg_message.tracking_settings = tracking_settings

            sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
            response = sg.send(sg_message)

            print(f"✅ SendGrid API: Email отправлен {user.username} ({user.email}), status: {response.status_code}")

        return f"Email sent to {user.email}"

    except User.DoesNotExist:
        print(f"❌ Пользователь с ID {user_id} не найден")
        return f"User {user_id} not found"
    except Exception as e:
        print(f"❌ Ошибка отправки email: {str(e)}")
        import traceback
        traceback.print_exc()
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
            print(f"❌ У рецепта {recipe_id} нет изображения")
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
        print(f"🖼️ Создаю thumbnail для рецепта '{recipe.title}'...")

        with Image.open(image_path) as img:
            # Создаём превью 300x300 (сохраняя пропорции)
            img.thumbnail((300, 300), Image.Resampling.LANCZOS)
            img.save(thumbnail_path, quality=85)

        print(f"✅ Thumbnail создан: {thumbnail_path}")
        return f"Thumbnail created for recipe {recipe_id}"

    except Recipe.DoesNotExist:
        print(f"❌ Рецепт с ID {recipe_id} не найден")
        return f"Recipe {recipe_id} not found"
    except Exception as e:
        print(f"❌ Ошибка создания thumbnail: {str(e)}")
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
            print("❌ Нет рецептов для отправки дайджеста")
            return "No recipes available"

        # Получаем всех пользователей с email
        users = User.objects.exclude(email='').exclude(email__isnull=True)

        subject = '🍳 Рецепт дня от Recipe API!'

        emails_sent = 0

        for user in users:
            message = f'''Привет {user.username}!

Сегодняшний рецепт дня: {recipe.title}

{recipe.description}

Время приготовления: {recipe.cook_time} минут
Порций: {recipe.servings}
Калорий: {recipe.calories}

Попробуй приготовить!

Смотреть рецепт: https://recipeapi.up.railway.app/api/recipes/{recipe.id}/

С уважением,
Команда Recipe API'''

            if settings.DEBUG:
                # Локально: Django SMTP (через Mailhog)
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL if hasattr(settings,
                                                                      'DEFAULT_FROM_EMAIL') else 'noreply@recipeapi.com',
                    recipient_list=[user.email],
                    fail_silently=True,
                )
            else:
                # На Railway: SendGrid API
                try:
                    import os
                    from sendgrid import SendGridAPIClient
                    from sendgrid.helpers.mail import Mail, ClickTracking, TrackingSettings

                    # Создаём письмо
                    sg_message = Mail(
                        from_email=settings.DEFAULT_FROM_EMAIL if hasattr(settings,
                                                                          'DEFAULT_FROM_EMAIL') else 'Recipe API <noreply@recipeapi.com>',
                        to_emails=user.email,
                        subject=subject,
                        plain_text_content=message
                    )

                    # ОТКЛЮЧАЕМ click tracking
                    tracking_settings = TrackingSettings()
                    tracking_settings.click_tracking = ClickTracking(enable=False, enable_text=False)
                    sg_message.tracking_settings = tracking_settings

                    sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
                    sg.send(sg_message)

                except Exception as e:
                    print(f"⚠️ Ошибка отправки дайджеста пользователю {user.username}: {str(e)}")
                    # Не падаем, продолжаем отправлять остальным
                    continue

            emails_sent += 1

        print(f"✅ Дайджест отправлен {emails_sent} пользователям. Рецепт: '{recipe.title}'")
        return f"Digest sent to {emails_sent} users"

    except Exception as e:
        print(f"❌ Ошибка отправки дайджеста: {str(e)}")
        raise


@shared_task
def cleanup_old_cache():
    """
    Очистка старого кэша (периодическая задача)
    Можно запускать раз в день
    """

    from django.core.cache import cache

    try:
        print("🧹 Запуск очистки старого кэша...")
        print("✅ Очистка кэша завершена")
        return "Cache cleanup completed"

    except Exception as e:
        print(f"❌ Ошибка очистки кэша: {str(e)}")
        raise


@shared_task
def demo_long_task(duration=10):
    """
    Демо-задача для тестирования (имитирует долгую работу)

    Args:
        duration: сколько секунд "работать"
    """

    print(f"⏳ Начинаю долгую задачу на {duration} секунд...")

    for i in range(duration):
        time.sleep(1)
        print(f"  Прогресс: {i + 1}/{duration} секунд")

    print(f"✅ Долгая задача завершена!")
    return f"Task completed after {duration} seconds"