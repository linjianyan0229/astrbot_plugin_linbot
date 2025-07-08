"""
排行榜模块 - 金钱排行榜系统
提供多种排行榜查询、图片生成、数据统计等功能
"""

import sqlite3
import os
import requests
import hashlib
from datetime import datetime, date
from typing import Dict, Any, Optional, List, Tuple
from PIL import Image, ImageDraw, ImageFont
import io


class RankingManager:
    """排行榜管理器"""
    
    def __init__(self, db_path: str, plugin_dir: str):
        self.db_path = db_path
        self.plugin_dir = plugin_dir
        
        # 数据目录
        self.data_dir = os.path.join("data", "plugins_data", "linbot", "rankings")
        os.makedirs(self.data_dir, exist_ok=True)
        
        # 排行榜配置
        self.ranking_types = {
            "money": {"name": "💰 金钱排行榜", "field": "money", "desc": "现金排名"},
            "assets": {"name": "💎 总资产排行榜", "field": "(money + bank_money)", "desc": "总资产排名"},
            "earned": {"name": "💼 累计收入排行榜", "field": "total_earned", "desc": "累计收入排名"},
            "level": {"name": "⭐ 等级排行榜", "field": "exp", "desc": "等级排名"},
            "checkin": {"name": "📅 签到排行榜", "field": "total_checkin", "desc": "签到次数排名"}
        }
        
        # 主题色配置
        self.colors = {
            'background': '#FFFFFF',           # 白色背景
            'header': '#FF6B6B',              # 红色头部
            'card_bg': '#FFF8F8',             # 浅红色卡片背景
            'gold': '#FFD700',                # 金色（第一名）
            'silver': '#C0C0C0',              # 银色（第二名）
            'bronze': '#CD7F32',              # 铜色（第三名）
            'text': '#2C3E50',                # 深色文本
            'subtitle': '#7F8C8D',            # 副标题颜色
            'border': '#E74C3C'               # 边框颜色
        }
        
        # 布局配置
        self.layout = {
            'image_width': 800,
            'margin': 30,
            'header_height': 80,
            'item_height': 80,
            'avatar_size': 50,
            'rank_circle_size': 40
        }
        
        # 字体配置
        self.fonts = self._load_fonts()
    
    def _get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        return sqlite3.connect(self.db_path)
    
    def _load_fonts(self) -> Dict[str, Any]:
        """加载字体"""
        font_path = os.path.join(self.plugin_dir, "assets", "LXGWWenKai-Regular.ttf")
        
        try:
            return {
                'title': ImageFont.truetype(font_path, 32),
                'subtitle': ImageFont.truetype(font_path, 18),
                'rank': ImageFont.truetype(font_path, 24),
                'name': ImageFont.truetype(font_path, 20),
                'value': ImageFont.truetype(font_path, 16),
                'small': ImageFont.truetype(font_path, 14)
            }
        except OSError:
            # 使用默认字体
            default_font = ImageFont.load_default()
            return {
                'title': default_font,
                'subtitle': default_font,
                'rank': default_font,
                'name': default_font,
                'value': default_font,
                'small': default_font
            }
    
    def get_ranking_data(self, ranking_type: str = "money", limit: int = 10) -> Dict[str, Any]:
        """
        获取排行榜数据
        
        Args:
            ranking_type: 排行榜类型
            limit: 返回条数
            
        Returns:
            排行榜数据
        """
        if ranking_type not in self.ranking_types:
            return {"error": f"不支持的排行榜类型: {ranking_type}"}
        
        config = self.ranking_types[ranking_type]
        field = config["field"]
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            # 根据排行榜类型构建查询
            if ranking_type == "level":
                # 等级排行榜需要特殊处理
                query = f'''
                    SELECT user_id, username, {field}, money, bank_money, level, total_checkin
                    FROM users 
                    WHERE {field} > 0
                    ORDER BY level DESC, {field} DESC
                    LIMIT ?
                '''
            else:
                query = f'''
                    SELECT user_id, username, {field}, money, bank_money, level, total_checkin
                    FROM users 
                    WHERE {field} > 0
                    ORDER BY {field} DESC
                    LIMIT ?
                '''
            
            cursor.execute(query, (limit,))
            results = cursor.fetchall()
            
            # 获取总用户数
            cursor.execute('SELECT COUNT(*) FROM users WHERE money > 0 OR total_checkin > 0')
            total_users = cursor.fetchone()[0]
            
            ranking_data = []
            for i, row in enumerate(results, 1):
                user_id, username, value, money, bank_money, level, total_checkin = row
                
                # 根据排行榜类型格式化显示值
                if ranking_type == "money":
                    display_value = f"{value:,} 金币"
                elif ranking_type == "assets":
                    display_value = f"{value:,} 金币"
                elif ranking_type == "earned":
                    display_value = f"{value:,} 金币"
                elif ranking_type == "level":
                    display_value = f"{level} 级 ({value} EXP)"
                elif ranking_type == "checkin":
                    display_value = f"{value} 次"
                else:
                    display_value = str(value)
                
                ranking_data.append({
                    'rank': i,
                    'user_id': user_id,
                    'username': username,
                    'value': value,
                    'display_value': display_value,
                    'money': money,
                    'bank_money': bank_money,
                    'level': level,
                    'total_checkin': total_checkin
                })
            
            return {
                'ranking_type': ranking_type,
                'config': config,
                'data': ranking_data,
                'total_users': total_users,
                'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
        except Exception as e:
            return {"error": f"获取排行榜数据失败：{str(e)}"}
        finally:
            conn.close()
    
    def _get_avatar_placeholder(self, username: str, size: int = 50) -> Image.Image:
        """
        生成头像占位符
        
        Args:
            username: 用户名
            size: 头像尺寸
            
        Returns:
            头像图片
        """
        # 创建圆形头像背景
        avatar = Image.new('RGB', (size, size), self._get_user_color(username))
        draw = ImageDraw.Draw(avatar)
        
        # 绘制用户名首字符
        char = username[0].upper() if username else '?'
        try:
            font = ImageFont.truetype(os.path.join(self.plugin_dir, "assets", "LXGWWenKai-Regular.ttf"), size//2)
        except:
            font = ImageFont.load_default()
        
        # 计算文字位置
        bbox = draw.textbbox((0, 0), char, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (size - text_width) // 2
        y = (size - text_height) // 2
        
        draw.text((x, y), char, fill='white', font=font)
        
        # 转换为圆形
        mask = Image.new('L', (size, size), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse([0, 0, size, size], fill=255)
        
        # 应用圆形蒙版
        avatar.putalpha(mask)
        return avatar
    
    def _get_user_color(self, username: str) -> str:
        """
        根据用户名生成唯一颜色
        
        Args:
            username: 用户名
            
        Returns:
            颜色hex值
        """
        # 使用用户名的哈希值生成颜色
        hash_object = hashlib.md5(username.encode())
        hash_hex = hash_object.hexdigest()
        
        # 提取RGB值
        r = int(hash_hex[0:2], 16)
        g = int(hash_hex[2:4], 16)
        b = int(hash_hex[4:6], 16)
        
        # 确保颜色不会太浅
        r = max(r, 100)
        g = max(g, 100)
        b = max(b, 100)
        
        return f'#{r:02x}{g:02x}{b:02x}'
    
    def generate_ranking_image(self, ranking_data: Dict[str, Any]) -> Optional[str]:
        """
        生成排行榜图片
        
        Args:
            ranking_data: 排行榜数据
            
        Returns:
            图片文件路径
        """
        if 'error' in ranking_data:
            return None
        
        try:
            data = ranking_data['data']
            config = ranking_data['config']
            
            # 计算图片高度
            image_height = (self.layout['header_height'] + 
                           len(data) * self.layout['item_height'] + 
                           self.layout['margin'] * 3 + 60)  # 额外空间
            
            # 创建图片
            image = Image.new('RGB', (self.layout['image_width'], image_height), self.colors['background'])
            draw = ImageDraw.Draw(image)
            
            # 绘制头部
            self._draw_ranking_header(draw, config['name'], ranking_data['update_time'])
            
            # 绘制排行榜条目
            y_offset = self.layout['header_height'] + self.layout['margin']
            
            for item in data:
                self._draw_ranking_item(draw, image, item, y_offset)
                y_offset += self.layout['item_height']
            
            # 绘制底部信息
            self._draw_ranking_footer(draw, ranking_data['total_users'], 
                                    len(data), y_offset)
            
            # 保存图片
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"ranking_{ranking_data['ranking_type']}_{timestamp}.png"
            image_path = os.path.join(self.data_dir, filename)
            image.save(image_path, "PNG", quality=95)
            
            return image_path
            
        except Exception as e:
            print(f"生成排行榜图片失败: {e}")
            return None
    
    def _draw_ranking_header(self, draw: ImageDraw.Draw, title: str, update_time: str):
        """绘制排行榜头部"""
        # 绘制头部背景
        draw.rectangle([0, 0, self.layout['image_width'], self.layout['header_height']], 
                      fill=self.colors['header'])
        
        # 绘制标题
        bbox = draw.textbbox((0, 0), title, font=self.fonts['title'])
        title_width = bbox[2] - bbox[0]
        title_x = (self.layout['image_width'] - title_width) // 2
        title_y = 15
        
        draw.text((title_x, title_y), title, fill='white', font=self.fonts['title'])
        
        # 绘制更新时间
        time_text = f"更新时间: {update_time}"
        bbox = draw.textbbox((0, 0), time_text, font=self.fonts['small'])
        time_width = bbox[2] - bbox[0]
        time_x = (self.layout['image_width'] - time_width) // 2
        time_y = 50
        
        draw.text((time_x, time_y), time_text, fill='white', font=self.fonts['small'])
    
    def _draw_ranking_item(self, draw: ImageDraw.Draw, image: Image.Image, 
                          item: Dict[str, Any], y_offset: int):
        """绘制排行榜条目"""
        rank = item['rank']
        username = item['username']
        display_value = item['display_value']
        
        # 确定排名颜色
        if rank == 1:
            rank_color = self.colors['gold']
            medal = "🥇"
        elif rank == 2:
            rank_color = self.colors['silver']
            medal = "🥈"
        elif rank == 3:
            rank_color = self.colors['bronze']
            medal = "🥉"
        else:
            rank_color = self.colors['subtitle']
            medal = ""
        
        # 绘制条目背景（奇偶行不同颜色）
        if rank % 2 == 0:
            bg_color = self.colors['card_bg']
        else:
            bg_color = self.colors['background']
        
        item_rect = [self.layout['margin'], y_offset, 
                    self.layout['image_width'] - self.layout['margin'], 
                    y_offset + self.layout['item_height']]
        draw.rectangle(item_rect, fill=bg_color, outline=self.colors['border'], width=1)
        
        # 绘制排名圆圈
        rank_x = self.layout['margin'] + 20
        rank_y = y_offset + (self.layout['item_height'] - self.layout['rank_circle_size']) // 2
        
        rank_circle = [rank_x, rank_y, 
                      rank_x + self.layout['rank_circle_size'], 
                      rank_y + self.layout['rank_circle_size']]
        draw.ellipse(rank_circle, fill=rank_color, outline='white', width=2)
        
        # 绘制排名数字
        rank_text = str(rank)
        bbox = draw.textbbox((0, 0), rank_text, font=self.fonts['rank'])
        rank_text_width = bbox[2] - bbox[0]
        rank_text_height = bbox[3] - bbox[1]
        rank_text_x = rank_x + (self.layout['rank_circle_size'] - rank_text_width) // 2
        rank_text_y = rank_y + (self.layout['rank_circle_size'] - rank_text_height) // 2
        
        draw.text((rank_text_x, rank_text_y), rank_text, fill='white', font=self.fonts['rank'])
        
        # 绘制头像
        avatar_x = rank_x + self.layout['rank_circle_size'] + 20
        avatar_y = y_offset + (self.layout['item_height'] - self.layout['avatar_size']) // 2
        
        avatar = self._get_avatar_placeholder(username, self.layout['avatar_size'])
        
        # 创建白色背景用于粘贴RGBA头像
        if avatar.mode == 'RGBA':
            avatar_bg = Image.new('RGB', avatar.size, bg_color)
            avatar_bg.paste(avatar, mask=avatar.split()[-1])
            avatar = avatar_bg
        
        image.paste(avatar, (avatar_x, avatar_y))
        
        # 绘制用户名
        name_x = avatar_x + self.layout['avatar_size'] + 15
        name_y = y_offset + 15
        
        # 添加奖牌emoji
        display_name = f"{medal} {username}" if medal else username
        draw.text((name_x, name_y), display_name, fill=self.colors['text'], font=self.fonts['name'])
        
        # 绘制数值
        value_y = y_offset + 45
        draw.text((name_x, value_y), display_value, fill=self.colors['subtitle'], font=self.fonts['value'])
        
        # 绘制额外信息
        extra_info = f"等级 {item['level']} | 总资产 {item['money'] + item['bank_money']:,}"
        extra_x = self.layout['image_width'] - 200
        extra_y = y_offset + 30
        draw.text((extra_x, extra_y), extra_info, fill=self.colors['subtitle'], font=self.fonts['small'])
    
    def _draw_ranking_footer(self, draw: ImageDraw.Draw, total_users: int, 
                           shown_count: int, y_offset: int):
        """绘制排行榜底部"""
        footer_text = f"显示前 {shown_count} 名 | 总用户数: {total_users}"
        bbox = draw.textbbox((0, 0), footer_text, font=self.fonts['subtitle'])
        footer_width = bbox[2] - bbox[0]
        footer_x = (self.layout['image_width'] - footer_width) // 2
        footer_y = y_offset + 20
        
        draw.text((footer_x, footer_y), footer_text, fill=self.colors['subtitle'], 
                 font=self.fonts['subtitle'])
    
    def get_user_ranking_info(self, user_id: str, ranking_type: str = "money") -> Dict[str, Any]:
        """
        获取用户在指定排行榜中的排名信息
        
        Args:
            user_id: 用户ID
            ranking_type: 排行榜类型
            
        Returns:
            用户排名信息
        """
        if ranking_type not in self.ranking_types:
            return {"error": f"不支持的排行榜类型: {ranking_type}"}
        
        config = self.ranking_types[ranking_type]
        field = config["field"]
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            # 获取用户信息
            cursor.execute(f'''
                SELECT username, {field}, money, bank_money, level, total_checkin
                FROM users WHERE user_id = ?
            ''', (user_id,))
            
            user_data = cursor.fetchone()
            if not user_data:
                return {"error": "用户不存在"}
            
            username, value, money, bank_money, level, total_checkin = user_data
            
            # 计算排名
            if ranking_type == "level":
                cursor.execute(f'''
                    SELECT COUNT(*) + 1 FROM users 
                    WHERE (level > (SELECT level FROM users WHERE user_id = ?))
                    OR (level = (SELECT level FROM users WHERE user_id = ?) 
                        AND {field} > (SELECT {field} FROM users WHERE user_id = ?))
                ''', (user_id, user_id, user_id))
            else:
                cursor.execute(f'''
                    SELECT COUNT(*) + 1 FROM users 
                    WHERE {field} > (SELECT {field} FROM users WHERE user_id = ?)
                ''', (user_id,))
            
            rank = cursor.fetchone()[0]
            
            # 获取总用户数
            cursor.execute('SELECT COUNT(*) FROM users WHERE money > 0 OR total_checkin > 0')
            total_users = cursor.fetchone()[0]
            
            return {
                'rank': rank,
                'username': username,
                'value': value,
                'total_users': total_users,
                'ranking_type': ranking_type,
                'config': config
            }
            
        except Exception as e:
            return {"error": f"获取用户排名失败：{str(e)}"}
        finally:
            conn.close()