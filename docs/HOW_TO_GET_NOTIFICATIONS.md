# 📬 Как получать уведомления от бота

**Статус:** Бот запущен ✅

---

## 🎯 Вариант 1: Через групповой чат (рекомендуется)

1. Создай чат в Telegram (с топиками или без)
2. Добавь бота `@docsinbox_onboardbot`
3. Напиши `/add <ID карточки>`
4. Готово! Отчёты будут приходить каждое утро в 9:00 МСК

---

## 🎯 Вариант 2: Личная подписка (через БД)

Если хочешь получать уведомления лично себе:

### 1. Узнай свой Telegram ID

Напиши боту [@userinfobot](https://t.me/userinfobot) → он вернёт твой ID

### 2. Добавь себя в БД

```bash
# Подключись к БД
docker exec -it onboarding_postgres psql -U postgres -d onboarding_bot

# Добавь пользователя (ЗАМЕНИ 123456789 на свой ID!)
INSERT INTO bot_users (tg_id, username, first_name, is_active)
VALUES (123456789, 'your_username', 'Your Name', TRUE)
ON CONFLICT (tg_id) DO UPDATE SET is_active = TRUE;

# Добавь подписку (18306 = ООО Фортуна)
INSERT INTO bot_subscriptions (user_id, bitrix_item_id, bitrix_fields)
SELECT id, '18306', '{"title": "ООО Фортуна"}'::jsonb
FROM bot_users
WHERE tg_id = 123456789;
```

### 3. Проверь

```sql
SELECT u.tg_id, u.username, s.bitrix_item_id
FROM bot_users u
JOIN bot_subscriptions s ON u.id = s.user_id
WHERE u.is_active = TRUE;
```

---

## ⏰ Расписание

| Задача | Время | Что делает |
|--------|-------|------------|
| `fetch_daily_statuses` | 08:00 МСК | Забирает статусы из Bitrix |
| `send_daily_reports` | 09:00 МСК | Отправляет отчёты пользователям |

---

## 📊 Что в отчёте

```
📊 Ежедневный отчёт Bitrix24

📌 ООО Фортуна
Статус: `DT1070_38:UC_IM0YI8`
```

---

## 🔧 Управление подпиской

### Отключить рассылку

```sql
UPDATE bot_users SET is_active = FALSE WHERE tg_id = 123456789;
```

### Включить обратно

```sql
UPDATE bot_users SET is_active = TRUE WHERE tg_id = 123456789;
```

### Добавить ещё карточку

```sql
INSERT INTO bot_subscriptions (user_id, bitrix_item_id)
SELECT id, '6784'  -- ID карточки
FROM bot_users
WHERE tg_id = 123456789;
```

---

## 🆘 Если не приходит

1. Проверь что бот запущен:
   ```bash
   curl http://localhost:8000/health
   ```

2. Проверь что ты в БД:
   ```bash
   docker exec -i onboarding_postgres psql -U postgres -d onboarding_bot -c "SELECT * FROM bot_users WHERE tg_id = 123456789;"
   ```

3. Проверь логи Celery:
   ```bash
   docker-compose logs -f worker
   docker-compose logs -f beat
   ```

---

## ✅ Готово!

Теперь ты будешь получать отчёты каждое утро в 9:00 МСК! 🚀
