# Telegram-бот онбординга

Бот для напоминания клиентам о необходимых действиях на этапе внедрения. Интегрируется с Bitrix24 и Telegram.

## 🚀 Запуск

### 1. Создайте базу данных

```bash
"C:\Program Files\PostgreSQL\15\bin\psql.exe" -U postgres -c "CREATE DATABASE onboarding_bot;"
"C:\Program Files\PostgreSQL\15\bin\psql.exe" -U postgres -d onboarding_bot -f init.sql
```

### 2. Настройте .env

Вставьте токен бота в файл `.env`:
```
TELEGRAM_BOT_TOKEN=ваш_токен
```

### 3. Запустите приложение

```bash
venv\Scripts\activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Запустите ngrok

```bash
tools\ngrok.exe config add-authtoken ВАШ_ТОКЕН
tools\ngrok.exe http 8000
```

## 📚 Документация

Полная документация в папке `docs/`.
