"""
打工列表模块 - 工作系统
提供多种工作选择、工资计算、工作限制等功能
"""

import sqlite3
import os
import random
from datetime import datetime, date, timedelta
from typing import Dict, Any, Optional, List, Tuple


class WorkManager:
    """打工管理器"""
    
    def __init__(self, db_path: str, config: Dict[str, Any] = None):
        self.db_path = db_path
        self.config = config or {}
        
        # 从配置获取参数
        game_settings = self.config.get('game_system_settings', {})
        self.cooldown_multiplier = game_settings.get('work_cooldown_multiplier', 1.0)
        self.daily_work_limit = game_settings.get('daily_work_limit', 10)
        self.exp_multiplier = game_settings.get('work_experience_multiplier', 1.0)
        
        # 工作配置
        self.jobs = {
            "搬砖": {
                "base_salary": 80,
                "salary_range": (60, 120),
                "description": "基础体力劳动，收入稳定",
                "level_required": 1,
                "cooldown_hours": 1,
                "exp_reward": 5
            },
            "送外卖": {
                "base_salary": 120,
                "salary_range": (80, 180),
                "description": "跑腿送餐，按单计费",
                "level_required": 1,
                "cooldown_hours": 1,
                "exp_reward": 8
            },
            "便利店员": {
                "base_salary": 150,
                "salary_range": (100, 200),
                "description": "店内服务，轻松稳定",
                "level_required": 2,
                "cooldown_hours": 2,
                "exp_reward": 10
            },
            "快递员": {
                "base_salary": 200,
                "salary_range": (150, 280),
                "description": "配送包裹，按件提成",
                "level_required": 3,
                "cooldown_hours": 2,
                "exp_reward": 15
            },
            "客服代表": {
                "base_salary": 250,
                "salary_range": (180, 350),
                "description": "电话客服，沟通为主",
                "level_required": 5,
                "cooldown_hours": 3,
                "exp_reward": 20
            },
            "程序员": {
                "base_salary": 500,
                "salary_range": (300, 800),
                "description": "代码开发，技术要求高",
                "level_required": 10,
                "cooldown_hours": 4,
                "exp_reward": 50
            },
            "设计师": {
                "base_salary": 450,
                "salary_range": (280, 700),
                "description": "创意设计，需要灵感",
                "level_required": 8,
                "cooldown_hours": 4,
                "exp_reward": 40
            },
            "金融分析师": {
                "base_salary": 800,
                "salary_range": (500, 1200),
                "description": "市场分析，高薪工作",
                "level_required": 15,
                "cooldown_hours": 6,
                "exp_reward": 80
            },
            "企业顾问": {
                "base_salary": 1000,
                "salary_range": (600, 1500),
                "description": "战略咨询，顶级收入",
                "level_required": 20,
                "cooldown_hours": 8,
                "exp_reward": 100
            }
        }
        
        # 工作限制
        self.daily_work_limit = 10  # 每日最多工作次数
        
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
    
    def get_available_jobs(self, user_id: str, username: str) -> List[Dict[str, Any]]:
        """
        获取用户可用的工作列表
        
        Returns:
            可用工作列表
        """
        self._ensure_user_exists(user_id, username)
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            # 获取用户等级
            cursor.execute('SELECT level FROM users WHERE user_id = ?', (user_id,))
            user_data = cursor.fetchone()
            user_level = user_data[0] if user_data else 1
            
            # 获取今日工作次数
            today = date.today()
            cursor.execute('''
                SELECT COUNT(*) FROM work_records 
                WHERE user_id = ? AND date(work_time) = ?
            ''', (user_id, today))
            today_work_count = cursor.fetchone()[0]
            
            # 获取最后工作时间
            cursor.execute('''
                SELECT work_type, work_time FROM work_records 
                WHERE user_id = ? 
                ORDER BY work_time DESC 
                LIMIT 10
            ''', (user_id,))
            recent_works = cursor.fetchall()
            
            available_jobs = []
            
            for job_name, job_config in self.jobs.items():
                # 检查等级要求
                if user_level < job_config["level_required"]:
                    continue
                
                # 检查冷却时间
                can_work = True
                cooldown_end = None
                
                for work_type, work_time in recent_works:
                    if work_type == job_name:
                        last_work = datetime.strptime(work_time, '%Y-%m-%d %H:%M:%S')
                        # 应用冷却时间倍数
                        actual_cooldown_hours = job_config["cooldown_hours"] * self.cooldown_multiplier
                        cooldown_end = last_work + timedelta(hours=actual_cooldown_hours)
                        
                        if datetime.now() < cooldown_end:
                            can_work = False
                        break
                
                available_jobs.append({
                    "name": job_name,
                    "config": job_config,
                    "available": can_work,
                    "cooldown_end": cooldown_end.strftime('%H:%M') if cooldown_end else None,
                    "user_level": user_level
                })
            
            return {
                "jobs": available_jobs,
                "today_work_count": today_work_count,
                "daily_limit": self.daily_work_limit,
                "can_work_today": today_work_count < self.daily_work_limit
            }
            
        except Exception as e:
            return {"error": f"获取工作列表失败：{str(e)}"}
        finally:
            conn.close()
    
    def work(self, user_id: str, username: str, job_name: str) -> Dict[str, Any]:
        """
        执行工作
        
        Args:
            user_id: 用户ID
            username: 用户名
            job_name: 工作名称
            
        Returns:
            工作结果
        """
        self._ensure_user_exists(user_id, username)
        
        # 检查工作是否存在
        if job_name not in self.jobs:
            return {
                "success": False,
                "message": f"工作 '{job_name}' 不存在"
            }
        
        job_config = self.jobs[job_name]
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            # 获取用户信息
            cursor.execute('''
                SELECT money, level, exp, work_count_today, last_work_time
                FROM users WHERE user_id = ?
            ''', (user_id,))
            
            user_data = cursor.fetchone()
            if not user_data:
                return {"success": False, "message": "用户数据错误"}
            
            money, level, exp, work_count_today, last_work_time = user_data
            
            # 检查等级要求
            if level < job_config["level_required"]:
                return {
                    "success": False,
                    "message": f"等级不足！需要等级 {job_config['level_required']}，当前等级 {level}"
                }
            
            # 检查今日工作次数
            today = date.today()
            cursor.execute('''
                SELECT COUNT(*) FROM work_records 
                WHERE user_id = ? AND date(work_time) = ?
            ''', (user_id, today))
            today_count = cursor.fetchone()[0]
            
            if today_count >= self.daily_work_limit:
                return {
                    "success": False,
                    "message": f"今日工作次数已达上限（{self.daily_work_limit}次）"
                }
            
            # 检查工作冷却时间
            cursor.execute('''
                SELECT work_time FROM work_records 
                WHERE user_id = ? AND work_type = ?
                ORDER BY work_time DESC 
                LIMIT 1
            ''', (user_id, job_name))
            
            last_work = cursor.fetchone()
            if last_work:
                last_work_time = datetime.strptime(last_work[0], '%Y-%m-%d %H:%M:%S')
                # 应用冷却时间倍数
                actual_cooldown_hours = job_config["cooldown_hours"] * self.cooldown_multiplier
                cooldown_end = last_work_time + timedelta(hours=actual_cooldown_hours)
                
                if datetime.now() < cooldown_end:
                    remaining = cooldown_end - datetime.now()
                    remaining_minutes = int(remaining.total_seconds() / 60)
                    return {
                        "success": False,
                        "message": f"工作冷却中，还需等待 {remaining_minutes} 分钟"
                    }
            
            # 计算工资和奖励
            salary_result = self._calculate_salary(job_config, level)
            
            # 更新用户信息
            new_money = money + salary_result["total_earned"]
            new_exp = exp + salary_result["exp_reward"]
            new_level = self._calculate_level(new_exp)
            
            cursor.execute('''
                UPDATE users 
                SET money = ?, exp = ?, level = ?, last_work_time = CURRENT_TIMESTAMP,
                    total_earned = total_earned + ?, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
            ''', (new_money, new_exp, new_level, salary_result["total_earned"], user_id))
            
            # 记录工作
            cursor.execute('''
                INSERT INTO work_records 
                (user_id, work_type, base_salary, bonus, total_earned)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, job_name, salary_result["base_salary"], 
                  salary_result["level_bonus"] + salary_result["luck_bonus"], 
                  salary_result["total_earned"]))
            
            conn.commit()
            
            # 检查是否升级
            level_up = new_level > level
            
            return {
                "success": True,
                "job_name": job_name,
                "salary_result": salary_result,
                "new_money": new_money,
                "new_exp": new_exp,
                "new_level": new_level,
                "level_up": level_up,
                "today_work_count": today_count + 1
            }
            
        except Exception as e:
            conn.rollback()
            return {
                "success": False,
                "message": f"工作失败：{str(e)}"
            }
        finally:
            conn.close()
    
    def _calculate_salary(self, job_config: Dict[str, Any], user_level: int) -> Dict[str, Any]:
        """
        计算工资
        
        Args:
            job_config: 工作配置
            user_level: 用户等级
            
        Returns:
            工资计算结果
        """
        base_salary = job_config["base_salary"]
        salary_range = job_config["salary_range"]
        
        # 随机工资（在范围内）
        random_salary = random.randint(salary_range[0], salary_range[1])
        
        # 等级加成（每级+2%）
        level_bonus = int(base_salary * (user_level - 1) * 0.02)
        
        # 幸运加成（10%概率获得50%额外奖励）
        luck_bonus = 0
        luck_triggered = False
        if random.random() < 0.1:
            luck_bonus = int(random_salary * 0.5)
            luck_triggered = True
        
        total_earned = random_salary + level_bonus + luck_bonus
        exp_reward = int(job_config["exp_reward"] * self.exp_multiplier)
        
        return {
            "base_salary": random_salary,
            "level_bonus": level_bonus,
            "luck_bonus": luck_bonus,
            "luck_triggered": luck_triggered,
            "total_earned": total_earned,
            "exp_reward": exp_reward
        }
    
    def _calculate_level(self, exp: int) -> int:
        """
        根据经验计算等级
        
        Args:
            exp: 经验值
            
        Returns:
            等级
        """
        # 分阶段等级计算
        if exp < 500:  # 1-5级：每级100经验
            return max(1, exp // 100 + 1)
        elif exp < 1500:  # 6-10级：每级200经验
            return 5 + (exp - 500) // 200 + 1
        elif exp < 4000:  # 11-15级：每级500经验  
            return 10 + (exp - 1500) // 500 + 1
        else:  # 16级以上：每级1000经验
            return 15 + (exp - 4000) // 1000 + 1
    
    def _get_level_info(self, exp: int) -> Dict[str, int]:
        """
        获取等级信息
        
        Args:
            exp: 当前经验值
            
        Returns:
            等级信息字典
        """
        current_level = self._calculate_level(exp)
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
    
    def get_work_statistics(self, user_id: str) -> Dict[str, Any]:
        """
        获取用户工作统计
        
        Returns:
            工作统计信息
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            # 总体统计
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_works,
                    SUM(total_earned) as total_income,
                    AVG(total_earned) as avg_income
                FROM work_records WHERE user_id = ?
            ''', (user_id,))
            
            overall_stats = cursor.fetchone()
            
            # 今日统计
            today = date.today()
            cursor.execute('''
                SELECT 
                    COUNT(*) as today_works,
                    SUM(total_earned) as today_income
                FROM work_records 
                WHERE user_id = ? AND date(work_time) = ?
            ''', (user_id, today))
            
            today_stats = cursor.fetchone()
            
            # 工作类型统计
            cursor.execute('''
                SELECT 
                    work_type,
                    COUNT(*) as count,
                    SUM(total_earned) as total_income,
                    AVG(total_earned) as avg_income,
                    MAX(total_earned) as max_income
                FROM work_records 
                WHERE user_id = ? 
                GROUP BY work_type
                ORDER BY total_income DESC
            ''', (user_id,))
            
            job_stats = cursor.fetchall()
            
            # 最近工作记录
            cursor.execute('''
                SELECT work_type, total_earned, work_time
                FROM work_records 
                WHERE user_id = ? 
                ORDER BY work_time DESC 
                LIMIT 5
            ''', (user_id,))
            
            recent_works = cursor.fetchall()
            
            return {
                "overall": {
                    "total_works": overall_stats[0] or 0,
                    "total_income": overall_stats[1] or 0,
                    "avg_income": round(overall_stats[2] or 0, 1)
                },
                "today": {
                    "works": today_stats[0] or 0,
                    "income": today_stats[1] or 0,
                    "remaining": self.daily_work_limit - (today_stats[0] or 0)
                },
                "job_stats": job_stats,
                "recent_works": recent_works
            }
            
        except Exception as e:
            return {"error": f"获取统计信息失败：{str(e)}"}
        finally:
            conn.close()