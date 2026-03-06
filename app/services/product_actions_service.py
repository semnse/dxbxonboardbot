"""
Сервис доступных действий по продуктам

Хранит маппинг стадий воронки к доступным действиям для каждого продукта.
Используется в ежедневных отчётах и команде /report.

Формат отображения:
- Показывает только если есть действия (>0)
- Формат: маркированный список в Telegram
"""
from typing import Dict, List, Optional, Set
import structlog

logger = structlog.get_logger(__name__)


# ============================================
# СТРУКТУРА ДАННЫХ: ДЕЙСТВИЯ ПО ПРОДУКТАМ
# ============================================

# Формат:
# PRODUCT_STAGE_ACTIONS[продукт][stage_id] = [список действий]
#
# product_key: код продукта из product_id_map
#   '8426' -> ЕГАИС
#   '8432' -> Меркурий
#   '8434' -> Маркировка
#   '8428' -> Накладные
#   '8430' -> ЮЗЭДО
#
# stage_id: ID стадии из Bitrix24 (DT1070_38:XXXX)
#
# actions: список строк с названиями действий

PRODUCT_STAGE_ACTIONS: Dict[str, Dict[str, List[str]]] = {
    # ========================================
    # ЕГАИС (product_id: 8426)
    # ========================================
    '8426': {
        # Новая заявка (2218)
        'DT1070_38:UC_70SK2H': [],  # Чек работы системы
        'DT1070_38:UC_B7P2X4': [],  # Выведена на MRR
        'DT1070_38:UC_ILDKHV': [],  # Ждём действий клиента
        
        # Настройка (2230)
        'DT1070_38:UC_NZK4JJ': [
            "Приемка накладных",
            "Списание пива вручную",
            "Списание пива Автопивом (если есть ЧЗ)",
        ],
        
        # Работа с остатками (2222)
        'DT1070_38:UC_XRWEHG': [
            "Возвраты/перемещения",
            "Списание крепкого вручную",
            "Инвентаризация",
        ],
        
        # Сопоставление (2916)
        'DT1070_38:UC_JK4IJR': [],
        
        # Торговый зал (2918)
        'DT1070_38:UC_9JH4GA': [
            "Списание крепкого по данным с кассы",
        ],
        
        # Обучение (2228)
        'DT1070_38:UC_REJAS2': [],
        
        # Ждём чек (2232)
        'DT1070_38:3': [],
        
        # Пауза (2376)
        'DT1070_38:UC_IM0YI8': [],
        
        # Завершить (final)
        'DT1070_38:SUCCESS': [],
    },
    
    # ========================================
    # Меркурий (product_id: 8432)
    # ========================================
    '8432': {
        # Новая заявка (2334)
        'DT1070_38:UC_70SK2H': [],
        'DT1070_38:UC_B7P2X4': [],
        'DT1070_38:UC_ILDKHV': [],
        
        # Сбор информации (2336)
        'DT1070_38:NEW': [],
        
        # Получаем доступ к ЭЦП (2338)
        'DT1070_38:PREPARATION': [],
        
        # Получен логпасс Меркурий (2344)
        'DT1070_38:UC_8IBNZ4': [],
        
        # Подтверждение площадки (2346)
        'DT1070_38:UC_70SK2H': [],
        
        # Ждем отвязку (2348)
        'DT1070_38:UC_B7P2X4': [],
        
        # Ждем привязку (2350)
        'DT1070_38:UC_ILDKHV': [],
        
        # Ждем ВСД (3340)
        'DT1070_38:UC_NZK4JJ': [
            "Получение, гашение и возврат ВСД",
        ],
        
        # Обучение (2394)
        'DT1070_38:UC_REJAS2': [],
        
        # Пауза (2384)
        'DT1070_38:UC_IM0YI8': [],
        
        # Завершить (final)
        'DT1070_38:SUCCESS': [],
    },
    
    # ========================================
    # Маркировка (product_id: 8434)
    # ========================================
    '8434': {
        # Новая заявка (2272)
        'DT1070_38:UC_70SK2H': [],
        'DT1070_38:UC_B7P2X4': [],
        'DT1070_38:UC_ILDKHV': [],
        
        # Сбор информации (2330)
        'DT1070_38:NEW': [],
        
        # Настройка УС (2274)
        'DT1070_38:PREPARATION': [],
        
        # ЛК ЧЗ (2276)
        'DT1070_38:UC_8IBNZ4': [],
        
        # Настройка ГИС МТ (2282)
        'DT1070_38:UC_NZK4JJ': [
            "Постановка на кран кег",
            "Автосписание маркированных товаров по послаблению",
        ],
        
        # Плагин (2938)
        'DT1070_38:UC_9JH4GA': [
            "GTIN в чеке при послаблении",
        ],
        
        # Обучение (2284)
        'DT1070_38:UC_REJAS2': [],
        
        # Ждем чек (2914)
        'DT1070_38:3': [],
        
        # Пауза (2382)
        'DT1070_38:UC_IM0YI8': [],
        
        # Завершить (final)
        'DT1070_38:SUCCESS': [],
    },
    
    # ========================================
    # Накладные (product_id: 8428)
    # ========================================
    '8428': {
        # Новая заявка (2238)
        'DT1070_38:UC_70SK2H': [],
        'DT1070_38:UC_B7P2X4': [],
        'DT1070_38:UC_ILDKHV': [],
        
        # Сбор информации (2326)
        'DT1070_38:NEW': [],
        
        # Настройка УС (2268)
        'DT1070_38:PREPARATION': [
            "Выгрузка в УС",
        ],
        
        # Запрос поставщиков (2240)
        'DT1070_38:UC_8IBNZ4': [],
        
        # Разобрать ТВП (2602)
        'DT1070_38:UC_XRWEHG': [],
        
        # Подключение поставщиков (2242)
        'DT1070_38:UC_JK4IJR': [
            "Получение, приемка накладных",
        ],
        
        # Обучение (2390)
        'DT1070_38:UC_REJAS2': [],
        
        # Пауза (2378)
        'DT1070_38:UC_IM0YI8': [],
        
        # Завершить (final)
        'DT1070_38:SUCCESS': [],
    },
    
    # ========================================
    # ЮЗЭДО (product_id: 8430)
    # ========================================
    '8430': {
        # Новая заявка (2248)
        'DT1070_38:UC_70SK2H': [],
        'DT1070_38:UC_B7P2X4': [],
        'DT1070_38:UC_ILDKHV': [],
        
        # Сбор информации (2328)
        'DT1070_38:NEW': [],
        
        # Настройка УС (2270)
        'DT1070_38:PREPARATION': [
            "Выгрузка в УС",
        ],
        
        # Настройка СБИС (2250)
        'DT1070_38:UC_8IBNZ4': [],
        
        # Запрос поставщиков (2252)
        'DT1070_38:UC_XRWEHG': [],
        
        # Подключение поставщиков (2912)
        'DT1070_38:UC_JK4IJR': [
            "Получение, приемка, подписание УПД",
        ],
        
        # Ждем УПД (2332)
        'DT1070_38:3': [],
        
        # Обучение (2258)
        'DT1070_38:UC_REJAS2': [],
        
        # Пауза (2380)
        'DT1070_38:UC_IM0YI8': [],
        
        # Завершить (final)
        'DT1070_38:SUCCESS': [],
    },
}

# ============================================
# МАППИНГ ПРОДУКТОВ
# ============================================

PRODUCT_NAME_MAP: Dict[str, str] = {
    '8426': 'ЕГАИС',
    '8432': 'Меркурий',
    '8434': 'Маркировка',
    '8428': 'Накладные',
    '8430': 'ЮЗЭДО',
}


class ProductActionsService:
    """
    Сервис для получения и форматирования доступных действий по продуктам.
    
    Использование:
        # Получить действия для стадии и продукта
        actions = ProductActionsService.get_actions(stage_id, product_code)
        
        # Получить все действия для стадии по всем продуктам
        actions = ProductActionsService.get_all_actions_for_stage(stage_id, product_codes)
        
        # Отформатировать для Telegram
        text = ProductActionsService.format_for_telegram(actions)
    """
    
    @classmethod
    def get_actions(
        cls,
        stage_id: str,
        product_code: str
    ) -> List[str]:
        """
        Получает список действий для стадии и продукта.
        
        Args:
            stage_id: ID стадии из Bitrix24 (например, DT1070_38:UC_NZK4JJ)
            product_code: Код продукта (8426, 8432, 8434, 8428, 8430)
        
        Returns:
            Список действий (пустой если нет действий)
        """
        product_data = PRODUCT_STAGE_ACTIONS.get(product_code, {})
        actions = product_data.get(stage_id, [])
        
        logger.debug(
            "get_product_actions",
            stage_id=stage_id,
            product_code=product_code,
            actions_count=len(actions)
        )
        
        return actions
    
    @classmethod
    def get_all_actions_for_stage(
        cls,
        stage_id: str,
        product_codes: List[str]
    ) -> Dict[str, List[str]]:
        """
        Получает все действия для стадии по списку продуктов.
        
        Args:
            stage_id: ID стадии из Bitrix24
            product_codes: Список кодов продуктов
        
        Returns:
            Dict {название_продукта: [список действий]}
            Возвращает только продукты с действиями (>0)
        """
        result = {}
        
        for product_code in product_codes:
            actions = cls.get_actions(stage_id, product_code)
            
            # Показываем только если есть действия
            if actions:
                product_name = PRODUCT_NAME_MAP.get(product_code, f"Продукт #{product_code}")
                result[product_name] = actions
        
        logger.debug(
            "get_all_actions_for_stage",
            stage_id=stage_id,
            product_codes=product_codes,
            products_with_actions=list(result.keys())
        )
        
        return result
    
    @classmethod
    def format_for_telegram(
        cls,
        actions_by_product: Dict[str, List[str]]
    ) -> str:
        """
        Форматирует действия для отображения в Telegram.
        
        Args:
            actions_by_product: Dict {название_продукта: [список действий]}
        
        Returns:
            Отформатированный текст для Telegram (Markdown)
        """
        if not actions_by_product:
            return ""
        
        lines = []
        
        for product_name, actions in actions_by_product.items():
            if not actions:
                continue
            
            # Заголовок продукта
            lines.append(f"🔹 *{product_name}:*")
            
            # Список действий
            for action in actions:
                lines.append(f"  • {action}")
        
        return "\n".join(lines)
    
    @classmethod
    def format_for_telegram_html(
        cls,
        actions_by_product: Dict[str, List[str]]
    ) -> str:
        """
        Форматирует действия для отображения в Telegram (HTML режим).
        
        Args:
            actions_by_product: Dict {название_продукта: [список действий]}
        
        Returns:
            Отформатированный текст для Telegram (HTML)
        """
        if not actions_by_product:
            return ""
        
        lines = []
        
        for product_name, actions in actions_by_product.items():
            if not actions:
                continue
            
            # Заголовок продукта
            lines.append(f"🔹 <b>{product_name}:</b>")
            
            # Список действий
            for action in actions:
                lines.append(f"  • {action}")
        
        return "\n".join(lines)
    
    @classmethod
    def has_actions(
        cls,
        stage_id: str,
        product_codes: List[str]
    ) -> bool:
        """
        Проверяет, есть ли действия для стадии по продуктам.
        
        Args:
            stage_id: ID стадии из Bitrix24
            product_codes: Список кодов продуктов
        
        Returns:
            True если есть хотя бы одно действие
        """
        actions = cls.get_all_actions_for_stage(stage_id, product_codes)
        return len(actions) > 0
    
    @classmethod
    def get_action_count(
        cls,
        stage_id: str,
        product_codes: List[str]
    ) -> int:
        """
        Подсчитывает общее количество действий.
        
        Args:
            stage_id: ID стадии из Bitrix24
            product_codes: Список кодов продуктов
        
        Returns:
            Общее количество действий
        """
        total = 0
        for product_code in product_codes:
            actions = cls.get_actions(stage_id, product_code)
            total += len(actions)
        return total
