-- Миграция: Добавление поддержки Telegram Topics
-- Дата: 2026-03-04

-- 1. Добавляем поле message_thread_id
ALTER TABLE chat_bindings 
ADD COLUMN message_thread_id BIGINT NULL;

-- 2. Удаляем старый уникальный индекс по chat_id
DROP INDEX IF EXISTS idx_chat_bindings_chat_id;

-- 3. Создаём новый уникальный индекс по паре chat_id + message_thread_id + bitrix_deal_id
CREATE UNIQUE INDEX idx_chat_bindings_unique 
ON chat_bindings(chat_id, message_thread_id, bitrix_deal_id);

-- 4. Создаём индекс для быстрого поиска по топику
CREATE INDEX idx_chat_bindings_thread 
ON chat_bindings(chat_id, message_thread_id);

-- 5. Комментарии
COMMENT ON COLUMN chat_bindings.message_thread_id IS 'ID топика в Telegram Topics (NULL для обычных чатов)';
