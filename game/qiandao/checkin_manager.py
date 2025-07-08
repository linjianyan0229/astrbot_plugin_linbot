"""
签到模块 - 用户签到功能
支持每日签到、连续签到奖励、签到记录查询
"""

import sqlite3
import os
from datetime import datetime, date
from typing import Dict, Any, Optional, Tuple
import random


class CheckinManager:
    """签到管理器"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        
        # 签到奖励配置
        self.base_reward = 100  # 基础签到奖励
        self.consecutive_bonus = {
            3: 50,   # 连续3天额外奖励50
            7: 200,  # 连续7天额外奖励200
            15: 500, # 连续15天额外奖励500
            30: 1000 # 连续30天额外奖励1000
        }
        
        # 随机奖励范围
        self.random_bonus_range = (0, 50)
    
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
    
    def daily_checkin(self, user_id: str, username: str) -> Dict[str, Any]:
        """
        执行每日签到
        
        Returns:
            Dict包含签到结果信息
        """
        self._ensure_user_exists(user_id, username)
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            today = date.today()
            
            # 检查今天是否已经签到
            cursor.execute('''
                SELECT id FROM checkin_records 
                WHERE user_id = ? AND checkin_date = ?
            ''', (user_id, today))
            
            if cursor.fetchone():
                return {
                    'success': False,
                    'message': '今天已经签到过了，明天再来吧！',
                    'already_checked': True
                }
            
            # 获取用户当前信息
            cursor.execute('''
                SELECT money, checkin_streak, total_checkin, last_checkin
                FROM users WHERE user_id = ?
            ''', (user_id,))
            
            user_data = cursor.fetchone()
            if not user_data:
                return {
                    'success': False,
                    'message': '用户数据错误，请重试',
                    'error': True
                }
            
            current_money, current_streak, total_checkin, last_checkin = user_data
            
            # 计算连续签到天数
            new_streak = 1
            if last_checkin:
                last_date = datetime.strptime(last_checkin, '%Y-%m-%d').date()
                days_diff = (today - last_date).days
                
                if days_diff == 1:
                    # 连续签到
                    new_streak = current_streak + 1
                elif days_diff == 0:
                    # 同一天（理论上不应该发生）
                    return {
                        'success': False,
                        'message': '今天已经签到过了',
                        'already_checked': True
                    }
                # 超过1天，重置连续签到
            
            # 计算奖励
            reward = self._calculate_reward(new_streak)
            
            # 更新用户信息
            new_money = current_money + reward['total']
            new_total_checkin = total_checkin + 1
            
            cursor.execute('''
                UPDATE users 
                SET money = ?, checkin_streak = ?, total_checkin = ?, 
                    last_checkin = ?, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
            ''', (new_money, new_streak, new_total_checkin, today, user_id))
            
            # 记录签到
            cursor.execute('''
                INSERT INTO checkin_records 
                (user_id, checkin_date, reward_money, consecutive_days)
                VALUES (?, ?, ?, ?)
            ''', (user_id, today, reward['total'], new_streak))
            
            conn.commit()
            
            return {
                'success': True,
                'message': '签到成功！',
                'reward': reward,
                'new_money': new_money,
                'consecutive_days': new_streak,
                'total_checkin': new_total_checkin
            }
            
        except Exception as e:
            conn.rollback()
            return {
                'success': False,
                'message': f'签到失败：{str(e)}',
                'error': True
            }
        finally:
            conn.close()
    
    def _calculate_reward(self, consecutive_days: int) -> Dict[str, int]:
        """
        计算签到奖励
        
        Args:
            consecutive_days: 连续签到天数
            
        Returns:
            Dict包含奖励详情
        """
        base = self.base_reward
        random_bonus = random.randint(*self.random_bonus_range)
        consecutive_bonus = 0
        
        # 计算连续签到奖励
        for days, bonus in self.consecutive_bonus.items():
            if consecutive_days >= days:
                consecutive_bonus = bonus
        
        return {
            'base': base,
            'random': random_bonus,
            'consecutive': consecutive_bonus,
            'total': base + random_bonus + consecutive_bonus
        }
    
    def get_checkin_info(self, user_id: str, username: str) -> Dict[str, Any]:
        """
        获取用户签到信息
        
        Returns:
            Dict包含签到统计信息
        """
        self._ensure_user_exists(user_id, username)
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            today = date.today()
            
            # 获取用户基本信息
            cursor.execute('''
                SELECT money, checkin_streak, total_checkin, last_checkin
                FROM users WHERE user_id = ?
            ''', (user_id,))
            
            user_data = cursor.fetchone()
            if not user_data:
                return {'error': '用户数据不存在'}
            
            money, streak, total, last_checkin = user_data
            
            # 检查今天是否已签到
            cursor.execute('''
                SELECT reward_money FROM checkin_records 
                WHERE user_id = ? AND checkin_date = ?
            ''', (user_id, today))
            
            today_reward = cursor.fetchone()
            has_checked_today = today_reward is not None
            
            # 获取最近7天签到记录
            cursor.execute('''
                SELECT checkin_date, reward_money, consecutive_days
                FROM checkin_records 
                WHERE user_id = ? 
                ORDER BY checkin_date DESC 
                LIMIT 7
            ''', (user_id,))
            
            recent_records = cursor.fetchall()
            
            # 计算下次签到预期奖励
            next_streak = streak + 1 if has_checked_today else (streak + 1 if last_checkin and 
                                     (today - datetime.strptime(last_checkin, '%Y-%m-%d').date()).days == 1 
                                     else 1)
            next_reward = self._calculate_reward(next_streak)
            
            return {
                'money': money,
                'streak': streak,
                'total_checkin': total,
                'last_checkin': last_checkin,
                'has_checked_today': has_checked_today,
                'today_reward': today_reward[0] if today_reward else 0,
                'recent_records': recent_records,
                'next_reward': next_reward
            }
            
        except Exception as e:
            return {'error': f'获取签到信息失败：{str(e)}'}
        finally:
            conn.close()
    
    def get_checkin_ranking(self, limit: int = 10) -> list:
        """
        获取签到排行榜
        
        Args:
            limit: 返回条数限制
            
        Returns:
            排行榜列表
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT username, checkin_streak, total_checkin
                FROM users 
                WHERE total_checkin > 0
                ORDER BY checkin_streak DESC, total_checkin DESC
                LIMIT ?
            ''', (limit,))
            
            return cursor.fetchall()
            
        except Exception as e:
            return []
        finally:
            conn.close()