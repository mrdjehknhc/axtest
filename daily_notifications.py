import asyncio
import logging
from datetime import datetime, time
from reports import ReportsManager
from notifications import notification_manager
from storage import PositionStorage

logger = logging.getLogger(__name__)

class DailyReporter:
    def __init__(self):
        self.reports = ReportsManager()
        self.storage = PositionStorage()
        self.is_running = False
        self.task = None
    
    async def send_daily_reports(self):
        """Отправляем ежедневные отчеты всем пользователям"""
        try:
            # Получаем всех пользователей с позициями
            positions_data = self.storage.load_positions()
            
            for user_id_str in positions_data.keys():
                user_id = int(user_id_str)
                
                # Проверяем настройки уведомлений пользователя
                settings = notification_manager.get_user_settings(user_id)
                if not settings.get('daily_summary', False):
                    continue
                
                # Генерируем отчет за день
                summary = self.reports.format_trade_summary(user_id, days=1)
                
                # Добавляем информацию об активных позициях
                active_positions = self.storage.get_positions(user_id)
                
                if active_positions:
                    summary += f"\n\n🔄 Активных позиций: {len(active_positions)}"
                
                # Отправляем отчет
                await notification_manager.send_daily_summary(user_id, summary)
                
                logger.info(f"📊 Ежедневный отчет отправлен пользователю {user_id}")
                
                # Небольшая задержка между отправками
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"Ошибка отправки ежедневных отчетов: {e}")
    
    async def schedule_daily_reports(self):
        """Планировщик ежедневных отчетов"""
        while self.is_running:
            now = datetime.now()
            
            # Отправляем в 20:00 каждый день
            target_time = time(20, 0)  # 20:00
            
            if now.time() >= target_time:
                # Если уже прошло 20:00, ждем до завтра
                tomorrow = now.replace(hour=20, minute=0, second=0, microsecond=0)
                if now.time() >= target_time:
                    tomorrow = tomorrow.replace(day=tomorrow.day + 1)
                
                wait_seconds = (tomorrow - now).total_seconds()
            else:
                # Ждем до 20:00 сегодня
                today_target = now.replace(hour=20, minute=0, second=0, microsecond=0)
                wait_seconds = (today_target - now).total_seconds()
            
            logger.info(f"📅 Следующий ежедневный отчет через {wait_seconds/3600:.1f} часов")
            
            # Ждем до времени отправки
            await asyncio.sleep(wait_seconds)
            
            if self.is_running:
                logger.info("📊 Отправка ежедневных отчетов...")
                await self.send_daily_reports()
    
    async def start(self):
        """Запускаем планировщик"""
        if self.is_running:
            return
        
        self.is_running = True
        self.task = asyncio.create_task(self.schedule_daily_reports())
        logger.info("📅 Планировщик ежедневных отчетов запущен")
    
    async def stop(self):
        """Останавливаем планировщик"""
        if not self.is_running:
            return
        
        self.is_running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        
        logger.info("📅 Планировщик ежедневных отчетов остановлен")
    
    async def send_test_report(self, user_id: int):
        """Отправляем тестовый отчет конкретному пользователю"""
        try:
            summary = self.reports.format_trade_summary(user_id, days=1)
            active_positions = self.storage.get_positions(user_id)
            
            if active_positions:
                summary += f"\n\n🔄 Активных позиций: {len(active_positions)}"
            
            summary += "\n\n🧪 Это тестовый отчет"
            
            await notification_manager.send_daily_summary(user_id, summary)
            logger.info(f"📊 Тестовый отчет отправлен пользователю {user_id}")
            
        except Exception as e:
            logger.error(f"Ошибка отправки тестового отчета: {e}")

# Глобальный экземпляр
daily_reporter = DailyReporter()