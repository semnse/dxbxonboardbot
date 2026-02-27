"""
Message Builder
Формирование текстов сообщений для клиентов
"""
import logging
from dataclasses import dataclass
from typing import List, Optional

from app.database.models import Client, DealState, WaitReason, RiskMessage, ProductFeature

logger = logging.getLogger(__name__)


@dataclass
class MessageData:
    """Данные для формирования сообщения"""
    
    company_name: str
    features: List[str]
    action_items: List[tuple[str, str]]  # (причина, риск)
    general_risk: str


@dataclass
class BuiltMessage:
    """Сформированное сообщение"""
    
    text: str
    company_name: str
    features_count: int
    action_items_count: int


class MessageBuilder:
    """
    Строитель сообщений для клиентов.
    
    Формирует сообщения по шаблону:
    
    🔍 [Название], напоминаем о шагах для завершения внедрения
    
    ✅ УЖЕ ДОСТУПНО:
    • [Функция 1]
    • [Функция 2]
    
    ⏳ ОСТАЛОСЬ СДЕЛАТЬ:
    • [Причина 1] → [Риск 1]
    • [Причина 2] → [Риск 2]
    
    💡 ЭТО ВАЖНО, ПОТОМУ ЧТО:
    [Общий риск]
    """
    
    # Шаблоны общих рисков по продуктам
    GENERAL_RISKS = {
        "EGAIС": (
            "Без этих шагов вы не сможете легально работать с алкоголем. "
            "Это может привести к штрафам от контролирующих органов и простою в закупках."
        ),
        "MERCURY": (
            "Без этих шагов вы не сможете работать с продукцией животного происхождения. "
            "Это приведёт к задержкам поставок и возможным штрафам."
        ),
        "MARKING": (
            "Без этих шагов вы не сможете работать с маркированными товарами. "
            "Это может привести к блокировке продаж и штрафам."
        ),
        "YZEDO": (
            "Без этих шагов вы не сможете получать электронные документы от поставщиков. "
            "Это приведёт к дополнительной бумажной работе и задержкам."
        ),
    }
    
    def build_reminder_message(
        self,
        client: Client,
        deal_state: DealState,
        features: List[str],
        action_items: List[tuple[str, str]],
        product_codes: Optional[List[str]] = None,
    ) -> BuiltMessage:
        """
        Формирует сообщение-напоминание.
        
        Args:
            client: Клиент
            deal_state: Состояние сделки
            features: Список доступных функций
            action_items: Список действий (причина, риск)
            product_codes: Коды продуктов (для общего риска)
        
        Returns:
            BuiltMessage с готовым сообщением
        """
        # Заголовок
        header = f"🔍 {client.company_name}, напоминаем о шагах для завершения внедрения"
        
        # Блок "Уже доступно"
        features_block = self._build_features_block(features)
        
        # Блок "Осталось сделать"
        action_block = self._build_action_block(action_items)
        
        # Общий риск
        general_risk = self._build_general_risk(product_codes or [])
        
        # Сборка сообщения
        message_parts = [
            header,
            "",
            "✅ УЖЕ ДОСТУПНО:",
            features_block,
            "",
            "⏳ ОСТАЛОСЬ СДЕЛАТЬ:",
            action_block,
            "",
            "💡 ЭТО ВАЖНО, ПОТОМУ ЧТО:",
            general_risk,
        ]
        
        message_text = "\n".join(message_parts)
        
        return BuiltMessage(
            text=message_text,
            company_name=client.company_name,
            features_count=len(features),
            action_items_count=len(action_items),
        )
    
    def _build_features_block(self, features: List[str]) -> str:
        """
        Формирует блок "Уже доступно".
        
        Если функций нет — возвращает заглушку.
        """
        if not features:
            return "• Функции загружаются..."
        
        return "\n".join(f"• {feature}" for feature in features)
    
    def _build_action_block(self, action_items: List[tuple[str, str]]) -> str:
        """
        Формирует блок "Осталось сделать".
        
        Формат: "• [Причина] → [Риск]"
        """
        if not action_items:
            return "• Нет активных задач"
        
        lines = []
        for reason, risk in action_items:
            lines.append(f"• {reason} → {risk}")
        
        return "\n".join(lines)
    
    def _build_general_risk(self, product_codes: List[str]) -> str:
        """
        Формирует общий бизнес-риск.
        
        Агрегирует риски по всем продуктам клиента.
        """
        if not product_codes:
            # Риск по умолчанию
            return (
                "Без выполнения этих шагов вы не сможете полноценно использовать "
                "систему. Это может привести к ошибкам в отчётности и проблемам "
                "с контролирующими органами."
            )
        
        # Собираем риски по всем продуктам
        risks = []
        for code in product_codes:
            if code in self.GENERAL_RISKS:
                risks.append(self.GENERAL_RISKS[code])
        
        if risks:
            # Возвращаем первый риск (основной продукт)
            return risks[0]
        else:
            # Риск по умолчанию
            return (
                "Без выполнения этих шагов система не будет работать полноценно. "
                "Обратитесь к менеджеру внедрения за помощью."
            )
    
    def build_welcome_message(self, client: Client) -> str:
        """
        Формирует приветственное сообщение.
        
        Отправляется при первой активации бота.
        """
        return (
            f"👋 Здравствуйте, {client.company_name}!\n\n"
            "Мы запустили бота напоминаний, чтобы помочь вам быстрее завершить внедрение.\n\n"
            "Бот будет напоминать о шагах, которые нужно сделать, и объяснять, "
            "почему это важно для вашего бизнеса.\n\n"
            "Если у вас возникнут вопросы — просто напишите вашему менеджеру внедрения."
        )
    
    def build_stop_message(self, client: Client) -> str:
        """
        Формирует сообщение при деактивации бота.
        
        Отправляется, когда сделка выходит из стадии ожидания.
        """
        return (
            f"✅ {client.company_name}, отличные новости!\n\n"
            "Ваша сделка перешла на следующий этап. Бот напоминаний больше не будет "
            "отправлять сообщения по этой сделке.\n\n"
            "Если вам понадобится помощь — обращайтесь к вашему менеджеру внедрения."
        )
    
    async def extract_action_items(
        self,
        wait_reason_codes: List[str],
    ) -> List[tuple[str, str]]:
        """
        Извлекает action items из кодов причин.
        
        Args:
            wait_reason_codes: Список кодов причин
        
        Returns:
            Список кортежей (причина, риск)
        """
        # TODO: Inject repository
        # wait_reason_repo = WaitReasonRepository(session)
        
        action_items = []
        
        for code in wait_reason_codes:
            # В реальности — загрузка из БД
            # reason = await wait_reason_repo.get_by_code(code)
            # risk = await wait_reason_repo.get_risk_text(code)
            
            # Заглушка для примера
            reason_name = self._get_reason_name(code)
            risk_text = self._get_risk_text(code)
            
            if reason_name and risk_text:
                action_items.append((reason_name, risk_text))
        
        return action_items
    
    def _get_reason_name(self, code: str) -> Optional[str]:
        """Получает название причины по коду (заглушка)"""
        names = {
            "NO_UKEP": "Нет УКЭП",
            "NO_JACARTA": "Не загружен сертификат JaCarta",
            "NO_MERCURY_PLATFORM": "Не подтверждена площадка в Меркурий",
            "NO_TRADE_HALL": "Не заполнен торговый зал",
            "NO_NOMENKLATURA_MAPPING": "Не проведено сопоставление номенклатуры",
            "NO_YZEDO_SUPPLIERS": "Не подключены поставщики в ЮЗЭДО",
            "NO_GTIN_BINDING": "Не привязан GTIN к номенклатуре",
            "NO_TRAINING_DATE": "Не назначена дата обучения",
        }
        return names.get(code)
    
    def _get_risk_text(self, code: str) -> Optional[str]:
        """Получает текст риска по коду (заглушка)"""
        risks = {
            "NO_UKEP": "Не сможете подписывать документы юридически значимой подписью",
            "NO_JACARTA": "Не сможете отправлять документы в ЕГАИС — риск штрафа при проверке",
            "NO_MERCURY_PLATFORM": "Не сможете гасить ветеринарные сертификаты — задержки в поставках",
            "NO_TRADE_HALL": "Не сможете списывать крепкий алкоголь по данным с кассы — только вручную",
            "NO_NOMENKLATURA_MAPPING": "Система не поймёт, какой товар вы продаёте — ошибки в отчётности",
            "NO_YZEDO_SUPPLIERS": "Не сможете получать электронные накладные от поставщиков — только бумага",
            "NO_GTIN_BINDING": "Не сможете работать с маркированными товарами — риск блокировки продаж",
            "NO_TRAINING_DATE": "Не получите инструктаж по работе — дольше будете разбираться сами",
        }
        return risks.get(code)
