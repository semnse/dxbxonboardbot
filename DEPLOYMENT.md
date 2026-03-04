# 🚀 Deployment Guide - Bitrix Status Telegram Bot

**Версия:** 1.0.0  
**Дата:** 2026-03-04  
**Статус:** Production Ready

---

## 📋 Требования

### Сервер

| Параметр | Минимум | Рекомендуется |
|----------|---------|---------------|
| CPU | 2 ядра | 4 ядра |
| RAM | 4 GB | 8 GB |
| Disk | 20 GB SSD | 40 GB SSD |
| OS | Ubuntu 22.04 LTS | Ubuntu 22.04 LTS |

### Домен

- Доменное имя (например, `bot.company.ru`)
- SSL сертификат (Let's Encrypt)

---

## 🔧 Предварительная настройка

### 1. Установка Docker

```bash
# Обновление системы
sudo apt update && sudo apt upgrade -y

# Установка Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Добавление пользователя в группу docker
sudo usermod -aG docker $USER

# Установка Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Проверка
docker --version
docker-compose --version
```

### 2. Настройка домена

```bash
# В DNS настройте A запись:
# bot.company.ru → IP_вашего_сервера
```

### 3. Получение SSL сертификата

```bash
# Установка Certbot
sudo apt install certbot python3-certbot-nginx -y

# Получение сертификата
sudo certbot certonly --standalone -d bot.company.ru

# Сертификаты будут в:
# /etc/letsencrypt/live/bot.company.ru/
```

---

## 📦 Развёртывание

### 1. Клонирование репозитория

```bash
cd /opt
sudo git clone https://github.com/semnse/dxbxonboardbot.git bot
cd bot
```

### 2. Настройка переменных окружения

```bash
# Копирование .env.production в .env
sudo cp .env.production .env

# Редактирование .env
sudo nano .env
```

**Заполните:**
- `TELEGRAM_BOT_TOKEN` — токен от @BotFather
- `BOT_WEBHOOK_URL` — https://bot.company.ru/webhook/telegram
- `BOT_SECRET_TOKEN` — любой секретный ключ
- `BITRIX_DOMAIN` — ваш домен Bitrix24
- `BITRIX_WEBHOOK_KEY` — ключ вебхука Bitrix
- `DATABASE_URL` — пароль PostgreSQL
- `WEBHOOK_SECRET_KEY` — любой секретный ключ

### 3. Настройка SSL для Nginx

```bash
# Копирование сертификатов
sudo mkdir -p ssl
sudo cp /etc/letsencrypt/live/bot.company.ru/fullchain.pem ssl/
sudo cp /etc/letsencrypt/live/bot.company.ru/privkey.pem ssl/

# Проверка прав
sudo chmod 644 ssl/fullchain.pem
sudo chmod 600 ssl/privkey.pem
```

### 4. Запуск через Docker Compose

```bash
# Сборка образов
sudo docker-compose build

# Запуск сервисов
sudo docker-compose up -d

# Проверка статуса
sudo docker-compose ps
```

### 5. Применение миграций БД

```bash
# Применение миграций Alembic
sudo docker-compose exec bot alembic upgrade head

# Проверка таблиц
sudo docker-compose exec db psql -U bot_user -d onboarding_bot -c "\dt"
```

### 6. Настройка вебхука Telegram

```bash
# Регистрация webhook в Telegram
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook" \
  -d "url=https://bot.company.ru/webhook/telegram" \
  -d "secret_token=YOUR_SECRET_TOKEN"

# Проверка
curl "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo"
```

---

## 🔍 Мониторинг

### Логи

```bash
# Все логи
sudo docker-compose logs -f

# Логи бота
sudo docker-compose logs -f bot

# Логи воркера
sudo docker-compose logs -f worker

# Логи БД
sudo docker-compose logs -f db
```

### Health Check

```bash
# Проверка здоровья
curl https://bot.company.ru/health

# Ответ:
# {"status":"ok","db":"ok"}
```

### Статус сервисов

```bash
# Список контейнеров
sudo docker-compose ps

# Использование ресурсов
sudo docker stats
```

---

## 🔄 Обновление

```bash
# Переход в директорию
cd /opt/bot

# Pull изменений
sudo git pull

# Пересборка
sudo docker-compose build

# Перезапуск
sudo docker-compose up -d

# Применение миграций
sudo docker-compose exec bot alembic upgrade head
```

---

## 🛡️ Безопасность

### Firewall (UFW)

```bash
# Установка
sudo apt install ufw -y

# Настройка
sudo ufw allow 22/tcp      # SSH
sudo ufw allow 80/tcp      # HTTP (для Let's Encrypt)
sudo ufw allow 443/tcp     # HTTPS
sudo ufw enable

# Проверка
sudo ufw status
```

### Автоматическое обновление SSL

```bash
# Cron задача для обновления
sudo crontab -e

# Добавьте строку:
0 3 * * * certbot renew --quiet && docker-compose restart nginx
```

### Резервное копирование БД

```bash
# Скрипт backup.sh
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
docker exec onboarding_postgres pg_dump -U bot_user onboarding_bot > /backups/db_$DATE.sql

# Добавление в cron
0 2 * * * /opt/bot/scripts/backup.sh
```

---

## 📊 Сервисы

| Сервис | Порт | Описание |
|--------|------|----------|
| bot | 8000 | FastAPI + aiogram |
| worker | — | Celery воркер |
| beat | — | Celery планировщик |
| db | 5432 | PostgreSQL 15 |
| redis | 6379 | Redis 7 |
| nginx | 80, 443 | Reverse proxy |

---

## 🆘 Troubleshooting

### Бот не запускается

```bash
# Проверка логов
sudo docker-compose logs bot

# Проверка .env
sudo docker-compose exec bot python -c "from app.config import settings; print(settings)"
```

### Ошибка БД

```bash
# Перезапуск БД
sudo docker-compose restart db

# Проверка подключения
sudo docker-compose exec db psql -U bot_user -d onboarding_bot -c "SELECT 1"
```

### Webhook не работает

```bash
# Проверка webhook info
curl "https://api.telegram.org/bot<TOKEN>/getWebhookInfo"

# Перерегистрация
curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook?url=https://bot.company.ru/webhook/telegram"
```

---

## 📞 Контакты

При проблемах обращайтесь к разработчику.
