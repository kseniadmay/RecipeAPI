import pytest
from rest_framework.test import APIClient
from django.contrib.auth.models import User


@pytest.fixture
def api_client():
    """API клиент для тестов"""

    return APIClient()

@pytest.fixture
def user():
    """Создание тестового пользователя"""

    return User.objects.create_user(username='testuser', email='test@example.com', password='testpass123')

@pytest.fixture
def authenticated_client(api_client, user):
    """API клиент с авторизацией"""

    api_client.force_authenticate(user=user)
    return api_client