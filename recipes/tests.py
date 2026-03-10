import pytest
from django.urls import reverse
from rest_framework import status

from .models import Recipe, Category, Favorite
from .factories import UserFactory, CategoryFactory, RecipeFactory, IngredientFactory, StepFactory


@pytest.mark.django_db
class TestRecipeAPI:
    """Тесты для API рецептов"""

    def test_list_recipes(self, api_client):
        """Тест получения списка рецептов"""

        RecipeFactory.create_batch(5)

        url = reverse('recipe-list')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 5

    def test_create_recipe_unauthorized(self, api_client):
        """Тест создания рецепта без авторизации"""

        url = reverse('recipe-list')
        data = {
            'title': 'Тестовый рецепт',
            'description': 'Описание',
            'cook_time': 30,
            'servings': 2,
            'difficulty': 'easy',
            'ingredients': [],
            'steps': []
        }

        response = api_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_recipe_authorized(self, authenticated_client):
        """Тест создания рецепта с авторизацией"""

        category = CategoryFactory()

        url = reverse('recipe-list')
        data = {
            'title': 'Бутерброд',
            'description': 'Вкусный бутерброд с колбаской',
            'category_id': category.id,
            'cook_time': 5,
            'servings': 1,
            'difficulty': 'easy',
            'ingredients': [
                {'name': 'Батон', 'amount': 2, 'unit': 'ломтик'},
                {'name': 'Колбаса', 'amount': 4, 'unit': 'ломтик'}
            ],
            'steps': [
                {'order': 1, 'description': 'Взять батон'},
                {'order': 2, 'description': 'Положить на него колбаску'}
            ]
        }

        response = authenticated_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['title'] == 'Бутерброд'
        assert len(response.data['ingredients']) == 2
        assert len(response.data['steps']) == 2

    def test_retrieve_recipe(self, api_client):
        """Тест получения детальной информации о рецепте"""

        recipe = RecipeFactory()
        IngredientFactory.create_batch(3, recipe=recipe)
        StepFactory.create_batch(2, recipe=recipe)

        url = reverse('recipe-detail', kwargs={'pk': recipe.pk})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == recipe.id
        assert response.data['title'] == recipe.title
        assert len(response.data['ingredients']) == 3
        assert len(response.data['steps']) == 2

    def test_update_recipe_by_author(self, api_client, user):
        """Тест обновления рецепта автором"""

        recipe = RecipeFactory(author=user)
        IngredientFactory(recipe=recipe, name='Яйца', amount=2, unit='шт')
        StepFactory(recipe=recipe, order=1, description='Жарить')

        api_client.force_authenticate(user=user)

        url = reverse('recipe-detail', kwargs={'pk': recipe.pk})
        data = {
            'title': 'Обновлённое название',
            'description': recipe.description,
            'cook_time': recipe.cook_time,
            'servings': recipe.servings,
            'difficulty': recipe.difficulty,
            'ingredients': [
            {'name': 'Яйца', 'amount': 3, 'unit': 'шт'}
        ],
        'steps': [
            {'order': 1, 'description': 'Жарить 10 минут'}
        ]
    }

        response = api_client.put(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['title'] == 'Обновлённое название'

    def test_update_recipe_by_other_user(self, api_client):
        """Тест редактирования чужого рецепта (должно быть запрещено)"""

        recipe = RecipeFactory()
        other_user = UserFactory()

        api_client.force_authenticate(user=other_user)

        url = reverse('recipe-detail', kwargs={'pk': recipe.pk})
        data = {'title': 'Попытка изменить'}

        response = api_client.patch(url, data, format='json')

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_delete_recipe_by_author(self, api_client, user):
        """Тест удаления рецепта автором"""

        recipe = RecipeFactory(author=user)

        api_client.force_authenticate(user=user)

        url = reverse('recipe-detail', kwargs={'pk': recipe.pk})
        response = api_client.delete(url)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Recipe.objects.filter(pk=recipe.pk).exists()

    def test_search_recipes(self, api_client):
        """Тест для поиска рецептов"""

        RecipeFactory(title='Салат с виноградом')
        RecipeFactory(title='Ризотто')
        RecipeFactory(title='Курица с картошкой в духовке')

        url = reverse('recipe-list')
        response = api_client.get(url, {'search': 'виноград'})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 1
        assert 'Салат' in response.data['results'][0]['title']

    def test_filter_recipes_by_difficulty(self, api_client):
        """Тест фильтрации по сложности"""

        RecipeFactory.create_batch(2, difficulty='easy')
        RecipeFactory.create_batch(3, difficulty='hard')

        url = reverse('recipe-list')
        response = api_client.get(url, {'difficulty': 'easy'})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 2

    def test_filter_recipes_by_cook_time(self, api_client):
        """Тест фильтрации по времени приготовления"""

        RecipeFactory(cook_time=15)
        RecipeFactory(cook_time=30)
        RecipeFactory(cook_time=60)

        url = reverse('recipe-list')
        response = api_client.get(url, {'cook_time_max': 30})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 2

    def test_random_recipes(self, api_client):
        """Тест на выдачу случайного рецепта"""

        RecipeFactory.create_batch(5)

        url = reverse('recipe-random')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert 'title' in response.data

    def test_add_to_favorites(self, authenticated_client, user):
        """Тест добавления рецепта в избранное"""

        recipe = RecipeFactory()

        url = reverse('recipe-add-to-favorites', kwargs={'pk': recipe.pk})
        response = authenticated_client.post(url)

        assert response.status_code == status.HTTP_201_CREATED
        assert Favorite.objects.filter(user=user, recipe=recipe).exists()

    def test_remove_from_favorites(self, authenticated_client, user):
        """Тест удаления рецепта из избранного"""

        recipe = RecipeFactory()
        Favorite.objects.create(user=user, recipe=recipe)

        url = reverse('recipe-remove-from-favorites', kwargs={'pk': recipe.pk})
        response = authenticated_client.delete(url)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Favorite.objects.filter(user=user, recipe=recipe).exists()


@pytest.mark.django_db
class TestCategoryAPI:
    """Тесты для API категорий"""

    def test_list_categories(self, api_client):
        """Тест получения списка категорий"""

        CategoryFactory.create_batch(3)

        url = reverse('category-list')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 3

    def test_create_category_as_user(self, authenticated_client):
        """Тест создания категории обычным пользователем (должно быть запрещено)"""

        url = reverse('category-list')
        data = {'name': 'Новая категория', 'slug': 'new-category'}

        response = authenticated_client.post(url, data, format='json')

        # Зависит от разрешения IsAdminOrReadOnly
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestAuthentication:
    """Тесты аутентификации"""

    def test_register_user(self, api_client):
        """Тест регистрации пользователя"""

        url = reverse('register')
        data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'newpass123',
            'password2': 'newpass123'
        }

        response = api_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert 'access' in response.data
        assert 'refresh' in response.data

    def test_register_user_password_mismatch(self, api_client):
        """Тест регистрации с несовпадающими паролями"""

        url = reverse('register')
        data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'pass123',
            'password2': 'differentpass123'
        }

        response = api_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_login_user(self, api_client, user):
        """Тест логина пользователя"""

        url = reverse('token_obtain_pair')
        data = {
            'username': 'testuser',
            'password': 'testpass123'
        }

        response = api_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data
        assert 'refresh' in response.data
