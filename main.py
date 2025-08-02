#!/usr/bin/env python3
"""
Space Deployer Bot - Professional Telegram Bot Hosting System
Created by @x_ifeelram for @billaspace
"""

import asyncio
import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode
import config
from database import Database
from bot_manager import BotManager
from subscription import SubscriptionManager
from handlers import start, help_handler, space, admin, deploy
from utils.logger import setup_logger
from utils.decorators import authorized_only, subscription_required
from utils.validators import TokenValidator
import aiohttp

# Setup logging
logger = setup_logger(__name__)

class SpaceDeployerBot:
    def __init__(self):
        self.db = Database()
        self.bot_manager = BotManager()
        self.subscription_manager = SubscriptionManager(self.db)
        self.application = None
        self.logger_enabled = True
        
    async def initialize(self):
        """Initialize the bot application"""
        self.application = Application.builder().token(config.BOT_TOKEN).build()
        
        # Register handlers
        await self.register_handlers()
        
        # Initialize database
        await self.db.initialize()
        
        logger.info("Space Deployer Bot initialized successfully")
        
    async def register_handlers(self):
        """Register all command and callback handlers"""
        app = self.application
        
        # Command handlers
        app.add_handler(CommandHandler("start", self.start_command))
        app.add_handler(CommandHandler("help", self.help_command))
        app.add_handler(CommandHandler("space", self.space_command))
        app.add_handler(CommandHandler("gban", self.gban_command))
        app.add_handler(CommandHandler("ungban", self.ungban_command))
        app.add_handler(CommandHandler("logger", self.logger_command))
        app.add_handler(CommandHandler("stats", self.stats_command))
        app.add_handler(CommandHandler("subs", self.subscription_command))
        
        # File handlers
        app.add_handler(MessageHandler(filters.Document.ZIP, self.handle_bot_upload))
        app.add_handler(MessageHandler(filters.Document.ALL, self.handle_requirements_upload))
        
        # Text message handler (for tokens)
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text_messages))
        
        # Callback query handlers
        app.add_handler(CallbackQueryHandler(self.handle_callback))
        
        # Error handler
        app.add_error_handler(self.error_handler)
        
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command with beautiful interface"""
        user = update.effective_user
        
        # Check if user is banned
        if await self.db.is_user_banned(user.id):
            await update.message.reply_text(
                "🚫 **You are banned from using this bot!**\n\n"
                "Contact @x_ifeelram if you think this is a mistake.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
            
        # Register user
        await self.db.register_user(user.id, user.username, user.first_name)
        
        # Welcome message with inline buttons
        welcome_text = f"""
🚀 **Welcome to Space Deployer Bot** 🚀

Hello {user.first_name}! I'm your professional bot hosting solution.

✨ **What I can do:**
• 🤖 Host multiple Telegram bots
• 📦 Auto-deploy from ZIP files
• 🔄 Start/Stop/Restart bots
• 📊 Real-time monitoring
• 💎 Subscription management

🌟 **Get Started:**
Use the buttons below or type /space to access the hosting menu.

**Updates:** @billaspace
**Support:** @billacore
**Developer:** @x_ifeelram
        """
        
        keyboard = [
            [
                InlineKeyboardButton("🚀 Deploy Bot", callback_data="deploy_menu"),
                InlineKeyboardButton("📱 My Bots", callback_data="my_bots")
            ],
            [
                InlineKeyboardButton("💎 Subscription", callback_data="subscription"),
                InlineKeyboardButton("📊 Statistics", callback_data="statistics")
            ],
            [
                InlineKeyboardButton("❓ Help", callback_data="help"),
                InlineKeyboardButton("🔧 Commands", callback_data="commands")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Send welcome image with message
        try:
            with open("static/welcome.jpg", "rb") as photo:
                await update.message.reply_photo(
                    photo=photo,
                    caption=welcome_text,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=reply_markup
                )
        except FileNotFoundError:
            await update.message.reply_text(
                welcome_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
            
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = """
📖 **Space Deployer Bot Help**

**Basic Commands:**
• `/start` - Start the bot and see main menu
• `/help` - Show this help message
• `/space` - Access bot hosting menu
• `/stats` - View your statistics

**Bot Management:**
• Upload a ZIP file to deploy a bot
• Use inline buttons to manage your bots
• Share requirements.txt for custom dependencies

**Subscription:**
• Contact @x_ifeelram for premium access
• Weekly, Monthly, or Bi-monthly plans available

**Support:**
• Updates: @billaspace
• Support Chat: @billacore
• Developer: @x_ifeelram

**Admin Commands:** (Authorized users only)
• `/gban <user_id>` - Globally ban user
• `/ungban <user_id>` - Remove global ban
• `/logger on/off` - Toggle logging

Need more help? Join @billacore!
        """
        
        keyboard = [
            [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")],
            [InlineKeyboardButton("🚀 Deploy Now", callback_data="deploy_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            help_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )

      async def space_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /space command - Host menu"""
        user_id = update.effective_user.id
        
        if await self.db.is_user_banned(user_id):
            await update.message.reply_text("🚫 You are banned from using this bot!")
            return
            
        user_bots = await self.db.get_user_bots(user_id)
        subscription = await self.subscription_manager.get_user_subscription(user_id)
        
        menu_text = f"""
🚀 **Space Hosting Menu**

**Your Status:** {'💎 Premium' if subscription and subscription['active'] else '🆓 Free'}
**Active Bots:** {len(user_bots)}/{'∞' if subscription and subscription['active'] else '1'}

**Quick Actions:**
        """
        
        keyboard = [
            [
                InlineKeyboardButton("📦 Deploy New Bot", callback_data="deploy_new"),
                InlineKeyboardButton("📱 Manage Bots", callback_data="manage_bots")
            ],
            [
                InlineKeyboardButton("📊 Bot Statistics", callback_data="bot_stats"),
                InlineKeyboardButton("🔄 Refresh Status", callback_data="refresh_status")
            ],
            [
                InlineKeyboardButton("💎 Upgrade Plan", callback_data="upgrade_plan"),
                InlineKeyboardButton("📞 Support", url="https://t.me/billacore")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            menu_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )

    async def handle_text_messages(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages (for token input)"""
        user_id = update.effective_user.id
        text = update.message.text.strip()
        
        # Check if user is waiting for token input
        if 'waiting_for_token' in context.user_data:
            await self.process_bot_token(update, context)
            return
            
        # Check if this looks like a bot token
        if TokenValidator.looks_like_token(text):
            if 'waiting_for_token' not in context.user_data:
                await update.message.reply_text(
                    "🔑 **Bot Token Detected**\n\n"
                    "To configure a bot token, please:\n"
                    "1. Deploy a bot first\n"
                    "2. Use the 'Configure Token' button\n\n"
                    "For security, I'm deleting this message.",
                    parse_mode=ParseMode.MARKDOWN
                )
                # Delete the token message for security
                try:
                    await update.message.delete()
                except:
                    pass
            return
            
        # Default response for unrecognized text
        await update.message.reply_text(
            "🤖 I didn't understand that command.\n\n"
            "Use /start to see the main menu or /help for assistance!"
        )

    async def process_bot_token(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Process received bot token"""
        if 'waiting_for_token' not in context.user_data:
            return
            
        bot_id = context.user_data['waiting_for_token']
        token = update.message.text.strip()
        user_id = update.effective_user.id
        
        # Validate token format
        validation = TokenValidator.validate_token_format(token)
        
        if not validation['valid']:
            await update.message.reply_text(
                f"❌ **Invalid Token Format**\n\n{validation['error']}\n\nPlease send a valid bot token.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
            
        # Test token by getting bot info
        token_test = await self.test_bot_token(token)
        
        if not token_test['valid']:
            await update.message.reply_text(
                f"❌ **Token Test Failed**\n\n{token_test['error']}\n\nPlease check your token and try again.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
            
        # Store token (plain text as requested by owner)
        await self.db.store_bot_token(user_id, bot_id, token, token_test['bot_info'])
        
        # Clear waiting state
        del context.user_data['waiting_for_token']
        
        # Delete the token message for security
        try:
            await update.message.delete()
        except:
            pass
            
        # Show success message
        bot_info = token_test['bot_info']
        success_text = f"""
✅ **Bot Token Configured Successfully!**

**Bot Information:**
🤖 **Name:** {bot_info['first_name']}
👤 **Username:** @{bot_info.get('username', 'Not set')}
🆔 **Bot ID:** `{bot_info['id']}`

**Security:**
• Token stored securely
• Ready for deployment

**Next Steps:**
Your bot is now ready to start!
        """
        
        keyboard = [
            [
                InlineKeyboardButton("▶️ Start Bot", callback_data=f"start_bot_{bot_id}"),
                InlineKeyboardButton("⚙️ Configure", callback_data=f"config_bot_{bot_id}")
            ],
            [
                InlineKeyboardButton("📊 View Details", callback_data=f"bot_details_{bot_id}"),
                InlineKeyboardButton("📱 My Bots", callback_data="my_bots")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            success_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )

    async def test_bot_token(self, token: str) -> dict:
        """Test bot token by calling Telegram API"""
        try:
            url = f"https://api.telegram.org/bot{token}/getMe"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('ok'):
                            return {
                                'valid': True,
                                'bot_info': data['result']
                            }
                        else:
                            return {
                                'valid': False,
                                'error': f"Telegram API error: {data.get('description', 'Unknown error')}"
                            }
                    else:
                        return {
                            'valid': False,
                            'error': f"HTTP error: {response.status}"
                        }
                        
        except Exception as e:
            return {
                'valid': False,
                'error': f"Connection error: {str(e)}"
            }

    # Continue with other methods...
    async def run(self):
        """Run the bot"""
        await self.initialize()
        
        logger.info("Starting Space Deployer Bot...")
        await self.application.run_polling(drop_pending_updates=True)

# Run the bot
if __name__ == "__main__":
    bot = SpaceDeployerBot()
    asyncio.run(bot.run())
