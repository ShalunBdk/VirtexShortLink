# Docker Deployment Guide

Это руководство по развертыванию Virtex Food Short Links с помощью Docker.

## Требования

- Docker 20.10+
- Docker Compose 1.29+

## Быстрый старт

### 1. Настройка переменных окружения

Создайте файл `.env` в корневой директории проекта:

```bash
cp .env.example .env
```

Отредактируйте `.env` и установите свои значения:

```env
SECRET_KEY=your-super-secret-key-min-32-characters-long
BASE_URL=https://your-domain.com
```

### 2. Запуск с помощью Docker Compose

```bash
# Сборка и запуск
docker-compose up -d

# Просмотр логов
docker-compose logs -f

# Остановка
docker-compose down

# Остановка с удалением данных
docker-compose down -v
```

### 3. Доступ к приложению

После запуска приложение будет доступно:

- **Главная страница:** http://localhost:8000
- **Admin панель:** http://localhost:8000/admin
- **API документация:** http://localhost:8000/docs

**Учетные данные по умолчанию:**
- Username: `admin`
- Password: `admin123`

⚠️ **ВАЖНО:** Измените пароль сразу после первого входа!

## Сборка образа вручную

```bash
# Сборка образа
docker build -t virtexfood-shortlinks .

# Запуск контейнера
docker run -d \
  --name shortlinks \
  -p 8000:8000 \
  -v shortlinks-data:/app/data \
  -e SECRET_KEY="your-secret-key" \
  -e BASE_URL="https://your-domain.com" \
  virtexfood-shortlinks
```

## Управление контейнером

```bash
# Просмотр логов
docker logs -f virtexfood-shortlinks

# Перезапуск
docker restart virtexfood-shortlinks

# Остановка
docker stop virtexfood-shortlinks

# Удаление
docker rm virtexfood-shortlinks
```

## Персистентность данных

База данных SQLite хранится в Docker volume `shortlinks-data`.

### Резервное копирование

```bash
# Создать backup
docker run --rm \
  -v shortlinks-data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/shortlinks-backup-$(date +%Y%m%d).tar.gz -C /data .

# Восстановить из backup
docker run --rm \
  -v shortlinks-data:/data \
  -v $(pwd):/backup \
  alpine tar xzf /backup/shortlinks-backup-YYYYMMDD.tar.gz -C /data
```

### Экспорт базы данных

```bash
# Копировать БД из контейнера
docker cp virtexfood-shortlinks:/app/data/shortlinks.db ./shortlinks-backup.db
```

## Production Deployment

### С Nginx reverse proxy

**docker-compose.prod.yml:**

```yaml
version: '3.8'

services:
  shortlinks:
    build: .
    container_name: virtexfood-shortlinks
    environment:
      - DATABASE_URL=sqlite:///./data/shortlinks.db
      - SECRET_KEY=${SECRET_KEY}
      - BASE_URL=${BASE_URL}
    volumes:
      - shortlinks-data:/app/data
    restart: always
    networks:
      - web

  nginx:
    image: nginx:alpine
    container_name: shortlinks-nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - shortlinks
    restart: always
    networks:
      - web

volumes:
  shortlinks-data:

networks:
  web:
    driver: bridge
```

**nginx.conf:**

```nginx
upstream shortlinks {
    server shortlinks:8000;
}

server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://shortlinks;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Запуск в production

```bash
docker-compose -f docker-compose.prod.yml up -d
```

## Мониторинг

### Health Check

```bash
# Проверка статуса
curl http://localhost:8000/health

# Health check в Docker
docker inspect --format='{{.State.Health.Status}}' virtexfood-shortlinks
```

### Логирование

```bash
# Реал-тайм логи
docker-compose logs -f shortlinks

# Последние 100 строк
docker-compose logs --tail=100 shortlinks
```

## Обновление

```bash
# Остановить контейнер
docker-compose down

# Обновить код
git pull

# Пересобрать образ
docker-compose build

# Запустить с новым образом
docker-compose up -d
```

## Troubleshooting

### Контейнер не запускается

```bash
# Проверить логи
docker-compose logs shortlinks

# Проверить статус
docker-compose ps
```

### База данных не создается

```bash
# Войти в контейнер
docker exec -it virtexfood-shortlinks bash

# Вручную инициализировать БД
cd /app && python init_db.py
```

### Очистка

```bash
# Удалить все (контейнеры, образы, volumes)
docker-compose down -v --rmi all

# Удалить неиспользуемые образы
docker image prune -a

# Полная очистка Docker
docker system prune -a --volumes
```

## Переменные окружения

| Переменная | Описание | По умолчанию |
|-----------|----------|--------------|
| `DATABASE_URL` | Путь к базе данных SQLite | `sqlite:///./data/shortlinks.db` |
| `SECRET_KEY` | Секретный ключ для JWT | - |
| `BASE_URL` | Базовый URL сервиса | `http://localhost:8000` |
| `SHORT_CODE_LENGTH` | Длина короткого кода | `5` |
| `RATE_LIMIT_PER_HOUR` | Лимит запросов в час | `10` |
| `RATE_LIMIT_PER_DAY` | Лимит запросов в день | `50` |

## Безопасность

1. **Всегда меняйте `SECRET_KEY` в production**
2. Используйте HTTPS в production
3. Измените пароль admin после первого входа
4. Настройте firewall для ограничения доступа
5. Регулярно делайте backup базы данных

## Лицензия

Proprietary - Virtex Food IT Department © 2024
