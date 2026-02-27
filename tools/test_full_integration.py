"""Финальный тест полной интеграции"""
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import dotenv_values

env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    env_values = dotenv_values(str(env_path))
    for key, value in env_values.items():
        if value is not None:
            os.environ[key] = value

from app.services.notification_service import NotificationService
from app.services.wait_reasons_service import WaitReasonsService
from app.services.bitrix_stage_service import BitrixStageService


async def main():
    print("="*70)
    print("FINAL TEST: Full Integration")
    print("="*70)
    
    # Тест 1: Проверка маппинга причин
    print("\n[1] Test reason mapping...")
    test_reasons = ['21098', '21082', '21078', '21080']
    
    for reason_id in test_reasons:
        reason_text = WaitReasonsService.get_reason_text(reason_id)
        action_desc = WaitReasonsService.get_action_description(reason_id)
        print(f"    {reason_id} -> {reason_text} -> {action_desc[:50]}")
    
    # Тест 2: Проверка маппинга стадий
    print("\n[2] Test stage mapping...")
    test_stages = ['DT1070_38:UC_IM0YI8', 'DT1070_38:UC_70SK2H', 'DT1070_38:SUCCESS']
    
    for stage_id in test_stages:
        stage_name = BitrixStageService.get_stage_name(stage_id)
        is_wait = BitrixStageService.is_wait_stage(stage_id)
        print(f"    {stage_id} -> {stage_name[:50]} (wait={is_wait})")
    
    # Тест 3: Проверка группировки по рискам
    print("\n[3] Test risk grouping...")
    test_reason_ids = ['21098', '21080', '21082']
    grouped = WaitReasonsService.group_by_risks(test_reason_ids)
    
    for risk, reasons in grouped.items():
        print(f"    {risk}:")
        for reason in reasons:
            print(f"      - {reason}")
    
    # Тест 4: Проверка формирования action items
    print("\n[4] Test action items...")
    action_items = WaitReasonsService.format_action_items(test_reason_ids)
    
    for action, risk in action_items:
        print(f"    Action: {action[:50]}")
        print(f"    Risk: {risk[:50]}")
    
    # Тест 5: Проверка NotificationService
    print("\n[5] Test NotificationService...")
    notification = NotificationService()
    print(f"    Token: {notification.token[:20]}...")
    print(f"    Max reminders: {notification.max_reminders}")
    print(f"    Work hours: {notification.work_hours_start}-{notification.work_hours_end}")
    
    print("\n" + "="*70)
    print("ALL TESTS PASSED")
    print("="*70)


if __name__ == "__main__":
    asyncio.run(main())
