# 🛠 ТРЕБОВАНИЯ К INFRASTRUCTURE ДЛЯ DXBX ONBOARDING BOT

**Версия:** 1.0  
**Дата:** 27.02.2026  
**Статус:** Production Ready

---

## 📋 СОДЕРЖАНИЕ

1. [Архитектура](#архитектура)
2. [Требования к серверу](#требования-к-серверу)
3. [Требования к БД](#требования-к-бд)
4. [Требования к сети](#требования-к-сети)
5. [Безопасность](#безопасность)
6. [Мониторинг](#мониторинг)
7. [Backup](#backup)
8. [Deployment](#deployment)

---

## 🏗 АРХИТЕКТУРА

```
┌─────────────────┐
│   Telegram      │
│     Bot         │
│  (aiogram)      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   FastAPI       │
│   Application   │
│  (uvicorn)      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌─────────────────┐
│   PostgreSQL    │◄────►│   Redis (opt)   │
│   (asyncpg)     │      │   (cache)       │
└─────────────────┘      └─────────────────┘
         │
         ▼
┌─────────────────┐
│   Bitrix24      │
│   REST API      │
└─────────────────┘
```

---

## 🖥 ТРЕБОВАНИЯ К СЕРВЕРУ

### Минимальные (для теста):

| Параметр | Значение |
|----------|----------|
| **CPU** | 2 vCPU |
| **RAM** | 4 GB |
| **Disk** | 20 GB SSD |
| **OS** | Ubuntu 22.04 LTS / Debian 12 |
| **Network** | 100 Mbps |

### Рекомендуемые (production):

| Параметр | Значение |
|----------|----------|
| **CPU** | 4 vCPU |
| **RAM** | 8 GB |
| **Disk** | 50 GB SSD (NVMe) |
| **OS** | Ubuntu 22.04 LTS |
| **Network** | 1 Gbps |
| **Availability** | 99.9% SLA |

### Облачные провайдеры (рекомендации):

| Провайдер | Конфигурация | Цена/мес |
|-----------|--------------|----------|
| **Yandex Cloud** | VM-2 + 8GB + 50GB | ~3000₽ |
| **Selectel** | 2vCPU + 8GB + 50GB | ~2500₽ |
| **Timeweb Cloud** | 2vCPU + 8GB + 60GB | ~2000₽ |
| **Aeza** | 2vCPU + 8GB + 40GB | ~1500₽ |
| **DigitalOcean** | 2vCPU + 8GB + 50GB | ~$24 |
| **Hetzner** | 2vCPU + 8GB + 40GB | ~€10 |

---

## 🗄 ТРЕБОВАНИЯ К БД

### PostgreSQL:

| Параметр | Значение |
|----------|----------|
| **Версия** | 15+ |
| **Порт** | 5432 (внутренний) |
| **User** | onboarding_bot |
| **Database** | onboarding_bot |
| **Pool Size** | 10-20 соединений |
| **Max Connections** | 100 |

### Конфигурация postgresql.conf:

```conf
# Memory
shared_buffers = 2GB
effective_cache_size = 6GB
work_mem = 16MB
maintenance_work_mem = 512MB

# Connections
max_connections = 100
superuser_reserved_connections = 3

# WAL
wal_buffers = 16MB
checkpoint_completion_target = 0.9

# Logging
log_min_duration_statement = 1000
log_checkpoints = on
log_connections = on
log_disconnections = on
log_lock_waits = on

# Timezone
timezone = 'Europe/Moscow'
log_timezone = 'Europe/Moscow'
```

### pg_hba.conf:

```conf
# Local connections
local   all             postgres                                peer
local   all             all                                     peer

# IPv4 local connections
host    all             all             127.0.0.1/32            scram-sha-256
host    all             all             0.0.0.0/0               scram-sha-256

# IPv6 local connections
host    all             all             ::1/128                 scram-sha-256
```

### Подключение из приложения:

```env
DATABASE_URL=postgresql+asyncpg://onboarding_bot:STRONG_PASSWORD@localhost:5432/onboarding_bot
```

---

## 🌐 ТРЕБОВАНИЯ К СЕТИ

### Открытые порты:

| Порт | Протокол | Назначение | Доступ |
|------|----------|------------|--------|
| 443 | HTTPS | Telegram Bot API + Webhooks | Public |
| 80 | HTTP | Redirect to HTTPS | Public |
| 22 | SSH | Administration | Whitelist only |

### Закрытые порты:

| Порт | Протокол | Назначение |
|------|----------|------------|
| 5432 | PostgreSQL | Database |
| 6379 | Redis | Cache (optional) |
| 8000 | Uvicorn | Internal API |

### Firewall (UFW):

```bash
# Enable UFW
ufw --force enable

# Allow SSH (from whitelist)
ufw allow from 10.0.0.0/8 to any port 22 proto tcp

# Allow HTTPS
ufw allow 443/tcp

# Allow HTTP (for Let's Encrypt)
ufw allow 80/tcp

# Deny all other incoming
ufw default deny incoming
ufw default allow outgoing
```

---

## 🔒 БЕЗОПАСНОСТЬ

### 1. PostgreSQL:

```sql
-- Создать пользователя
CREATE USER onboarding_bot WITH ENCRYPTED PASSWORD 'STRONG_PASSWORD';

-- Создать базу
CREATE DATABASE onboarding_bot OWNER onboarding_bot;

-- Гранты
GRANT ALL PRIVILEGES ON DATABASE onboarding_bot TO onboarding_bot;
GRANT ALL ON SCHEMA public TO onboarding_bot;

-- Ограничить подключения
ALTER USER onboarding_bot WITH CONNECTION LIMIT 20;
```

### 2. Переменные окружения:

```env
# .env (НЕ коммитить в git!)
TELEGRAM_BOT_TOKEN=bot_token_here
BITRIX_WEBHOOK_URL=https://company.bitrix24.ru/rest/1/webhook/
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db
WEBHOOK_SECRET_KEY=super_secret_key_min_32_chars
APP_ENV=production
LOG_LEVEL=INFO
```

### 3. SSL/TLS:

```bash
# Let's Encrypt
apt install certbot python3-certbot-nginx
certbot --nginx -d your-domain.com

# Auto-renewal
certbot renew --dry-run
```

### 4. Fail2Ban:

```bash
apt install fail2ban
systemctl enable fail2ban
systemctl start fail2ban
```

---

## 📊 МОНИТОРИНГ

### System metrics:

| Метрика | Threshold | Alert |
|---------|-----------|-------|
| CPU | > 80% | Warning |
| RAM | > 90% | Critical |
| Disk | > 85% | Warning |
| Network | > 90% | Warning |

### Application metrics:

| Метрика | Threshold | Alert |
|---------|-----------|-------|
| Response Time | > 5s | Warning |
| Error Rate | > 1% | Critical |
| DB Connections | > 80% | Warning |
| Queue Size | > 100 | Warning |

### Prometheus + Grafana (опционально):

```yaml
# docker-compose.monitoring.yml
version: '3.8'
services:
  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
  
  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
```

---

## 💾 BACKUP

### PostgreSQL backup:

```bash
#!/bin/bash
# /opt/scripts/backup_db.sh

BACKUP_DIR="/var/backups/postgresql"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="onboarding_bot"
DB_USER="postgres"

# Create backup
pg_dump -U $DB_USER $DB_NAME | gzip > $BACKUP_DIR/$DB_NAME_$DATE.sql.gz

# Delete old backups (keep 7 days)
find $BACKUP_DIR -name "*.sql.gz" -mtime +7 -delete

# Upload to S3 (optional)
# aws s3 cp $BACKUP_DIR/$DB_NAME_$DATE.sql.gz s3://your-bucket/backups/
```

### Cron:

```bash
# Daily backup at 3 AM
0 3 * * * /opt/scripts/backup_db.sh
```

### Restore:

```bash
# Download backup
aws s3 cp s3://your-bucket/backups/onboarding_bot_20260227_030000.sql.gz .

# Restore
gunzip -c onboarding_bot_20260227_030000.sql.gz | psql -U postgres onboarding_bot
```

---

## 🚀 DEPLOYMENT

### Docker Compose (production):

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  bot:
    build: .
    restart: unless-stopped
    environment:
      - DATABASE_URL=postgresql+asyncpg://user:pass@db:5432/onboarding_bot
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
      - BITRIX_WEBHOOK_URL=${BITRIX_WEBHOOK_URL}
      - APP_ENV=production
      - LOG_LEVEL=INFO
    depends_on:
      - db
    networks:
      - bot_network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  db:
    image: postgres:15-alpine
    restart: unless-stopped
    environment:
      - POSTGRES_DB=onboarding_bot
      - POSTGRES_USER=onboarding_bot
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql
    networks:
      - bot_network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U onboarding_bot"]
      interval: 10s
      timeout: 5s
      retries: 5

  nginx:
    image: nginx:alpine
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - bot
    networks:
      - bot_network

volumes:
  postgres_data:

networks:
  bot_network:
    driver: bridge
```

### Deploy script:

```bash
#!/bin/bash
# deploy.sh

set -e

echo "🚀 Deploying DXBX Onboarding Bot..."

# Pull latest code
git pull origin main

# Build and restart
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d --build

# Show logs
docker-compose logs -f bot

echo "✅ Deployment complete!"
```

### Systemd service:

```ini
# /etc/systemd/system/dxbx-bot.service
[Unit]
Description=DXBX Onboarding Bot
After=network.target postgresql.service

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/dxbx-bot
Environment=PATH=/opt/dxbx-bot/venv/bin
ExecStart=/opt/dxbx-bot/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

---

## 📋 CHECKLIST ДЛЯ DEVOPS

### Перед развёртыванием:

- [ ] Сервер создан (4 vCPU, 8GB RAM, 50GB SSD)
- [ ] Ubuntu 22.04 LTS установлен
- [ ] SSH доступ настроен (ключи, не пароль)
- [ ] Firewall настроен (UFW)
- [ ] PostgreSQL 15 установлен
- [ ] БД создана (onboarding_bot)
- [ ] Пользователь БД создан
- [ ] SSL сертификат получен (Let's Encrypt)
- [ ] Docker и Docker Compose установлены
- [ ] Переменные окружения настроены (.env)

### После развёртывания:

- [ ] Бот отвечает на /start
- [ ] Бот отвечает на /add
- [ ] Бот отвечает на /report
- [ ] Scheduler работает (9:00 МСК)
- [ ] Логи пишутся
- [ ] Мониторинг работает
- [ ] Backup настроен
- [ ] Health checks проходят

### Документация:

- [ ] README.md обновлён
- [ ] .env.example актуален
- [ ] Инструкции по deployment есть
- [ ] Контакты для emergency есть

---

## 🆘 EMERGENCY CONTACTS

| Роль | Контакт |
|------|---------|
| **DevOps** | @devops_team |
| **Developer** | @semnse |
| **Database Admin** | @dba_team |

---

**Документация актуальна на 27.02.2026**  
**DXBX Team**
