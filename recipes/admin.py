from django.contrib import admin
from .models import Category, Recipe, Ingredient, Step, Favorite, UserProfile


class IngredientInline(admin.TabularInline):
    model = Ingredient
    extra = 1


class StepInline(admin.TabularInline):
    model = Step
    extra = 1


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'email_notifications', 'created_at')
    list_filter = ('email_notifications', 'created_at')
    search_fields = ('user__username', 'user__email')


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'created_at']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name']


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ['title', 'author', 'category', 'difficulty', 'cook_time', 'servings', 'created_at']
    list_filter = ['difficulty', 'category', 'created_at']
    search_fields = ['title', 'description']
    inlines = [IngredientInline, StepInline]
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Основная информация', {
            'fields': ('title', 'description', 'author', 'category', 'image')
        }),
        ('Характеристики', {
            'fields': ('cook_time', 'servings', 'difficulty', 'calories')
        }),
        ('Метаданные', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ['name', 'recipe', 'amount', 'unit']
    list_filter = ['recipe']
    search_fields = ['name']


@admin.register(Step)
class StepAdmin(admin.ModelAdmin):
    list_display = ['recipe', 'order', 'description_preview']
    list_filter = ['recipe']

    def description_preview(self, obj):
        return obj.description[:50] + '...'

    description_preview.short_description = 'Описание'


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ['user', 'recipe', 'added_at']
    list_filter = ['added_at']
    search_fields = ['user__username', 'recipe__title']
