from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator


class Category(models.Model):
    """Категория рецепта"""

    name = models.CharField(max_length=100, unique=True, verbose_name='Название')
    slug = models.SlugField(max_length=100, unique=True, verbose_name='Slug')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создано')

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'
        ordering = ['name']

    def __str__(self):
        return self.name


class Recipe(models.Model):
    """Рецепт блюда"""

    DIFFICULTY_CHOICES = [
        ('easy', 'Легко'),
        ('medium', 'Средне'),
        ('hard', 'Сложно'),
    ]

    title = models.CharField(max_length=200, verbose_name='Название')
    description = models.TextField(verbose_name='Описание')
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='recipes',
        verbose_name='Автор'
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='recipes',
        verbose_name='Категория'
    )

    # Характеристики
    cook_time = models.PositiveIntegerField(
        verbose_name='Время приготовления (минуты)',
        validators=[MinValueValidator(1)]
    )
    servings = models.PositiveIntegerField(
        verbose_name='Количество порций',
        validators=[MinValueValidator(1)]
    )
    difficulty = models.CharField(
        max_length=10,
        choices=DIFFICULTY_CHOICES,
        default='medium',
        verbose_name='Сложность'
    )

    # Опционально
    image = models.ImageField(
        upload_to='recipes/%Y/%m/%d/',
        blank=True,
        null=True,
        verbose_name='Фото'
    )
    calories = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name='Калории на порцию'
    )

    # Метаданные
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создано')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлено')

    class Meta:
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class Ingredient(models.Model):
    """Ингредиент рецепта"""

    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='ingredients',
        verbose_name='Рецепт'
    )
    name = models.CharField(max_length=100, verbose_name='Название')
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Количество'
    )
    unit = models.CharField(
        max_length=20,
        verbose_name='Единица измерения',
        help_text='г, кг, мл, л, шт, ч.л., ст.л'
    )

    class Meta:
        verbose_name = 'Ингредиент'
        verbose_name_plural = 'Ингредиенты'
        ordering = ['name']

        # Ограничение: в одном рецепте один и тот же ингредиент может быть только один раз
        constraints = [models.UniqueConstraint(fields=['recipe', 'name'], name='unique_recipe_ingredient')]

    def __str__(self):
        return f'{self.name} - {self.amount} {self.unit}'


class Step(models.Model):
    """Шаг приготовления"""

    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='steps',
        verbose_name='Рецепт'
    )
    order = models.PositiveIntegerField(verbose_name='Порядок')
    description = models.TextField(verbose_name='Описание')

    class Meta:
        verbose_name = 'Шаг'
        verbose_name_plural = 'Шаги'
        ordering = ['order']

    def __str__(self):
        return f'Шаг {self.order}: {self.description[:50]}'


class Favorite(models.Model):
    """Избранные рецепты пользователя"""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='favorites',
        verbose_name='Пользователь'
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='favorited_by',
        verbose_name='Рецепт'
    )
    added_at = models.DateTimeField(auto_now_add=True, verbose_name='Добавлено')

    class Meta:
        verbose_name = 'Избранное'
        verbose_name_plural = 'Избранное'
        unique_together = ['user', 'recipe']  # Один пользователь может добавить рецепт в избранное только один раз
        ordering = ['-added_at']

    def __str__(self):
        return f"{self.user.username} - {self.recipe.title}"
