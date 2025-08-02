from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
import config
from utils.decorators import authorized_only

class AdminHandler:
    def __init__(self, db, bot_manager, subscription_manager):
        self.db = db
        self.bot_manager = bot_manager
        self.subscription_manager = subscription_manager
        
    @authorized_only
    async def handle_admin_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Main admin control panel"""
        stats = await self.db.get_total_stats()
        
        admin_text = f"""
🛡️ **Admin Control Panel**

**Platform Statistics:**
• 👥 Total Users: {stats['total_users']:,}
• 🤖 Total Bots: {stats['total_bots']:,}
• 🟢 Active Bots: {stats['active_bots']:,}
• 💎 Premium Users: {stats['premium_users']:,}

**System Status:**
• 🔋 Server Health: 🟢 Healthy
• 💾 Storage Usage: {await self.get_storage_usage()}%
• 🔄 Uptime: {await self.get_system_uptime()}

**Quick Actions:**
Use the buttons below for administrative tasks.
        """
        
        keyboard = [
            [
                InlineKeyboardButton("👥 User Management", callback_data="admin_users"),
                InlineKeyboardButton("🤖 Bot Management", callback_data="admin_bots")
            ],
            [
                InlineKeyboardButton("💎 Subscriptions", callback_data="admin_subscriptions"),
                InlineKeyboardButton("📊 Analytics", callback_data="admin_analytics")
            ],
            [
                InlineKeyboardButton("⚙️ System Settings", callback_data="admin_settings"),
                InlineKeyboardButton("📋 Logs", callback_data="admin_logs")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            admin_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
        
    async def get_storage_usage(self):
        """Get current storage usage percentage"""
        import shutil
        try:
            total, used, free = shutil.disk_usage("/")
            return round((used / total) * 100, 1)
        except:
            return "N/A"
            
    async def get_system_uptime(self):
        """Get system uptime"""
        try:
            with open('/proc/uptime', 'r') as f:
                uptime_seconds = float(f.readline().split()[0])
                
            days = int(uptime_seconds // 86400)
            hours = int((uptime_seconds % 86400) // 3600)
            minutes = int((uptime_seconds % 3600) // 60)
            
            return f"{days}d {hours}h {minutes}m"
        except:
            return "N/A"
