from rest_framework import serializers
from django.contrib.auth.models import User

from .models import Category, Recipe, Ingredient, Step, Favorite


class UserSerializer(serializers.ModelSerializer):
    """Сериализатор пользователей"""

    class Meta:
        model = User
        fields = ['id', 'username', 'email']
        read_only_fields = ['id']


class CategorySerializer(serializers.ModelSerializer):
    """Сериализатор категорий рецептов"""

    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'created_at']
        read_only_fields = ['id', 'created_at']


class IngredientSerializer(serializers.ModelSerializer):
    """Сериализатор ингредиентов"""

    class Meta:
        model = Ingredient
        fields = ['id', 'name', 'amount', 'unit']
        read_only_fields = ['id']


class StepSerializer(serializers.ModelSerializer):
    """Сериализатор шагов приготовления"""

    class Meta:
        model = Step
        fields = ['id', 'order', 'description']
        read_only_fields = ['id']


class RecipeListSerializer(serializers.ModelSerializer):
    """Краткий сериализатор рецептов для списков"""

    author = UserSerializer(read_only=True)
    category = CategorySerializer(read_only=True)

    class Meta:
        model = Recipe
        fields = [
            'id', 'title', 'description', 'author', 'category',
            'cook_time', 'servings', 'difficulty', 'image',
            'calories', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class RecipeDetailSerializer(serializers.ModelSerializer):
    """Подробный сериализатор рецепта с ингредиентами и шагами"""

    author = UserSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    ingredients = IngredientSerializer(many=True)
    steps = StepSerializer(many=True)

    class Meta:
        model = Recipe
        fields = [
            'id', 'title', 'description', 'author', 'category',
            'cook_time', 'servings', 'difficulty', 'image',
            'calories', 'ingredients', 'steps',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'author', 'created_at', 'updated_at']

    def create(self, validated_data):
        """Создает рецепт вместе с ингредиентами и шагами"""

        ingredients_data = validated_data.pop('ingredients')
        steps_data = validated_data.pop('steps')

        # Создаём рецепт
        recipe = Recipe.objects.create(**validated_data)

        # Создаём ингредиенты
        for ingredient in ingredients_data:
            Ingredient.objects.create(recipe=recipe, **ingredient)

        # Создаём шаги
        for step in steps_data:
            Step.objects.create(recipe=recipe, **step)
        return recipe

    def update(self, instance, validated_data):
        """Обновляет рецепт вместе с ингредиентами и шагами"""

        ingredients_data = validated_data.pop('ingredients', None)
        steps_data = validated_data.pop('steps', None)

        # Обновляем основные поля рецепта
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Обновляем ингредиенты
        if ingredients_data is not None:
            instance.ingredients.all().delete()
            for ingredient_data in ingredients_data:
                Ingredient.objects.create(recipe=instance, **ingredient_data)

        # Обновляем шаги
        if steps_data is not None:
            instance.steps.all().delete()
            for step_data in steps_data:
                Step.objects.create(recipe=instance, **step_data)
        return instance


class FavoriteSerializer(serializers.ModelSerializer):
    """Сериализатор избранного пользователя"""

    recipe = RecipeListSerializer(read_only=True)
    recipe_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Favorite
        fields = ['id', 'recipe', 'recipe_id', 'added_at']
        read_only_fields = ['id', 'added_at']

    def create(self, validated_data):
        """Добавляет рецепт в избранное пользователя"""

        user = self.context['request'].user
        recipe_id = validated_data.pop('recipe_id')

        # Проверяем, что рецепт существует
        try:
            recipe = Recipe.objects.get(id=recipe_id)
        except Recipe.DoesNotExist:
            raise serializers.ValidationError("Рецепт не найден")

        # Проверяем, что уже не добавлен
        if Favorite.objects.filter(user=user, recipe=recipe).exists():
            raise serializers.ValidationError("Рецепт уже в избранном")
        return Favorite.objects.create(user=user, recipe=recipe)


class RegisterSerializer(serializers.ModelSerializer):
    """Сериализатор регистрации пользователей"""

    password = serializers.CharField(write_only=True, min_length=8)
    password2 = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password2']

    def validate(self, data):
        """Проверяет, что пароли совпадают"""

        if data['password'] != data['password2']:
            raise serializers.ValidationError('Пароли не совпадают!')
        return data

    def create(self, validated_data):
        """Создает нового пользователя"""

        validated_data.pop('password2')
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password']
        )
        return user
