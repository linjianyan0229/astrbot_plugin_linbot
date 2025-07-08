import os
import shutil
from typing import Dict, Any
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger, AstrBotConfig

# 导入帮助功能模块
from .helps.helps import PluginHelpGenerator
# 导入服务器监控模块
from .server.monitor import ServerMonitor
# 导入游戏模块
from .game.qiandao import CheckinManager
from .game.mybag import UserInfoManager
from .game.gzrw import WorkManager
from .game.bank import BankManager
from .game.phb import RankingManager
from .game.qiangjie import RobberyManager

@register("linbot", "YourName", "LinBot - AstrBot 外部插件帮助中心和服务器监控工具", "1.4.0", "https://github.com/yourusername/astrbot_plugin_linbot")
class LinBotPlugin(Star):
    """LinBot - AstrBot 外部插件帮助中心和服务器监控工具"""

    def __init__(self, context: Context, config: AstrBotConfig = None):
        super().__init__(context)
        self.plugin_dir = os.path.dirname(__file__)
        self.data_dir = os.path.join("data", "plugins_data", "astrbot_plugin_linbot")
        self.plugin_config = config or {}
        
        # 获取系统前缀配置
        system_config = self.context.get_config()
        self.prefix = system_config.get("wake_prefix", ["/"])[0] if system_config.get("wake_prefix") else "/"
        
        # 获取显示设置
        display_settings = self.plugin_config.get("display_settings", {})
        self.max_commands_per_row = display_settings.get("max_commands_per_row", 4)
        self.show_plugin_logos = display_settings.get("show_plugin_logos", True)
        
        # 验证设置范围
        if not (1 <= self.max_commands_per_row <= 6):
            self.max_commands_per_row = 4
        
        # 获取服务器监控设置
        monitor_settings = self.plugin_config.get("server_monitor_settings", {})
        self.enable_monitor = monitor_settings.get("enable_monitor", True)
        self.monitor_interval = monitor_settings.get("monitor_interval", 1)
        self.chart_duration = monitor_settings.get("chart_duration", 30)
        
        # 验证监控设置范围
        if not (1 <= self.monitor_interval <= 10):
            self.monitor_interval = 1
        if not (10 <= self.chart_duration <= 120):
            self.chart_duration = 30
        
        # 初始化帮助生成器，传递配置参数
        self.help_generator = PluginHelpGenerator(
            context=self.context,
            plugin_dir=self.plugin_dir,
            prefix=self.prefix,
            max_commands_per_row=self.max_commands_per_row,
            show_plugin_logos=self.show_plugin_logos
        )
        
        # 初始化服务器监控
        if self.enable_monitor:
            self.server_monitor = ServerMonitor()
        else:
            self.server_monitor = None
        
        # 初始化游戏模块
        game_db_path = os.path.join(self.plugin_dir, "game", "user.db")
        self.checkin_manager = CheckinManager(game_db_path)
        self.user_info_manager = UserInfoManager(game_db_path)
        self.work_manager = WorkManager(game_db_path, self.plugin_config)
        self.bank_manager = BankManager(game_db_path, self.plugin_config)
        self.ranking_manager = RankingManager(game_db_path, self.plugin_dir)
        self.robbery_manager = RobberyManager(game_db_path, self.plugin_config)
        
        logger.info(f"LinBot 插件加载完成 - 每行指令数: {self.max_commands_per_row}, 显示头像: {self.show_plugin_logos}, 使用系统前缀: {self.prefix}")

    @filter.command("帮助")
    async def help_command(self, event: AstrMessageEvent):
        """生成AstrBot外部插件帮助中心图片"""
        try:
            # 获取外部插件信息
            plugins = self.help_generator.get_external_plugins()
            
            if not plugins:
                yield event.plain_result("暂无外部插件信息")
                return
            
            # 生成帮助图片
            image_path = await self.help_generator.generate_help_image(plugins)
            
            if image_path and os.path.exists(image_path):
                yield event.image_result(image_path)
            else:
                # 降级到文本帮助
                text_help = self.help_generator.generate_text_help(plugins)
                yield event.plain_result(text_help)
                
        except Exception as e:
            logger.error(f"LinBot帮助功能出错: {e}")
            yield event.plain_result("帮助功能暂时不可用，请稍后再试")

    @filter.command("linbot_config")
    async def config_command(self, event: AstrMessageEvent):
        """LinBot配置管理指令"""
        try:
            args = event.message_str.split()
            
            if len(args) == 1:
                # 显示当前配置
                config_info = f"""📋 LinBot 当前配置：

🎨 显示设置：
• 每行指令数：{self.max_commands_per_row} (1-6)
• 显示插件头像：{'开启' if self.show_plugin_logos else '关闭'}

🖥️ 服务器监控设置：
• 监控功能：{'启用' if self.enable_monitor else '禁用'}
• 监控间隔：{self.monitor_interval}秒 (1-10)
• 图表时长：{self.chart_duration}秒 (10-120)

ℹ️ 系统信息：
• 当前指令前缀：{self.prefix} (来自系统配置)

💡 提示：
• 修改配置请前往 AstrBot 管理页面 -> 插件管理 -> LinBot -> 配置
• 修改指令前缀请前往 AstrBot 系统设置
• 配置修改后需要重载插件才能生效"""
                yield event.plain_result(config_info)
                
            elif len(args) == 2 and args[1] == "reload":
                # 重新加载配置
                display_settings = self.plugin_config.get("display_settings", {})
                monitor_settings = self.plugin_config.get("server_monitor_settings", {})
                
                old_commands_per_row = self.max_commands_per_row
                old_show_logos = self.show_plugin_logos
                old_enable_monitor = self.enable_monitor
                old_monitor_interval = self.monitor_interval
                old_chart_duration = self.chart_duration
                
                # 更新显示配置
                self.max_commands_per_row = display_settings.get("max_commands_per_row", 4)
                self.show_plugin_logos = display_settings.get("show_plugin_logos", True)
                
                # 验证设置范围
                if not (1 <= self.max_commands_per_row <= 6):
                    self.max_commands_per_row = 4
                
                # 更新服务器监控配置
                self.enable_monitor = monitor_settings.get("enable_monitor", True)
                self.monitor_interval = monitor_settings.get("monitor_interval", 1)
                self.chart_duration = monitor_settings.get("chart_duration", 30)
                
                # 验证监控设置范围
                if not (1 <= self.monitor_interval <= 10):
                    self.monitor_interval = 1
                if not (10 <= self.chart_duration <= 120):
                    self.chart_duration = 30
                
                # 重新获取系统前缀配置
                system_config = self.context.get_config()
                self.prefix = system_config.get("wake_prefix", ["/"])[0] if system_config.get("wake_prefix") else "/"
                
                # 重新初始化帮助生成器
                self.help_generator = PluginHelpGenerator(
                    context=self.context,
                    plugin_dir=self.plugin_dir,
                    prefix=self.prefix,
                    max_commands_per_row=self.max_commands_per_row,
                    show_plugin_logos=self.show_plugin_logos
                )
                
                # 重新初始化服务器监控
                if self.enable_monitor:
                    self.server_monitor = ServerMonitor()
                else:
                    self.server_monitor = None
                
                changes = []
                if old_commands_per_row != self.max_commands_per_row:
                    changes.append(f"每行指令数: {old_commands_per_row} → {self.max_commands_per_row}")
                if old_show_logos != self.show_plugin_logos:
                    changes.append(f"显示头像: {old_show_logos} → {self.show_plugin_logos}")
                if old_enable_monitor != self.enable_monitor:
                    changes.append(f"监控功能: {old_enable_monitor} → {self.enable_monitor}")
                if old_monitor_interval != self.monitor_interval:
                    changes.append(f"监控间隔: {old_monitor_interval}秒 → {self.monitor_interval}秒")
                if old_chart_duration != self.chart_duration:
                    changes.append(f"图表时长: {old_chart_duration}秒 → {self.chart_duration}秒")
                
                if changes:
                    yield event.plain_result(f"✅ 配置已重载\n\n变更内容：\n" + "\n".join(f"• {change}" for change in changes))
                else:
                    yield event.plain_result("✅ 配置已重载，无变更")
                    
            else:
                yield event.plain_result("""📖 LinBot 配置指令使用说明：

/linbot_config - 查看当前配置
/linbot_config reload - 重新加载配置

💡 要修改配置，请前往：
AstrBot 管理页面 → 插件管理 → LinBot → 配置""")
                
        except Exception as e:
            logger.error(f"LinBot配置管理出错: {e}")
            yield event.plain_result("配置管理功能出现错误，请检查日志")

    @filter.command("签到")
    async def checkin_command(self, event: AstrMessageEvent):
        """用户签到指令"""
        try:
            user_id = str(event.get_sender_id())
            username = event.get_sender_name() or f"用户{user_id}"
            
            # 执行签到
            result = self.checkin_manager.daily_checkin(user_id, username)
            
            if result['success']:
                # 签到成功
                reward_info = result['reward']
                message = f"""✅ 签到成功！

💰 获得奖励：
• 基础奖励：{reward_info['base']} 金币
• 随机奖励：{reward_info['random']} 金币"""
                
                if reward_info['consecutive'] > 0:
                    message += f"\n• 连续奖励：{reward_info['consecutive']} 金币"
                
                message += f"""
• 总计获得：{reward_info['total']} 金币

📊 签到统计：
• 当前金币：{result['new_money']}
• 连续签到：{result['consecutive_days']} 天
• 累计签到：{result['total_checkin']} 次

💡 明天记得继续签到哦！"""
                
            else:
                # 签到失败
                if result.get('already_checked'):
                    message = f"""⏰ 今天已经签到过了！

💡 提示：
• 每天只能签到一次
• 明天再来领取奖励吧
• 连续签到可以获得额外奖励

📋 想查看签到信息？发送 "{self.prefix}签到信息" """
                else:
                    message = f"❌ {result['message']}"
            
            yield event.plain_result(message)
            
        except Exception as e:
            logger.error(f"签到功能出错: {e}")
            yield event.plain_result("签到功能暂时不可用，请稍后再试")

    @filter.command("签到信息")
    async def checkin_info_command(self, event: AstrMessageEvent):
        """查看签到信息"""
        try:
            user_id = str(event.get_sender_id())
            username = event.get_sender_name() or f"用户{user_id}"
            
            # 获取签到信息
            info = self.checkin_manager.get_checkin_info(user_id, username)
            
            if 'error' in info:
                yield event.plain_result(f"❌ {info['error']}")
                return
            
            # 格式化信息
            message = f"""📋 {username} 的签到信息

💰 当前金币：{info['money']}
🔥 连续签到：{info['streak']} 天
📅 累计签到：{info['total_checkin']} 次
⏰ 最后签到：{info['last_checkin'] or '从未签到'}

🎯 今日状态：{'✅ 已签到' if info['has_checked_today'] else '❌ 未签到'}"""
            
            if info['has_checked_today']:
                message += f"\n💰 今日奖励：{info['today_reward']} 金币"
            else:
                next_reward = info['next_reward']
                message += f"""

🎁 明日预期奖励：
• 基础奖励：{next_reward['base']} 金币
• 随机奖励：{next_reward['random']} 金币"""
                if next_reward['consecutive'] > 0:
                    message += f"\n• 连续奖励：{next_reward['consecutive']} 金币"
                message += f"\n• 预计总计：{next_reward['total']} 金币"
            
            # 显示最近签到记录
            if info['recent_records']:
                message += "\n\n📊 最近签到记录："
                for record in info['recent_records'][:5]:
                    date_str, reward, consecutive = record
                    message += f"\n• {date_str}：{reward}金币 (连续{consecutive}天)"
            
            message += f"\n\n💡 发送 \"{self.prefix}签到\" 进行签到"
            
            yield event.plain_result(message)
            
        except Exception as e:
            logger.error(f"获取签到信息出错: {e}")
            yield event.plain_result("获取签到信息失败，请稍后再试")

    @filter.command("签到排行")
    async def checkin_ranking_command(self, event: AstrMessageEvent):
        """签到排行榜"""
        try:
            ranking = self.checkin_manager.get_checkin_ranking(10)
            
            if not ranking:
                yield event.plain_result("暂无签到排行数据")
                return
            
            message = "🏆 签到排行榜 (按连续签到天数)\n\n"
            
            for i, (username, streak, total) in enumerate(ranking, 1):
                emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                message += f"{emoji} {username}\n"
                message += f"   连续：{streak}天 | 累计：{total}次\n\n"
            
            message += f"💡 发送 \"{self.prefix}签到\" 开始签到"
            
            yield event.plain_result(message)
            
        except Exception as e:
            logger.error(f"获取签到排行出错: {e}")
            yield event.plain_result("获取排行榜失败，请稍后再试")

    @filter.command("我的信息")
    async def user_info_command(self, event: AstrMessageEvent):
        """查看用户详细信息"""
        try:
            user_id = str(event.get_sender_id())
            username = event.get_sender_name() or f"用户{user_id}"
            
            # 获取用户完整信息
            info = self.user_info_manager.get_comprehensive_info(user_id, username)
            
            if 'error' in info:
                yield event.plain_result(f"❌ {info['error']}")
                return
            
            basic = info['basic']
            stats = info['stats']
            rankings = info['rankings']
            
            # 格式化基本信息
            message = f"""👤 {basic['username']} 的个人信息

💰 财富状况：
• 现金：{basic['money']} 金币
• 银行：{basic['bank_money']} 金币
• 总资产：{basic['total_assets']} 金币
• 累计收入：{basic['total_earned']} 金币

📊 等级信息：
• 等级：{basic['level']} 级"""
            
            # 获取等级信息
            level_info = self.user_info_manager._get_level_info(basic['exp'])
            message += f"""
• 经验：{level_info['current_exp']} EXP ({level_info['level_progress']}/{level_info['exp_for_current_level']})
• 距离 {level_info['next_level']} 级还需：{level_info['exp_needed']} EXP

🎯 签到统计：
• 连续签到：{basic['checkin_streak']} 天
• 累计签到：{basic['total_checkin']} 次

🏆 排名情况：
• 金钱排名：第 {rankings['money_rank']} 名
• 资产排名：第 {rankings['assets_rank']} 名  
• 签到排名：第 {rankings['checkin_rank']} 名
• 总用户数：{rankings['total_users']} 人

⏰ 账户信息：
• 注册天数：{basic['days_registered']} 天
• 注册时间：{basic['created_at'][:10] if basic['created_at'] else '未知'}"""

            # 添加统计信息
            if 'error' not in stats:
                bank_stats = stats.get('bank', {})
                work_stats = stats.get('work', {})
                rob_stats = stats.get('robbery', {})
                
                message += f"""

📈 活动统计：
• 银行交易：{bank_stats.get('total_transactions', 0)} 次
• 打工次数：{work_stats.get('total_works', 0)} 次
• 打工收入：{work_stats.get('total_income', 0)} 金币
• 抢劫成功：{rob_stats.get('successful_robberies', 0)}/{rob_stats.get('robberies_initiated', 0)} 次
• 抢劫成功率：{rob_stats.get('rob_success_rate', 0)}%"""

            message += f"\n\n💡 发送 \"{self.prefix}我的详情\" 查看更多详细统计"
            
            yield event.plain_result(message)
            
        except Exception as e:
            logger.error(f"获取用户信息出错: {e}")
            yield event.plain_result("获取用户信息失败，请稍后再试")

    @filter.command("我的详情")
    async def user_details_command(self, event: AstrMessageEvent):
        """查看用户详细统计"""
        try:
            user_id = str(event.get_sender_id())
            username = event.get_sender_name() or f"用户{user_id}"
            
            # 获取用户统计信息
            stats = self.user_info_manager.get_user_statistics(user_id)
            
            if 'error' in stats:
                yield event.plain_result(f"❌ {stats['error']}")
                return
            
            bank_stats = stats.get('bank', {})
            work_stats = stats.get('work', {})
            rob_stats = stats.get('robbery', {})
            item_stats = stats.get('items', {})
            
            message = f"""📋 {username} 的详细统计

🏦 银行统计：
• 总交易次数：{bank_stats.get('total_transactions', 0)} 次
• 累计存款：{bank_stats.get('total_deposits', 0)} 金币
• 累计取款：{bank_stats.get('total_withdraws', 0)} 金币

💼 打工统计：
• 总打工次数：{work_stats.get('total_works', 0)} 次
• 总打工收入：{work_stats.get('total_income', 0)} 金币"""
            
            # 打工类型统计
            work_types = work_stats.get('work_types', [])
            if work_types:
                message += "\n• 打工类型分布："
                for work_type, count, income in work_types[:3]:  # 显示前3种
                    message += f"\n  └─ {work_type}：{count}次，{income}金币"
            
            message += f"""

🦹 抢劫统计：
• 发起抢劫：{rob_stats.get('robberies_initiated', 0)} 次
• 成功抢劫：{rob_stats.get('successful_robberies', 0)} 次
• 抢劫成功率：{rob_stats.get('rob_success_rate', 0)}%
• 抢劫所得：{rob_stats.get('total_robbed', 0)} 金币
• 被抢次数：{rob_stats.get('times_robbed', 0)} 次
• 被抢损失：{rob_stats.get('total_lost', 0)} 金币

🎒 物品统计：
• 物品种类：{item_stats.get('total_items', 0)} 种
• 物品总数：{item_stats.get('total_quantity', 0)} 个
• 物品总值：{item_stats.get('total_value', 0)} 金币"""
            
            yield event.plain_result(message)
            
        except Exception as e:
            logger.error(f"获取用户详情出错: {e}")
            yield event.plain_result("获取用户详情失败，请稍后再试")

    @filter.command("我的记录")
    async def user_activities_command(self, event: AstrMessageEvent):
        """查看用户最近活动记录"""
        try:
            user_id = str(event.get_sender_id())
            username = event.get_sender_name() or f"用户{user_id}"
            
            # 获取最近活动记录
            activities = self.user_info_manager.get_recent_activities(user_id, 10)
            
            if not activities:
                yield event.plain_result("暂无活动记录")
                return
            
            message = f"📝 {username} 的最近活动记录\n\n"
            
            for activity in activities:
                timestamp = activity['timestamp'][:16]  # 截取到分钟
                
                if activity['type'] == 'checkin':
                    message += f"✅ {timestamp} 签到获得 {activity['amount']} 金币 ({activity['extra']})\n"
                elif activity['type'] == 'bank':
                    action_text = "存款" if activity['action'] == 'deposit' else "取款"
                    message += f"🏦 {timestamp} {action_text} {activity['amount']} 金币\n"
            
            message += f"\n💡 更多功能：\n• \"{self.prefix}我的信息\" - 查看基本信息\n• \"{self.prefix}我的详情\" - 查看详细统计"
            
            yield event.plain_result(message)
            
        except Exception as e:
            logger.error(f"获取活动记录出错: {e}")
            yield event.plain_result("获取活动记录失败，请稍后再试")

    @filter.command("打工")
    async def work_command(self, event: AstrMessageEvent):
        """打工指令"""
        try:
            user_id = str(event.get_sender_id())
            username = event.get_sender_name() or f"用户{user_id}"
            
            args = event.message_str.split()
            
            if len(args) == 1:
                # 显示工作列表
                jobs_info = self.work_manager.get_available_jobs(user_id, username)
                
                if 'error' in jobs_info:
                    yield event.plain_result(f"❌ {jobs_info['error']}")
                    return
                
                message = f"""💼 工作列表

📊 今日工作：{jobs_info['today_work_count']}/{jobs_info['daily_limit']} 次
{'✅ 还可以工作' if jobs_info['can_work_today'] else '❌ 今日工作次数已满'}

🔧 可用工作："""
                
                for job in jobs_info['jobs']:
                    name = job['name']
                    config = job['config']
                    status = "✅" if job['available'] else "❌"
                    
                    if not job['available'] and job['cooldown_end']:
                        status += f" (冷却至{job['cooldown_end']})"
                    elif job['user_level'] < config['level_required']:
                        status += f" (需要{config['level_required']}级)"
                    
                    salary_range = f"{config['salary_range'][0]}-{config['salary_range'][1]}"
                    # 计算实际冷却时间（考虑配置倍数）
                    actual_cooldown = config['cooldown_hours'] * self.work_manager.cooldown_multiplier
                    cooldown_display = f"{actual_cooldown:.1f}小时" if actual_cooldown != int(actual_cooldown) else f"{int(actual_cooldown)}小时"
                    
                    message += f"""
{status} {name}
   💰 工资：{salary_range} 金币
   📖 描述：{config['description']}
   ⭐ 要求：{config['level_required']}级 | 冷却：{cooldown_display}"""
                
                message += f"\n\n💡 使用方法：{self.prefix}打工 [工作名称]"
                message += f"\n📊 查看统计：{self.prefix}打工统计"
                
                yield event.plain_result(message)
                
            else:
                # 执行指定工作
                job_name = " ".join(args[1:])
                result = self.work_manager.work(user_id, username, job_name)
                
                if result['success']:
                    salary = result['salary_result']
                    message = f"""✅ 打工成功！

💼 工作：{result['job_name']}
💰 收入详情：
• 基础工资：{salary['base_salary']} 金币
• 等级加成：{salary['level_bonus']} 金币"""
                    
                    if salary['luck_triggered']:
                        message += f"\n• 🍀 幸运加成：{salary['luck_bonus']} 金币"
                    
                    message += f"""
• 总收入：{salary['total_earned']} 金币
• 经验奖励：{salary['exp_reward']} EXP

📊 更新后：
• 金币：{result['new_money']}
• 等级：{result['new_level']}"""
                    
                    # 获取等级信息
                    level_info = self.work_manager._get_level_info(result['new_exp'])
                    message += f"\n• 经验：{level_info['current_exp']} EXP ({level_info['level_progress']}/{level_info['exp_for_current_level']})"
                    
                    if not result['level_up']:
                        message += f"\n• 距离 {level_info['next_level']} 级还需：{level_info['exp_needed']} EXP"
                    
                    if result['level_up']:
                        message += f"\n🎉 恭喜升级！等级提升至 {result['new_level']} 级！"
                    
                    message += f"\n• 今日工作：{result['today_work_count']}/{self.work_manager.daily_work_limit} 次"
                else:
                    message = f"❌ {result['message']}"
                
                yield event.plain_result(message)
                
        except Exception as e:
            logger.error(f"打工功能出错: {e}")
            yield event.plain_result("打工功能暂时不可用，请稍后再试")

    @filter.command("打工统计")
    async def work_stats_command(self, event: AstrMessageEvent):
        """打工统计"""
        try:
            user_id = str(event.get_sender_id())
            username = event.get_sender_name() or f"用户{user_id}"
            
            stats = self.work_manager.get_work_statistics(user_id)
            
            if 'error' in stats:
                yield event.plain_result(f"❌ {stats['error']}")
                return
            
            overall = stats['overall']
            today = stats['today']
            
            message = f"""📊 {username} 的打工统计

📈 总体统计：
• 总工作次数：{overall['total_works']} 次
• 总收入：{overall['total_income']} 金币
• 平均收入：{overall['avg_income']} 金币/次

📅 今日统计：
• 今日工作：{today['works']} 次
• 今日收入：{today['income']} 金币
• 剩余次数：{today['remaining']} 次

💼 工作类型统计："""
            
            job_stats = stats['job_stats']
            if job_stats:
                for work_type, count, total_income, avg_income, max_income in job_stats[:5]:
                    message += f"""
• {work_type}：{count}次
  └─ 总收入：{total_income} | 平均：{int(avg_income)} | 最高：{max_income}"""
            else:
                message += "\n• 暂无工作记录"
            
            # 最近工作记录
            recent_works = stats['recent_works']
            if recent_works:
                message += "\n\n📝 最近工作："
                for work_type, earned, work_time in recent_works[:3]:
                    time_str = work_time[:16]  # 截取到分钟
                    message += f"\n• {time_str} {work_type} +{earned}金币"
            
            message += f"\n\n💡 继续努力：{self.prefix}打工"
            
            yield event.plain_result(message)
            
        except Exception as e:
            logger.error(f"获取打工统计出错: {e}")
            yield event.plain_result("获取打工统计失败，请稍后再试")

    @filter.command("银行")
    async def bank_command(self, event: AstrMessageEvent):
        """银行指令"""
        try:
            user_id = str(event.get_sender_id())
            username = event.get_sender_name() or f"用户{user_id}"
            
            args = event.message_str.split()
            
            if len(args) == 1:
                # 显示银行信息
                info = self.bank_manager.get_bank_info(user_id, username)
                
                if 'error' in info:
                    yield event.plain_result(f"❌ {info['error']}")
                    return
                
                vip_status = "🌟 VIP用户" if info['is_vip'] else f"普通用户 (存款{info['vip_threshold']}金币可升级VIP)"
                
                message = f"""🏦 {info['username']} 的银行信息

💰 资产状况：
• 现金：{info['money']} 金币
• 银行存款：{info['bank_money']} 金币
• 总资产：{info['total_assets']} 金币

👑 账户等级：{vip_status}
📈 利率：{info['interest_rate']:.2f}% (日利率)
💎 每日利息：{info['daily_interest']} 金币

📊 今日取款：
• 已取款：{info['today_withdraw']} 金币
• 剩余额度：{info['remaining_withdraw']} 金币
• 每日限额：{info['daily_limit']} 金币

📋 交易统计：
• 总交易次数：{info['stats']['total_transactions']} 次
• 累计存款：{info['stats']['total_deposits']} 金币
• 累计取款：{info['stats']['total_withdraws']} 金币

💡 使用方法：
• {self.prefix}银行 存款 [金额] - 存入现金
• {self.prefix}银行 取款 [金额] - 取出现金
• {self.prefix}银行 转账 [用户名] [金额] - 转账给他人"""
                
                # 显示最近交易
                if info['recent_transactions']:
                    message += "\n\n📝 最近交易："
                    for trans_type, amount, created_at in info['recent_transactions'][:3]:
                        type_text = {
                            'deposit': '存款',
                            'withdraw': '取款',
                            'transfer_in': '转入',
                            'transfer_out': '转出',
                            'interest': '利息'
                        }.get(trans_type, trans_type)
                        
                        time_str = created_at[:16]
                        sign = '+' if trans_type in ['deposit', 'transfer_in', 'interest'] else '-'
                        message += f"\n• {time_str} {type_text} {sign}{amount}金币"
                
                yield event.plain_result(message)
                
            elif len(args) >= 3 and args[1] == "存款":
                # 执行存款
                try:
                    amount = int(args[2])
                    result = self.bank_manager.deposit(user_id, username, amount)
                    
                    if result['success']:
                        message = f"""✅ 存款成功！

💰 存款金额：{result['amount']} 金币

📊 更新后资产：
• 现金：{result['new_money']} 金币
• 银行存款：{result['new_bank_money']} 金币
• 总资产：{result['total_assets']} 金币

💡 提示：银行存款每日可获得利息"""
                    else:
                        message = f"❌ {result['message']}"
                    
                    yield event.plain_result(message)
                    
                except ValueError:
                    yield event.plain_result("❌ 请输入有效的金额数字")
                    
            elif len(args) >= 3 and args[1] == "取款":
                # 执行取款
                try:
                    amount = int(args[2])
                    result = self.bank_manager.withdraw(user_id, username, amount)
                    
                    if result['success']:
                        message = f"""✅ 取款成功！

💰 取款金额：{result['amount']} 金币

📊 更新后资产：
• 现金：{result['new_money']} 金币
• 银行存款：{result['new_bank_money']} 金币
• 总资产：{result['total_assets']} 金币

📋 今日取款情况：
• 今日已取款：{result['today_withdraw']} 金币
• 剩余额度：{result['remaining_limit']} 金币"""
                    else:
                        message = f"❌ {result['message']}"
                    
                    yield event.plain_result(message)
                    
                except ValueError:
                    yield event.plain_result("❌ 请输入有效的金额数字")
                    
            elif len(args) >= 4 and args[1] == "转账":
                # 执行转账
                try:
                    to_username = args[2]
                    amount = int(args[3])
                    
                    # 这里简化处理，实际应该通过用户名查找用户ID
                    # 暂时提示功能开发中
                    yield event.plain_result("🚧 转账功能开发中，敬请期待！")
                    
                except ValueError:
                    yield event.plain_result("❌ 请输入有效的金额数字")
                    
            else:
                # 显示帮助信息
                limits = self.bank_manager
                message = f"""🏦 银行使用帮助

💰 基本操作：
• {self.prefix}银行 - 查看银行信息
• {self.prefix}银行 存款 [金额] - 存入现金到银行
• {self.prefix}银行 取款 [金额] - 从银行取出现金

📋 限制说明：
• 最小存款：{limits.min_deposit} 金币
• 最大存款：{limits.max_deposit} 金币/次
• 最小取款：{limits.min_withdraw} 金币
• 最大取款：{limits.max_withdraw} 金币/次
• 每日取款限额：{limits.daily_withdraw_limit} 金币

💎 VIP特权：
• 存款达到 {limits.vip_threshold} 金币自动成为VIP
• VIP用户享受更高利率：{limits.vip_interest_rate*100:.2f}%
• 普通用户利率：{limits.interest_rate*100:.2f}%

💡 小贴士：
• 银行存款安全可靠，不会被抢劫
• 每日自动计算利息，存款越多收益越高
• 建议将大额资金存入银行获得利息"""
                
                yield event.plain_result(message)
                
        except Exception as e:
            logger.error(f"银行功能出错: {e}")
            yield event.plain_result("银行功能暂时不可用，请稍后再试")

    @filter.command("排行榜")
    async def ranking_command(self, event: AstrMessageEvent):
        """排行榜指令"""
        try:
            user_id = str(event.get_sender_id())
            username = event.get_sender_name() or f"用户{user_id}"
            
            args = event.message_str.split()
            
            # 确定排行榜类型
            ranking_type = "money"  # 默认金钱排行榜
            if len(args) > 1:
                type_map = {
                    "金钱": "money",
                    "财富": "money", 
                    "资产": "assets",
                    "总资产": "assets",
                    "收入": "earned",
                    "累计收入": "earned",
                    "等级": "level",
                    "签到": "checkin"
                }
                ranking_type = type_map.get(args[1], "money")
            
            # 获取排行榜数据
            ranking_data = self.ranking_manager.get_ranking_data(ranking_type, limit=10)
            
            if 'error' in ranking_data:
                yield event.plain_result(f"❌ {ranking_data['error']}")
                return
            
            # 生成排行榜图片
            image_path = self.ranking_manager.generate_ranking_image(ranking_data)
            
            if image_path and os.path.exists(image_path):
                yield event.image_result(image_path)
                
                # 获取用户在此排行榜中的排名
                user_rank_info = self.ranking_manager.get_user_ranking_info(user_id, ranking_type)
                
                if 'error' not in user_rank_info:
                    summary = f"""📊 {ranking_data['config']['name']} 

🏆 您的排名：第 {user_rank_info['rank']} 名 / 共 {user_rank_info['total_users']} 人

💡 其他排行榜：
• {self.prefix}排行榜 金钱 - 💰 金钱排行榜
• {self.prefix}排行榜 资产 - 💎 总资产排行榜  
• {self.prefix}排行榜 等级 - ⭐ 等级排行榜
• {self.prefix}排行榜 签到 - 📅 签到排行榜
• {self.prefix}排行榜 收入 - 💼 累计收入排行榜"""
                else:
                    summary = f"""📊 {ranking_data['config']['name']}

💡 其他排行榜：
• {self.prefix}排行榜 金钱 - 💰 金钱排行榜
• {self.prefix}排行榜 资产 - 💎 总资产排行榜  
• {self.prefix}排行榜 等级 - ⭐ 等级排行榜
• {self.prefix}排行榜 签到 - 📅 签到排行榜
• {self.prefix}排行榜 收入 - 💼 累计收入排行榜"""
                
                yield event.plain_result(summary)
            else:
                # 降级到文本输出
                text_ranking = self._format_ranking_text(ranking_data)
                yield event.plain_result(text_ranking)
                
        except Exception as e:
            logger.error(f"排行榜功能出错: {e}")
            yield event.plain_result("排行榜功能暂时不可用，请稍后再试")

    def _format_ranking_text(self, ranking_data: Dict[str, Any]) -> str:
        """格式化排行榜为文本"""
        if 'error' in ranking_data:
            return f"❌ {ranking_data['error']}"
        
        config = ranking_data['config']
        data = ranking_data['data']
        
        text = f"🏆 {config['name']}\n\n"
        
        for item in data:
            rank = item['rank']
            username = item['username']
            display_value = item['display_value']
            
            # 添加奖牌
            if rank == 1:
                medal = "🥇"
            elif rank == 2:
                medal = "🥈"
            elif rank == 3:
                medal = "🥉"
            else:
                medal = f"{rank}."
            
            text += f"{medal} {username} - {display_value}\n"
        
        text += f"\n📊 显示前 {len(data)} 名 | 总用户数: {ranking_data['total_users']}"
        text += f"\n🕐 更新时间: {ranking_data['update_time']}"
        
        return text

    @filter.command("我的排名")
    async def my_ranking_command(self, event: AstrMessageEvent):
        """查看我的排名"""
        try:
            user_id = str(event.get_sender_id())
            username = event.get_sender_name() or f"用户{user_id}"
            
            # 获取用户在各个排行榜中的排名
            rankings = {}
            for rank_type in ["money", "assets", "level", "checkin", "earned"]:
                rank_info = self.ranking_manager.get_user_ranking_info(user_id, rank_type)
                if 'error' not in rank_info:
                    rankings[rank_type] = rank_info
            
            if not rankings:
                yield event.plain_result("❌ 无法获取排名信息，请稍后再试")
                return
            
            message = f"🏆 {username} 的排名信息\n\n"
            
            rank_names = {
                "money": "💰 金钱排行",
                "assets": "💎 总资产排行", 
                "level": "⭐ 等级排行",
                "checkin": "📅 签到排行",
                "earned": "💼 累计收入排行"
            }
            
            for rank_type, rank_info in rankings.items():
                rank_name = rank_names.get(rank_type, rank_type)
                message += f"{rank_name}：第 {rank_info['rank']} 名 / {rank_info['total_users']} 人\n"
            
            message += f"\n💡 查看详细排行榜：{self.prefix}排行榜 [类型]"
            
            yield event.plain_result(message)
            
        except Exception as e:
            logger.error(f"查看排名出错: {e}")
            yield event.plain_result("获取排名信息失败，请稍后再试")

    @filter.command("服务器")
    async def server_monitor_command(self, event: AstrMessageEvent):
        """服务器监控指令"""
        try:
            # 检查是否启用了服务器监控
            if not self.enable_monitor or self.server_monitor is None:
                yield event.plain_result("❌ 服务器监控功能已禁用\n\n💡 要启用此功能，请前往：\nAstrBot 管理页面 → 插件管理 → LinBot → 配置 → 服务器监控设置")
                return
            
            args = event.message_str.split()
            
            # 如果有参数且参数是"图表"，生成CPU图表
            if len(args) > 1 and args[1] == "图表":
                yield event.plain_result(f"🔄 正在生成CPU使用率图表（{self.chart_duration}秒数据），请稍候...")
                try:
                    chart_path = self.server_monitor.generate_cpu_chart(
                        duration=self.chart_duration,
                        interval=self.monitor_interval
                    )
                    if chart_path and os.path.exists(chart_path):
                        yield event.image_result(chart_path)
                    else:
                        yield event.plain_result("❌ CPU图表生成失败")
                except Exception as e:
                    logger.error(f"生成CPU图表失败: {e}")
                    yield event.plain_result(f"❌ CPU图表生成失败: {str(e)}")
                return
            
            # 默认生成服务器监控图片
            yield event.plain_result("🔄 正在获取服务器信息，请稍候...")
            
            # 获取系统信息
            system_info = self.server_monitor.get_system_info()
            
            # 生成监控图片
            image_path = self.server_monitor.generate_monitor_image(system_info)
            
            if image_path and os.path.exists(image_path):
                yield event.image_result(image_path)
                
                # 补充一些关键信息的文本
                summary = f"""📊 服务器状态摘要：
🔥 CPU使用率：{system_info['cpu']['使用率']}
💾 内存使用率：{system_info['memory']['使用率']}
⚡ 进程总数：{system_info['process']['进程总数']}
⏱️ 运行时间：{system_info['process']['运行时间']}

💡 提示：
• 发送 "/服务器 图表" 查看CPU使用率趋势图（{self.chart_duration}秒）
• 图片包含完整的系统信息详情"""
                yield event.plain_result(summary)
            else:
                # 降级到文本信息
                text_info = self._format_system_info_text(system_info)
                yield event.plain_result(text_info)
                
        except Exception as e:
            logger.error(f"服务器监控功能出错: {e}")
            yield event.plain_result(f"❌ 服务器监控功能出现错误：{str(e)}")

    def _format_system_info_text(self, info):
        """格式化系统信息为文本格式"""
        try:
            text = f"""🖥️ 服务器监控报告
更新时间：{info['timestamp']}

📋 系统信息：
• 系统：{info['system']['系统']}
• 架构：{info['system']['架构']}
• 主机名：{info['system']['主机名']}
• 启动时间：{info['system']['启动时间']}

🔥 CPU信息：
• 使用率：{info['cpu']['使用率']}
• 物理核心：{info['cpu']['物理核心']}
• 逻辑核心：{info['cpu']['逻辑核心']}

💾 内存信息：
• 总量：{info['memory']['总量']}
• 已用：{info['memory']['已用']}
• 使用率：{info['memory']['使用率']}

⚡ 进程信息：
• 总数：{info['process']['进程总数']}
• 运行时间：{info['process']['运行时间']}

🌐 网络信息：
• 发送：{info['network']['发送字节']}
• 接收：{info['network']['接收字节']}

💿 磁盘信息："""
            
            for i, disk in enumerate(info['disk'][:3]):
                text += f"\n• {disk['设备']}: {disk['已用']}/{disk['总量']} ({disk['使用率']})"
            
            return text
            
        except Exception as e:
            return f"格式化系统信息失败: {str(e)}"

    @filter.command("抢劫")
    async def robbery_command(self, event: AstrMessageEvent):
        """抢劫指令"""
        try:
            user_id = str(event.get_sender_id())
            username = event.get_sender_name() or f"用户{user_id}"
            
            args = event.message_str.split()
            
            # 特殊处理：如果是 "/抢劫目标" 这样的单个命令，分离出 "目标" 参数
            if len(args) == 1 and args[0].endswith("目标"):
                base_command = args[0][:-2]  # 去掉最后的 "目标"
                if base_command in ["抢劫", "/抢劫"]:
                    args = [base_command, "目标"]
            
            if len(args) == 1:
                # 显示抢劫统计和目标列表
                stats = self.robbery_manager.get_robbery_stats(user_id)
                
                if 'error' in stats:
                    yield event.plain_result(f"❌ {stats['error']}")
                    return
                
                message = f"""🏴‍☠️ {stats['username']} 的抢劫信息

⚔️ 基本状态：
• 等级：{stats['level']} 级（需要 {stats['level_requirement']} 级）
• 现金：{stats['money']} 金币
• 状态：{'✅ 可以抢劫' if stats['can_rob'] else '❌ 不能抢劫'}"""

                if not stats['can_rob']:
                    if stats['level'] < stats['level_requirement']:
                        message += f"\n• 原因：等级不足"
                    elif stats['cooldown_remaining'] > 0:
                        message += f"\n• 原因：冷却中（还需 {stats['cooldown_remaining']:.1f} 小时）"

                message += f"""

📊 今日统计：
• 抢劫次数：{stats['today']['rob_count']} 次
• 被抢次数：{stats['today']['robbed_count']} 次

📈 总体统计：
• 总抢劫：{stats['overall']['total_robberies']} 次
• 成功抢劫：{stats['overall']['successful_robberies']} 次
• 成功率：{stats['overall']['rob_success_rate']:.1f}%
• 总收益：{stats['overall']['total_robbed']} 金币
• 被抢损失：{stats['overall']['total_lost']} 金币"""

                # 显示抢劫配置
                config = stats['config']
                message += f"""

🎯 抢劫规则：
• 成功率：{config['success_rate']:.1f}%
• 金额范围：{config['min_amount']}-{config['max_amount']} 金币
• 冷却时间：{config['cooldown_hours']} 小时
• 保护金额：{config['protection_amount']} 金币
• 失败惩罚：{config['failure_penalty']} 金币

💡 使用方法：
• {self.prefix}抢劫 [用户名] - 抢劫指定用户
• {self.prefix}抢劫目标 - 查看可抢劫目标"""

                # 显示最近抢劫记录
                if stats['recent_robberies']:
                    message += "\n\n📝 最近抢劫："
                    for victim_id, victim_name, amount, success, created_at in stats['recent_robberies'][:3]:
                        time_str = created_at[:16]
                        result = f"✅ +{amount}金币" if success else "❌ 失败"
                        message += f"\n• {time_str} {victim_name} {result}"

                yield event.plain_result(message)
                
            elif len(args) >= 2 and args[1] == "目标":
                # 显示抢劫目标列表
                targets = self.robbery_manager.get_robbery_targets(user_id, 10)
                
                if 'error' in targets:
                    yield event.plain_result(f"❌ {targets['error']}")
                    return
                
                if not targets['targets']:
                    yield event.plain_result("❌ 暂无可抢劫的目标")
                    return
                
                message = f"""🎯 可抢劫目标 (前10名)

💰 成功率：{targets['config']['success_rate']:.1f}%
🛡️ 保护金额：{targets['config']['protection_amount']} 金币

🏆 富豪榜："""

                for i, target in enumerate(targets['targets'][:10], 1):
                    message += f"""
{i}. {target['username']} (Lv.{target['level']})
   💰 现金：{target['money']} | 总资产：{target['total_assets']}
   🎯 可抢：{target['rob_range']} 金币"""

                message += f"\n\n💡 抢劫指令：{self.prefix}抢劫 [用户名]"

                yield event.plain_result(message)
                
            else:
                # 执行抢劫
                target_name = " ".join(args[1:])
                
                # 检查是否有At用户
                victim_id = None
                victim_name = None
                
                # 尝试从事件中获取At用户信息
                at_user_found = False
                try:
                    # 多种方式尝试获取消息数据
                    message_data = None
                    if hasattr(event, 'message'):
                        if hasattr(event.message, 'data'):
                            message_data = event.message.data
                        elif hasattr(event.message, 'message'):
                            message_data = getattr(event.message.message, 'data', None)
                    
                    if message_data:
                        # 查找At消息段
                        for segment in message_data:
                            if isinstance(segment, dict) and segment.get('type') == 'at':
                                # 尝试多种字段名
                                segment_data = segment.get('data', {})
                                at_user_id = segment_data.get('qq') or segment_data.get('user_id') or segment_data.get('target')
                                
                                if at_user_id:
                                    at_user_id = str(at_user_id)
                                    # 根据At的用户ID查找用户信息
                                    result = self._find_user_by_id(at_user_id)
                                    if result['success']:
                                        victim_id = result['user_id']
                                        victim_name = result['username']
                                        at_user_found = True
                                        break
                except Exception as e:
                    logger.error(f"解析At消息失败: {e}")
                    pass
                
                # 如果没有找到At用户，则按用户名查找
                if not at_user_found:
                    # 清理用户名中的At符号和特殊字符
                    clean_target_name = target_name.strip()
                    if clean_target_name.startswith('@'):
                        clean_target_name = clean_target_name[1:]
                    
                    # 移除可能的括号内容 (如 @用户名.(1234567890))
                    if '(' in clean_target_name:
                        clean_target_name = clean_target_name.split('(')[0].rstrip('.')
                    
                    result = self._find_user_by_name(clean_target_name)
                    if not result['success']:
                        yield event.plain_result(result['message'])
                        return
                    victim_id = result['user_id']
                    victim_name = result['username']
                
                # 执行抢劫
                rob_result = self.robbery_manager.rob_user(user_id, username, victim_id, victim_name)
                
                if rob_result['success']:
                    yield event.plain_result(rob_result['message'])
                else:
                    yield event.plain_result(rob_result['message'])
                    
        except Exception as e:
            logger.error(f"抢劫指令出错: {e}")
            yield event.plain_result("抢劫功能暂时不可用，请稍后再试")

    def _find_user_by_id(self, user_id: str) -> Dict[str, Any]:
        """根据用户ID查找用户信息"""
        try:
            import sqlite3
            
            game_db_path = os.path.join(self.plugin_dir, "game", "user.db")
            conn = sqlite3.connect(game_db_path)
            cursor = conn.cursor()
            
            # 根据用户ID查找
            cursor.execute('SELECT user_id, username FROM users WHERE user_id = ?', (user_id,))
            result = cursor.fetchone()
            
            conn.close()
            
            if result:
                return {
                    "success": True,
                    "user_id": result[0],
                    "username": result[1]
                }
            else:
                return {
                    "success": False,
                    "message": f"❌ 用户不存在（ID: {user_id}）"
                }
                
        except Exception as e:
            return {
                "success": False,
                "message": f"❌ 查找用户失败：{str(e)}"
            }

    def _find_user_by_name(self, target_name: str) -> Dict[str, Any]:
        """根据用户名查找用户ID"""
        try:
            import sqlite3
            
            game_db_path = os.path.join(self.plugin_dir, "game", "user.db")
            conn = sqlite3.connect(game_db_path)
            cursor = conn.cursor()
            
            # 精确匹配用户名
            cursor.execute('SELECT user_id, username FROM users WHERE username = ?', (target_name,))
            result = cursor.fetchone()
            
            if result:
                conn.close()
                return {
                    "success": True,
                    "user_id": result[0],
                    "username": result[1]
                }
            
            # 模糊匹配用户名
            cursor.execute('SELECT user_id, username FROM users WHERE username LIKE ?', (f'%{target_name}%',))
            results = cursor.fetchall()
            
            conn.close()
            
            if not results:
                return {
                    "success": False,
                    "message": f"❌ 未找到用户：{target_name}"
                }
            elif len(results) == 1:
                return {
                    "success": True,
                    "user_id": results[0][0],
                    "username": results[0][1]
                }
            else:
                usernames = [r[1] for r in results[:5]]
                return {
                    "success": False,
                    "message": f"❌ 找到多个匹配用户，请输入更精确的用户名：\n" + "\n".join([f"• {name}" for name in usernames])
                }
                
        except Exception as e:
            return {
                "success": False,
                "message": f"❌ 查找用户失败：{str(e)}"
            }

    async def terminate(self):
        """插件卸载时的清理方法"""
        try:
            # 清除插件数据目录
            if os.path.exists(self.data_dir):
                shutil.rmtree(self.data_dir)
                logger.info(f"已清除LinBot插件数据目录: {self.data_dir}")
            
            logger.info("LinBot 插件卸载完成")
        except Exception as e:
            logger.error(f"LinBot插件卸载时清理失败: {e}")
