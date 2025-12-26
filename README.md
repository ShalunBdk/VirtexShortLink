# Virtex Food Short Links Service

Корпоративный сервис по сокращению ссылок для Virtex Food с административной панелью.

## Возможности

- ✅ Сокращение длинных URL в короткие ссылки (4-5 символов)
- ✅ Case-insensitive коды (vrxf.ru/ABC123 = vrxf.ru/abc123)
- ✅ Создание кастомных коротких ссылок
- ✅ Защита от спама с rate limiting (10 ссылок/час)
- ✅ Валидация URL и защита от вредоносных ссылок
- ✅ Admin панель с JWT аутентификацией
- ✅ Статистика переходов по каждой ссылке
- ✅ Управление ссылками (активация/деактивация, удаление)
- ✅ SQLite база данных с WAL режимом

## Технологический стек

**Backend:**
- FastAPI (Python web framework)
- SQLAlchemy (ORM)
- SQLite (database)
- PyJWT (JWT authentication)
- SlowAPI (rate limiting)
- Pydantic (data validation)
- Bcrypt (password hashing)

**Frontend:**
- Vanilla JavaScript
- HTML5/CSS3
- Фирменный стиль Virtex Food

## Структура проекта

```
ShortLinks/
├── backend/
│   ├── app/
│   │   ├── models/         # Модели БД
│   │   ├── schemas/        # Pydantic схемы
│   │   ├── api/            # API endpoints
│   │   ├── core/           # Бизнес-логика
│   │   ├── utils/          # Вспомогательные функции
│   │   ├── config.py       # Настройки
│   │   ├── database.py     # Подключение к БД
│   │   └── main.py         # Точка входа
│   ├── init_db.py          # Инициализация БД
│   ├── requirements.txt    # Зависимости
│   └── .env                # Переменные окружения
├── frontend/
│   ├── index.html          # Главная страница
│   └── admin/
│       └── index.html      # Admin панель
└── README.md
```

## Установка и запуск

### Вариант 1: Docker (рекомендуется)

**Быстрый старт:**

```bash
# Запуск с Docker Compose
docker-compose up -d

# Приложение доступно на http://localhost:8000
```

Подробнее см. [DOCKER.md](DOCKER.md)

### Вариант 2: Локальная установка

#### 1. Установка зависимостей

```bash
cd backend
pip install -r requirements.txt
```

#### 2. Настройка переменных окружения

Отредактируйте файл `backend/.env`:

```env
DATABASE_URL=sqlite:///./shortlinks.db
SECRET_KEY=your-super-secret-key-change-in-production
BASE_URL=https://vrxf.ru
SHORT_CODE_LENGTH=5
RATE_LIMIT_PER_HOUR=10
```

**Важно:** Измените `SECRET_KEY` на случайную строку в продакшене!

#### 3. Инициализация базы данных

```bash
cd backend
python init_db.py
```

Это создаст таблицы БД и первого суперпользователя:
- **Username:** `admin`
- **Password:** `admin123`
- **Email:** `admin@virtexfood.com`

⚠️ **ВАЖНО:** Измените пароль после первого входа!

#### 4. Запуск сервера

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Сервис будет доступен по адресу:
- Главная страница: http://localhost:8000
- Admin панель: http://localhost:8000/admin
- API документация: http://localhost:8000/docs

## Использование

### Для пользователей

1. Откройте http://localhost:8000
2. Вставьте длинную ссылку в поле ввода
3. Нажмите "Получить короткую ссылку"
4. Скопируйте сокращенную ссылку

### Для администраторов

1. Откройте http://localhost:8000/admin
2. Войдите используя учетные данные
3. Просматривайте статистику и управляйте ссылками

**Возможности admin панели:**
- Просмотр всех созданных ссылок
- Статистика по переходам
- Поиск по коду или URL
- Активация/деактивация ссылок
- Удаление ссылок
- Копирование коротких ссылок

## API Endpoints

### Публичные

```http
POST /api/shorten
Content-Type: application/json

{
  "url": "https://example.com/very-long-url",
  "custom_alias": "mylink"  // опционально
}
```

```http
GET /{short_code}
# Редирект на оригинальную ссылку
```

### Аутентификация (Admin)

```http
POST /api/auth/login
Content-Type: application/x-www-form-urlencoded

username=admin&password=admin123
```

Ответ:
```json
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer"
}
```

### Admin панель

Все admin endpoints требуют JWT токен в заголовке:
```http
Authorization: Bearer <token>
```

```http
GET /api/admin/links?skip=0&limit=100&search=keyword
GET /api/admin/links/{id}
PUT /api/admin/links/{id}
DELETE /api/admin/links/{id}
PATCH /api/admin/links/{id}/toggle
GET /api/admin/stats/overview
GET /api/admin/links/{id}/stats
```

## Особенности реализации

### Case-insensitive коды

Все коды хранятся в нижнем регистре и поиск происходит без учета регистра:
- `vrxf.ru/ABC123` и `vrxf.ru/abc123` ведут на одну ссылку

### Генерация кодов

- Алфавит: a-z, 0-9 (Base36)
- Длина: 5 символов (60+ миллионов комбинаций)
- Автоматическая проверка уникальности

### Защита от спама

1. **Rate Limiting:** 10 ссылок в час с одного IP
2. **URL валидация:** Проверка на корректность и безопасность
3. **Spam фильтр:** Блокировка подозрительных доменов
4. **IP Blacklist:** Возможность заблокировать спамеров

### Статистика

Для каждого перехода записывается:
- IP адрес
- User Agent
- Referer
- Время перехода

## Безопасность

- JWT токены для аутентификации
- Bcrypt хеширование паролей
- CORS middleware
- Валидация всех входных данных
- Защита от SQL injection (SQLAlchemy ORM)
- Rate limiting

## Продакшен деплой

### Рекомендации:

1. **Изменить SECRET_KEY** в `.env`
2. **Изменить пароль админа** после первого входа
3. **Настроить CORS** для конкретных доменов в `main.py`
4. **Использовать HTTPS**
5. **Настроить прокси** (nginx/Apache)
6. **Регулярные бэкапы** базы данных

### Пример с Gunicorn:

```bash
pip install gunicorn
gunicorn app.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Пример nginx конфигурации:

```nginx
server {
    listen 80;
    server_name vrxf.ru;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

## Создание новых админов

Через API (требуется superuser):

```http
POST /api/auth/register
Authorization: Bearer <superuser_token>
Content-Type: application/json

{
  "username": "newadmin",
  "email": "newadmin@virtexfood.com",
  "password": "securepassword",
  "is_superuser": false
}
```

## Мониторинг

Health check endpoint:
```http
GET /health
```

Ответ:
```json
{
  "status": "healthy",
  "service": "Virtex Food Short Links"
}
```
