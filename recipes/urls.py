from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register('categories', views.CategoryViewSet, basename='category')
router.register('recipes', views.RecipeViewSet, basename='recipe')
router.register('favorites', views.FavoriteViewSet, basename='favorite')

urlpatterns = [
    path('', include(router.urls)),
    path('auth/register/', views.register, name='register'),
    path('auth/me/', views.current_user, name='current_user'),
    path('settings/notifications/', views.email_notifications_settings, name='email-notifications-settings'),
]
