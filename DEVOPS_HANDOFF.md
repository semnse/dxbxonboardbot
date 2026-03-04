# 📦 Передача проекта DevOps инженеру

**Проект:** Bitrix Status Telegram Bot  
**Версия:** 1.0.0  
**Дата:** 2026-03-04

---

## 📋 Чек-лист для DevOps

### 1. Сервер

- [ ] Выделен сервер (Ubuntu 22.04 LTS)
- [ ] CPU: 4 ядра, RAM: 8 GB, Disk: 40 GB SSD
- [ ] Настроен firewall (UFW: 22, 80, 443)
- [ ] Установлен Docker + Docker Compose
- [ ] Пользователь добавлен в группу `docker`

### 2. Домен и SSL

- [ ] Куплен домен (например, `bot.company.ru`)
- [ ] Настроена DNS A запись → IP сервера
- [ ] Получен SSL сертификат (Let's Encrypt)
- [ ] Сертификаты в `/etc/letsencrypt/live/bot.company.ru/`

### 3. Переменные окружения

Заполнить файл `.env`:

```bash
TELEGRAM_BOT_TOKEN=1234567890:ABCdef...
BOT_WEBHOOK_URL=https://bot.company.ru/webhook/telegram
BOT_SECRET_TOKEN=xxxxxxxxxx

BITRIX_DOMAIN=company.bitrix24.ru
BITRIX_WEBHOOK_KEY=xxxxxxxxxxxxxxxxxxxx

DATABASE_URL=postgresql+asyncpg://bot_user:PASSWORD@localhost:5432/onboarding_bot
REDIS_URL=redis://localhost:6379/0

APP_ENV=production
TIMEZONE=Europe/Moscow
```

### 4. Развёртывание

```bash
# Переход в директорию
cd /opt/bot

# Запуск скрипта развёртывания
sudo ./deploy.sh

# ИЛИ вручную:
docker-compose -f docker-compose.production.yml build
docker-compose -f docker-compose.production.yml up -d
docker-compose exec bot alembic upgrade head
```

### 5. Настройка Telegram Webhook

```bash
# Регистрация webhook
curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook" \
  -d "url=https://bot.company.ru/webhook/telegram" \
  -d "secret_token=<SECRET>"

# Проверка
curl "https://api.telegram.org/bot<TOKEN>/getWebhookInfo"
```

### 6. Проверка

```bash
# Статус сервисов
docker-compose -f docker-compose.production.yml ps

# Логи
docker-compose -f docker-compose.production.yml logs -f

# Health check
curl https://bot.company.ru/health
```

---

## 📁 Файлы для передачи

### Основные

- ✅ `docker-compose.production.yml` — production конфигурация
- ✅ `.env.production` — шаблон переменных
- ✅ `Dockerfile` — бот
- ✅ `Dockerfile.worker` — воркер
- ✅ `nginx/nginx.conf` — nginx конфигурация
- ✅ `deploy.sh` — скрипт развёртывания
- ✅ `DEPLOYMENT.md` — полная инструкция
- ✅ `requirements.txt` — зависимости

### Приложение

- ✅ `app/` — весь код
- ✅ `alembic/` — миграции БД
- ✅ `init.sql` — инициализация БД

### Документация

- ✅ `README.md` — основная документация
- ✅ `DEPLOYMENT.md` — инструкция по развёртыванию
- ✅ `docs/` — дополнительная документация

---

## 🔧 Команды для управления

### Запуск

```bash
cd /opt/bot
sudo docker-compose -f docker-compose.production.yml up -d
```

### Остановка

```bash
sudo docker-compose -f docker-compose.production.yml down
```

### Логи

```bash
# Все
sudo docker-compose -f docker-compose.production.yml logs -f

# Бот
sudo docker-compose -f docker-compose.production.yml logs -f bot

# Воркер
sudo docker-compose -f docker-compose.production.yml logs -f worker
```

### Обновление

```bash
cd /opt/bot
sudo git pull
sudo docker-compose -f docker-compose.production.yml build
sudo docker-compose -f docker-compose.production.yml up -d
sudo docker-compose exec bot alembic upgrade head
```

### Резервное копирование

```bash
# БД
docker exec onboarding_postgres pg_dump -U bot_user onboarding_bot > backup.sql

# Восстановление
docker exec -i onboarding_postgres psql -U bot_user onboarding_bot < backup.sql
```

---

## 📊 Мониторинг

### Health Check

```bash
curl https://bot.company.ru/health
# Ожидаемый ответ: {"status":"ok","db":"ok"}
```

### Docker Stats

```bash
docker stats
```

### Проверка сервисов

```bash
# Бот
curl http://localhost:8000/

# БД
docker exec onboarding_postgres psql -U bot_user -d onboarding_bot -c "SELECT 1"

# Redis
docker exec onboarding_redis redis-cli ping
```

---

## 🆘 Troubleshooting

### Бот не запускается

```bash
# Проверка логов
docker-compose logs bot

# Проверка конфигурации
docker-compose exec bot python -c "from app.config import settings; print(settings)"
```

### Ошибка подключения к БД

```bash
# Перезапуск БД
docker-compose restart db

# Проверка
docker-compose exec db psql -U bot_user -d onboarding_bot -c "SELECT 1"
```

### Webhook не работает

```bash
# Проверка
curl "https://api.telegram.org/bot<TOKEN>/getWebhookInfo"

# Перерегистрация
curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook?url=https://bot.company.ru/webhook/telegram"
```

---

## 📞 Контакты

**Разработчик:** [ваш контакт]  
**Репозиторий:** https://github.com/semnse/dxbxonboardbot  
**Документация:** DEPLOYMENT.md

---

## ✅ Готово!

После выполнения всех шагов бот готов к работе!
