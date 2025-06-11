# Фудграм

Фудграм — это сервис для публикации и поиска рецептов. Пользователи могут делиться рецептами, добавлять их в избранное, подписываться на других пользователей и формировать список покупок.

## Технологии

- Python 3.10+
- Django 4.x
- Django REST Framework
- PostgreSQL
- Docker, Docker Compose
- Gunicorn
- Nginx

## Пример .env файла

DB_ENGINE=django.db.backends.postgresql
DB_NAME=postgres
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
DB_HOST=db
DB_PORT=5432
SECRET_KEY=your_secret_key
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1

## Запуск проекта локально

1. Клонируйте репозиторий https://github.com/VoroninEgor/foodgram-st

2. Создайте файл `.env` в папке `infra` по образцу `.env.example`.

3. Запустите Docker Compose: docker-compose up -d

4. Миграции и наполнение базы выполняются автоматически при первом запуске.

## Создание суперпользователя

Для доступа к админке выполните команду:
docker-compose exec backend python manage.py createsuperuser
