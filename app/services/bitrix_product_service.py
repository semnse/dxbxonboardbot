"""
Сервис для работы со смарт-процессами продуктов

Продукты:
- ЕГАИС
- Меркурий
- Маркировка
- Накладные
- ЮЗЭДО
"""
import json
import logging
from typing import Optional, List, Dict, Any

import aiohttp

from app.config import settings

logger = logging.getLogger(__name__)


class BitrixProductService:
    """
    Сервис для получения статусов продуктов из смарт-процессов.
    
    Каждый продукт имеет свой смарт-процесс с собственной воронкой.
    
    Пример: ООО Фортуна (карточка 18306)
    - Основная карточка: https://docsinbox.bitrix24.ru/page/otdel_vnedreniya/torgovye_tochki/type/1070/details/18306/
    - Воронка внедрения: type=1056
    """
    
    # ID смарт-процессов продуктов
    # Все продукты используют один смарт-процесс "Внедрение" (ID=1056)
    # Разделение по продуктам через ID карточек внутри процесса
    PRODUCT_ENTITY_ID = 1056  # Смарт-процесс "Внедрение"
    
    # Маппинг продуктов → ID карточек в смарт-процессе "Внедрение"
    # Для ООО Фортуна (родительская карточка 18306):
    PRODUCT_CARD_IDS = {
        'usedo': 68566,       # ЮЗЭДО
        'marking': 68564,     # Маркировка
        'nakladnye': 68562,   # Накладные
        'mercury': 68560,     # Меркурий
        'egais': 68558,       # ЕГАИС
    }
    
    # Маппинг стадий → сообщения для пользователя
    STAGE_MESSAGES = {
        # ===== ЮЗЭДО =====
        'usedo_2248': {
            'title': 'Новая заявка',
            'message': 'Заявка на подключение ЮЗЭДО получена',
            'action_required': 'Ожидайте сбора информации',
        },
        'usedo_2328': {
            'title': 'Сбор информации',
            'message': 'Идёт сбор информации для подключения ЮЗЭДО',
            'action_required': 'Предоставьте необходимую информацию',
        },
        'usedo_2270': {
            'title': 'Настройка УС',
            'message': 'Настройка учётной системы для ЮЗЭДО',
            'action_required': 'Проверьте корректность настроек',
        },
        'usedo_2250': {
            'title': 'Настройка СБИС',
            'message': 'Настройка СБИС для работы с ЮЗЭДО',
            'action_required': 'Проверьте работу СБИС',
        },
        'usedo_2252': {
            'title': 'Запрос поставщиков',
            'message': 'Отправлен запрос поставщикам на подключение ЮЗЭДО',
            'action_required': 'Контролируйте ответ поставщиков',
        },
        'usedo_2912': {
            'title': 'Подключение поставщиков',
            'message': 'Идёт подключение поставщиков к ЮЗЭДО',
            'action_required': 'Проверьте подключение всех поставщиков',
        },
        'usedo_2332': {
            'title': 'Ждем УПД',
            'message': 'Ожидаем получение УПД',
            'action_required': 'Проверьте поступление УПД',
        },
        'usedo_2258': {
            'title': 'Обучение',
            'message': 'Проводится обучение работе с ЮЗЭДО',
            'action_required': 'Пройдите обучение',
        },
        'usedo_2380': {
            'title': 'Пауза',
            'message': 'Процесс подключения ЮЗЭДО на паузе',
            'action_required': 'Сообщите о готовности продолжить',
        },
        'usedo_final': {
            'title': 'Завершить',
            'message': 'Подключение ЮЗЭДО завершено успешно',
            'action_required': '',
        },
        
        # ===== Маркировка =====
        'marking_2272': {
            'title': 'Новая заявка',
            'message': 'Заявка на подключение маркировки получена',
            'action_required': 'Ожидайте сбора информации',
        },
        'marking_2330': {
            'title': 'Сбор информации',
            'message': 'Идёт сбор информации для подключения маркировки',
            'action_required': 'Предоставьте необходимую информацию',
        },
        'marking_2274': {
            'title': 'Настройка УС',
            'message': 'Настройка учётной системы для маркировки',
            'action_required': 'Проверьте корректность настроек',
        },
        'marking_2276': {
            'title': 'ЛК ЧЗ',
            'message': 'Настройка личного кабинета Честный Знак',
            'action_required': 'Проверьте доступ к ЛК ЧЗ',
        },
        'marking_2282': {
            'title': 'Настройка ГИС МТ',
            'message': 'Настройка ГИС Маркировка Товаров',
            'action_required': 'Проверьте работу ГИС МТ',
        },
        'marking_2938': {
            'title': 'Плагин',
            'message': 'Установка и настройка плагина для маркировки',
            'action_required': 'Проверьте работу плагина',
        },
        'marking_2284': {
            'title': 'Обучение',
            'message': 'Проводится обучение работе с маркировкой',
            'action_required': 'Пройдите обучение',
        },
        'marking_2914': {
            'title': 'Ждем чек',
            'message': 'Ожидаем получение чека о маркировке',
            'action_required': 'Проверьте поступление чека',
        },
        'marking_2382': {
            'title': 'Пауза',
            'message': 'Процесс подключения маркировки на паузе',
            'action_required': 'Сообщите о готовности продолжить',
        },
        'marking_final': {
            'title': 'Завершить',
            'message': 'Подключение маркировки завершено успешно',
            'action_required': '',
        },
        
        # ===== Накладные =====
        'nakladnye_2238': {
            'title': 'Новая заявка',
            'message': 'Заявка на подключение накладных получена',
            'action_required': 'Ожидайте сбора информации',
        },
        'nakladnye_2326': {
            'title': 'Сбор информации',
            'message': 'Идёт сбор информации для настройки накладных',
            'action_required': 'Предоставьте необходимую информацию',
        },
        'nakladnye_2268': {
            'title': 'Настройка УС',
            'message': 'Настройка учётной системы для работы с накладными',
            'action_required': 'Проверьте корректность настроек',
        },
        'nakladnye_2240': {
            'title': 'Запрос поставщиков',
            'message': 'Отправлен запрос поставщикам на ЭДО',
            'action_required': 'Контролируйте ответ поставщиков',
        },
        'nakladnye_2602': {
            'title': 'Разобрать ТВП',
            'message': 'Обработка товарных возвратных накладных',
            'action_required': 'Проверьте корректность обработки',
        },
        'nakladnye_2242': {
            'title': 'Подключение поставщиков',
            'message': 'Идёт подключение поставщиков к ЭДО',
            'action_required': 'Проверьте подключение всех поставщиков',
        },
        'nakladnye_2390': {
            'title': 'Обучение',
            'message': 'Проводится обучение работе с накладными',
            'action_required': 'Пройдите обучение',
        },
        'nakladnye_2378': {
            'title': 'Пауза',
            'message': 'Процесс подключения накладных на паузе',
            'action_required': 'Сообщите о готовности продолжить',
        },
        'nakladnye_final': {
            'title': 'Завершить',
            'message': 'Подключение накладных завершено успешно',
            'action_required': '',
        },
        
        # ===== Меркурий =====
        'mercury_2334': {
            'title': 'Новая заявка',
            'message': 'Заявка на подключение Меркурия получена',
            'action_required': 'Ожидайте сбора информации',
        },
        'mercury_2336': {
            'title': 'Сбор информации',
            'message': 'Идёт сбор информации для подключения Меркурия',
            'action_required': 'Предоставьте необходимую информацию',
        },
        'mercury_2338': {
            'title': 'Получаем доступ к ЭЦП',
            'message': 'Получение доступа к электронной подписи',
            'action_required': 'Предоставьте доступ к ЭЦП',
        },
        'mercury_2344': {
            'title': 'Получен логпасс Меркурий',
            'message': 'Получены учётные данные Меркурия',
            'action_required': 'Проверьте доступ к Меркурию',
        },
        'mercury_2346': {
            'title': 'Подтверждение площадки',
            'message': 'Подтверждение торговой площадки в Меркурии',
            'action_required': 'Проверьте подтверждение площадки',
        },
        'mercury_2348': {
            'title': 'Ждем отвязку',
            'message': 'Ожидаем отвязку от старой учётной записи',
            'action_required': 'Контролируйте процесс отвязки',
        },
        'mercury_2350': {
            'title': 'Ждем привязку',
            'message': 'Ожидаем привязку к новой учётной записи',
            'action_required': 'Контролируйте процесс привязки',
        },
        'mercury_3340': {
            'title': 'Ждем ВСД',
            'message': 'Ожидаем получение ветеринарных сопроводительных документов',
            'action_required': 'Проверьте поступление ВСД',
        },
        'mercury_2394': {
            'title': 'Обучение',
            'message': 'Проводится обучение работе с Меркурием',
            'action_required': 'Пройдите обучение',
        },
        'mercury_2384': {
            'title': 'Пауза',
            'message': 'Процесс подключения Меркурия на паузе',
            'action_required': 'Сообщите о готовности продолжить',
        },
        'mercury_final': {
            'title': 'Завершить',
            'message': 'Подключение Меркурия завершено успешно',
            'action_required': '',
        },
        
        # ===== ЕГАИС =====
        'egais_2218': {
            'title': 'Новая заявка',
            'message': 'Заявка на подключение ЕГАИС получена',
            'action_required': 'Ожидайте сбора информации',
        },
        'egais_2324': {
            'title': 'Знакомство',
            'message': 'Первичное знакомство с системой ЕГАИС',
            'action_required': 'Изучите базовую информацию о ЕГАИС',
        },
        'egais_2230': {
            'title': 'Настройка',
            'message': 'Настройка учётной системы для ЕГАИС',
            'action_required': 'Проверьте корректность настроек',
        },
        'egais_2222': {
            'title': 'Работа с остатками',
            'message': 'Настройка работы с остатками алкоголя в ЕГАИС',
            'action_required': 'Проверьте корректность остатков',
        },
        'egais_2916': {
            'title': 'Сопоставление',
            'message': 'Сопоставление товаров в ЕГАИС',
            'action_required': 'Выполните сопоставление всех товаров',
        },
        'egais_2918': {
            'title': 'Торговый зал',
            'message': 'Настройка торгового зала в ЕГАИС',
            'action_required': 'Проверьте настройки торгового зала',
        },
        'egais_2228': {
            'title': 'Обучение',
            'message': 'Проводится обучение работе с ЕГАИС',
            'action_required': 'Пройдите обучение',
        },
        'egais_2232': {
            'title': 'Ждём чек',
            'message': 'Ожидаем получение чека о продаже алкоголя',
            'action_required': 'Проверьте поступление чека',
        },
        'egais_2376': {
            'title': 'Пауза',
            'message': 'Процесс подключения ЕГАИС на паузе',
            'action_required': 'Сообщите о готовности продолжить',
        },
        'egais_final': {
            'title': 'Завершить',
            'message': 'Подключение ЕГАИС завершено успешно',
            'action_required': '',
        },
    }
    
    def __init__(self):
        self.webhook_url = settings.bitrix_webhook_url
        
        if not self.webhook_url:
            logger.error("Bitrix webhook URL not configured")
    
    async def get_product_status(
        self,
        product_card_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Получает статус продукта по ID карточки в смарт-процессе "Внедрение".
        
        Args:
            product_card_id: ID карточки продукта в смарт-процессе 1056
        
        Returns:
            Данные о статусе продукта или None
        """
        if not self.webhook_url:
            return None
        
        url = f"{self.webhook_url}/crm.item.get.json"
        params = {
            "entityTypeId": self.PRODUCT_ENTITY_ID,
            "id": product_card_id
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=params,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    result = await response.json()
                    item = result.get('result', {})
                    
                    logger.info(f"Bitrix response for {product_card_id}: {bool(item)}")
                    
                    if item:
                        # Bitrix возвращает поля в lowercase
                        stage_id = item.get('stageId', '') or item.get('stage', '')
                        
                        # Определяем код продукта по ID карточки
                        product_code = None
                        for code, card_id in self.PRODUCT_CARD_IDS.items():
                            if str(card_id) == str(product_card_id):
                                product_code = code
                                break
                        
                        logger.info(f"Product {product_code}: stage_id={stage_id}")
                        
                        return {
                            'product_code': product_code,
                            'card_id': product_card_id,
                            'stage_id': stage_id,
                            'item': item,
                        }
                    else:
                        logger.debug(f"No item found for card {product_card_id}")
                        return None
                        
        except Exception as e:
            logger.error(f"Error getting product status: {e}")
            return None
    
    async def get_all_products_status(
        self,
        parent_deal_id: str
    ) -> Dict[str, Dict[str, Any]]:
        """
        Получает статусы всех продуктов для торговой точки.
        
        Args:
            parent_deal_id: ID торговой точки (сделки 1070)
        
        Returns:
            Словарь {product_code: status_data}
        """
        results = {}
        
        # Для каждого продукта получаем статус по его карточке
        for product_code, card_id in self.PRODUCT_CARD_IDS.items():
            status = await self.get_product_status(str(card_id))
            if status:
                results[product_code] = status
        
        return results
    
    async def get_stage_messages(
        self,
        product_code: str
    ) -> List[Dict[str, str]]:
        """
        Получает сообщения для всех стадий продукта.
        
        Args:
            product_code: Код продукта
        
        Returns:
            Список стадий с сообщениями
        """
        entity_id = self.PRODUCT_ENTITY_IDS.get(product_code)
        if not entity_id:
            return []
        
        url = f"{self.webhook_url}/crm.status.list.json"
        params = {
            "entityTypeId": entity_id,
            "type": "STATUS"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=params
                ) as response:
                    result = await response.json()
                    stages = result.get('result', [])
                    
                    # Возвращаем стадии с сообщениями из маппинга
                    result_stages = []
                    for stage in stages:
                        stage_id = stage.get('STATUS_ID')
                        stage_name = stage.get('NAME')
                        
                        # Ищем сообщение для этой стадии
                        message_key = f"{product_code}_{stage_id}"
                        message_data = self.STAGE_MESSAGES.get(
                            message_key,
                            {
                                'title': stage_name,
                                'message': 'Информация уточняется',
                                'action_required': 'Ожидайте инструкций',
                            }
                        )
                        
                        result_stages.append({
                            'stage_id': stage_id,
                            'stage_name': stage_name,
                            **message_data,
                        })
                    
                    return result_stages
                    
        except Exception as e:
            logger.error(f"Error getting stage messages: {e}")
            return []
    
    def format_report(
        self,
        products_status: Dict[str, Dict[str, Any]]
    ) -> str:
        """
        Формирует отчёт по продуктам.
        
        Args:
            products_status: Статусы продуктов
        
        Returns:
            Текст отчёта
        """
        lines = ["📊 *Отчёт по продуктам*\n"]
        
        product_names = {
            'egais': 'ЕГАИС',
            'mercury': 'Меркурий',
            'marking': 'Маркировка',
            'nakladnye': 'Накладные',
            'usedo': 'ЮЗЭДО',
        }
        
        for product_code, status in products_status.items():
            product_name = product_names.get(product_code, product_code)
            stage_id = status.get('stage_id', '')
            
            # Получаем сообщение для стадии
            message_key = f"{product_code}_{stage_id}"
            message = self.STAGE_MESSAGES.get(
                message_key,
                {
                    'title': 'Статус уточняется',
                    'message': 'Информация уточняется',
                    'action_required': '',
                }
            )
            
            lines.append(f"📌 *{product_name}*\n")
            lines.append(f"  Стадия: `{message.get('title', stage_id)}`")
            
            if message.get('message'):
                lines.append(f"  {message.get('message')}")
            
            if message.get('action_required'):
                lines.append(f"  ⚠️ {message.get('action_required')}")
            
            lines.append("")
        
        return "\n\n".join(lines)


# Глобальный экземпляр
bitrix_product_service = BitrixProductService()
