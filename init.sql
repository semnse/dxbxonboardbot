-- ============================================
-- Инициализация базы данных
-- Создание таблиц + заполнение справочников
-- ============================================

-- ============================================
-- CHAT BINDINGS (Привязки Telegram чатов к Bitrix)
-- ============================================
CREATE TABLE IF NOT EXISTS chat_bindings (
    id SERIAL PRIMARY KEY,
    chat_id BIGINT NOT NULL,
    message_thread_id BIGINT,  -- NULL для обычных чатов, ID топика для Topics
    chat_title VARCHAR(255),
    bitrix_deal_id VARCHAR(50) NOT NULL,
    company_name VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(chat_id, message_thread_id, bitrix_deal_id),
    UNIQUE(chat_id, bitrix_deal_id)
);

CREATE INDEX IF NOT EXISTS idx_chat_bindings_chat_id ON chat_bindings(chat_id);
CREATE INDEX IF NOT EXISTS idx_chat_bindings_bitrix_deal_id ON chat_bindings(bitrix_deal_id);
CREATE INDEX IF NOT EXISTS idx_chat_bindings_active ON chat_bindings(is_active) WHERE is_active = TRUE;

-- ============================================
-- КЛИЕНТЫ (Торговые точки)
-- ============================================
CREATE TABLE IF NOT EXISTS clients (
    id SERIAL PRIMARY KEY,
    bitrix_deal_id VARCHAR(50) UNIQUE NOT NULL,
    company_name VARCHAR(255) NOT NULL,
    telegram_chat_id BIGINT,
    telegram_chat_username VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_clients_bitrix_deal_id ON clients(bitrix_deal_id);
CREATE INDEX IF NOT EXISTS idx_clients_telegram_chat_id ON clients(telegram_chat_id) WHERE telegram_chat_id IS NOT NULL;

-- ============================================
-- ПРОДУКТЫ (Купленные модули)
-- ============================================
CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE
);

-- ============================================
-- ФУНКЦИИ ПРОДУКТОВ (Что доступно при покупке)
-- ============================================
CREATE TABLE IF NOT EXISTS product_features (
    id SERIAL PRIMARY KEY,
    product_code VARCHAR(50) NOT NULL REFERENCES products(code),
    feature_text VARCHAR(255) NOT NULL,
    display_order INT DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    UNIQUE(product_code, feature_text)
);

-- ============================================
-- СВЯЗЬ КЛИЕНТ-ПРОДУКТЫ (Что купил клиент)
-- ============================================
CREATE TABLE IF NOT EXISTS client_products (
    id SERIAL PRIMARY KEY,
    client_id INT NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    product_code VARCHAR(50) NOT NULL REFERENCES products(code),
    purchased_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,
    UNIQUE(client_id, product_code)
);

CREATE INDEX IF NOT EXISTS idx_client_products_client_id ON client_products(client_id);

-- ============================================
-- ПРИЧИНЫ ОЖИДАНИЯ (Словарь)
-- ============================================
CREATE TABLE IF NOT EXISTS wait_reasons (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    bitrix_field_value VARCHAR(100),
    product_code VARCHAR(50) REFERENCES products(code),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_wait_reasons_code ON wait_reasons(code);

-- ============================================
-- РИСКИ (Маппинг Причина → Риск)
-- ============================================
CREATE TABLE IF NOT EXISTS risk_messages (
    id SERIAL PRIMARY KEY,
    reason_code VARCHAR(50) NOT NULL REFERENCES wait_reasons(code),
    risk_text TEXT NOT NULL,
    display_order INT DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    UNIQUE(reason_code, risk_text)
);

CREATE INDEX IF NOT EXISTS idx_risk_messages_reason_code ON risk_messages(reason_code);

-- ============================================
-- СТАДИИ СДЕЛОК (Мониторинг состояний)
-- ============================================
CREATE TABLE IF NOT EXISTS deal_stages (
    id SERIAL PRIMARY KEY,
    bitrix_stage_id VARCHAR(50) UNIQUE NOT NULL,
    stage_name VARCHAR(100) NOT NULL,
    is_wait_stage BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE
);

-- ============================================
-- ТЕКУЩИЕ СОСТОЯНИЯ СДЕЛОК
-- ============================================
CREATE TABLE IF NOT EXISTS deal_states (
    id SERIAL PRIMARY KEY,
    client_id INT NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    current_stage_id INT REFERENCES deal_stages(id),
    wait_reasons JSONB,
    entered_wait_stage_at TIMESTAMP WITH TIME ZONE,
    last_message_sent_at TIMESTAMP WITH TIME ZONE,
    messages_sent_count INT DEFAULT 0,
    is_bot_active BOOLEAN DEFAULT FALSE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(client_id)
);

CREATE INDEX IF NOT EXISTS idx_deal_states_stage_id ON deal_states(current_stage_id);
CREATE INDEX IF NOT EXISTS idx_deal_states_bot_active ON deal_states(is_bot_active) WHERE is_bot_active = TRUE;

-- ============================================
-- ЛОГИ СООБЩЕНИЙ (Аналитика)
-- ============================================
CREATE TABLE IF NOT EXISTS message_logs (
    id SERIAL PRIMARY KEY,
    client_id INT NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    message_type VARCHAR(50) NOT NULL,
    message_text TEXT NOT NULL,
    telegram_message_id BIGINT,
    send_status VARCHAR(20) DEFAULT 'SENT',
    sent_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_message_logs_client_id ON message_logs(client_id);
CREATE INDEX IF NOT EXISTS idx_message_logs_sent_at ON message_logs(sent_at);

-- ============================================
-- НАСТРОЙКИ БОТА
-- ============================================
CREATE TABLE IF NOT EXISTS bot_settings (
    key VARCHAR(50) PRIMARY KEY,
    value TEXT NOT NULL,
    description TEXT,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================
-- ЗАПОЛНЕНИЕ СПРАВОЧНИКОВ
-- ============================================

-- ПРОДУКТЫ
INSERT INTO products (code, name, description) VALUES
('EGAIС', 'ЕГАИС', 'Единая государственная автоматизированная информационная система'),
('MERCURY', 'Меркурий', 'ФГИС Меркурий - ветеринарная сертификация'),
('MARKING', 'Маркировка', 'Честный ЗНАК - маркировка товаров'),
('YZEDO', 'ЮЗЭДО', 'Юридически значимый электронный документооборот')
ON CONFLICT (code) DO NOTHING;

-- ФУНКЦИИ ПРОДУКТОВ
INSERT INTO product_features (product_code, feature_text, display_order) VALUES
('EGAIС', 'Приём алкогольных накладных в ЕГАИС', 1),
('EGAIС', 'Просмотр остатков по пиву', 2),
('EGAIС', 'Списание алкоголя по данным с кассы', 3),
('MERCURY', 'Получение ветеринарных сертификатов', 1),
('MERCURY', 'Гашение ВСД', 2),
('MERCURY', 'Просмотр реестра сертификатов', 3),
('MARKING', 'Приём маркированных товаров', 1),
('MARKING', 'Вывод из оборота', 2),
('MARKING', 'Отчётность в Честный ЗНАК', 3),
('YZEDO', 'Получение электронных накладных', 1),
('YZEDO', 'Подписание документов УКЭП', 2),
('YZEDO', 'Архив документов', 3)
ON CONFLICT (product_code, feature_text) DO NOTHING;

-- ПРИЧИНЫ ОЖИДАНИЯ
INSERT INTO wait_reasons (code, name, bitrix_field_value, product_code) VALUES
('NO_UKEP', 'Нет УКЭП', 'no_ukep', 'EGAIС'),
('NO_JACARTA', 'Не загружен сертификат JaCarta', 'no_jacarta', 'EGAIС'),
('NO_MERCURY_PLATFORM', 'Не подтверждена площадка в Меркурий', 'no_mercury_platform', 'MERCURY'),
('NO_TRADE_HALL', 'Не заполнен торговый зал', 'no_trade_hall', 'EGAIС'),
('NO_NOMENKLATURA_MAPPING', 'Не проведено сопоставление номенклатуры', 'no_nomenklatura_mapping', 'EGAIС'),
('NO_YZEDO_SUPPLIERS', 'Не подключены поставщики в ЮЗЭДО', 'no_yzedo_suppliers', 'YZEDO'),
('NO_GTIN_BINDING', 'Не привязан GTIN к номенклатуре', 'no_gtin_binding', 'MARKING'),
('NO_TRAINING_DATE', 'Не назначена дата обучения', 'no_training_date', NULL)
ON CONFLICT (code) DO NOTHING;

-- РИСКИ
INSERT INTO risk_messages (reason_code, risk_text, display_order) VALUES
('NO_UKEP', 'Не сможете подписывать документы юридически значимой подписью', 1),
('NO_JACARTA', 'Не сможете отправлять документы в ЕГАИС — риск штрафа при проверке', 1),
('NO_MERCURY_PLATFORM', 'Не сможете гасить ветеринарные сертификаты — задержки в поставках', 1),
('NO_TRADE_HALL', 'Не сможете списывать крепкий алкоголь по данным с кассы — только вручную', 1),
('NO_NOMENKLATURA_MAPPING', 'Система не поймёт, какой товар вы продаёте — ошибки в отчётности', 1),
('NO_YZEDO_SUPPLIERS', 'Не сможете получать электронные накладные от поставщиков — только бумага', 1),
('NO_GTIN_BINDING', 'Не сможете работать с маркированными товарами — риск блокировки продаж', 1),
('NO_TRAINING_DATE', 'Не получите инструктаж по работе — дольше будете разбираться сами', 1)
ON CONFLICT (reason_code, risk_text) DO NOTHING;

-- СТАДИИ СДЕЛОК
INSERT INTO deal_stages (bitrix_stage_id, stage_name, is_wait_stage) VALUES
('3150', 'ЖДЁМ_ДЕЙСТВИЙ_КЛИЕНТА', TRUE),
('SUCCESS', 'УСПЕШНО', FALSE),
('FAIL', 'ПРОВАЛ', FALSE)
ON CONFLICT (bitrix_stage_id) DO NOTHING;

-- НАСТРОЙКИ БОТА
INSERT INTO bot_settings (key, value, description) VALUES
('timezone', 'Europe/Moscow', 'Часовой пояс для планировщика'),
('send_time_hour', '9', 'Время отправки напоминаний (час)'),
('work_hours_start', '9', 'Начало рабочего времени'),
('work_hours_end', '18', 'Конец рабочего времени'),
('max_reminders', '30', 'Максимальное количество напоминаний по одной сделке')
ON CONFLICT (key) DO NOTHING;
