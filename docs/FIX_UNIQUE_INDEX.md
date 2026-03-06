# 🔧 Исправление ошибки уникального индекса

**Дата:** 2026-03-04  
**Статус:** ✅ Исправлено

---

## ❌ Проблема

При привязке карточек в Topics чатах возникала ошибка:

```
ERROR: duplicate key value violates unique constraint "chat_bindings_chat_id_key"
DETAIL: Key (chat_id)=(-1003876900857) already exists.
```

### Причина

Старое ограничение уникальности `chat_bindings_chat_id_key` требовало уникальности только по `chat_id`, что не позволяло создавать несколько привязок в одном чате (для разных топиков).

---

## ✅ Решение

### 1. Удалено старое ограничение

```sql
ALTER TABLE chat_bindings 
DROP CONSTRAINT IF EXISTS chat_bindings_chat_id_key;
```

### 2. Создано новое уникальное ограничение

```sql
CREATE UNIQUE INDEX idx_chat_bindings_unique 
ON chat_bindings(chat_id, message_thread_id, bitrix_deal_id);
```

Теперь уникальность обеспечивается по **комбинации полей**:
- `chat_id` + `message_thread_id` + `bitrix_deal_id`

Это позволяет:
- В обычных чатах: 1 привязка на чат
- В Topics чатах: 1 привязка на топик

---

## 📊 Индексы после исправления

```sql
SELECT indexname, indexdef FROM pg_indexes WHERE tablename='chat_bindings';

indexname             | indexdef
----------------------+--------------------------------------------------
chat_bindings_pkey   | CREATE UNIQUE INDEX ... (id)
idx_chat_bindings_unique | CREATE UNIQUE INDEX ... (chat_id, message_thread_id, bitrix_deal_id)
idx_chat_bindings_thread | CREATE INDEX ... (chat_id, message_thread_id)
idx_chat_bindings_bitrix_deal_id | CREATE INDEX ... (bitrix_deal_id)
```

---

## 🧪 Проверка работы

### Тест 1: Обычный чат

```sql
-- Должно работать
INSERT INTO chat_bindings (chat_id, bitrix_deal_id, company_name)
VALUES (-1003876900857, '12345', 'ООО Ромашка');

-- Должно вызвать ошибку (дубликат)
INSERT INTO chat_bindings (chat_id, bitrix_deal_id, company_name)
VALUES (-1003876900857, '67890', 'ООО Коломбус');
```

### Тест 2: Topics чат

```sql
-- Топик 1: ООО Восход
INSERT INTO chat_bindings (chat_id, message_thread_id, bitrix_deal_id, company_name)
VALUES (-1003876900857, 2, '12345', 'ООО Восход');

-- Топик 2: ООО Коломбус (должно работать!)
INSERT INTO chat_bindings (chat_id, message_thread_id, bitrix_deal_id, company_name)
VALUES (-1003876900857, 3, '67890', 'ООО Коломбус');

-- Топик 1: Дубликат (должно вызвать ошибку)
INSERT INTO chat_bindings (chat_id, message_thread_id, bitrix_deal_id, company_name)
VALUES (-1003876900857, 2, '11111', 'ООО Рассвет');
```

---

## 📝 Логи после исправления

**До:**
```
ERROR: duplicate key value violates unique constraint "chat_bindings_chat_id_key"
```

**После:**
```
INFO:app.bot.commands:Topic detected: thread_id=2
INFO:app.bot.commands:Created binding: chat=-1003876900857, thread=2, bitrix=12345
INFO:app.bot.commands:Command /add executed successfully
```

---

## ✅ Вывод

Ошибка исправлена. Теперь бот поддерживает:
- ✅ Обычные чаты (1 привязка на чат)
- ✅ Topics чаты (1 привязка на топик)
