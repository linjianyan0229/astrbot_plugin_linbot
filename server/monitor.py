"""
服务器监控模块
用于获取系统信息并生成美观的监控图片
"""

import os
import platform
import psutil
import time
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import io
import json


class ServerMonitor:
    """服务器监控类"""
    
    def __init__(self):
        self.data_dir = "data/plugins_data/astrbot_plugin_linbot"
        os.makedirs(self.data_dir, exist_ok=True)
        
    def get_system_info(self):
        """获取系统信息"""
        try:
            # 基本系统信息
            system_info = {
                "系统": platform.system(),
                "版本": platform.version(),
                "架构": platform.machine(),
                "处理器": platform.processor() or "未知",
                "主机名": platform.node(),
                "启动时间": datetime.fromtimestamp(psutil.boot_time()).strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # CPU信息
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count(logical=False)
            cpu_count_logical = psutil.cpu_count(logical=True)
            cpu_freq = psutil.cpu_freq()
            
            cpu_info = {
                "使用率": f"{cpu_percent:.1f}%",
                "物理核心": cpu_count,
                "逻辑核心": cpu_count_logical,
                "当前频率": f"{cpu_freq.current:.1f}MHz" if cpu_freq else "未知",
                "最大频率": f"{cpu_freq.max:.1f}MHz" if cpu_freq and cpu_freq.max else "未知"
            }
            
            # 内存信息
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            memory_info = {
                "总量": self._format_bytes(memory.total),
                "已用": self._format_bytes(memory.used),
                "可用": self._format_bytes(memory.available),
                "使用率": f"{memory.percent:.1f}%",
                "交换区总量": self._format_bytes(swap.total),
                "交换区已用": self._format_bytes(swap.used),
                "交换区使用率": f"{swap.percent:.1f}%"
            }
            
            # 磁盘信息
            disk_info = []
            for partition in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    disk_info.append({
                        "设备": partition.device,
                        "挂载点": partition.mountpoint,
                        "文件系统": partition.fstype,
                        "总量": self._format_bytes(usage.total),
                        "已用": self._format_bytes(usage.used),
                        "可用": self._format_bytes(usage.free),
                        "使用率": f"{(usage.used / usage.total * 100):.1f}%"
                    })
                except PermissionError:
                    continue
            
            # 网络信息
            network_io = psutil.net_io_counters()
            network_info = {
                "发送字节": self._format_bytes(network_io.bytes_sent),
                "接收字节": self._format_bytes(network_io.bytes_recv),
                "发送包数": network_io.packets_sent,
                "接收包数": network_io.packets_recv
            }
            
            # 进程信息
            process_count = len(psutil.pids())
            running_time = datetime.now() - datetime.fromtimestamp(psutil.boot_time())
            
            process_info = {
                "进程总数": process_count,
                "运行时间": str(running_time).split('.')[0]
            }
            
            return {
                "system": system_info,
                "cpu": cpu_info,
                "memory": memory_info,
                "disk": disk_info,
                "network": network_info,
                "process": process_info,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
        except Exception as e:
            raise Exception(f"获取系统信息失败: {str(e)}")
    
    def _format_bytes(self, bytes_value):
        """格式化字节数"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.1f}{unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.1f}PB"
    
    def generate_monitor_image(self, info):
        """生成监控图片"""
        try:
            # 创建图片
            width, height = 800, 1000
            img = Image.new('RGB', (width, height), color='#1a1a1a')
            draw = ImageDraw.Draw(img)
            
            # 加载指定字体
            font_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "LXGWWenKai-Regular.ttf")
            try:
                font_large = ImageFont.truetype(font_path, 24)
                font_medium = ImageFont.truetype(font_path, 16)
                font_small = ImageFont.truetype(font_path, 12)
            except Exception as font_error:
                print(f"字体加载失败: {font_error}")
                # 备用字体方案
                try:
                    # Windows系统字体
                    font_large = ImageFont.truetype("msyh.ttc", 24)
                    font_medium = ImageFont.truetype("msyh.ttc", 16)
                    font_small = ImageFont.truetype("msyh.ttc", 12)
                except:
                    try:
                        # Linux系统字体
                        font_large = ImageFont.truetype("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc", 24)
                        font_medium = ImageFont.truetype("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc", 16)
                        font_small = ImageFont.truetype("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc", 12)
                    except:
                        # 默认字体
                        font_large = ImageFont.load_default()
                        font_medium = ImageFont.load_default()
                        font_small = ImageFont.load_default()
            
            y_offset = 20
            
            # 标题
            title = "🖥️ 服务器监控报告"
            draw.text((width//2 - 100, y_offset), title, fill='#00d4aa', font=font_large)
            y_offset += 50
            
            # 时间戳
            draw.text((width//2 - 80, y_offset), f"更新时间: {info['timestamp']}", fill='#888', font=font_small)
            y_offset += 40
            
            # 系统信息
            self._draw_section(draw, "📋 系统信息", info['system'], y_offset, font_medium, font_small, width)
            y_offset += len(info['system']) * 25 + 60
            
            # CPU信息
            self._draw_section(draw, "🔥 CPU信息", info['cpu'], y_offset, font_medium, font_small, width)
            y_offset += len(info['cpu']) * 25 + 60
            
            # 内存信息
            self._draw_section(draw, "💾 内存信息", info['memory'], y_offset, font_medium, font_small, width)
            y_offset += len(info['memory']) * 25 + 60
            
            # 进程信息
            self._draw_section(draw, "⚡ 进程信息", info['process'], y_offset, font_medium, font_small, width)
            y_offset += len(info['process']) * 25 + 60
            
            # 网络信息
            self._draw_section(draw, "🌐 网络信息", info['network'], y_offset, font_medium, font_small, width)
            y_offset += len(info['network']) * 25 + 60
            
            # 磁盘信息（只显示前3个）
            disk_title = "💿 磁盘信息"
            draw.text((20, y_offset), disk_title, fill='#00d4aa', font=font_medium)
            y_offset += 35
            
            for i, disk in enumerate(info['disk'][:3]):  # 只显示前3个磁盘
                disk_text = f"{disk['设备']} ({disk['文件系统']})"
                draw.text((40, y_offset), disk_text, fill='#fff', font=font_small)
                y_offset += 20
                
                usage_text = f"  {disk['已用']} / {disk['总量']} ({disk['使用率']})"
                draw.text((40, y_offset), usage_text, fill='#ccc', font=font_small)
                y_offset += 25
            
            # 保存图片
            image_path = os.path.join(self.data_dir, "server_monitor.png")
            img.save(image_path, "PNG")
            
            return image_path
            
        except Exception as e:
            raise Exception(f"生成监控图片失败: {str(e)}")
    
    def _draw_section(self, draw, title, data, y_offset, font_medium, font_small, width):
        """绘制信息段落"""
        # 段落标题
        draw.text((20, y_offset), title, fill='#00d4aa', font=font_medium)
        y_offset += 35
        
        # 段落内容
        for key, value in data.items():
            text = f"{key}: {value}"
            draw.text((40, y_offset), text, fill='#fff', font=font_small)
            y_offset += 25
    
    def generate_cpu_chart(self, duration=30, interval=1):
        """生成CPU使用率图表"""
        try:
            # 收集CPU数据
            cpu_data = []
            timestamps = []
            
            for i in range(duration):  # 根据配置收集数据
                cpu_percent = psutil.cpu_percent(interval=interval)
                cpu_data.append(cpu_percent)
                timestamps.append(datetime.now().strftime("%H:%M:%S"))
            
            # 设置字体路径
            font_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "LXGWWenKai-Regular.ttf")
            
            # 设置中文字体
            try:
                # 使用指定字体
                plt.rcParams['font.family'] = ['LXGWWenKai']
                from matplotlib.font_manager import FontProperties
                font_prop = FontProperties(fname=font_path)
                plt.rcParams['font.sans-serif'] = [font_prop.get_name()]
            except Exception as font_error:
                print(f"matplotlib字体设置失败: {font_error}")
                # 备用字体设置
                plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans', 'Liberation Sans']
            
            plt.rcParams['axes.unicode_minus'] = False
            
            # 创建图表
            plt.figure(figsize=(12, 6))
            plt.plot(timestamps[::max(1, duration//10)], cpu_data[::max(1, duration//10)], 'b-', linewidth=2, marker='o', markersize=4)
            plt.title(f'CPU使用率趋势 (最近{duration}秒)', fontsize=16, fontweight='bold')
            plt.xlabel('时间', fontsize=12)
            plt.ylabel('CPU使用率 (%)', fontsize=12)
            plt.grid(True, alpha=0.3)
            plt.xticks(rotation=45)
            plt.ylim(0, 100)
            
            # 添加统计信息
            avg_cpu = sum(cpu_data) / len(cpu_data)
            max_cpu = max(cpu_data)
            min_cpu = min(cpu_data)
            plt.text(0.02, 0.98, f'平均: {avg_cpu:.1f}%\n最高: {max_cpu:.1f}%\n最低: {min_cpu:.1f}%', 
                    transform=plt.gca().transAxes, verticalalignment='top',
                    bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
            
            plt.tight_layout()
            
            # 保存图表
            chart_path = os.path.join(self.data_dir, "cpu_chart.png")
            plt.savefig(chart_path, dpi=150, bbox_inches='tight')
            plt.close()
            
            return chart_path
            
        except Exception as e:
            raise Exception(f"生成CPU图表失败: {str(e)}") 