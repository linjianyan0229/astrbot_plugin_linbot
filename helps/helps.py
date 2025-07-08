import os
import re
from typing import List, Dict, Any, Optional
from PIL import Image, ImageDraw, ImageFont, ImageOps
from astrbot.api import logger


class PluginHelpGenerator:
    """插件帮助信息生成器"""
    
    def __init__(self, context, plugin_dir: str, prefix: str = "/", max_commands_per_row: int = 4, show_plugin_logos: bool = True):
        self.context = context
        self.plugin_dir = plugin_dir
        self.prefix = prefix
        self.max_commands_per_row = max_commands_per_row
        self.show_plugin_logos = show_plugin_logos
        
        # 数据目录
        self.data_dir = os.path.join("data", "plugins_data", "linbot")
        os.makedirs(self.data_dir, exist_ok=True)
        
        # 主题色配置 - 白色和淡蓝色
        self.colors = {
            'background': '#FFFFFF',           # 白色背景
            'header': '#E3F2FD',             # 淡蓝色头部
            'card_bg': '#F8FAFE',            # 非常淡的蓝色卡片背景
            'card_border': '#2196F3',        # 蓝色边框
            'title': '#1565C0',              # 深蓝色标题
            'text': '#424242',               # 深灰色文本
            'command_bg': '#E3F2FD',         # 淡蓝色指令背景
            'command_border': '#2196F3',     # 蓝色指令边框
            'command_text': '#1976D2'        # 指令文本颜色
        }
        
        # 布局配置（使用配置参数）
        self.layout = {
            'image_width': 1000,
            'margin': 30,
            'header_height': 80,
            'card_margin': 20,
            'card_padding': 20,
            'avatar_size': 40,
            'command_item_width': 200,
            'command_item_height': 35,
            'command_margin': 10,
            'commands_per_row': self.max_commands_per_row
        }
        
        # 字体配置
        self.fonts = self._load_fonts()

    def _load_fonts(self) -> Dict[str, Any]:
        """加载字体"""
        font_path = os.path.join(self.plugin_dir, "assets", "LXGWWenKai-Regular.ttf")
        
        try:
            return {
                'title': ImageFont.truetype(font_path, 28),
                'subtitle': ImageFont.truetype(font_path, 20),
                'text': ImageFont.truetype(font_path, 16),
                'command': ImageFont.truetype(font_path, 14),
                'header': ImageFont.truetype(font_path, 32)
            }
        except OSError:
            logger.warning(f"字体文件加载失败: {font_path}")
            # 使用默认字体
            default_font = ImageFont.load_default()
            return {
                'title': default_font,
                'subtitle': default_font,
                'text': default_font,
                'command': default_font,
                'header': default_font
            }

    def get_external_plugins(self) -> List[Dict[str, Any]]:
        """获取外部插件信息"""
        try:
            all_stars = self.context.get_all_stars()
            external_plugins = []
            
            # 内置插件列表
            builtin_plugins = {
                'astrbot', 'session_controller', 'thinking_filter', 
                'reminder', 'python_interpreter', 'long_term_memory', 
                'web_searcher'
            }
            
            for star_metadata in all_stars:
                try:
                    # star_metadata 是 StarMetadata 对象，需要获取真正的插件实例
                    # 根据开发文档，StarMetadata 包含了插件类实例、配置等等
                    
                    # 获取插件实例（star_cls 实际上是实例，不是类）
                    if hasattr(star_metadata, 'star_cls') and star_metadata.star_cls is not None:
                        star_instance = star_metadata.star_cls
                        star_class = star_instance.__class__
                    else:
                        continue
                    
                    # 获取插件信息
                    plugin_name = getattr(star_metadata, 'name', star_class.__name__.replace('Plugin', '').replace('Star', ''))
                    description = getattr(star_metadata, 'desc', '')
                    version = getattr(star_metadata, 'version', '1.0.0')
                    author = getattr(star_metadata, 'author', '未知作者')
                    
                    plugin_module = star_class.__module__
                    star_class_name = star_class.__name__
                    
                    # 过滤内置插件
                    if plugin_name.lower() in builtin_plugins:
                        continue
                    
                    # 检查是否是内置插件路径
                    # 外部插件通常以 astrbot_plugin_ 开头，在 data/plugins/ 目录下
                    # 内置插件在 astrbot.core, packages. 等路径下
                    if any(keyword in plugin_module for keyword in ['astrbot.core', 'packages.', 'builtin']):
                        continue
                        
                    # 只保留外部插件（通常在 data/plugins/ 目录下或模块名包含 astrbot_plugin_）
                    if not ('astrbot_plugin_' in plugin_module or 'data.plugins.' in plugin_module):
                        continue
                    
                    # LinBot也作为外部插件显示，不进行过滤
                    
                    # 处理描述信息
                    if not description:
                        description = getattr(star_class, '__doc__', '').strip() or '暂无描述'
                    
                    # 清理描述
                    if description:
                        description = description.split('\n')[0].strip()
                        if len(description) > 50:
                            description = description[:47] + "..."
                    
                    plugin_info = {
                        'name': plugin_name,
                        'description': description,
                        'version': version,
                        'author': author,
                        'commands': self._extract_commands(star_instance, plugin_name)
                    }
                    
                    external_plugins.append(plugin_info)
                    
                except Exception as e:
                    continue
            
            # 按插件名称排序
            external_plugins.sort(key=lambda x: x['name'])
            
            return external_plugins
            
        except Exception as e:
            logger.error(f"获取外部插件信息失败: {e}")
            return []

    def _extract_commands(self, star, plugin_name: str) -> List[str]:
        """提取插件指令（从实例）"""
        commands = []
        
        try:
            # 获取插件类对应的 handler 元数据
            star_class = star.__class__
            from astrbot.core.star.star_handler import star_handlers_registry
            
            # 查找与插件类相关的所有 handler
            for handler_md in star_handlers_registry._handlers:
                # 检查handler是否属于当前插件
                module_match = (handler_md.handler_module_path and 
                               plugin_name.lower() in handler_md.handler_module_path.lower())
                
                if (hasattr(handler_md.handler, '__self__') and 
                    handler_md.handler.__self__.__class__ == star_class) or \
                   (hasattr(handler_md.handler, 'im_class') and 
                    handler_md.handler.im_class == star_class) or \
                   module_match:
                    
                    # 检查该handler的event_filters
                    for event_filter in handler_md.event_filters:
                        # 检查CommandFilter
                        if hasattr(event_filter, 'command_name') and event_filter.command_name:
                            cmd = f"{self.prefix}{event_filter.command_name}"
                            commands.append(cmd)
                        # 检查RegexFilter (转换为字符串)
                        elif hasattr(event_filter, 'regex') and event_filter.regex:
                            regex_str = str(event_filter.regex)
                            # 移除正则表达式的编译标记，只保留模式字符串
                            if regex_str.startswith("re.compile('") and regex_str.endswith("')"):
                                regex_str = regex_str[12:-2]  # 移除 "re.compile('" 和 "')"
                            elif regex_str.startswith('re.compile("') and regex_str.endswith('")'):
                                regex_str = regex_str[12:-2]  # 移除 're.compile("' 和 '")'
                            commands.append(regex_str)
            
            # 如果上面的方法没找到，尝试检查方法装饰器标记
            if not commands:
                for method_name in dir(star):
                    if method_name.startswith('_'):
                        continue
                        
                    method = getattr(star, method_name)
                    if callable(method):
                        # 检查多种装饰器模式
                        
                        # 模式1: @filter.command() 装饰器
                        if hasattr(method, '_filter_type'):
                            filter_type = method._filter_type
                            if filter_type == 'command':
                                cmd = getattr(method, '_command', method_name)
                                commands.append(f"{self.prefix}{cmd}")
                            elif filter_type == 'regex':
                                pattern = getattr(method, '_pattern', '')
                                if pattern:
                                    commands.append(pattern)
                        
                        # 模式2: 检查其他可能的装饰器属性
                        elif hasattr(method, '_command_name'):
                            cmd = method._command_name
                            commands.append(f"{self.prefix}{cmd}")
                        elif hasattr(method, 'command'):
                            cmd = method.command
                            commands.append(f"{self.prefix}{cmd}")
            
            # 如果还是没有找到指令，尝试推断
            if not commands:
                commands = self._infer_commands(plugin_name)
                
        except Exception as e:
            commands = self._infer_commands(plugin_name)
        
        # 确保返回的所有指令都是字符串类型
        return [str(cmd) if not isinstance(cmd, str) else cmd for cmd in commands]

    def _extract_commands_from_class(self, star_class, plugin_name: str) -> List[str]:
        """提取插件指令（从类）"""
        commands = []
        
        try:
            # 检查类的方法
            for method_name in dir(star_class):
                if method_name.startswith('_'):
                    continue
                    
                method = getattr(star_class, method_name)
                if callable(method):
                    # 检查装饰器属性
                    if hasattr(method, '__wrapped__'):
                        # 检查装饰器
                        if hasattr(method, '_filter_type'):
                            filter_type = method._filter_type
                            if filter_type == 'command':
                                cmd = getattr(method, '_command', method_name)
                                commands.append(f"{self.prefix}{cmd}")
                            elif filter_type == 'regex':
                                pattern = getattr(method, '_pattern', '')
                                if pattern:
                                    commands.append(pattern)
                    
                    # 也检查未包装的方法
                    elif hasattr(method, '_filter_type'):
                        filter_type = method._filter_type
                        if filter_type == 'command':
                            cmd = getattr(method, '_command', method_name)
                            commands.append(f"{self.prefix}{cmd}")
                        elif filter_type == 'regex':
                            pattern = getattr(method, '_pattern', '')
                            if pattern:
                                commands.append(pattern)
            
            # 如果没有找到指令，尝试推断
            if not commands:
                commands = self._infer_commands(plugin_name)
                
        except Exception as e:
            commands = self._infer_commands(plugin_name)
        
        # 确保返回的所有指令都是字符串类型
        return [str(cmd) if not isinstance(cmd, str) else cmd for cmd in commands]

    def _infer_commands(self, plugin_name: str) -> List[str]:
        """根据插件名称推断指令"""
        name_lower = plugin_name.lower()
        
        # LinBot特殊处理，返回帮助和配置指令
        if 'linbot' in name_lower or name_lower == 'linbot':
            return [f"{self.prefix}帮助", f"{self.prefix}linbot_config"]
        
        command_map = {
            'weather': ['天气', 'weather'],
            'music': ['音乐', 'music'],
            'search': ['搜索', 'search'],
            'translate': ['翻译', 'translate'],
            'chat': ['聊天', 'chat'],
            'image': ['图片', 'image'],
            'news': ['新闻', 'news'],
            'joke': ['笑话', 'joke'],
            'game': ['游戏', 'game'],
            'tool': ['工具', 'tool']
        }
        
        for key, cmds in command_map.items():
            if key in name_lower:
                return [f"{self.prefix}{cmd}" for cmd in cmds]
        
        return [f"{self.prefix}{plugin_name}"]

    def _calculate_card_height(self, commands: List[str]) -> int:
        """计算卡片高度（自适应）"""
        base_height = 80  # 基础高度（插件名和描述）
        
        if not commands:
            return base_height
        
        # 计算指令行数
        commands_rows = (len(commands) + self.layout['commands_per_row'] - 1) // self.layout['commands_per_row']
        command_area_height = commands_rows * (self.layout['command_item_height'] + self.layout['command_margin'])
        
        return base_height + command_area_height + 20  # 额外间距

    def _calculate_image_height(self, plugins: List[Dict[str, Any]]) -> int:
        """计算图片总高度"""
        if not plugins:
            return 400
        
        total_height = self.layout['header_height'] + self.layout['margin'] * 2
        
        for plugin in plugins:
            card_height = self._calculate_card_height(plugin['commands'])
            total_height += card_height + self.layout['card_margin']
        
        return total_height + 50  # 底部额外空间

    async def generate_help_image(self, plugins: List[Dict[str, Any]]) -> Optional[str]:
        """生成帮助图片"""
        if not plugins:
            return None

        try:
            # 计算图片尺寸
            image_height = self._calculate_image_height(plugins)
            
            # 创建图片
            image = Image.new('RGB', (self.layout['image_width'], image_height), self.colors['background'])
            draw = ImageDraw.Draw(image)
            
            # 绘制头部
            self._draw_header(draw, image)
            
            # 加载头像
            avatar = self._load_avatar()
            
            # 绘制插件卡片
            y_offset = self.layout['header_height'] + self.layout['margin']
            
            for plugin in plugins:
                card_height = self._calculate_card_height(plugin['commands'])
                self._draw_plugin_card(draw, image, plugin, y_offset, card_height, avatar)
                y_offset += card_height + self.layout['card_margin']
            
            # 保存图片
            image_path = os.path.join(self.data_dir, "help.png")
            image.save(image_path, "PNG", quality=95)
            
            logger.info(f"帮助图片已生成: {image_path}")
            return image_path
            
        except Exception as e:
            logger.error(f"生成帮助图片失败: {e}")
            return None

    def _draw_header(self, draw: ImageDraw.Draw, image: Image.Image):
        """绘制头部"""
        # 绘制头部背景
        draw.rectangle([0, 0, self.layout['image_width'], self.layout['header_height']], 
                      fill=self.colors['header'])
        
        # 绘制标题
        title = "AstrBot 外部插件中心"
        bbox = draw.textbbox((0, 0), title, font=self.fonts['header'])
        title_width = bbox[2] - bbox[0]
        title_x = (self.layout['image_width'] - title_width) // 2
        title_y = (self.layout['header_height'] - (bbox[3] - bbox[1])) // 2
        
        draw.text((title_x, title_y), title, fill=self.colors['title'], font=self.fonts['header'])

    def _load_avatar(self) -> Optional[Image.Image]:
        """加载头像图片"""
        avatar_path = os.path.join(self.plugin_dir, "assets", "logo.png")
        
        try:
            if os.path.exists(avatar_path):
                avatar = Image.open(avatar_path)
                
                # 调整头像大小并转为圆形
                avatar = avatar.resize((self.layout['avatar_size'], self.layout['avatar_size']), Image.Resampling.LANCZOS)
                
                # 创建圆形蒙版
                mask = Image.new('L', (self.layout['avatar_size'], self.layout['avatar_size']), 0)
                mask_draw = ImageDraw.Draw(mask)
                mask_draw.ellipse([0, 0, self.layout['avatar_size'], self.layout['avatar_size']], fill=255)
                
                # 应用蒙版
                avatar.putalpha(mask)
                return avatar
            else:
                return None
        except Exception as e:
            return None

    def _draw_plugin_card(self, draw: ImageDraw.Draw, image: Image.Image, plugin: Dict[str, Any], 
                         y_offset: int, card_height: int, avatar: Optional[Image.Image]):
        """绘制插件卡片"""
        # 卡片边界
        card_left = self.layout['margin']
        card_right = self.layout['image_width'] - self.layout['margin']
        card_top = y_offset
        card_bottom = y_offset + card_height
        
        # 绘制卡片背景
        draw.rectangle([card_left, card_top, card_right, card_bottom], 
                      fill=self.colors['card_bg'], outline=self.colors['card_border'], width=2)
        
        # 内容区域
        content_left = card_left + self.layout['card_padding']
        content_top = card_top + self.layout['card_padding']
        content_right = card_right - self.layout['card_padding']
        
        # 第一行：头像 + 插件名 + 描述
        current_y = content_top
        
        # 根据配置决定是否绘制头像
        if self.show_plugin_logos:
            if avatar:
                try:
                    # 将头像直接粘贴到image对象上
                    # 由于image是RGB模式，需要特殊处理RGBA头像
                    if avatar.mode == 'RGBA':
                        # 创建白色背景
                        avatar_bg = Image.new('RGB', avatar.size, self.colors['card_bg'])
                        avatar_bg.paste(avatar, mask=avatar.split()[-1])  # 使用alpha通道作为蒙版
                        avatar = avatar_bg
                    
                    # 确保头像是RGB模式
                    if avatar.mode != 'RGB':
                        avatar = avatar.convert('RGB')
                    
                    # 计算粘贴位置
                    paste_x = content_left
                    paste_y = current_y
                    
                    # 直接粘贴到主图片上
                    image.paste(avatar, (paste_x, paste_y))
                    
                except Exception as e:
                    # 绘制占位符圆形
                    draw.ellipse([content_left, current_y, 
                                 content_left + self.layout['avatar_size'], 
                                 current_y + self.layout['avatar_size']], 
                                fill=self.colors['command_bg'], outline=self.colors['card_border'])
            else:
                # 没有头像时绘制占位符
                draw.ellipse([content_left, current_y, 
                             content_left + self.layout['avatar_size'], 
                             current_y + self.layout['avatar_size']], 
                            fill=self.colors['command_bg'], outline=self.colors['card_border'])
        # 插件名称和描述
        if self.show_plugin_logos:
            text_left = content_left + self.layout['avatar_size'] + 15
        else:
            text_left = content_left
        
        # 插件名称
        name_text = plugin['name']
        draw.text((text_left, current_y), name_text, fill=self.colors['title'], font=self.fonts['title'])
        
        # 插件描述（在名称下方）
        desc_y = current_y + 35
        desc_text = plugin['description']
        draw.text((text_left, desc_y), desc_text, fill=self.colors['text'], font=self.fonts['text'])
        
        # 第二行：指令列表（圆角矩形，一行4个）
        commands = plugin['commands']
        if commands:
            commands_start_y = content_top + 80
            self._draw_commands(draw, commands, content_left, commands_start_y, content_right)

    def _draw_commands(self, draw: ImageDraw.Draw, commands: List[str], 
                      left: int, top: int, right: int):
        """绘制指令列表（圆角矩形，一行4个）"""
        if not commands:
            return
        
        # 确保所有命令都是字符串类型
        string_commands = []
        for cmd in commands:
            if isinstance(cmd, str):
                string_commands.append(cmd)
            else:
                # 转换非字符串类型为字符串
                string_commands.append(str(cmd))
        
        # 计算每个指令框的位置
        available_width = right - left
        item_width = self.layout['command_item_width']
        item_height = self.layout['command_item_height']
        margin = self.layout['command_margin']
        
        # 调整项目宽度以适应容器
        if self.layout['commands_per_row'] * item_width + (self.layout['commands_per_row'] - 1) * margin > available_width:
            item_width = (available_width - (self.layout['commands_per_row'] - 1) * margin) // self.layout['commands_per_row']
        
        current_x = left
        current_y = top
        items_in_row = 0
        
        for command in string_commands:
            # 绘制圆角矩形背景
            self._draw_rounded_rectangle(draw, 
                                       [current_x, current_y, current_x + item_width, current_y + item_height],
                                       fill=self.colors['command_bg'], 
                                       outline=self.colors['command_border'],
                                       radius=8, width=1)
            
            # 绘制指令文本（居中）
            bbox = draw.textbbox((0, 0), command, font=self.fonts['command'])
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            text_x = current_x + (item_width - text_width) // 2
            text_y = current_y + (item_height - text_height) // 2
            
            draw.text((text_x, text_y), command, fill=self.colors['command_text'], font=self.fonts['command'])
            
            # 更新位置
            items_in_row += 1
            if items_in_row >= self.layout['commands_per_row']:
                # 换行
                current_x = left
                current_y += item_height + margin
                items_in_row = 0
            else:
                current_x += item_width + margin

    def _draw_rounded_rectangle(self, draw: ImageDraw.Draw, coords: List[int], 
                              fill: str, outline: str, radius: int = 5, width: int = 1):
        """绘制圆角矩形"""
        x1, y1, x2, y2 = coords
        
        # 绘制圆角矩形
        draw.rounded_rectangle([x1, y1, x2, y2], radius=radius, fill=fill, outline=outline, width=width)

    def generate_text_help(self, plugins: List[Dict[str, Any]]) -> str:
        """生成文本版帮助信息"""
        if not plugins:
            return "暂无外部插件信息"
        
        help_text = f"📋 AstrBot 外部插件中心 ({len(plugins)}个插件)\n\n"
        
        for i, plugin in enumerate(plugins, 1):
            help_text += f"{i}. 【{plugin['name']}】\n"
            help_text += f"   📝 {plugin['description']}\n"
            help_text += f"   👤 作者: {plugin['author']} | 版本: {plugin['version']}\n"
            
            if plugin['commands']:
                # 确保所有指令都是字符串类型
                string_commands = [str(cmd) if not isinstance(cmd, str) else cmd for cmd in plugin['commands']]
                commands_str = " | ".join(string_commands)
                help_text += f"   🔧 指令: {commands_str}\n"
            
            help_text += "\n"
        
        help_text += "💡 输入对应指令即可使用插件功能"
        return help_text 