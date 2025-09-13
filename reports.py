import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class TradeRecord:
    """Запись о сделке"""
    id: str
    user_id: int
    contract_address: str
    action: str  # 'open', 'close', 'sl', 'tp', 'breakeven'
    amount_sol: float
    token_amount: float
    price: float
    pnl_percent: float = 0
    pnl_sol: float = 0
    timestamp: float = None
    details: dict = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().timestamp()
        if self.details is None:
            self.details = {}

class ReportsManager:
    def __init__(self, filename: str = 'trade_history.json'):
        self.filename = filename
        self.ensure_file_exists()
    
    def ensure_file_exists(self):
        if not os.path.exists(self.filename):
            with open(self.filename, 'w') as f:
                json.dump([], f)
    
    def load_history(self) -> List[dict]:
        try:
            with open(self.filename, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Ошибка загрузки истории: {e}")
            return []
    
    def save_history(self, history: List[dict]):
        try:
            with open(self.filename, 'w') as f:
                json.dump(history, f, indent=2)
        except Exception as e:
            logger.error(f"Ошибка сохранения истории: {e}")
    
    def add_trade_record(self, record: TradeRecord):
        """Добавляем запись о сделке"""
        history = self.load_history()
        history.append({
            'id': record.id,
            'user_id': record.user_id,
            'contract_address': record.contract_address,
            'action': record.action,
            'amount_sol': record.amount_sol,
            'token_amount': record.token_amount,
            'price': record.price,
            'pnl_percent': record.pnl_percent,
            'pnl_sol': record.pnl_sol,
            'timestamp': record.timestamp,
            'date': datetime.fromtimestamp(record.timestamp).strftime('%Y-%m-%d %H:%M:%S'),
            'details': record.details
        })
        self.save_history(history)
        logger.info(f"📝 Добавлена запись о сделке: {record.action} для {record.contract_address[:8]}...")
    
    def get_user_trades(self, user_id: int, days: int = None) -> List[dict]:
        """Получаем сделки пользователя за период"""
        history = self.load_history()
        user_trades = [t for t in history if t['user_id'] == user_id]
        
        if days:
            cutoff = datetime.now() - timedelta(days=days)
            user_trades = [t for t in user_trades if t['timestamp'] > cutoff.timestamp()]
        
        return sorted(user_trades, key=lambda x: x['timestamp'], reverse=True)
    
    def get_user_statistics(self, user_id: int, days: int = None) -> Dict:
        """Статистика по пользователю"""
        trades = self.get_user_trades(user_id, days)
        
        if not trades:
            return {
                'total_trades': 0,
                'open_positions': 0,
                'closed_positions': 0,
                'total_invested': 0,
                'total_pnl_sol': 0,
                'total_pnl_percent': 0,
                'win_rate': 0,
                'best_trade': None,
                'worst_trade': None,
                'avg_hold_time': 0
            }
        
        # Группируем сделки по контрактам
        positions = {}
        for trade in trades:
            contract = trade['contract_address']
            if contract not in positions:
                positions[contract] = []
            positions[contract].append(trade)
        
        total_invested = 0
        total_pnl_sol = 0
        closed_trades = []
        open_count = 0
        
        for contract, contract_trades in positions.items():
            contract_trades.sort(key=lambda x: x['timestamp'])
            
            # Ищем пары открытие-закрытие
            opens = [t for t in contract_trades if t['action'] == 'open']
            closes = [t for t in contract_trades if t['action'] in ['close', 'sl']]
            
            for open_trade in opens:
                total_invested += open_trade['amount_sol']
                
                # Ищем соответствующее закрытие
                close_trade = None
                for c in closes:
                    if c['timestamp'] > open_trade['timestamp']:
                        close_trade = c
                        break
                
                if close_trade:
                    pnl_sol = close_trade['pnl_sol']
                    total_pnl_sol += pnl_sol
                    closed_trades.append({
                        'open_time': open_trade['timestamp'],
                        'close_time': close_trade['timestamp'],
                        'hold_time': close_trade['timestamp'] - open_trade['timestamp'],
                        'pnl_sol': pnl_sol,
                        'pnl_percent': close_trade['pnl_percent'],
                        'invested': open_trade['amount_sol'],
                        'contract': contract
                    })
                else:
                    open_count += 1
        
        # Рассчитываем метрики
        win_count = len([t for t in closed_trades if t['pnl_sol'] > 0])
        win_rate = (win_count / len(closed_trades) * 100) if closed_trades else 0
        
        best_trade = max(closed_trades, key=lambda x: x['pnl_percent']) if closed_trades else None
        worst_trade = min(closed_trades, key=lambda x: x['pnl_percent']) if closed_trades else None
        
        avg_hold_time = sum(t['hold_time'] for t in closed_trades) / len(closed_trades) if closed_trades else 0
        avg_hold_hours = avg_hold_time / 3600
        
        total_pnl_percent = (total_pnl_sol / total_invested * 100) if total_invested > 0 else 0
        
        return {
            'total_trades': len(trades),
            'open_positions': open_count,
            'closed_positions': len(closed_trades),
            'total_invested': total_invested,
            'total_pnl_sol': total_pnl_sol,
            'total_pnl_percent': total_pnl_percent,
            'win_rate': win_rate,
            'best_trade': best_trade,
            'worst_trade': worst_trade,
            'avg_hold_time_hours': avg_hold_hours,
            'recent_trades': trades[:10]  # Последние 10 сделок
        }
    
    def log_position_open(self, user_id: int, position: dict):
        """Логируем открытие позиции"""
        record = TradeRecord(
            id=position['id'],
            user_id=user_id,
            contract_address=position['contract_address'],
            action='open',
            amount_sol=position['invested_sol'],
            token_amount=position['token_amount'],
            price=position['entry_price'],
            details={
                'sl': position.get('sl'),
                'tp_levels': position.get('tp_levels'),
                'breakeven_percent': position.get('breakeven_percent'),
                'tx_hash': position.get('transaction_hash')
            }
        )
        self.add_trade_record(record)
    
    def log_position_close(self, user_id: int, contract_address: str, action: str, 
                          amount_sol: float, token_amount: float, current_price: float, 
                          pnl_percent: float, entry_price: float = None):
        """Логируем закрытие позиции"""
        pnl_sol = amount_sol * (pnl_percent / 100) if entry_price else 0
        
        record = TradeRecord(
            id=f"{contract_address}_{action}_{int(datetime.now().timestamp())}",
            user_id=user_id,
            contract_address=contract_address,
            action=action,
            amount_sol=amount_sol,
            token_amount=token_amount,
            price=current_price,
            pnl_percent=pnl_percent,
            pnl_sol=pnl_sol,
            details={'entry_price': entry_price}
        )
        self.add_trade_record(record)
    
    def format_trade_summary(self, user_id: int, days: int = 7) -> str:
        """Форматируем краткий отчет"""
        stats = self.get_user_statistics(user_id, days)
        
        if stats['total_trades'] == 0:
            return f"📊 Отчет за {days} дней:\n\n🔭 Сделок не найдено"
        
        period_text = f"{days} дней" if days else "все время"
        status_icon = "🟢" if stats['total_pnl_sol'] >= 0 else "🔴"
        
        text = f"📊 Отчет за {period_text}:\n\n"
        text += f"📈 Сделок: {stats['total_trades']}\n"
        text += f"📂 Открытых: {stats['open_positions']}\n"
        text += f"✅ Закрытых: {stats['closed_positions']}\n"
        text += f"💰 Вложено: {stats['total_invested']:.4f} SOL\n"
        text += f"{status_icon} P&L: {stats['total_pnl_sol']:+.4f} SOL ({stats['total_pnl_percent']:+.2f}%)\n"
        text += f"🎯 Винрейт: {stats['win_rate']:.1f}%\n"
        
        if stats['best_trade']:
            text += f"🚀 Лучшая: +{stats['best_trade']['pnl_percent']:.1f}%\n"
        
        if stats['worst_trade']:
            text += f"💥 Худшая: {stats['worst_trade']['pnl_percent']:+.1f}%\n"
        
        if stats['avg_hold_time_hours'] > 0:
            text += f"⏱️ Ср. время: {stats['avg_hold_time_hours']:.1f}ч"
        
        return text