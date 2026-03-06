"""
Сервис маппинга стадий и справочников Bitrix24
"""
from typing import Dict, Optional


class BitrixStageService:
    """
    Сервис для работы со стадиями смарт-процесса "Торговые точки".
    
    Маппинг ID стадий из Bitrix24 в текстовые названия.
    """
    
    # Стадии "Ждём действий клиента" (с причинами)
    WAIT_STAGES = {
        # Основные стадии ожидания
        'DT1070_38:UC_70SK2H': 'Ждём действий клиента - Чек работы системы',
        'DT1070_38:UC_B7P2X4': 'Ждём действий клиента - Выведена на MRR',
        'DT1070_38:UC_JK4IJR': 'Ждём действий клиента - Подключение поставщиков',
        'DT1070_38:UC_ILDKHV': 'Ждём действий клиента - Ждём действий клиента',
        'DT1070_38:UC_NZK4JJ': 'Ждём действий клиента - Подключение поставщиков (другая)',
        'DT1070_38:UC_XRWEHG': 'Ждём действий клиента - Чек работы системы (другая)',
        'DT1070_38:UC_9JH4GA': 'Ждём действий клиента - Не можем завершить',
        'DT1070_38:UC_REJAS2': 'Ждём действий клиента - Завершение внедрения',
        'DT1070_38:3': 'Ждём действий клиента - Не можем завершить (краткая)',
        'DT1070_38:UC_IM0YI8': 'Ждём действий клиента - Пауза до вывода',
        
        # Другие стадии (для справки)
        'DT1070_38:NEW': 'Знакомство',
        'DT1070_38:PREPARATION': 'Базовые настройки',
        'DT1070_38:2': 'Пауза до вывода',
        'DT1070_38:SUCCESS': 'Внедрение завершено',
        'DT1070_38:FAIL': 'Не можем вывести на MRR',
        'DT1070_38:UC_8IBNZ4': 'Не можем вывести на MRR',
    }
    
    # Стадии ожидания (для фильтрации)
    WAIT_STAGE_IDS = list(WAIT_STAGES.keys())
    
    @classmethod
    def get_stage_name(cls, stage_id: str) -> str:
        """Получает название стадии по ID"""
        stage_name = cls.WAIT_STAGES.get(stage_id, stage_id)
        
        # Для стадий группы "Ждём действий клиента" возвращаем только "Ждём действий клиента"
        if cls.is_wait_stage(stage_id) and ' - ' in stage_name:
            parts = stage_name.split(' - ', 1)
            if len(parts) == 2:
                # Возвращаем первую часть (например "Ждём действий клиента")
                return parts[0].strip()
        
        return stage_name
    
    @classmethod
    def is_wait_stage(cls, stage_id: str) -> bool:
        """Проверяет, является ли стадия стадией ожидания"""
        # Проверяем по префиксу или явному списку
        if stage_id in cls.WAIT_STAGE_IDS:
            return True
        
        # Проверяем по названию
        stage_name = cls.get_stage_name(stage_id)
        return 'ждём' in stage_name.lower() or 'пауза' in stage_name.lower()
    
    @classmethod
    def get_wait_stage_reason(cls, stage_id: str) -> Optional[str]:
        """
        Получает причину ожидания из названия стадии.
        
        Например:
        - "Ждём действий клиента - Чек работы системы" → "Чек работы системы"
        """
        stage_name = cls.get_stage_name(stage_id)
        
        if ' - ' in stage_name:
            parts = stage_name.split(' - ', 1)
            if len(parts) == 2:
                return parts[1].strip()
        
        return None
