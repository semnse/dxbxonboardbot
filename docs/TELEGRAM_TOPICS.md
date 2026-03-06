# 📱 Поддержка Telegram Topics

**Дата:** 2026-03-04  
**Статус:** ✅ Готово

---

## 🎯 Задача

Бот должен привязываться к **конкретному топику** (thread) в Telegram Topics группе, а не ко всей группе целиком.

### Пример использования:

```
Группа "Внедрение клиентов" (Topics)
├── Топик 1: "General" (ID: 1)
├── Топик 2: "ООО Восход" (ID: 2) → привязка к карточке 12345
├── Топик 3: "ООО Коломбус" (ID: 3) → привязка к карточке 67890
└── Топик 4: "ООО Рассвет" (ID: 4) → привязка к карточке 11111
```

**Результат:**
- Команда `/add 12345` в топике "ООО Восход" → отчёты только по Восходу
- Команда `/add 67890` в топике "ООО Коломбус" → отчёты только по Коломбусу

---

## 🔧 Реализация

### 1. Обновлена модель БД

**Файл:** `app/database/models.py`

```python
class ChatBinding(Base):
    __tablename__ = "chat_bindings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    message_thread_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)  # ← НОВОЕ ПОЛЕ
    chat_title: Mapped[str] = mapped_column(String(255), nullable=True)
    bitrix_deal_id: Mapped[str] = mapped_column(String(50), nullable=False)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Уникальная пара chat_id + message_thread_id + bitrix_deal_id
    __table_args__ = (
        Index("idx_chat_bindings_unique", "chat_id", "message_thread_id", "bitrix_deal_id", unique=True),
    )
```

### 2. Миграция БД

**Файл:** `migrations/003_add_topics_support.sql`

```sql
-- Добавляем поле message_thread_id
ALTER TABLE chat_bindings 
ADD COLUMN message_thread_id BIGINT NULL;

-- Создаём уникальный индекс по паре chat_id + message_thread_id
CREATE UNIQUE INDEX idx_chat_bindings_unique 
ON chat_bindings(chat_id, message_thread_id, bitrix_deal_id);

-- Индекс для быстрого поиска по топику
CREATE INDEX idx_chat_bindings_thread 
ON chat_bindings(chat_id, message_thread_id);
```

### 3. Обновлён репозиторий

**Файл:** `app/database/repository.py`

```python
class ChatBindingRepository:
    async def get_by_chat_and_thread(
        self,
        chat_id: int,
        message_thread_id: Optional[int] = None
    ) -> List[ChatBinding]:
        """Получить привязки по чату и топику"""
        
        if message_thread_id:
            # Для Topics
            SELECT * FROM chat_bindings 
            WHERE chat_id = %s AND message_thread_id = %s
        else:
            # Для обычных чатов
            SELECT * FROM chat_bindings 
            WHERE chat_id = %s AND message_thread_id IS NULL
```

### 4. Обновлена команда /add

**Файл:** `app/bot/commands.py`

```python
@dp.message(Command("add"))
async def cmd_add(message: Message):
    # Получаем ID топика
    message_thread_id = message.message_thread_id  # ← Для Topics
    
    # Сохраняем привязку с учётом топика
    await chat_binding_repo.create(
        chat_id=message.chat.id,
        message_thread_id=message_thread_id,  # ← Сохраняем ID топика
        bitrix_deal_id=bitrix_id,
        company_name=company_name
    )
```

### 5. Обновлена команда /report

```python
@dp.message(Command("report"))
async def cmd_report(message: Message):
    # Получаем ID топика
    message_thread_id = message.message_thread_id
    
    # Ищем привязку только для этого топика
    bindings = await repo.get_by_chat_and_thread(
        message.chat.id,
        message_thread_id
    )
```

---

## 📊 Как это работает

### Для обычных чатов (без Topics)

```
chat_id: -1003876900857
message_thread_id: NULL
```

### Для Topics чатов

```
Топик 1 (General):
  chat_id: -1003876900857
  message_thread_id: 1

Топик 2 (ООО Восход):
  chat_id: -1003876900857
  message_thread_id: 2  ← Уникальный ID топика

Топик 3 (ООО Коломбус):
  chat_id: -1003876900857
  message_thread_id: 3  ← Другой ID топика
```

---

## 🧪 Тестирование

### 1. Создайте Topics группу в Telegram

1. Создайте группу
2. Включите режим "Форум" (Topics)
3. Создайте несколько топиков

### 2. Добавьте бота в группу

```
/add @docsinbox_onboardbot
```

### 3. Привяжите карточки к разным топикам

**В топике "ООО Восход":**
```
/add 12345
```

**В топике "ООО Коломбус":**
```
/add 67890
```

### 4. Проверьте отчёты

**В топике "ООО Восход":**
```
/report
```
→ Должен прийти отчёт только по карточке 12345

**В топике "ООО Коломбус":**
```
/report
```
→ Должен прийти отчёт только по карточке 67890

---

## 📋 Логи

После обновления бот будет логировать:

```
INFO:app.bot.commands:Topic detected: thread_id=2
INFO:app.bot.commands:Created binding: chat=-1003876900857, thread=2, bitrix=12345
INFO:app.bot.commands:Cached binding with topic: chat=-1003876900857, thread=2, bitrix=12345
```

---

## ⚠️ Важные замечания

1. **Обратная совместимость:**
   - Для обычных чатов (без Topics) `message_thread_id = NULL`
   - Старые привязки продолжат работать

2. **Уникальность:**
   - Уникальная пара `chat_id + message_thread_id + bitrix_deal_id`
   - В одном топике не может быть двух привязок к одной карточке

3. **Кэширование:**
   - Для Topics: ключ кэша `"{chat_id}_thread_{message_thread_id}"`
   - Для обычных чатов: ключ кэша `"{chat_id}"`

---

## 🚀 Готово к использованию!

Бот теперь поддерживает Telegram Topics и может работать с несколькими топиками в одной группе.
