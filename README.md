# RECIPE API

[![Live Demo](https://img.shields.io/badge/demo-live-brightgreen)](https://recipeapi.up.railway.app/docs/)

REST API для хранения рецептов: создание, поиск, фильтрация и избранное.  
Проект реализован на Django REST Framework с JWT-аутентификацией и документацией Swagger.

---

## Live Demo

**Swagger документация:**  
https://recipeapi.up.railway.app/docs/


### 1. Тестовый пользователь
Используйте этот аккаунт для проверки API:

Username: `demo`  
Password: `demo1234`


### 2. Получение токена
API защищён JWT. Токен нужен для всех операций, которые требуют авторизации: создание и редактирование рецептов, 
добавление в избранное, доступ к личным данным.
Без токена защищённые запросы вернут ошибку `401 Unauthorized`.

Отправьте POST-запрос на логин пользователя `demo`:

```http
POST https://recipeapi.up.railway.app/api/auth/login/
Content-Type: application/json

{
  "username": "demo",
  "password": "demo1234"
}
```
В ответе получите JSON с полем `access` - это ваш токен.

Пример ответа сервера:
```JSON
{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```


### 3. Использование токена

В Swagger:
1. Нажмите `Authorize`
2. Вставьте: `Bearer <введите_ваш_токен>`  

Или в любом HTTP‑клиенте используйте заголовок:  
`Authorization: Bearer <введите_ваш_токен>`

После этого защищённые endpoints будут доступны для тестирования.  

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
    "password": "pass1234",
    "password2": "pass1234"
  }'
```

### Создание рецепта
```bash
curl -X POST http://127.0.0.1:8000/api/recipes/ \
  -H "Authorization: Bearer <введите_ваш_токен>" \
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

## Структура проекта
```
RecipeAPI/                # Корень репозитория
├── RecipeAPI/            # Django проект с настройками
├── recipes/              # Основное приложение с логикой API
│   ├── models.py         # Модели данных
│   ├── serializers.py    # Сериализаторы DRF
│   ├── views.py          # API views
│   ├── urls.py           # URL маршруты
│   ├── filters.py        # Фильтры
│   ├── permissions.py    # Разрешения
│   ├── tests.py          # Тесты
│   └── factories.py      # Фабрики для тестов
├── manage.py             # Точка входа Django
├── requirements.txt      # Зависимости для запуска проекта
├── requirements-dev.txt  # Зависимости для разработки
├── Dockerfile            # Docker образ проекта
├── docker-compose.yml    # Docker Compose конфигурация
├── entrypoint.sh         # Скрипт запуска Docker контейнера
├── .env.example          # Шаблон переменных окружения
# ├── pytest.ini          # Настройки тестирования
# ├── conftest.py         # Общие фикстуры для тестов
# ├── Procfile            # Для деплоя на Railway
# ├── runtime.txt         # Версия Python для хостинга
└── README.md             # Документация
```

## Автор

GitHub: [@kseniadmay](https://github.com/kseniadmay)  
Email: kseniadmay@gmail.com

## Лицензия

MIT License