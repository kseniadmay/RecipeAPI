from rest_framework import viewsets, status, filters
from rest_framework.decorators import api_view, action, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import (
    IsAuthenticated,
    AllowAny,
    IsAuthenticatedOrReadOnly,
)
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.models import User
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.views.decorators.cache import cache_page
from django.core.cache import cache
from django.utils.decorators import method_decorator
from rest_framework.parsers import MultiPartParser, FormParser

from .models import Category, Recipe, Favorite, UserProfile
from .serializers import (
    CategorySerializer,
    RecipeListSerializer,
    RecipeDetailSerializer,
    FavoriteSerializer,
    RegisterSerializer,
    UserSerializer,
)
from .filters import RecipeFilter
from .permissions import IsAuthorOrReadOnly, IsAdminOrReadOnly
from .pagination import RecipePagination
from .tasks import send_welcome_email, generate_recipe_thumbnail


class CategoryViewSet(viewsets.ModelViewSet):
    """
    API для управления категориями рецептов

    Доступ:
    - Чтение (GET): все пользователи
    - Создание/Изменение/Удаление (POST/PUT/DELETE): только администраторы

    Функции:
    - Список всех категорий с кэшированием (1 час)
    - Создание новой категории
    - Обновление существующей категории
    - Удаление категории
    """

    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAdminOrReadOnly]

    @swagger_auto_schema(
        operation_summary='Список категорий',
        operation_description='Получить список всех категорий рецептов. Результат кэшируется на 1 час',
        responses={200: CategorySerializer(many=True), 400: 'Некорректный запрос'},
        tags=['Категории'],
    )
    @method_decorator(cache_page(60 * 60, key_prefix='category_list'))
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary='Создать категорию',
        operation_description='Создать новую категорию рецептов. Требуются права администратора',
        responses={
            201: CategorySerializer(),
            400: 'Некорректные данные',
            403: 'Доступ запрещён (требуются права администратора)',
        },
        tags=['Категории'],
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary='Получить категорию',
        operation_description='Получить детальную информацию о конкретной категории',
        responses={200: CategorySerializer(), 404: 'Категория не найдена'},
        tags=['Категории'],
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary='Обновить категорию',
        operation_description='Обновить существующую категорию. Требуются права администратора',
        responses={
            200: CategorySerializer(),
            400: 'Некорректные данные',
            403: 'Доступ запрещён',
            404: 'Категория не найдена',
        },
        tags=['Категории'],
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary='Частично обновить категорию',
        operation_description='Частично обновить категорию (только указанные поля). Требуются права администратора',
        responses={
            200: CategorySerializer(),
            400: 'Некорректные данные',
            403: 'Доступ запрещён',
            404: 'Категория не найдена',
        },
        tags=['Категории'],
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary='Удалить категорию',
        operation_description='Удалить категорию. Требуются права администратора',
        responses={
            204: 'Категория успешно удалена',
            403: 'Доступ запрещён',
            404: 'Категория не найдена',
        },
        tags=['Категории'],
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save()
        cache.delete('category_list')

    def perform_update(self, serializer):
        serializer.save()
        cache.delete('category_list')

    def perform_destroy(self, instance):
        instance.delete()
        cache.delete('category_list')


class RecipeViewSet(viewsets.ModelViewSet):
    """
    API для управления рецептами

    Функции:
    - CRUD операции для рецептов
    - Поиск по названию, описанию, ингредиентам
    - Фильтрация по времени, сложности, калориям, категории
    - Сортировка по дате, времени приготовления, порциям
    - Избранное (добавление/удаление)
    - Специальные выборки (случайный, быстрые, простые рецепты)

    Оптимизация:
    - Redis кэширование (5 минут для списка, 10 минут для деталей)
    - Оптимизация SQL-запросов (select_related, prefetch_related)
    - Асинхронная обработка изображений через Celery
    """

    queryset = (
        Recipe.objects.all()
        .select_related('author', 'category')
        .prefetch_related('ingredients', 'steps')
    )
    permission_classes = [IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_class = RecipeFilter
    search_fields = ('title', 'description', 'ingredients__name')
    ordering_fields = ('created_at', 'cook_time', 'servings', 'calories')
    ordering = ('-created_at',)
    pagination_class = RecipePagination
    parser_classes = [MultiPartParser, FormParser]

    def get_serializer_class(self):
        if self.action == 'list':
            return RecipeListSerializer
        return RecipeDetailSerializer

    @swagger_auto_schema(
        operation_summary='Список рецептов',
        operation_description='''
        Получить список всех рецептов с поддержкой:
        - Поиска по названию, описанию, ингредиентам (?search=паста)
        - Фильтрации (?cook_time_max=30&difficulty=easy&category_slug=vypechka)
        - Сортировки (?ordering=-created_at)
        - Пагинации (?page=2)

        Результат кэшируется на 5 минут
        ''',
        manual_parameters=[
            openapi.Parameter(
                'search',
                openapi.IN_QUERY,
                description='Поиск по названию/описанию/ингредиентам',
                type=openapi.TYPE_STRING,
            ),
            openapi.Parameter(
                'cook_time_min',
                openapi.IN_QUERY,
                description='Минимальное время приготовления (мин)',
                type=openapi.TYPE_INTEGER,
            ),
            openapi.Parameter(
                'cook_time_max',
                openapi.IN_QUERY,
                description='Максимальное время приготовления (мин)',
                type=openapi.TYPE_INTEGER,
            ),
            openapi.Parameter(
                'difficulty',
                openapi.IN_QUERY,
                description='Сложность (easy/medium/hard)',
                type=openapi.TYPE_STRING,
            ),
            openapi.Parameter(
                'category_slug',
                openapi.IN_QUERY,
                description='Slug категории',
                type=openapi.TYPE_STRING,
            ),
            openapi.Parameter(
                'ordering',
                openapi.IN_QUERY,
                description='Сортировка (-created_at, cook_time, calories)',
                type=openapi.TYPE_STRING,
            ),
            openapi.Parameter(
                'page',
                openapi.IN_QUERY,
                description='Номер страницы',
                type=openapi.TYPE_INTEGER,
            ),
        ],
        responses={
            200: RecipeListSerializer(many=True),
        },
        tags=['Рецепты'],
    )
    @method_decorator(cache_page(60 * 5, key_prefix='recipe_list'))
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary='Создать рецепт',
        operation_description='''
        Создать новый рецепт с ингредиентами и шагами приготовления

        Требуется авторизация. Автор рецепта устанавливается автоматически

        Если загружено изображение, превью генерируется асинхронно через Celery

        Формат ingredients_data и steps_data: JSON-массив объектов
        ''',
        request_body=RecipeDetailSerializer,
        responses={
            201: RecipeDetailSerializer(),
            400: 'Некорректные данные',
            401: 'Требуется авторизация',
        },
        tags=['Рецепты'],
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary='Получить рецепт',
        operation_description='Получить детальную информацию о рецепте включая ингредиенты и шаги. Результат кэшируется на 10 минут',
        responses={200: RecipeDetailSerializer(), 404: 'Рецепт не найден'},
        tags=['Рецепты'],
    )
    def retrieve(self, request, *args, **kwargs):
        recipe_id = kwargs.get('pk')
        cache_key = f'recipe_{recipe_id}'
        cached_data = cache.get(cache_key)

        if cached_data:
            return Response(cached_data)

        instance = self.get_object()
        serializer = self.get_serializer(instance)
        cache.set(cache_key, serializer.data, timeout=60 * 10)

        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary='Обновить рецепт',
        operation_description='Полное обновление рецепта. Доступно только автору рецепта',
        responses={
            200: RecipeDetailSerializer(),
            400: 'Некорректные данные',
            403: 'Доступ запрещён (вы не автор рецепта)',
            404: 'Рецепт не найден',
        },
        tags=['Рецепты'],
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary='Частично обновить рецепт',
        operation_description='Частичное обновление рецепта. Доступно только автору',
        responses={
            200: RecipeDetailSerializer(),
            400: 'Некорректные данные',
            403: 'Доступ запрещён',
            404: 'Рецепт не найден',
        },
        tags=['Рецепты'],
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary='Удалить рецепт',
        operation_description='Удалить рецепт. Доступно только автору',
        responses={
            204: 'Рецепт успешно удалён',
            403: 'Доступ запрещён',
            404: 'Рецепт не найден',
        },
        tags=['Рецепты'],
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary='Случайный рецепт',
        operation_description='Получить случайный рецепт из базы данных',
        responses={200: RecipeDetailSerializer(), 404: 'Рецепты не найдены'},
        tags=['Рецепты - Специальные'],
    )
    @action(detail=False, methods=['get'])
    def random(self, request):
        recipe = Recipe.objects.order_by('?').first()
        if recipe:
            serializer = RecipeDetailSerializer(recipe)
            return Response(serializer.data)
        return Response(
            {'detail': 'Рецепты не найдены!'}, status=status.HTTP_404_NOT_FOUND
        )

    @swagger_auto_schema(
        operation_summary='Мои рецепты',
        operation_description='Получить список рецептов текущего авторизованного пользователя',
        responses={200: RecipeListSerializer(many=True), 401: 'Требуется авторизация'},
        tags=['Рецепты - Специальные'],
    )
    @action(detail=False, methods=['get'])
    def my_recipes(self, request):
        if not request.user.is_authenticated:
            return Response(
                {'detail': 'Требуется авторизация!'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        recipes = self.queryset.filter(author=request.user)
        page = self.paginate_queryset(recipes)

        if page is not None:
            serializer = RecipeListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = RecipeListSerializer(recipes, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary='Добавить в избранное',
        operation_description='Добавить рецепт в избранное. Требуется авторизация',
        responses={
            201: openapi.Response(
                'Рецепт добавлен в избранное',
                examples={
                    'application/json': {'detail': 'Рецепт добавлен в избранное'}
                },
            ),
            200: openapi.Response(
                'Рецепт уже в избранном',
                examples={'application/json': {'detail': 'Рецепт уже в избранном'}},
            ),
            401: 'Требуется авторизация',
            404: 'Рецепт не найден',
        },
        tags=['Избранное'],
    )
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def add_to_favorites(self, request, pk=None):
        recipe = self.get_object()
        favorite, created = Favorite.objects.get_or_create(
            user=request.user, recipe=recipe
        )

        if created:
            return Response(
                {'detail': 'Рецепт добавлен в избранное'},
                status=status.HTTP_201_CREATED,
            )
        return Response({'detail': 'Рецепт уже в избранном'}, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary='Удалить из избранного',
        operation_description='Удалить рецепт из избранного. Требуется авторизация',
        responses={
            204: 'Рецепт удалён из избранного',
            401: 'Требуется авторизация',
            404: 'Рецепт не найден в избранном',
        },
        tags=['Избранное'],
    )
    @action(detail=True, methods=['delete'], permission_classes=[IsAuthenticated])
    def remove_from_favorites(self, request, pk=None):
        recipe = self.get_object()

        try:
            favorite = Favorite.objects.get(user=request.user, recipe=recipe)
            favorite.delete()
            return Response(
                {'detail': 'Рецепт удалён из избранного'},
                status=status.HTTP_204_NO_CONTENT,
            )
        except Favorite.DoesNotExist:
            return Response(
                {'detail': 'Рецепт не найден в избранном'},
                status=status.HTTP_404_NOT_FOUND,
            )

    @swagger_auto_schema(
        operation_summary='Список избранного',
        operation_description='Получить список избранных рецептов текущего пользователя',
        responses={200: RecipeListSerializer(many=True), 401: 'Требуется авторизация'},
        tags=['Избранное'],
    )
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def favorites(self, request):
        favorites = Favorite.objects.filter(user=request.user).select_related('recipe')
        recipes = [favorite.recipe for favorite in favorites]

        page = self.paginate_queryset(recipes)
        if page is not None:
            serializer = RecipeListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = RecipeListSerializer(recipes, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary='Быстрые рецепты',
        operation_description='Получить рецепты с временем приготовления до 30 минут. Результат кэшируется на 5 минут',
        responses={200: RecipeListSerializer(many=True)},
        tags=['Рецепты - Специальные'],
    )
    @method_decorator(cache_page(60 * 5, key_prefix='quick_recipes'))
    @action(detail=False, methods=['get'])
    def quick_recipes(self, request):
        recipes = self.queryset.filter(cook_time__lte=30)

        page = self.paginate_queryset(recipes)
        if page is not None:
            serializer = RecipeListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = RecipeListSerializer(recipes, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary='Простые рецепты',
        operation_description='Получить рецепты с уровнем сложности "easy" (простые)',
        responses={200: RecipeListSerializer(many=True)},
        tags=['Рецепты - Специальные'],
    )
    @action(detail=False, methods=['get'])
    def easy_recipes(self, request):
        recipes = self.queryset.filter(difficulty='easy')

        page = self.paginate_queryset(recipes)
        if page is not None:
            serializer = RecipeListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = RecipeListSerializer(recipes, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary='Поиск по ингредиенту',
        operation_description='Найти рецепты содержащие указанный ингредиент',
        manual_parameters=[
            openapi.Parameter(
                'name',
                openapi.IN_QUERY,
                description='Название ингредиента (например: мука)',
                type=openapi.TYPE_STRING,
                required=True,
            ),
        ],
        responses={
            200: RecipeListSerializer(many=True),
            400: 'Параметр "name" обязателен',
        },
        tags=['Рецепты - Специальные'],
    )
    @action(detail=False, methods=['get'])
    def search_by_ingredient(self, request):
        ingredient = request.query_params.get('name', None)
        if not ingredient:
            return Response(
                {'detail': 'Параметр "name" обязателен'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        recipes = self.queryset.filter(
            ingredients__name__icontains=ingredient
        ).distinct()

        page = self.paginate_queryset(recipes)
        if page is not None:
            serializer = RecipeListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = RecipeListSerializer(recipes, many=True)
        return Response(serializer.data)

    def get_permissions(self):
        if self.action in ['update', 'partial_update', 'destroy']:
            permission_classes = [IsAuthenticated, IsAuthorOrReadOnly]
        elif self.action == 'create':
            permission_classes = [IsAuthenticated]
        else:
            permission_classes = [AllowAny]
        return [permission() for permission in permission_classes]

    def perform_create(self, serializer):
        recipe = serializer.save(author=self.request.user)
        cache.delete('recipe_list')

        if recipe.image:
            generate_recipe_thumbnail.delay(recipe.id)

    def perform_update(self, serializer):
        serializer.save()
        cache.delete('recipe_list')
        cache.delete(f'recipe_{self.kwargs['pk']}')

    def perform_destroy(self, instance):
        instance.delete()
        cache.delete('recipe_list')
        cache.delete(f'recipe_{instance.pk}')


class FavoriteViewSet(viewsets.ModelViewSet):
    """
    API для управления избранными рецептами пользователя

    Доступ: только авторизованные пользователи
    Каждый пользователь видит только своё избранное
    """

    serializer_class = FavoriteSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Favorite.objects.none()
        user = self.request.user
        if not user.is_authenticated:
            return Favorite.objects.none()
        return Favorite.objects.filter(user=user).select_related('recipe')

    @swagger_auto_schema(
        operation_summary='Список избранного',
        operation_description='Получить список избранных рецептов текущего пользователя',
        responses={200: FavoriteSerializer(many=True), 401: 'Требуется авторизация'},
        tags=['Избранное'],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary='Добавить в избранное',
        operation_description='Добавить рецепт в избранное',
        responses={
            201: FavoriteSerializer(),
            400: 'Некорректные данные',
            401: 'Требуется авторизация',
        },
        tags=['Избранное'],
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary='Удалить из избранного',
        operation_description='Удалить рецепт из избранного',
        responses={
            204: openapi.Response(
                'Удалено из избранного',
                examples={'application/json': {'detail': 'Удалено из избранного!'}},
            ),
            401: 'Требуется авторизация',
            404: 'Запись не найдена',
        },
        tags=['Избранное'],
    )
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(
            {'detail': 'Удалено из избранного!'}, status=status.HTTP_204_NO_CONTENT
        )


@swagger_auto_schema(
    method='post',
    operation_summary='Регистрация пользователя',
    operation_description='''
    Регистрация нового пользователя с автоматической генерацией JWT-токенов

    После успешной регистрации:
    - Пользователю отправляется приветственное письмо (асинхронно через Celery)
    - Возвращаются access и refresh токены для немедленной авторизации

    Пароли должны совпадать и быть не менее 8 символов
    ''',
    request_body=RegisterSerializer,
    responses={
        201: openapi.Response(
            'Пользователь успешно зарегистрирован',
            examples={
                'application/json': {
                    'user': {
                        'id': 1,
                        'username': 'john_doe',
                        'email': 'john@example.com',
                    },
                    'refresh': 'eyJ0eXAiOiJKV1QiLCJhbGc...',
                    'access': 'eyJ0eXAiOiJKV1QiLCJhbGc...',
                    'message': 'Пользователь успешно зарегистрирован! Проверьте вашу почту!',
                }
            },
        ),
        400: 'Некорректные данные (пароли не совпадают, пользователь существует и т.д.)',
    },
    tags=['Аутентификация'],
)
@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    serializer = RegisterSerializer(data=request.data)

    if serializer.is_valid():
        user = serializer.save()
        refresh = RefreshToken.for_user(user)

        send_welcome_email.delay(user.id)

        return Response(
            {
                'user': UserSerializer(user).data,
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'message': 'Пользователь успешно зарегистрирован! Проверьте вашу почту!',
            },
            status=status.HTTP_201_CREATED,
        )

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@swagger_auto_schema(
    method='get',
    operation_summary='Текущий пользователь',
    operation_description='Получить данные текущего авторизованного пользователя',
    responses={200: UserSerializer(), 401: 'Требуется авторизация'},
    tags=['Аутентификация'],
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def current_user(request):
    serializer = UserSerializer(request.user)
    return Response(serializer.data)


@swagger_auto_schema(
    method='get',
    operation_summary='Настройки уведомлений',
    operation_description='Получить текущие настройки email уведомлений пользователя.',
    responses={
        200: openapi.Response(
            'Настройки уведомлений',
            examples={
                'application/json': {
                    'email_notifications': True
                }
            }
        ),
        401: 'Требуется авторизация'
    },
    tags=['Настройки']
)
@swagger_auto_schema(
    method='patch',
    operation_summary='Изменить настройки уведомлений',
    operation_description='Включить или отключить ежедневный email дайджест.',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'email_notifications': openapi.Schema(
                type=openapi.TYPE_BOOLEAN,
                description='Получать ежедневный дайджест'
            ),
        },
    ),
    responses={
        200: openapi.Response(
            'Настройки обновлены',
            examples={
                'application/json': {
                    'email_notifications': False,
                    'message': 'Настройки обновлены'
                }
            }
        ),
        401: 'Требуется авторизация'
    },
    tags=['Настройки']
)
@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def email_notifications_settings(request):
    """Управление настройками email уведомлений"""

    # Получаем или создаём профиль
    profile, created = UserProfile.objects.get_or_create(user=request.user)

    if request.method == 'GET':
        return Response({
            'email_notifications': profile.email_notifications
        })

    elif request.method == 'PATCH':
        email_notifications = request.data.get('email_notifications')

        if email_notifications is not None:
            profile.email_notifications = email_notifications
            profile.save()

            status_msg = 'включены' if email_notifications else 'отключены'

            return Response({
                'email_notifications': profile.email_notifications,
                'message': f'Email уведомления {status_msg}'
            })

        return Response(
            {'error': 'Параметр email_notifications обязателен'},
            status=status.HTTP_400_BAD_REQUEST
        )
