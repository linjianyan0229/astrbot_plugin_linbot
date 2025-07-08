#!/usr/bin/env python3
"""
游戏数据库初始化脚本
创建用户数据表结构
"""

import sqlite3
import os

def init_database():
    """初始化游戏数据库"""
    db_path = os.path.join(os.path.dirname(__file__), 'user.db')
    
    # 连接数据库
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 创建用户主表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            username TEXT NOT NULL,
            money INTEGER DEFAULT 0,
            bank_money INTEGER DEFAULT 0,
            total_earned INTEGER DEFAULT 0,
            level INTEGER DEFAULT 1,
            exp INTEGER DEFAULT 0,
            last_checkin DATE,
            checkin_streak INTEGER DEFAULT 0,
            total_checkin INTEGER DEFAULT 0,
            last_work_time DATETIME,
            work_count_today INTEGER DEFAULT 0,
            rob_count_today INTEGER DEFAULT 0,
            robbed_count_today INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # 创建银行交易记录表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS bank_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            transaction_type TEXT NOT NULL,
            amount INTEGER NOT NULL,
            balance_before INTEGER NOT NULL,
            balance_after INTEGER NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
        ''')
        
        # 创建打工记录表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS work_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            work_type TEXT NOT NULL,
            base_salary INTEGER NOT NULL,
            bonus INTEGER DEFAULT 0,
            total_earned INTEGER NOT NULL,
            work_time DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
        ''')
        
        # 创建签到记录表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS checkin_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            checkin_date DATE NOT NULL,
            reward_money INTEGER NOT NULL,
            consecutive_days INTEGER NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            UNIQUE(user_id, checkin_date)
        )
        ''')
        
        # 创建抢劫记录表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS robbery_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            robber_id TEXT NOT NULL,
            victim_id TEXT NOT NULL,
            amount INTEGER NOT NULL,
            success BOOLEAN NOT NULL,
            result_message TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (robber_id) REFERENCES users(user_id),
            FOREIGN KEY (victim_id) REFERENCES users(user_id)
        )
        ''')
        
        # 创建用户物品表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            item_name TEXT NOT NULL,
            item_type TEXT NOT NULL,
            quantity INTEGER DEFAULT 1,
            value INTEGER DEFAULT 0,
            obtained_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
        ''')
        
        # 创建索引以优化查询性能
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_money ON users(money DESC)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_bank_transactions_user ON bank_transactions(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_work_records_user ON work_records(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_checkin_records_user ON checkin_records(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_robbery_records_robber ON robbery_records(robber_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_robbery_records_victim ON robbery_records(victim_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_items_user ON user_items(user_id)')
        
        # 提交更改
        conn.commit()
        print("数据库初始化完成！")
        print("已创建以下表:")
        print("- users: 用户主表")
        print("- bank_transactions: 银行交易记录")
        print("- work_records: 打工记录")
        print("- checkin_records: 签到记录")
        print("- robbery_records: 抢劫记录")
        print("- user_items: 用户物品")
        
    except Exception as e:
        print(f"数据库初始化失败: {e}")
        conn.rollback()
    finally:
        conn.close()

def check_tables():
    """检查数据库表结构"""
    db_path = os.path.join(os.path.dirname(__file__), 'user.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    
    print("\n当前数据库中的表:")
    for table in tables:
        print(f"- {table[0]}")
        
        # 显示表结构
        cursor.execute(f"PRAGMA table_info({table[0]})")
        columns = cursor.fetchall()
        for col in columns:
            print(f"  └─ {col[1]} ({col[2]})")
    
    conn.close()

if __name__ == "__main__":
    init_database()
    check_tables()