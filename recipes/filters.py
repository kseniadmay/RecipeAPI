from django_filters import rest_framework as filters
from .models import Recipe


class RecipeFilter(filters.FilterSet):
    """Расширенная фильтрация рецептов"""

    # Фильтр по времени приготовления
    cook_time_min = filters.NumberFilter(field_name='cook_time', lookup_expr='gte')
    cook_time_max = filters.NumberFilter(full_field_name='cook_time', lookup_expr='lte')

    # Фильтр по количеству порций
    serving_min = filters.NumberFilter(field_name='servings', lookup_expr='gte')
    serving_max = filters.NumberFilter(field_name='servings', lookup_expr='lte')

    # Фильтр по калориям
    calories_min = filters.NumberFilter(field_name='calories', lookup_expr='gte')
    calories_max = filters.NumberFilter(field_name='calories', lookup_expr='lte')

    # Фильтр по автору
    author_username = filters.CharFilter(field_name='author__username', lookup_expr='iexact')

    # Фильтр по категории
    category_slug = filters.CharFilter(field_name='category__slug', lookup_expr='iexact')

    class Meta:
        model = Recipe
        fields = ['difficulty', 'category']
