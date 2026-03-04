#!/bin/bash
# Скрипт быстрого развёртывания бота
# Использование: ./deploy.sh

set -e

echo "============================================"
echo "🚀 Развёртывание Bitrix Status Bot"
echo "============================================"

# Проверка прав
if [ "$EUID" -ne 0 ]; then 
  echo "❌ Запустите от root (sudo ./deploy.sh)"
  exit 1
fi

# Цвета
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Функции
log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 1. Проверка Docker
log_info "Проверка Docker..."
if ! command -v docker &> /dev/null; then
    log_error "Docker не установлен. Установите вручную."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    log_error "Docker Compose не установлен."
    exit 1
fi

log_info "✓ Docker установлен"

# 2. Копирование .env
if [ ! -f .env ]; then
    log_info "Копирование .env.production в .env..."
    cp .env.production .env
    log_warn "⚠️  Не забудьте заполнить .env!"
    log_warn "   Отредактируйте: nano .env"
    exit 0
fi

# 3. Проверка SSL
if [ ! -d "ssl" ] || [ ! -f "ssl/fullchain.pem" ]; then
    log_warn "SSL сертификаты не найдены!"
    log_info "Создайте директорию ssl и поместите туда:"
    log_info "  - fullchain.pem"
    log_info "  - privkey.pem"
    exit 0
fi

log_info "✓ SSL сертификаты найдены"

# 4. Сборка
log_info "Сборка Docker образов..."
docker-compose -f docker-compose.production.yml build

# 5. Запуск
log_info "Запуск сервисов..."
docker-compose -f docker-compose.production.yml up -d

# 6. Ожидание БД
log_info "Ожидание готовности БД (10 сек)..."
sleep 10

# 7. Миграции
log_info "Применение миграций..."
docker-compose exec -T bot alembic upgrade head

# 8. Проверка
log_info "Проверка здоровья..."
sleep 5
curl -s http://localhost:8000/health || log_warn "⚠️  Health check не прошёл"

# 9. Статус
echo ""
log_info "✓ Развёртывание завершено!"
echo ""
echo "📊 Статус сервисов:"
docker-compose -f docker-compose.production.yml ps
echo ""
echo "📋 Логи:"
echo "  docker-compose -f docker-compose.production.yml logs -f"
echo ""
echo "🔗 Health check:"
echo "  curl http://localhost:8000/health"
echo ""
