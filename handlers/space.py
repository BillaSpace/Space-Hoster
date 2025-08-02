from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
import config

class SpaceHandler:
    def __init__(self, db, bot_manager, subscription_manager):
        self.db = db
        self.bot_manager = bot_manager
        self.subscription_manager = subscription_manager
        
    async def handle_space_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Enhanced /space command handler"""
        user_id = update.effective_user.id
        
        if await self.db.is_user_banned(user_id):
            await self.send_banned_message(update)
            return
            
        # Get user data
        user_bots = await self.db.get_user_bots(user_id)
        subscription = await self.subscription_manager.get_user_subscription(user_id)
        
        # Generate space menu
        menu_text = await self.generate_space_menu_text(user_id, user_bots, subscription)
        keyboard = await self.create_space_keyboard(user_bots, subscription)
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.callback_query:
            await update.callback_query.edit_message_text(
                menu_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(
                menu_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
            
    async def generate_space_menu_text(self, user_id, user_bots, subscription):
        """Generate comprehensive space menu text"""
        # Calculate statistics
        running_bots = [bot for bot in user_bots if bot.get('status') == 'running']
        stopped_bots = [bot for bot in user_bots if bot.get('status') == 'stopped']
        error_bots = [bot for bot in user_bots if bot.get('status') == 'error']
        
        # Subscription info
        is_premium = subscription and subscription['active']
        plan_name = subscription['plan'].title() if is_premium else 'Free'
        max_bots = '∞' if is_premium else str(config.MAX_BOTS_FREE)
        
        return f"""
🚀 **Space Hosting Control Center**

**Account Overview:**
• 👤 User ID: `{user_id}`
• 💎 Plan: {plan_name}
• 🤖 Bots: {len(user_bots)}/{max_bots}
{f"• ⏰ Expires: {subscription['expires_at'].strftime('%b %d, %Y')}" if is_premium else ""}

**Bot Status Summary:**
• 🟢 Running: {len(running_bots)}
• 🔴 Stopped: {len(stopped_bots)}
• 🟠 Error: {len(error_bots)}

**Quick Actions:**
Use the buttons below for instant bot management.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
**Last Updated:** {self.get_current_time()}
        """
        
    async def create_space_keyboard(self, user_bots, subscription):
        """Create dynamic space management keyboard"""
        keyboard = []
        
        is_premium = subscription and subscription['active']
        can_deploy = len(user_bots) < config.MAX_BOTS_FREE or is_premium
        
        # First row - Primary actions
        if can_deploy:
            keyboard.append([
                InlineKeyboardButton("🚀 Deploy New Bot", callback_data="deploy_new"),
                InlineKeyboardButton("📦 Quick Deploy", callback_data="quick_deploy")
            ])
        else:
            keyboard.append([
                InlineKeyboardButton("💎 Upgrade to Deploy", callback_data="upgrade_subscription"),
                InlineKeyboardButton("📱 Manage Existing", callback_data="manage_bots")
            ])
            
        # Second row - Bot management
        if user_bots:
            keyboard.append([
                InlineKeyboardButton("📱 All Bots", callback_data="show_all_bots"),
                InlineKeyboardButton("🟢 Running Bots", callback_data="show_running_bots")
            ])
            
            keyboard.append([
                InlineKeyboardButton("▶️ Start All", callback_data="start_all_bots"),
                InlineKeyboardButton("⏹️ Stop All", callback_data="stop_all_bots")
            ])
        
        # Third row - Monitoring and tools
        keyboard.append([
            InlineKeyboardButton("📊 Performance", callback_data="performance_dashboard"),
            InlineKeyboardButton("📋 Activity Logs", callback_data="activity_logs")
        ])
        
        # Bottom row - Navigation
        keyboard.append([
            InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu"),
            InlineKeyboardButton("❓ Help", callback_data="help")
        ])
        
        return keyboard
        
    def get_current_time(self):
        """Get current formatted time"""
        from datetime import datetime
        return datetime.now().strftime("%H:%M UTC")
        
    async def send_banned_message(self, update):
        """Send message for banned users"""
        await update.message.reply_text(
            "🚫 **Access Restricted**\n\n"
            "Your account has been restricted from using Space Deployer Bot.\n"
            "Contact @x_ifeelram for Mercy.",
            parse_mode=ParseMode.MARKDOWN
        )
