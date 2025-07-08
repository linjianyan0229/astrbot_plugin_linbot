"""
抢劫系统模块 - 抢劫功能
提供抢劫、被抢统计、抢劫记录等功能
"""

import sqlite3
import os
import random
from datetime import datetime, date, timedelta
from typing import Dict, Any, Optional, List, Tuple


class RobberyManager:
    """抢劫管理器"""
    
    def __init__(self, db_path: str, config: Dict[str, Any] = None):
        self.db_path = db_path
        self.config = config or {}
        
        # 从配置获取参数
        game_settings = self.config.get('game_system_settings', {})
        self.success_rate = game_settings.get('robbery_success_rate', 30.0) / 100  # 转换为小数
        self.min_amount = game_settings.get('robbery_min_amount', 50)
        self.max_amount = game_settings.get('robbery_max_amount', 300)
        self.cooldown_hours = game_settings.get('robbery_cooldown_hours', 6.0)
        self.level_requirement = game_settings.get('robbery_level_requirement', 5)
        self.protection_amount = game_settings.get('robbery_protection_amount', 100)
        self.failure_penalty = game_settings.get('robbery_failure_penalty', 20)
    
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
            
            # 更新用户名（如果有变化）
            cursor.execute('''
                UPDATE users SET username = ?, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ? AND username != ?
            ''', (username, user_id, username))
            
            conn.commit()
        finally:
            conn.close()
    
    def rob_user(self, robber_id: str, robber_name: str, victim_id: str, victim_name: str) -> Dict[str, Any]:
        """
        抢劫用户
        
        Args:
            robber_id: 抢劫者ID
            robber_name: 抢劫者名称
            victim_id: 被抢劫者ID
            victim_name: 被抢劫者名称
            
        Returns:
            抢劫结果
        """
        # 确保用户存在
        self._ensure_user_exists(robber_id, robber_name)
        self._ensure_user_exists(victim_id, victim_name)
        
        # 检查是否抢劫自己
        if robber_id == victim_id:
            return {
                "success": False,
                "message": "❌ 不能抢劫自己！"
            }
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            # 获取抢劫者信息
            cursor.execute('''
                SELECT level, money, rob_count_today FROM users WHERE user_id = ?
            ''', (robber_id,))
            robber_data = cursor.fetchone()
            
            if not robber_data:
                return {"success": False, "message": "抢劫者数据错误"}
            
            robber_level, robber_money, rob_count_today = robber_data
            
            # 检查等级要求
            if robber_level < self.level_requirement:
                return {
                    "success": False,
                    "message": f"❌ 等级不足！需要等级 {self.level_requirement}，当前等级 {robber_level}"
                }
            
            # 检查冷却时间
            cursor.execute('''
                SELECT created_at FROM robbery_records 
                WHERE robber_id = ? 
                ORDER BY created_at DESC 
                LIMIT 1
            ''', (robber_id,))
            
            last_robbery = cursor.fetchone()
            if last_robbery:
                last_time = datetime.strptime(last_robbery[0], '%Y-%m-%d %H:%M:%S')
                cooldown_end = last_time + timedelta(hours=self.cooldown_hours)
                
                if datetime.now() < cooldown_end:
                    remaining = cooldown_end - datetime.now()
                    remaining_hours = remaining.total_seconds() / 3600
                    return {
                        "success": False,
                        "message": f"❌ 抢劫冷却中，还需等待 {remaining_hours:.1f} 小时"
                    }
            
            # 获取被抢劫者信息
            cursor.execute('''
                SELECT money, level, username FROM users WHERE user_id = ?
            ''', (victim_id,))
            victim_data = cursor.fetchone()
            
            if not victim_data:
                return {"success": False, "message": "被抢劫者不存在"}
            
            victim_money, victim_level, victim_username = victim_data
            
            # 检查被抢劫者保护金额
            if victim_money < self.protection_amount:
                return {
                    "success": False,
                    "message": f"❌ {victim_username} 现金不足 {self.protection_amount} 金币，受到保护无法抢劫"
                }
            
            # 判断抢劫是否成功
            success = random.random() < self.success_rate
            
            if success:
                # 抢劫成功，计算抢劫金额
                max_rob_amount = min(self.max_amount, victim_money - self.protection_amount)
                if max_rob_amount < self.min_amount:
                    rob_amount = max_rob_amount
                else:
                    rob_amount = random.randint(self.min_amount, max_rob_amount)
                
                # 更新双方金额
                new_robber_money = robber_money + rob_amount
                new_victim_money = victim_money - rob_amount
                
                cursor.execute('''
                    UPDATE users 
                    SET money = ?, rob_count_today = rob_count_today + 1, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                ''', (new_robber_money, robber_id))
                
                cursor.execute('''
                    UPDATE users 
                    SET money = ?, robbed_count_today = robbed_count_today + 1, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                ''', (new_victim_money, victim_id))
                
                # 记录抢劫成功
                cursor.execute('''
                    INSERT INTO robbery_records 
                    (robber_id, victim_id, amount, success, result_message)
                    VALUES (?, ?, ?, ?, ?)
                ''', (robber_id, victim_id, rob_amount, True, f"成功抢劫{rob_amount}金币"))
                
                message = f"✅ 抢劫成功！\n\n💰 抢劫收获：{rob_amount} 金币\n🎯 目标：{victim_username}\n💸 您的金币：{robber_money} → {new_robber_money}"
                
            else:
                # 抢劫失败，扣除惩罚金额
                penalty_amount = min(self.failure_penalty, robber_money)  # 不能扣除超过现有金额的惩罚
                new_robber_money = robber_money - penalty_amount
                new_victim_money = victim_money + penalty_amount  # 被抢劫者获得惩罚金额
                
                # 更新抢劫者金额（扣除惩罚）
                cursor.execute('''
                    UPDATE users 
                    SET money = ?, rob_count_today = rob_count_today + 1, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                ''', (new_robber_money, robber_id))
                
                # 更新被抢劫者金额（获得惩罚金额）
                cursor.execute('''
                    UPDATE users 
                    SET money = ?, robbed_count_today = robbed_count_today + 1, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                ''', (new_victim_money, victim_id))
                
                # 记录抢劫失败
                cursor.execute('''
                    INSERT INTO robbery_records 
                    (robber_id, victim_id, amount, success, result_message)
                    VALUES (?, ?, ?, ?, ?)
                ''', (robber_id, victim_id, penalty_amount, False, f"抢劫失败，被扣除{penalty_amount}金币"))
                
                rob_amount = 0
                message = f"❌ 抢劫失败！\n\n🎯 目标：{victim_username}\n💸 惩罚扣除：{penalty_amount} 金币\n💰 您的金币：{robber_money} → {new_robber_money}\n🎁 {victim_username} 获得：{penalty_amount} 金币"
            
            conn.commit()
            
            return {
                "success": True,
                "robbery_success": success,
                "amount": rob_amount,
                "victim_name": victim_username,
                "message": message
            }
            
        except Exception as e:
            conn.rollback()
            return {"success": False, "message": f"抢劫失败：{str(e)}"}
        finally:
            conn.close()
    
    def get_robbery_stats(self, user_id: str) -> Dict[str, Any]:
        """
        获取抢劫统计信息
        
        Args:
            user_id: 用户ID
            
        Returns:
            抢劫统计信息
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            # 获取用户基本信息
            cursor.execute('''
                SELECT username, level, money, rob_count_today, robbed_count_today 
                FROM users WHERE user_id = ?
            ''', (user_id,))
            
            user_data = cursor.fetchone()
            if not user_data:
                return {"error": "用户不存在"}
            
            username, level, money, rob_count_today, robbed_count_today = user_data
            
            # 获取总抢劫统计
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_robberies,
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_robberies,
                    SUM(CASE WHEN success = 1 THEN amount ELSE 0 END) as total_robbed
                FROM robbery_records 
                WHERE robber_id = ?
            ''', (user_id,))
            
            rob_stats = cursor.fetchone()
            total_robberies, successful_robberies, total_robbed = rob_stats
            total_robbed = total_robbed or 0
            
            # 获取被抢统计
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_robbed_times,
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_robbed_times,
                    SUM(CASE WHEN success = 1 THEN amount ELSE 0 END) as total_lost
                FROM robbery_records 
                WHERE victim_id = ?
            ''', (user_id,))
            
            robbed_stats = cursor.fetchone()
            total_robbed_times, successful_robbed_times, total_lost = robbed_stats
            total_lost = total_lost or 0
            
            # 计算成功率
            rob_success_rate = (successful_robberies / total_robberies * 100) if total_robberies > 0 else 0
            
            # 获取最近抢劫记录
            cursor.execute('''
                SELECT r.victim_id, u.username, r.amount, r.success, r.created_at
                FROM robbery_records r
                LEFT JOIN users u ON r.victim_id = u.user_id
                WHERE r.robber_id = ?
                ORDER BY r.created_at DESC
                LIMIT 5
            ''', (user_id,))
            
            recent_robberies = cursor.fetchall()
            
            # 获取最近被抢记录
            cursor.execute('''
                SELECT r.robber_id, u.username, r.amount, r.success, r.created_at
                FROM robbery_records r
                LEFT JOIN users u ON r.robber_id = u.user_id
                WHERE r.victim_id = ?
                ORDER BY r.created_at DESC
                LIMIT 3
            ''', (user_id,))
            
            recent_robbed = cursor.fetchall()
            
            # 检查冷却时间
            cursor.execute('''
                SELECT created_at FROM robbery_records 
                WHERE robber_id = ? 
                ORDER BY created_at DESC 
                LIMIT 1
            ''', (user_id,))
            
            last_robbery = cursor.fetchone()
            can_rob = True
            cooldown_remaining = 0
            
            if last_robbery:
                last_time = datetime.strptime(last_robbery[0], '%Y-%m-%d %H:%M:%S')
                cooldown_end = last_time + timedelta(hours=self.cooldown_hours)
                
                if datetime.now() < cooldown_end:
                    can_rob = False
                    remaining = cooldown_end - datetime.now()
                    cooldown_remaining = remaining.total_seconds() / 3600
            
            return {
                "username": username,
                "level": level,
                "money": money,
                "level_requirement": self.level_requirement,
                "can_rob": can_rob and level >= self.level_requirement,
                "cooldown_remaining": cooldown_remaining,
                "today": {
                    "rob_count": rob_count_today,
                    "robbed_count": robbed_count_today
                },
                "overall": {
                    "total_robberies": total_robberies,
                    "successful_robberies": successful_robberies,
                    "rob_success_rate": rob_success_rate,
                    "total_robbed": total_robbed,
                    "total_robbed_times": total_robbed_times,
                    "successful_robbed_times": successful_robbed_times,
                    "total_lost": total_lost
                },
                "recent_robberies": recent_robberies,
                "recent_robbed": recent_robbed,
                "config": {
                    "success_rate": self.success_rate * 100,
                    "min_amount": self.min_amount,
                    "max_amount": self.max_amount,
                    "cooldown_hours": self.cooldown_hours,
                    "protection_amount": self.protection_amount,
                    "failure_penalty": self.failure_penalty
                }
            }
            
        except Exception as e:
            return {"error": f"获取抢劫统计失败：{str(e)}"}
        finally:
            conn.close()
    
    def get_robbery_targets(self, robber_id: str, limit: int = 10) -> Dict[str, Any]:
        """
        获取可抢劫的目标列表
        
        Args:
            robber_id: 抢劫者ID
            limit: 返回数量限制
            
        Returns:
            可抢劫目标列表
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            # 获取有足够现金的用户（排除自己）
            cursor.execute('''
                SELECT user_id, username, money, level, 
                       (money + bank_money) as total_assets
                FROM users 
                WHERE user_id != ? 
                AND money >= ?
                ORDER BY money DESC
                LIMIT ?
            ''', (robber_id, self.protection_amount, limit))
            
            targets = cursor.fetchall()
            
            target_list = []
            for user_id, username, money, level, total_assets in targets:
                # 计算可抢劫金额范围
                max_rob = min(self.max_amount, money - self.protection_amount)
                min_rob = min(self.min_amount, max_rob)
                
                target_list.append({
                    "user_id": user_id,
                    "username": username,
                    "money": money,
                    "level": level,
                    "total_assets": total_assets,
                    "rob_range": f"{min_rob}-{max_rob}" if min_rob < max_rob else str(max_rob)
                })
            
            return {
                "targets": target_list,
                "config": {
                    "success_rate": self.success_rate * 100,
                    "protection_amount": self.protection_amount
                }
            }
            
        except Exception as e:
            return {"error": f"获取抢劫目标失败：{str(e)}"}
        finally:
            conn.close()