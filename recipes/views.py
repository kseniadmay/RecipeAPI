from rest_framework import viewsets, status, filters
from rest_framework.decorators import api_view, action, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAuthenticatedOrReadOnly
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.models import User
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg.utils import swagger_auto_schema
from django.views.decorators.cache import cache_page
from django.core.cache import cache
from django.utils.decorators import method_decorator
from rest_framework.parsers import MultiPartParser, FormParser

from .models import Category, Recipe, Favorite
from .serializers import CategorySerializer, RecipeListSerializer, RecipeDetailSerializer, FavoriteSerializer, \
    RegisterSerializer, UserSerializer
from .filters import RecipeFilter
from .permissions import IsAuthorOrReadOnly, IsAdminOrReadOnly
from .pagination import RecipePagination
from .tasks import send_welcome_email, generate_recipe_thumbnail


class CategoryViewSet(viewsets.ModelViewSet):
    """CRUD API для категорий рецептов с ограничением прав доступа"""

    queryset = Category.objects.all()
    serializer_class = CategorySerializer

    # Создавать и редактировать категории могут только админы
    permission_classes = [IsAdminOrReadOnly]

    # Кэшируем список категорий на 1 час (категории меняются редко)
    @method_decorator(cache_page(60 * 60, key_prefix='category_list'))
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

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
    """CRUD API для рецептов с поддержкой фильтров, поиска и сортировки"""

    queryset = Recipe.objects.all().select_related('author', 'category').prefetch_related('ingredients', 'steps')
    permission_classes = [IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]

    # Фильтрация
    filterset_class = RecipeFilter

    # Поиск
    search_fields = ('title', 'description', 'ingredients__name')

    # Сортировка
    ordering_fields = ('created_at', 'cook_time', 'servings', 'calories')
    ordering = ('-created_at',)

    # Пагинация
    pagination_class = RecipePagination

    # Добавляем поддержку загрузки файлов через Swagger / multipart/form-data
    parser_classes = [MultiPartParser, FormParser]

    def get_serializer_class(self):
        """Использует краткий сериализатор для списка и подробный для остальных действий"""

        if self.action == 'list':
            return RecipeListSerializer
        return RecipeDetailSerializer

    def perform_create(self, serializer):
        """Автоматически устанавливает текущего пользователя как автора нового рецепта"""

        serializer.save(author=self.request.user)
        recipe = serializer.save(author=self.request.user)

        # Инвалидируем кэш при создании
        cache.delete('recipe_list')

        # CELERY: Генерируем thumbnail асинхронно (если есть изображение)
        if recipe.image:
            generate_recipe_thumbnail.delay(recipe.id)

    def perform_update(self, serializer):
        serializer.save()
        # Инвалидируем кэш при обновлении

        cache.delete('recipe_list')
        cache.delete(f'recipe_{self.kwargs["pk"]}')

    def perform_destroy(self, instance):
        instance.delete()
        # Инвалидируем кэш при удалении
        cache.delete('recipe_list')
        cache.delete(f'recipe_{instance.pk}')

    def get_permissions(self):
        """Разные разрешения для разных действий"""

        if self.action in ['update', 'partial_update', 'destroy']:
            # Только автор может редактировать и удалять рецепты
            permission_classes = [IsAuthenticated, IsAuthorOrReadOnly]
        elif self.action == 'create':
            # Только авторизованные могут создавать рецепты
            permission_classes = [IsAuthenticated]
        else:
            # Читать рецепты могут все
            permission_classes = [AllowAny]

        return [permission() for permission in permission_classes]

    # Кэшируем список рецептов на 5 минут
    @method_decorator(cache_page(60 * 5, key_prefix='recipe_list'))
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    # Кэшируем детали рецепта на 10 минут
    def retrieve(self, request, *args, **kwargs):
        recipe_id = kwargs.get('pk')
        cache_key = f'recipe_{recipe_id}'

        # Пытаемся получить из кэша
        cached_data = cache.get(cache_key)
        if cached_data:
            return Response(cached_data)

        # Если нет в кэше, получаем из БД
        instance = self.get_object()
        serializer = self.get_serializer(instance)

        # Сохраняем в кэш на 10 минут
        cache.set(cache_key, serializer.data, timeout=60 * 10)

        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def random(self, request):
        """Возвращает случайный рецепт, если рецептов нет - 404"""

        recipe = Recipe.objects.order_by('?').first()
        if recipe:
            serializer = RecipeDetailSerializer(recipe)
            return Response(serializer.data)
        return Response({'detail': 'Рецепты не найдены!'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['get'])
    def my_recipes(self, request):
        """Возвращает рецепты текущего пользователя с поддержкой пагинации"""

        if not request.user.is_authenticated:
            return Response({'detail': 'Требуется авторизация!'}, status=status.HTTP_401_UNAUTHORIZED)

        recipes = self.queryset.filter(author=request.user)
        page = self.paginate_queryset(recipes)

        if page is not None:
            serializer = RecipeListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = RecipeListSerializer(recipes, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def add_to_favorites(self, request, pk=None):
        """Добавить рецепт в избранное"""

        recipe = self.get_object()
        favorite, created = Favorite.objects.get_or_create(user=request.user, recipe=recipe)

        if created:
            return Response({'detail': 'Рецепт добавлен в избранное'}, status=status.HTTP_201_CREATED)
        return Response({'detail': 'Рецепт уже в избранном'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['delete'], permission_classes=[IsAuthenticated])
    def remove_from_favorites(self, request, pk=None):
        """Удалить рецепт из избранного"""

        recipe = self.get_object()

        try:
            favorite = Favorite.objects.get(user=request.user, recipe=recipe)
            favorite.delete()
            return Response({'detail': 'Рецепт удалён из избранного'}, status=status.HTTP_204_NO_CONTENT)
        except Favorite.DoesNotExist:
            return Response({'detail': 'Рецепт не найден в избранном'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def favorites(self, request):
        """Получить избранные рецепты пользователя"""

        favorites = Favorite.objects.filter(user=request.user).select_related('recipe')
        recipes = [favorite.recipe for favorite in favorites]

        page = self.paginate_queryset(recipes)
        if page is not None:
            serializer = RecipeListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = RecipeListSerializer(recipes, many=True)
        return Response(serializer.data)

    # Кэшируем быстрые рецепты
    @method_decorator(cache_page(60 * 5, key_prefix='quick_recipes'))
    @action(detail=False, methods=['get'])
    def quick_recipes(self, request):
        """Рецепты до 30 минут"""

        recipes = self.queryset.filter(cook_time__lte=30)

        page = self.paginate_queryset(recipes)
        if page is not None:
            serializer = RecipeListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = RecipeListSerializer(recipes, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def easy_recipes(self, request):
        """Простые рецепты"""

        recipes = self.queryset.filter(difficulty='easy')

        page = self.paginate_queryset(recipes)
        if page is not None:
            serializer = RecipeListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = RecipeListSerializer(recipes, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def search_by_ingredient(self, request):
        """Поиск рецептов по ингредиенту"""

        ingredient = request.query_params.get('name', None)
        if not ingredient:
            return Response({'detail': 'Параметр "name" обязателен'}, status=status.HTTP_400_BAD_REQUEST)

        recipes = self.queryset.filter(ingredients__name__icontains=ingredient).distinct()

        page = self.paginate_queryset(recipes)
        if page is not None:
            serializer = RecipeListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = RecipeListSerializer(recipes, many=True)
        return Response(serializer.data)


class FavoriteViewSet(viewsets.ModelViewSet):
    """CRUD API для избранного пользователя с ограничением доступа"""

    serializer_class = FavoriteSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Возвращает объекты избранного только для текущего пользователя.

        1. swagger_fake_view - флаг, который drf_yasg ставит при генерации документации Swagger.
           В этот момент нет реального пользователя, поэтому self.request.user - AnonymousUser.
           Если не проверять, Django пытается преобразовать его в id и падает с TypeError.

        2. Если пользователь не аутентифицирован, возвращаем пустой queryset,
           чтобы не допустить ошибок при фильтрации.

        3. В реальном API фильтруем объекты только по текущему авторизованному пользователю.
        """

        if getattr(self, 'swagger_fake_view', False):
            return Favorite.objects.none()
        user = self.request.user
        if not user.is_authenticated:
            return Favorite.objects.none()
        return Favorite.objects.filter(user=user).select_related('recipe')

    def destroy(self, request, *args, **kwargs):
        """Удаляет объект из избранного и возвращает информативный ответ"""

        instance = self.get_object()
        self.perform_destroy(instance)
        return Response({'detail': 'Удалено из избранного!'}, status=status.HTTP_204_NO_CONTENT)


# swagger_auto_schema здесь используется, чтобы Swagger видел, какие данные принимает register.
# Без него в функциональном представлении (@api_view) форма JSON не появляется
@swagger_auto_schema(
    method='post',
    request_body=RegisterSerializer
)
@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """
    Регистрация нового пользователя с генерацией JWT-токенов.
    Используется функциональное представление, потому что логика
    выходит за рамки стандартного CRUD (включает password2 и токены).
    """

    serializer = RegisterSerializer(data=request.data)

    if serializer.is_valid():
        user = serializer.save()

        # Генерируем токены
        refresh = RefreshToken.for_user(user)

        # CELERY: Отправляем приветственное письмо асинхронно
        send_welcome_email.delay(user.id)

        return Response({
            'user': UserSerializer(user).data,
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'message': 'Пользователь успешно зарегистрирован! Проверьте вашу почту!'
        }, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def current_user(request):
    """Возвращает данные текущего авторизованного пользователя"""

    serializer = UserSerializer(request.user)
    return Response(serializer.data)
