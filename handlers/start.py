from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
import config

class StartHandler:
    def __init__(self, db, subscription_manager):
        self.db = db
        self.subscription_manager = subscription_manager
        
    async def handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Enhanced start command handler"""
        user = update.effective_user
        
        # Check if user is banned
        if await self.db.is_user_banned(user.id):
            await self.send_banned_message(update, context)
            return
            
        # Register/update user
        await self.db.register_user(user.id, user.username, user.first_name)
        
        # Get user stats
        user_bots = await self.db.get_user_bots(user.id)
        subscription = await self.subscription_manager.get_user_subscription(user.id)
        
        # Create personalized welcome message
        welcome_text = self.generate_welcome_message(user, user_bots, subscription)
        
        # Create dynamic keyboard
        keyboard = self.create_welcome_keyboard(subscription, len(user_bots))
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Send welcome with image
        await self.send_welcome_message(update, welcome_text, reply_markup)
        
    def generate_welcome_message(self, user, user_bots, subscription):
        """Generate personalized welcome message"""
        status_emoji = "💎" if subscription and subscription['active'] else "🆓"
        status_text = "Premium" if subscription and subscription['active'] else "Free"
        
        return f"""
🚀 **Welcome to Space Deployer Bot** 🚀

Hello **{user.first_name}**! Ready to deploy some amazing bots?

**Your Dashboard:**
{status_emoji} **Status:** {status_text} User
🤖 **Active Bots:** {len([b for b in user_bots if b.get('status') == 'running'])}/{len(user_bots)}
📊 **Total Deployments:** {len(user_bots)}

**🌟 What's New:**
• Advanced monitoring system
• Multi-language support
• Module-based Python bot support
• Real-time performance metrics

**💡 Quick Tips:**
• Upload a ZIP file to deploy instantly
• Use /space for quick bot management
• Premium users get unlimited deployments

**Need Help?** Check out our comprehensive guide below!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
**Updates:** {config.UPDATES_CHANNEL} | **Support:** {config.SUPPORT_CHAT}
**Developer:** {config.DEVELOPER}
        """
        
    def create_welcome_keyboard(self, subscription, bot_count):
        """Create dynamic welcome keyboard"""
        keyboard = []
        
        # First row - Primary actions
        if subscription and subscription['active']:
            keyboard.append([
                InlineKeyboardButton("🚀 Deploy Bot", callback_data="deploy_menu"),
                InlineKeyboardButton("📱 My Bots", callback_data="my_bots")
            ])
        else:
            if bot_count < config.MAX_BOTS_FREE:
                keyboard.append([
                    InlineKeyboardButton("🚀 Deploy Bot", callback_data="deploy_menu"),
                    InlineKeyboardButton("📱 My Bots", callback_data="my_bots")
                ])
            else:
                keyboard.append([
                    InlineKeyboardButton("💎 Upgrade to Deploy", callback_data="subscription"),
                    InlineKeyboardButton("📱 My Bots", callback_data="my_bots")
                ])
        
        # Second row - Management
        keyboard.append([
            InlineKeyboardButton("📊 Statistics", callback_data="statistics"),
            InlineKeyboardButton("⚙️ Settings", callback_data="settings")
        ])
        
        # Third row - Information
        keyboard.append([
            InlineKeyboardButton("❓ Help & Guide", callback_data="help"),
            InlineKeyboardButton("🔧 Commands", callback_data="commands")
        ])
        
        # Fourth row - External links
        keyboard.append([
            InlineKeyboardButton("📢 Updates", url=f"https://t.me/{config.UPDATES_CHANNEL[1:]}"),
            InlineKeyboardButton("💬 Support", url=f"https://t.me/{config.SUPPORT_CHAT[1:]}")
        ])
        
        return keyboard
        
    async def send_welcome_message(self, update, text, reply_markup):
        """Send welcome message with image"""
        try:
            # Try to send with image first
            with open("static/welcome.jpg", "rb") as photo:
                await update.message.reply_photo(
                    photo=photo,
                    caption=text,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=reply_markup
                )
        except FileNotFoundError:
            # Fallback to text message
            await update.message.reply_text(
                text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
        except Exception as e:
            # Last resort - simple text
            await update.message.reply_text(
                "🚀 **Welcome to Space Deployer Bot!**\n\n"
                "Your professional bot hosting solution is ready!\n"
                "Use the buttons below to get started.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
            
    async def send_banned_message(self, update, context):
        """Send message to banned users"""
        ban_text = """
🚫 **Access Denied**

Your account has been restricted from using Space Deployer Bot.

**Reason:** Violation of terms of service

**Appeal Process:**
If you believe this is a mistake, please contact:
👤 **Developer:** @x_ifeelram

**Note:** All your deployed bots have been stopped and will remain inaccessible until the restriction is lifted.
        """
        
        keyboard = [
            [InlineKeyboardButton("📞 Contact Developer", url="https://t.me/x_ifeelram")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            ban_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
  )
