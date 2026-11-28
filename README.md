# Django Email Auth API

Учебный Django REST API с кастомным пользователем, входом по email, JWT и Swagger UI.

## Установка и запуск

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
python -c "from secrets import token_urlsafe; from pathlib import Path; p=Path('.env'); p.write_text(p.read_text().replace('replace-this-with-a-long-random-secret', token_urlsafe(48)))"
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

При создании суперпользователя Django запросит `email` и обязательный `phone_number` формата `+996XXXXXXXXX`.

## API

- `POST /api/register/` — регистрация; `phone_number` и `birthdate` можно пропустить.
  Дата рождения задается как `YYYY-MM-DD`.
- `POST /api/login/` — вход по email и паролю; возвращает access и refresh JWT.
- `POST /api/token/` — получение стандартной пары Simple JWT.
- `POST /api/token/refresh/` — получение нового access JWT.
- `GET /api/me/` — данные вошедшего пользователя (нужен `Authorization: Bearer <access>`).
- `GET /api/schema/` — OpenAPI-схема.
- `GET /api/docs/` — Swagger UI.
- `POST /api/products/` — создание продукта с access JWT; дата рождения в токене должна
  подтверждать возраст 18 лет или старше.
- `/admin/` — Django Admin.

Номер телефона задается только в формате E.164 `+996` и ровно 9 цифр после кода страны, например `+996555123456`. Для обычного пользователя поле необязательно; для суперпользователя оно обязательно.

Проверки проекта:

```bash
python manage.py check
python manage.py test
```
