"""
银行模块 - 银行系统
提供存款、取款、利息计算、交易记录等功能
"""

import sqlite3
import os
from datetime import datetime, date, timedelta
from typing import Dict, Any, Optional, List, Tuple


class BankManager:
    """银行管理器"""
    
    def __init__(self, db_path: str, config: Dict[str, Any] = None):
        self.db_path = db_path
        self.config = config or {}
        
        # 从配置获取参数
        game_settings = self.config.get('game_system_settings', {})
        
        # 银行配置
        self.min_deposit = 10          # 最小存款金额
        self.min_withdraw = 10         # 最小取款金额
        self.max_deposit = 100000      # 单次最大存款
        self.max_withdraw = 50000      # 单次最大取款
        self.daily_withdraw_limit = 200000  # 每日取款限额
        self.interest_rate = game_settings.get('bank_interest_rate', 0.1) / 100  # 转换为小数
        self.vip_threshold = game_settings.get('vip_threshold', 10000)     # VIP用户门槛
        self.vip_interest_rate = game_settings.get('bank_vip_interest_rate', 0.15) / 100  # 转换为小数
        
    def _get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        return sqlite3.connect(self.db_path)
    
    def _ensure_user_exists(self, user_id: str, username: str) -> None:
        """确保用户存在于数据库中"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT OR IGNORE INTO users (user_id, username)
                VALUES (?, ?)
            ''', (user_id, username))
            conn.commit()
        finally:
            conn.close()
    
    def deposit(self, user_id: str, username: str, amount: int) -> Dict[str, Any]:
        """
        存款功能
        
        Args:
            user_id: 用户ID
            username: 用户名
            amount: 存款金额
            
        Returns:
            存款结果
        """
        self._ensure_user_exists(user_id, username)
        
        # 验证存款金额
        if amount < self.min_deposit:
            return {
                "success": False,
                "message": f"存款金额不能少于 {self.min_deposit} 金币"
            }
        
        if amount > self.max_deposit:
            return {
                "success": False,
                "message": f"单次存款不能超过 {self.max_deposit} 金币"
            }
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            # 获取用户当前信息
            cursor.execute('''
                SELECT money, bank_money FROM users WHERE user_id = ?
            ''', (user_id,))
            
            user_data = cursor.fetchone()
            if not user_data:
                return {"success": False, "message": "用户数据错误"}
            
            current_money, current_bank_money = user_data
            
            # 检查现金是否足够
            if current_money < amount:
                return {
                    "success": False,
                    "message": f"现金不足！当前现金：{current_money} 金币，需要：{amount} 金币"
                }
            
            # 更新用户资金
            new_money = current_money - amount
            new_bank_money = current_bank_money + amount
            
            cursor.execute('''
                UPDATE users 
                SET money = ?, bank_money = ?, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
            ''', (new_money, new_bank_money, user_id))
            
            # 记录交易
            cursor.execute('''
                INSERT INTO bank_transactions 
                (user_id, transaction_type, amount, balance_before, balance_after)
                VALUES (?, 'deposit', ?, ?, ?)
            ''', (user_id, amount, current_bank_money, new_bank_money))
            
            conn.commit()
            
            return {
                "success": True,
                "transaction_type": "存款",
                "amount": amount,
                "new_money": new_money,
                "new_bank_money": new_bank_money,
                "total_assets": new_money + new_bank_money
            }
            
        except Exception as e:
            conn.rollback()
            return {
                "success": False,
                "message": f"存款失败：{str(e)}"
            }
        finally:
            conn.close()
    
    def withdraw(self, user_id: str, username: str, amount: int) -> Dict[str, Any]:
        """
        取款功能
        
        Args:
            user_id: 用户ID
            username: 用户名
            amount: 取款金额
            
        Returns:
            取款结果
        """
        self._ensure_user_exists(user_id, username)
        
        # 验证取款金额
        if amount < self.min_withdraw:
            return {
                "success": False,
                "message": f"取款金额不能少于 {self.min_withdraw} 金币"
            }
        
        if amount > self.max_withdraw:
            return {
                "success": False,
                "message": f"单次取款不能超过 {self.max_withdraw} 金币"
            }
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            # 检查每日取款限额
            today = date.today()
            cursor.execute('''
                SELECT SUM(amount) FROM bank_transactions 
                WHERE user_id = ? AND transaction_type = 'withdraw' 
                AND date(created_at) = ?
            ''', (user_id, today))
            
            today_withdraw = cursor.fetchone()[0] or 0
            
            if today_withdraw + amount > self.daily_withdraw_limit:
                remaining = self.daily_withdraw_limit - today_withdraw
                return {
                    "success": False,
                    "message": f"超过每日取款限额！今日已取款：{today_withdraw}，剩余额度：{remaining}"
                }
            
            # 获取用户当前信息
            cursor.execute('''
                SELECT money, bank_money FROM users WHERE user_id = ?
            ''', (user_id,))
            
            user_data = cursor.fetchone()
            if not user_data:
                return {"success": False, "message": "用户数据错误"}
            
            current_money, current_bank_money = user_data
            
            # 检查银行余额是否足够
            if current_bank_money < amount:
                return {
                    "success": False,
                    "message": f"银行余额不足！当前余额：{current_bank_money} 金币，需要：{amount} 金币"
                }
            
            # 更新用户资金
            new_money = current_money + amount
            new_bank_money = current_bank_money - amount
            
            cursor.execute('''
                UPDATE users 
                SET money = ?, bank_money = ?, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
            ''', (new_money, new_bank_money, user_id))
            
            # 记录交易
            cursor.execute('''
                INSERT INTO bank_transactions 
                (user_id, transaction_type, amount, balance_before, balance_after)
                VALUES (?, 'withdraw', ?, ?, ?)
            ''', (user_id, amount, current_bank_money, new_bank_money))
            
            conn.commit()
            
            return {
                "success": True,
                "transaction_type": "取款",
                "amount": amount,
                "new_money": new_money,
                "new_bank_money": new_bank_money,
                "total_assets": new_money + new_bank_money,
                "today_withdraw": today_withdraw + amount,
                "remaining_limit": self.daily_withdraw_limit - today_withdraw - amount
            }
            
        except Exception as e:
            conn.rollback()
            return {
                "success": False,
                "message": f"取款失败：{str(e)}"
            }
        finally:
            conn.close()
    
    def get_bank_info(self, user_id: str, username: str) -> Dict[str, Any]:
        """
        获取银行信息
        
        Returns:
            银行信息
        """
        self._ensure_user_exists(user_id, username)
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            # 获取用户基本信息
            cursor.execute('''
                SELECT money, bank_money, username FROM users WHERE user_id = ?
            ''', (user_id,))
            
            user_data = cursor.fetchone()
            if not user_data:
                return {"error": "用户数据不存在"}
            
            money, bank_money, username = user_data
            total_assets = money + bank_money
            
            # 判断是否为VIP用户
            is_vip = bank_money >= self.vip_threshold
            current_interest_rate = self.vip_interest_rate if is_vip else self.interest_rate
            
            # 计算每日利息
            daily_interest = int(bank_money * current_interest_rate)
            
            # 获取今日取款额度
            today = date.today()
            cursor.execute('''
                SELECT SUM(amount) FROM bank_transactions 
                WHERE user_id = ? AND transaction_type = 'withdraw' 
                AND date(created_at) = ?
            ''', (user_id, today))
            
            today_withdraw = cursor.fetchone()[0] or 0
            remaining_withdraw = self.daily_withdraw_limit - today_withdraw
            
            # 获取银行统计
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_transactions,
                    SUM(CASE WHEN transaction_type = 'deposit' THEN amount ELSE 0 END) as total_deposits,
                    SUM(CASE WHEN transaction_type = 'withdraw' THEN amount ELSE 0 END) as total_withdraws
                FROM bank_transactions WHERE user_id = ?
            ''', (user_id,))
            
            stats = cursor.fetchone()
            
            # 获取最近交易记录
            cursor.execute('''
                SELECT transaction_type, amount, created_at
                FROM bank_transactions 
                WHERE user_id = ? 
                ORDER BY created_at DESC 
                LIMIT 5
            ''', (user_id,))
            
            recent_transactions = cursor.fetchall()
            
            return {
                "username": username,
                "money": money,
                "bank_money": bank_money,
                "total_assets": total_assets,
                "is_vip": is_vip,
                "vip_threshold": self.vip_threshold,
                "interest_rate": current_interest_rate * 100,  # 转换为百分比
                "daily_interest": daily_interest,
                "today_withdraw": today_withdraw,
                "remaining_withdraw": remaining_withdraw,
                "daily_limit": self.daily_withdraw_limit,
                "limits": {
                    "min_deposit": self.min_deposit,
                    "max_deposit": self.max_deposit,
                    "min_withdraw": self.min_withdraw,
                    "max_withdraw": self.max_withdraw
                },
                "stats": {
                    "total_transactions": stats[0],
                    "total_deposits": stats[1] or 0,
                    "total_withdraws": stats[2] or 0
                },
                "recent_transactions": recent_transactions
            }
            
        except Exception as e:
            return {"error": f"获取银行信息失败：{str(e)}"}
        finally:
            conn.close()
    
    def transfer(self, from_user_id: str, to_user_id: str, from_username: str, 
                to_username: str, amount: int) -> Dict[str, Any]:
        """
        银行转账功能
        
        Args:
            from_user_id: 转出用户ID
            to_user_id: 转入用户ID
            from_username: 转出用户名
            to_username: 转入用户名
            amount: 转账金额
            
        Returns:
            转账结果
        """
        if from_user_id == to_user_id:
            return {"success": False, "message": "不能向自己转账"}
        
        if amount < self.min_deposit:
            return {
                "success": False,
                "message": f"转账金额不能少于 {self.min_deposit} 金币"
            }
        
        if amount > self.max_deposit:
            return {
                "success": False,
                "message": f"单次转账不能超过 {self.max_deposit} 金币"
            }
        
        self._ensure_user_exists(from_user_id, from_username)
        self._ensure_user_exists(to_user_id, to_username)
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            # 获取转出用户信息
            cursor.execute('''
                SELECT bank_money FROM users WHERE user_id = ?
            ''', (from_user_id,))
            
            from_user = cursor.fetchone()
            if not from_user or from_user[0] < amount:
                return {
                    "success": False,
                    "message": f"银行余额不足！当前余额：{from_user[0] if from_user else 0} 金币"
                }
            
            # 获取转入用户信息
            cursor.execute('''
                SELECT bank_money FROM users WHERE user_id = ?
            ''', (to_user_id,))
            
            to_user = cursor.fetchone()
            if not to_user:
                return {"success": False, "message": "转入用户不存在"}
            
            # 执行转账
            new_from_balance = from_user[0] - amount
            new_to_balance = to_user[0] + amount
            
            # 更新转出用户
            cursor.execute('''
                UPDATE users 
                SET bank_money = ?, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
            ''', (new_from_balance, from_user_id))
            
            # 更新转入用户
            cursor.execute('''
                UPDATE users 
                SET bank_money = ?, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
            ''', (new_to_balance, to_user_id))
            
            # 记录转出交易
            cursor.execute('''
                INSERT INTO bank_transactions 
                (user_id, transaction_type, amount, balance_before, balance_after)
                VALUES (?, 'transfer_out', ?, ?, ?)
            ''', (from_user_id, amount, from_user[0], new_from_balance))
            
            # 记录转入交易
            cursor.execute('''
                INSERT INTO bank_transactions 
                (user_id, transaction_type, amount, balance_before, balance_after)
                VALUES (?, 'transfer_in', ?, ?, ?)
            ''', (to_user_id, amount, to_user[0], new_to_balance))
            
            conn.commit()
            
            return {
                "success": True,
                "from_username": from_username,
                "to_username": to_username,
                "amount": amount,
                "new_from_balance": new_from_balance,
                "new_to_balance": new_to_balance
            }
            
        except Exception as e:
            conn.rollback()
            return {
                "success": False,
                "message": f"转账失败：{str(e)}"
            }
        finally:
            conn.close()
    
    def apply_daily_interest(self) -> Dict[str, Any]:
        """
        应用每日利息（系统功能）
        
        Returns:
            利息应用结果
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            # 获取所有有存款的用户
            cursor.execute('''
                SELECT user_id, bank_money FROM users WHERE bank_money > 0
            ''')
            
            users = cursor.fetchall()
            total_interest = 0
            processed_users = 0
            
            for user_id, bank_money in users:
                # 判断用户类型和利率
                is_vip = bank_money >= self.vip_threshold
                rate = self.vip_interest_rate if is_vip else self.interest_rate
                
                # 计算利息
                interest = int(bank_money * rate)
                
                if interest > 0:
                    new_bank_money = bank_money + interest
                    
                    # 更新用户银行余额
                    cursor.execute('''
                        UPDATE users 
                        SET bank_money = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE user_id = ?
                    ''', (new_bank_money, user_id))
                    
                    # 记录利息交易
                    cursor.execute('''
                        INSERT INTO bank_transactions 
                        (user_id, transaction_type, amount, balance_before, balance_after)
                        VALUES (?, 'interest', ?, ?, ?)
                    ''', (user_id, interest, bank_money, new_bank_money))
                    
                    total_interest += interest
                    processed_users += 1
            
            conn.commit()
            
            return {
                "success": True,
                "processed_users": processed_users,
                "total_interest": total_interest
            }
            
        except Exception as e:
            conn.rollback()
            return {
                "success": False,
                "message": f"应用利息失败：{str(e)}"
            }
        finally:
            conn.close()