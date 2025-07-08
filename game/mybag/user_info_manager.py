"""
我的信息模块 - 用户信息查询和统计
提供用户个人信息、财富统计、游戏记录等功能
"""

import sqlite3
import os
from datetime import datetime, date, timedelta
from typing import Dict, Any, Optional, List, Tuple


class UserInfoManager:
    """用户信息管理器"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
    
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
    
    def get_user_basic_info(self, user_id: str, username: str) -> Dict[str, Any]:
        """
        获取用户基本信息
        
        Returns:
            Dict包含用户基本信息
        """
        self._ensure_user_exists(user_id, username)
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            # 获取用户基本信息
            cursor.execute('''
                SELECT username, money, bank_money, total_earned, level, exp,
                       checkin_streak, total_checkin, created_at, updated_at
                FROM users WHERE user_id = ?
            ''', (user_id,))
            
            user_data = cursor.fetchone()
            if not user_data:
                return {'error': '用户数据不存在'}
            
            (username, money, bank_money, total_earned, level, exp,
             checkin_streak, total_checkin, created_at, updated_at) = user_data
            
            # 计算总资产
            total_assets = money + bank_money
            
            # 获取注册天数
            if created_at:
                created_date = datetime.strptime(created_at, '%Y-%m-%d %H:%M:%S')
                days_registered = (datetime.now() - created_date).days + 1
            else:
                days_registered = 1
            
            return {
                'username': username,
                'money': money,
                'bank_money': bank_money,
                'total_assets': total_assets,
                'total_earned': total_earned,
                'level': level,
                'exp': exp,
                'checkin_streak': checkin_streak,
                'total_checkin': total_checkin,
                'days_registered': days_registered,
                'created_at': created_at,
                'updated_at': updated_at
            }
            
        except Exception as e:
            return {'error': f'获取用户信息失败：{str(e)}'}
        finally:
            conn.close()
    
    def get_user_statistics(self, user_id: str) -> Dict[str, Any]:
        """
        获取用户统计信息
        
        Returns:
            Dict包含各种统计数据
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            stats = {}
            
            # 银行交易统计
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_transactions,
                    SUM(CASE WHEN transaction_type = 'deposit' THEN amount ELSE 0 END) as total_deposits,
                    SUM(CASE WHEN transaction_type = 'withdraw' THEN amount ELSE 0 END) as total_withdraws
                FROM bank_transactions WHERE user_id = ?
            ''', (user_id,))
            
            bank_stats = cursor.fetchone()
            stats['bank'] = {
                'total_transactions': bank_stats[0] or 0,
                'total_deposits': bank_stats[1] or 0,
                'total_withdraws': bank_stats[2] or 0
            }
            
            # 打工统计
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_works,
                    SUM(total_earned) as total_work_income,
                    AVG(total_earned) as avg_work_income,
                    work_type
                FROM work_records 
                WHERE user_id = ? 
                GROUP BY work_type
                ORDER BY COUNT(*) DESC
            ''', (user_id,))
            
            work_data = cursor.fetchall()
            stats['work'] = {
                'total_works': sum(row[0] for row in work_data),
                'total_income': sum(row[1] for row in work_data),
                'work_types': [(row[3], row[0], row[1]) for row in work_data]  # (类型, 次数, 收入)
            }
            
            # 抢劫统计（作为抢劫者）
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_robberies,
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_robberies,
                    SUM(CASE WHEN success = 1 THEN amount ELSE 0 END) as total_robbed
                FROM robbery_records WHERE robber_id = ?
            ''', (user_id,))
            
            rob_stats = cursor.fetchone()
            
            # 被抢统计（作为受害者）
            cursor.execute('''
                SELECT 
                    COUNT(*) as times_robbed,
                    SUM(CASE WHEN success = 1 THEN amount ELSE 0 END) as total_lost
                FROM robbery_records WHERE victim_id = ?
            ''', (user_id,))
            
            robbed_stats = cursor.fetchone()
            
            stats['robbery'] = {
                'robberies_initiated': rob_stats[0] or 0,
                'successful_robberies': rob_stats[1] or 0,
                'total_robbed': rob_stats[2] or 0,
                'times_robbed': robbed_stats[0] or 0,
                'total_lost': robbed_stats[1] or 0,
                'rob_success_rate': round((rob_stats[1] or 0) / max(rob_stats[0] or 1, 1) * 100, 1)
            }
            
            # 物品统计
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_items,
                    SUM(quantity) as total_quantity,
                    SUM(value * quantity) as total_item_value
                FROM user_items WHERE user_id = ?
            ''', (user_id,))
            
            item_stats = cursor.fetchone()
            stats['items'] = {
                'total_items': item_stats[0] or 0,
                'total_quantity': item_stats[1] or 0,
                'total_value': item_stats[2] or 0
            }
            
            return stats
            
        except Exception as e:
            return {'error': f'获取统计信息失败：{str(e)}'}
        finally:
            conn.close()
    
    def get_user_ranking(self, user_id: str) -> Dict[str, Any]:
        """
        获取用户在各个排行榜中的排名
        
        Returns:
            Dict包含各种排名信息
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            rankings = {}
            
            # 金钱排名
            cursor.execute('''
                SELECT COUNT(*) + 1 as rank
                FROM users 
                WHERE money > (SELECT money FROM users WHERE user_id = ?)
            ''', (user_id,))
            rankings['money_rank'] = cursor.fetchone()[0]
            
            # 总资产排名
            cursor.execute('''
                SELECT COUNT(*) + 1 as rank
                FROM users 
                WHERE (money + bank_money) > (
                    SELECT money + bank_money FROM users WHERE user_id = ?
                )
            ''', (user_id,))
            rankings['assets_rank'] = cursor.fetchone()[0]
            
            # 签到排名
            cursor.execute('''
                SELECT COUNT(*) + 1 as rank
                FROM users 
                WHERE checkin_streak > (SELECT checkin_streak FROM users WHERE user_id = ?)
                   OR (checkin_streak = (SELECT checkin_streak FROM users WHERE user_id = ?) 
                       AND total_checkin > (SELECT total_checkin FROM users WHERE user_id = ?))
            ''', (user_id, user_id, user_id))
            rankings['checkin_rank'] = cursor.fetchone()[0]
            
            # 获取总用户数
            cursor.execute('SELECT COUNT(*) FROM users WHERE money > 0 OR total_checkin > 0')
            total_users = cursor.fetchone()[0]
            rankings['total_users'] = total_users
            
            return rankings
            
        except Exception as e:
            return {'error': f'获取排名信息失败：{str(e)}'}
        finally:
            conn.close()
    
    def get_recent_activities(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取用户最近活动记录
        
        Args:
            user_id: 用户ID
            limit: 返回记录数限制
            
        Returns:
            活动记录列表
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            activities = []
            
            # 签到记录
            cursor.execute('''
                SELECT 'checkin' as type, checkin_date as date, reward_money as amount, 
                       consecutive_days as extra, created_at
                FROM checkin_records 
                WHERE user_id = ? 
                ORDER BY created_at DESC 
                LIMIT ?
            ''', (user_id, limit // 2))
            
            for row in cursor.fetchall():
                activities.append({
                    'type': row[0],
                    'date': row[1],
                    'amount': row[2],
                    'extra': f"连续{row[3]}天",
                    'timestamp': row[4]
                })
            
            # 银行交易记录
            cursor.execute('''
                SELECT 'bank' as type, transaction_type, amount, created_at
                FROM bank_transactions 
                WHERE user_id = ? 
                ORDER BY created_at DESC 
                LIMIT ?
            ''', (user_id, limit // 2))
            
            for row in cursor.fetchall():
                activities.append({
                    'type': row[0],
                    'action': row[1],
                    'amount': row[2],
                    'timestamp': row[3]
                })
            
            # 按时间排序
            activities.sort(key=lambda x: x['timestamp'], reverse=True)
            
            return activities[:limit]
            
        except Exception as e:
            return []
        finally:
            conn.close()
    
    def _get_level_info(self, exp: int) -> Dict[str, int]:
        """
        获取等级信息
        
        Args:
            exp: 当前经验值
            
        Returns:
            等级信息字典
        """
        # 分阶段等级计算
        def calculate_level(exp):
            if exp < 500:  # 1-5级：每级100经验
                return max(1, exp // 100 + 1)
            elif exp < 1500:  # 6-10级：每级200经验
                return 5 + (exp - 500) // 200 + 1
            elif exp < 4000:  # 11-15级：每级500经验  
                return 10 + (exp - 1500) // 500 + 1
            else:  # 16级以上：每级1000经验
                return 15 + (exp - 4000) // 1000 + 1
        
        current_level = calculate_level(exp)
        next_level = current_level + 1
        
        # 计算当前等级的经验起点和下一等级的经验起点
        def get_level_exp_requirement(level):
            if level <= 5:
                return (level - 1) * 100
            elif level <= 10:
                return 500 + (level - 6) * 200
            elif level <= 15:
                return 1500 + (level - 11) * 500
            else:
                return 4000 + (level - 16) * 1000
        
        # 计算每个等级需要多少经验升级
        def get_exp_for_next_level(level):
            if level <= 4:
                return 100
            elif level <= 9:
                return 200
            elif level <= 14:
                return 500
            else:
                return 1000
        
        current_level_start = get_level_exp_requirement(current_level)
        next_level_start = get_level_exp_requirement(next_level)
        exp_for_current_level = get_exp_for_next_level(current_level)
        
        # 当前等级进度
        level_progress = exp - current_level_start
        # 升级还需要的经验
        exp_needed = next_level_start - exp
        
        return {
            'current_level': current_level,
            'next_level': next_level,
            'current_exp': exp,
            'level_progress': level_progress,
            'exp_needed': exp_needed,
            'exp_for_current_level': exp_for_current_level,
            'progress_percentage': int((level_progress / exp_for_current_level) * 100)
        }
    
    def get_comprehensive_info(self, user_id: str, username: str) -> Dict[str, Any]:
        """
        获取用户完整信息（包含基本信息、统计、排名）
        
        Returns:
            完整的用户信息字典
        """
        basic_info = self.get_user_basic_info(user_id, username)
        if 'error' in basic_info:
            return basic_info
        
        statistics = self.get_user_statistics(user_id)
        rankings = self.get_user_ranking(user_id)
        recent_activities = self.get_recent_activities(user_id, 5)
        
        return {
            'basic': basic_info,
            'stats': statistics,
            'rankings': rankings,
            'recent_activities': recent_activities
        }