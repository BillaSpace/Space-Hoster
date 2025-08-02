from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

class HelpHandler:
    def __init__(self, db):
        self.db = db
        
    async def handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comprehensive help system"""
        help_sections = {
            "getting_started": "🚀 Getting Started",
            "deployment": "📦 Bot Deployment", 
            "management": "⚙️ Bot Management",
            "subscription": "💎 Subscription Plans",
            "troubleshooting": "🔧 Troubleshooting",
            "advanced": "🎯 Advanced Features"
        }
        
        main_help_text = """
📖 **Space Deployer Bot - Complete Guide**

Welcome to the most comprehensive bot hosting platform! Here's everything you need to know:

**📋 Quick Navigation:**
Choose a topic below to get detailed information.

**🆘 Need Immediate Help?**
• Join our support chat: @billacore
• Contact developer: @x_ifeelram
• Check updates: @billaspace

**💡 Pro Tip:** Use /space for quick bot management!
        """
        
        keyboard = []
        for key, title in help_sections.items():
            keyboard.append([InlineKeyboardButton(title, callback_data=f"help_{key}")])
            
        keyboard.extend([
            [
                InlineKeyboardButton("📋 Command List", callback_data="help_commands"),
                InlineKeyboardButton("🔄 Refresh", callback_data="help_main")
            ],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.callback_query:
            await update.callback_query.edit_message_text(
                main_help_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(
                main_help_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )

    async def show_token_help(self, update, context):
        """Show detailed token help"""
        help_text = """
🔑 **How to Get a Telegram Bot Token**

**Step-by-Step Guide:**

**1. Contact BotFather**
• Open Telegram and search for @BotFather
• Start a conversation with BotFather

**2. Create New Bot**
• Send `/newbot` command
• Choose a name for your bot (e.g., "My Awesome Bot")
• Choose a username ending in 'bot' (e.g., "myawesomebot")

**3. Get Your Token**
• BotFather will send you a token
• It looks like: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`
• Copy this token completely

**4. Send Token Here**
• Paste the token in this chat
• We'll store it securely

**⚠️ Security Tips:**
• Never share your bot token publicly
• Your token gives full control over your bot
• We store all tokens securely

**Token Format Example:**
`1234567890:ABCdefGHIjklMNOpqrsTUVwxyz123456`

Ready to send your token?
        """
        
        keyboard = [
            [InlineKeyboardButton("🔙 Back", callback_data="deploy_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            help_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
