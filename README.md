# RECIPE API

REST API для хранения рецептов: создание, поиск, фильтрация и избранное.   
Проект реализован на Django REST Framework с JWT-аутентификацией и документацией Swagger

---

## Стек технологий

Python 3.14  
Django 6.0  
Django REST Framework 3.16  
PostgreSQL / SQLite  
JWT Authentication  
Swagger/OpenAPI документация  
pytest для тестирования

## Возможности

**Рецепты**: CRUD операции, поиск, фильтры  
**Ингредиенты и шаги**: детальное и пошаговое описание рецептов  
**Категории**: организация рецептов по типам  
**Избранное**: добавление любимых рецептов  
**Аутентификация**: JWT токены  
**Фильтрация**: по времени, сложности, калориям  
**Поиск**: по названию, описанию, ингредиентам  
**API документация**: Swagger UI

## Endpoints

### Аутентификация

`POST /api/auth/register/` - регистрация  
`POST /api/auth/login/` - получение JWT токена  
`GET /api/auth/me/` - текущий пользователь  

### Рецепты

`GET /api/recipes/` - список рецептов  
`POST /api/recipes/` - создать рецепт  
`GET /api/recipes/{id}/` - детали рецепта  
`PUT /api/recipes/{id}/` - обновить рецепт  
`DELETE /api/recipes/{id}/` - удалить рецепт  
`GET /api/recipes/random/` - случайный рецепт  
`GET /api/recipes/quick_recipes/` - быстрые рецепты до 30 минут  
`POST /api/recipes/{id}/add_to_favorites/` - добавить в избранное  
`DELETE /api/recipes/{id}/remove_from_favorites/` - удалить из избранного  

### Категории

`GET /api/categories/` - список категорий  
`POST /api/categories/` - создать категорию (только администраторам)

## Установка и запуск

### 1. Клонирование репозитория

```bash
git clone https://github.com/kseniadmay/recipeapi.git
cd recipeapi
```

### 2. Создание и активация виртуального окружения
```bash
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac
```

### 3. Установка зависимостей
```bash
# Зависимости для запуска проекта
pip install -r requirements.txt

# Зависимости для разработки (опционально)
pip install -r requirements-dev.txt 
```

### 4. Настройка переменных окружения

Создайте файл `.env` на основе шаблона:
```bash
cp .env.example .env
```
После этого при необходимости замените значения переменных

### 5. Миграции базы данных
```bash
python manage.py migrate
```

### 6. Создание суперпользователя
```bash
python manage.py createsuperuser
```

### 7. Запуск сервера
```bash
python manage.py runserver
```

## Документация API

После запуска сервера, документация доступна по адресам:

- **Swagger UI**: http://127.0.0.1:8000/docs/
- **ReDoc**: http://127.0.0.1:8000/redoc/
- **Admin панель**: http://127.0.0.1:8000/admin/

## Тестирование
```bash
# Запуск всех тестов
pytest

# С подробным выводом
pytest -v

# С покрытием кода
pytest --cov=recipes
```

## Примеры использования

### Регистрация пользователя
```bash
curl -X POST http://127.0.0.1:8000/api/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "user",
    "email": "user@example.com",
    "password": "pass123",
    "password2": "pass123"
  }'
```

### Создание рецепта
```bash
curl -X POST http://127.0.0.1:8000/api/recipes/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Бутерброд",
    "description": "Вкусный бутерброд с колбаской",
    "cook_time": 5,
    "servings": 1,
    "difficulty": "easy",
    "ingredients": [
      {"name": "Батон", "amount": 2, "unit": "ломтик"},
      {"name": "Колбаса", "amount": 4, "unit": "ломтик"}
    ],
    "steps": [
      {"order": 1, "description": "Взять батон"},
      {"order": 2, "description": "Положить на него колбаску"}
    ]
  }'
```

### Поиск рецептов
```bash
# Поиск по названию
curl http://127.0.0.1:8000/api/recipes/?search=омлет

# Фильтр по времени
curl http://127.0.0.1:8000/api/recipes/?cook_time_max=30

# Фильтр по сложности
curl http://127.0.0.1:8000/api/recipes/?difficulty=easy
```

## Аутентификация

API использует JWT (JSON Web Tokens) для аутентификации.

1. Получите токен через `/api/auth/login/`
2. Добавляйте токен в заголовок: `Authorization: Bearer YOUR_TOKEN`

## Структура проекта
```
RecipeApi/                # Корень репозитория
├── RecipeApi/            # Django проект с настройками
├── recipes/              # Основное приложение с логикой API
│   ├── models.py         # Модели данных
│   ├── serializers.py    # Сериализаторы DRF
│   ├── views.py          # API views
│   ├── urls.py           # URL маршруты
│   ├── filters.py        # Фильтры
│   ├── permissions.py    # Разрешения
│   ├── tests.py          # Тесты
│   └── factories.py      # Фабрики для тестов
├── requirements.txt      # Зависимости для запуска проекта
├── requirements-dev.txt  # Зависимости для разработки
├── .env.example          # Шаблон переменных окружения
└── README.md             # Документация
```

## Автор

GitHub: [@kseniadmay](https://github.com/kseniadmay)  
Email: kseniadmay@gmail.com

## Лицензия

MIT License