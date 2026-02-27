-- Миграция: Добавление таблицы chat_bindings
-- Дата: 2026-02-26

CREATE TABLE IF NOT EXISTS chat_bindings (
    id SERIAL PRIMARY KEY,
    chat_id BIGINT NOT NULL UNIQUE,
    chat_title VARCHAR(255),
    bitrix_deal_id VARCHAR(50) NOT NULL,
    company_name VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chat_bindings_chat_id ON chat_bindings(chat_id);
CREATE INDEX IF NOT EXISTS idx_chat_bindings_bitrix_deal_id ON chat_bindings(bitrix_deal_id);

COMMENT ON TABLE chat_bindings IS 'Привязка Telegram чатов к карточкам Bitrix24';
COMMENT ON COLUMN chat_bindings.chat_id IS 'ID Telegram чата';
COMMENT ON COLUMN chat_bindings.bitrix_deal_id IS 'ID сделки в Bitrix24';
COMMENT ON COLUMN chat_bindings.company_name IS 'Название компании';
