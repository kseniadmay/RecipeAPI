import json
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
    category_id = serializers.IntegerField(write_only=True, required=False)

    # Для отображения
    ingredients = IngredientSerializer(many=True, read_only=True)
    steps = StepSerializer(many=True, read_only=True)

    # Для записи
    ingredients_data = serializers.CharField(write_only=True, required=False, allow_blank=True)
    steps_data = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = Recipe
        fields = [
            'id', 'title', 'description', 'author', 'category', 'category_id',
            'cook_time', 'servings', 'difficulty', 'image',
            'calories', 'ingredients', 'steps',
            'ingredients_data', 'steps_data',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'author', 'created_at', 'updated_at']

    def validate_ingredients_data(self, value):
        """Валидация и парсинг ingredients_data"""
        if not value:
            return []

        try:
            # Парсим JSON-строку
            data = json.loads(value)

            # Проверяем что это список
            if not isinstance(data, list):
                raise serializers.ValidationError('Должен быть массив объектов')

            # Проверяем количество
            if not data:
                raise serializers.ValidationError('Рецепт должен содержать хотя бы один ингредиент')
            if len(data) > 50:
                raise serializers.ValidationError('Слишком много ингредиентов (максимум 50)')

            # Проверяем структуру каждого ингредиента
            for i, ingredient in enumerate(data):
                if not isinstance(ingredient, dict):
                    raise serializers.ValidationError(f'Ингредиент #{i + 1} должен быть объектом')
                if 'name' not in ingredient:
                    raise serializers.ValidationError(f'Ингредиент #{i + 1}: отсутствует поле "name"')
                if 'amount' not in ingredient:
                    raise serializers.ValidationError(f'Ингредиент #{i + 1}: отсутствует поле "amount"')
                if 'unit' not in ingredient:
                    raise serializers.ValidationError(f'Ингредиент #{i + 1}: отсутствует поле "unit"')

            return data

        except json.JSONDecodeError as e:
            raise serializers.ValidationError(f'Некорректный JSON: {str(e)}')

    def validate_steps_data(self, value):
        """Валидация и парсинг steps_data"""
        if not value:
            return []

        try:
            # Парсим JSON-строку
            data = json.loads(value)

            # Проверяем что это список
            if not isinstance(data, list):
                raise serializers.ValidationError('Должен быть массив объектов')

            # Проверяем количество
            if not data:
                raise serializers.ValidationError('Рецепт должен содержать хотя бы один шаг')
            if len(data) > 30:
                raise serializers.ValidationError('Слишком много шагов (максимум 30)')

            # Проверяем структуру каждого шага
            for i, step in enumerate(data):
                if not isinstance(step, dict):
                    raise serializers.ValidationError(f'Шаг #{i + 1} должен быть объектом')
                if 'order' not in step:
                    raise serializers.ValidationError(f'Шаг #{i + 1}: отсутствует поле "order"')
                if 'description' not in step:
                    raise serializers.ValidationError(f'Шаг #{i + 1}: отсутствует поле "description"')

            return data

        except json.JSONDecodeError as e:
            raise serializers.ValidationError(f'Некорректный JSON: {str(e)}')

    def validate_cook_time(self, value):
        """Валидация времени приготовления"""
        if value <= 0:
            raise serializers.ValidationError('Время приготовления должно быть больше 0')
        if value > 1440:  # 24 часа
            raise serializers.ValidationError('Время приготовления не может быть больше 24 часов')
        return value

    def validate_servings(self, value):
        """Валидация количества порций"""
        if value <= 0:
            raise serializers.ValidationError('Количество порций должно быть больше 0')
        if value > 100:
            raise serializers.ValidationError('Количество порций не может быть больше 100')
        return value

    def create(self, validated_data):
        """Создает рецепт вместе с ингредиентами и шагами"""

        # Извлекаем данные (уже распарсенные в validate_*)
        ingredients_data = validated_data.pop('ingredients_data', [])
        steps_data = validated_data.pop('steps_data', [])
        category_id = validated_data.pop('category_id', None)

        # Проверяем категорию
        if category_id:
            try:
                validated_data['category'] = Category.objects.get(id=category_id)
            except Category.DoesNotExist:
                raise serializers.ValidationError('Категория не найдена')

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

        # Извлекаем данные (уже распарсенные в validate_*)
        ingredients_data = validated_data.pop('ingredients_data', None)
        steps_data = validated_data.pop('steps_data', None)
        category_id = validated_data.pop('category_id', None)

        # Обновляем категорию
        if category_id:
            try:
                validated_data['category'] = Category.objects.get(id=category_id)
            except Category.DoesNotExist:
                raise serializers.ValidationError('Категория не найдена')

        # Обновляем основные поля рецепта
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Обновляем ингредиенты
        if ingredients_data is not None:
            instance.ingredients.all().delete()
            for ingredient in ingredients_data:
                Ingredient.objects.create(recipe=instance, **ingredient)

        # Обновляем шаги
        if steps_data is not None:
            instance.steps.all().delete()
            for step in steps_data:
                Step.objects.create(recipe=instance, **step)

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
            raise serializers.ValidationError('Рецепт не найден')

        # Проверяем, что уже не добавлен
        if Favorite.objects.filter(user=user, recipe=recipe).exists():
            raise serializers.ValidationError('Рецепт уже в избранном')
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
