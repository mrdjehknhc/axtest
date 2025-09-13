import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional
from aiogram import Bot
from config import BOT_TOKEN

logger = logging.getLogger(__name__)

class NotificationManager:
    def __init__(self, bot_token: str = BOT_TOKEN):
        self.bot = Bot(token=bot_token)
        self.notification_settings = {}  # user_id -> settings
        
    def set_user_notifications(self, user_id: int, settings: dict):
        """Настройки уведомлений пользователя"""
        self.notification_settings[user_id] = settings
    
    def get_user_settings(self, user_id: int) -> dict:
        """Получаем настройки уведомлений"""
        return self.notification_settings.get(user_id, {
            'position_open': True,
            'position_close': True,
            'stop_loss': True,
            'take_profit': True,
            'breakeven': True,
            'daily_summary': False,
            'errors': True
        })
    
    async def send_notification(self, user_id: int, message: str, notification_type: str = 'info'):
        """Отправляем уведомление пользователю"""
        try:
            settings = self.get_user_settings(user_id)
            if not settings.get(notification_type, True):
                return
            
            await self.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode='HTML'
            )
            logger.debug(f"📨 Уведомление отправлено пользователю {user_id}: {notification_type}")
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления пользователю {user_id}: {e}")
    
    async def notify_position_opened(self, user_id: int, position: dict):
        """Уведомление об открытии позиции"""
        contract = position['contract_address']
        amount = position['invested_sol']
        price = position['entry_price']
        sl = position.get('sl', 0)
        tp_count = len(position.get('tp_levels', []))
        
        message = f"""
🟢 <b>Позиция открыта</b>

💰 Контракт: <code>{contract[:8]}...{contract[-6:]}</code>
💵 Размер: {amount:.4f} SOL
📈 Цена входа: {price:.8f}
🛑 Stop Loss: {sl}%
🎯 Take Profit: {tp_count} уровней

⏰ {datetime.now().strftime('%H:%M:%S')}
"""
        await self.send_notification(user_id, message, 'position_open')
    
    async def notify_position_closed(self, user_id: int, contract_address: str, 
                                   pnl_percent: float, pnl_sol: float, reason: str = "manual"):
        """Уведомление о закрытии позиции"""
        status_icon = "🟢" if pnl_sol >= 0 else "🔴"
        reason_text = {
            'manual': 'Ручное закрытие',
            'sl': 'Stop Loss',
            'tp': 'Take Profit',
            'panic': 'Panic Sell'
        }.get(reason, reason)
        
        message = f"""
{status_icon} <b>Позиция закрыта</b>

💰 Контракт: <code>{contract_address[:8]}...{contract_address[-6:]}</code>
📊 P&L: {pnl_sol:+.4f} SOL ({pnl_percent:+.2f}%)
🔄 Причина: {reason_text}

⏰ {datetime.now().strftime('%H:%M:%S')}
"""
        await self.send_notification(user_id, message, 'position_close')
    
    async def notify_stop_loss(self, user_id: int, contract_address: str, pnl_percent: float):
        """Уведомление о срабатывании стоп-лосс"""
        message = f"""
🛑 <b>STOP LOSS</b>

💰 Контракт: <code>{contract_address[:8]}...{contract_address[-6:]}</code>
📉 Убыток: {pnl_percent:.2f}%
🔄 Позиция автоматически закрыта

⏰ {datetime.now().strftime('%H:%M:%S')}
"""
        await self.send_notification(user_id, message, 'stop_loss')
    
    async def notify_take_profit(self, user_id: int, contract_address: str, 
                               tp_level: float, volume_percent: float, pnl_percent: float):
        """Уведомление о срабатывании тейк-профит"""
        message = f"""
🎯 <b>TAKE PROFIT</b>

💰 Контракт: <code>{contract_address[:8]}...{contract_address[-6:]}</code>
📈 Уровень: {tp_level}x (+{(tp_level-1)*100:.0f}%)
📊 Продано: {volume_percent}% позиции
💹 Текущий P&L: +{pnl_percent:.2f}%

⏰ {datetime.now().strftime('%H:%M:%S')}
"""
        await self.send_notification(user_id, message, 'take_profit')
    
    async def notify_breakeven(self, user_id: int, contract_address: str, pnl_percent: float):
        """Уведомление о перемещении в безубыток"""
        message = f"""
⚖️ <b>BREAKEVEN</b>

💰 Контракт: <code>{contract_address[:8]}...{contract_address[-6:]}</code>
📈 Прибыль: +{pnl_percent:.2f}%
🔒 Stop Loss перемещен в безубыток

⏰ {datetime.now().strftime('%H:%M:%S')}
"""
        await self.send_notification(user_id, message, 'breakeven')
    
    async def notify_error(self, user_id: int, error_message: str, context: str = ""):
        """Уведомление об ошибке"""
        message = f"""
⚠️ <b>Ошибка системы</b>

🔍 Контекст: {context}
💥 Ошибка: {error_message[:200]}

⏰ {datetime.now().strftime('%H:%M:%S')}
"""
        await self.send_notification(user_id, message, 'errors')
    
    async def send_daily_summary(self, user_id: int, summary_text: str):
        """Ежедневная сводка"""
        message = f"""
📊 <b>Ежедневный отчет</b>

{summary_text}

📅 {datetime.now().strftime('%d.%m.%Y')}
"""
        await self.send_notification(user_id, message, 'daily_summary')
    
    def format_notification_settings(self, user_id: int) -> str:
        """Форматируем текущие настройки уведомлений"""
        settings = self.get_user_settings(user_id)
        
        status_map = {True: "✅", False: "❌"}
        
        text = "🔔 <b>Настройки уведомлений:</b>\n\n"
        text += f"{status_map[settings['position_open']]} Открытие позиций\n"
        text += f"{status_map[settings['position_close']]} Закрытие позиций\n"
        text += f"{status_map[settings['stop_loss']]} Stop Loss\n"
        text += f"{status_map[settings['take_profit']]} Take Profit\n"
        text += f"{status_map[settings['breakeven']]} Breakeven\n"
        text += f"{status_map[settings['daily_summary']]} Ежедневная сводка\n"
        text += f"{status_map[settings['errors']]} Ошибки системы\n"
        
        return text

# Глобальный экземпляр для использования в других модулях
notification_manager = NotificationManager()