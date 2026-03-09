from rest_framework import viewsets, status, filters
from rest_framework.decorators import api_view, action, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAuthenticatedOrReadOnly
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.models import User
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg.utils import swagger_auto_schema

from .models import Category, Recipe, Favorite
from .serializers import CategorySerializer, RecipeListSerializer, RecipeDetailSerializer, FavoriteSerializer, \
    RegisterSerializer, UserSerializer
from .filters import RecipeFilter
from .permissions import IsAuthorOrReadOnly, IsAdminOrReadOnly


class CategoryViewSet(viewsets.ModelViewSet):
    """CRUD API для категорий рецептов с ограничением прав доступа"""

    queryset = Category.objects.all()
    serializer_class = CategorySerializer

    # Создавать и редактировать категории могут только админы
    permission_classes = [IsAdminOrReadOnly]


class RecipeViewSet(viewsets.ModelViewSet):
    """CRUD API для рецептов с поддержкой фильтров, поиска и сортировки"""

    queryset = Recipe.objects.all().select_related('author', 'category').prefetch_related('ingredients', 'steps')
    permission_classes = [IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]

    # Фильтрация
    filter_fields = RecipeFilter

    # Поиск
    search_fields = ('title', 'description', 'ingredients__name')

    # Сортировка
    ordering_fields = ('created_at', 'cook_time', 'servings', 'calories')
    ordering = ('-created_at',)

    def get_serializer_class(self):
        """Использует краткий сериализатор для списка и подробный для остальных действий"""

        if self.action == 'list':
            return RecipeListSerializer
        return RecipeDetailSerializer

    def perform_create(self, serializer):
        """Автоматически устанавливает текущего пользователя как автора нового рецепта"""

        serializer.save(author=self.request.user)

    def get_permissions(self):
        """Разные разрешения для разных действий"""

        if self.action == ['update', 'partial_update', 'destroy']:
            # Только автор может редактировать и удалять рецепты
            permission_classes = [IsAuthenticated, IsAuthorOrReadOnly]
        elif self.action == 'create':
            # Только авторизованные могут создавать рецепты
            permission_classes = [IsAuthenticated]
        else:
            # Читать рецепты могут все
            permission_classes = [AllowAny]

        return [permission() for permission in permission_classes]

    @action(detail=False, methods=['get'])
    def random(self, request):
        """Возвращает случайный рецепт, если рецептов нет - 404"""

        recipe = Recipe.objects.order_by('?').first()
        if recipe:
            serializer = RecipeDetailSerializer(recipe)
            return Response(serializer.data)
        return Response({'detail': "Рецепты не найдены!"}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['get'])
    def my_recipes(self, request):
        """Возвращает рецепты текущего пользователя с поддержкой пагинации"""

        if not request.user.is_authenticated:
            return Response({'detail': "Требуется авторизация!"}, status=status.HTTP_401_UNAUTHORIZED)

        recipes = self.queryset.filter(author=request.user)
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
        """Возвращает объекты избранного только для текущего пользователя"""

        return Favorite.objects.filter(user=self.request.user).select_related('recipe')

    def destroy(self, request, *args, **kwargs):
        """Удаляет объект из избранного и возвращает информативный ответ"""

        instance = self.get_object()
        self.perform_destroy(instance)
        return Response({'detail': "Удалено из избранного!"}, status=status.HTTP_204_NO_CONTENT)


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

        return Response({
            'user': UserSerializer(user).data,
            'refresh': str(refresh),
            'access': str(refresh.access_token)
        }, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def current_user(request):
    """Возвращает данные текущего авторизованного пользователя"""

    serializer = UserSerializer(request.user)
    return Response(serializer.data)
