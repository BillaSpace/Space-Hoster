from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
import os
import tempfile
import asyncio
from utils.validators import BotValidator, TokenValidator
from utils.decorators import subscription_required

class DeployHandler:
    def __init__(self, db, bot_manager, subscription_manager):
        self.db = db
        self.bot_manager = bot_manager
        self.subscription_manager = subscription_manager
        
    async def handle_deployment_process(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the complete deployment process"""
        user_id = update.effective_user.id
        
        # Check if user can deploy
        can_deploy = await self.subscription_manager.check_deployment_limit(user_id)
        
        if not can_deploy:
            await self.send_upgrade_message(update)
            return
            
        # Check if file is uploaded
        if not update.message.document:
            await self.send_upload_instructions(update)
            return
            
        # Process the uploaded file
        await self.process_bot_upload(update, context)
        
    async def process_bot_upload(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Process uploaded bot file"""
        document = update.message.document
        user_id = update.effective_user.id
        
        # Validate file
        validation_result = await self.validate_upload(document)
        if not validation_result['valid']:
            await update.message.reply_text(
                f"❌ **Upload Validation Failed**\n\n{validation_result['error']}",
                parse_mode=ParseMode.MARKDOWN
            )
            return
            
        # Show upload progress
        progress_msg = await update.message.reply_text(
            "📥 **Uploading Bot Files...**\n\n⏳ Please wait while we process your bot.",
            parse_mode=ParseMode.MARKDOWN
        )
        
        try:
            # Download file
            file_path = await self.download_file(document, context, user_id)
            
            # Update progress
            await progress_msg.edit_text(
                "🔍 **Analyzing Bot Structure...**\n\n⏳ Detecting bot type and dependencies.",
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Deploy bot
            deployment_result = await self.bot_manager.deploy_bot(user_id, file_path)
            
            if deployment_result['success']:
                await self.send_deployment_success(progress_msg, deployment_result)
            else:
                await self.send_deployment_error(progress_msg, deployment_result)
                
        except Exception as e:
            await progress_msg.edit_text(
                f"❌ **Unexpected Error**\n\nError: {str(e)}\n\nPlease try again or contact support.",
                parse_mode=ParseMode.MARKDOWN
            )
            
    async def validate_upload(self, document):
        """Validate uploaded file"""
        # Check file size
        if document.file_size > 100 * 1024 * 1024:  # 100MB limit
            return {
                'valid': False,
                'error': 'File too large. Maximum size is 100MB.'
            }
            
        # Check file type
        if not document.file_name.endswith('.zip'):
            return {
                'valid': False,
                'error': 'Only ZIP files are supported. Please compress your bot files into a ZIP archive.'
            }
            
        return {'valid': True}
        
    async def download_file(self, document, context, user_id):
        """Download file to temporary location"""
        file = await context.bot.get_file(document.file_id)
        
        # Create temporary file
        temp_dir = tempfile.mkdtemp()
        file_path = os.path.join(temp_dir, document.file_name)
        
        # Download
        await file.download_to_drive(file_path)
        
        return file_path
        
    async def send_deployment_success(self, message, deployment_result):
        """Send deployment success message with token request"""
        bot_id = deployment_result['bot_id']
        analysis = deployment_result.get('analysis', {})
        
        # Format start method info
        start_info = ""
        start_method = analysis.get('start_method', 'direct')
        if start_method == 'bash_script':
            script_name = analysis.get('start_script', 'unknown')
            start_info = f"🔧 **Start Method:** Bash Script (`{script_name}`)\n"
            if analysis.get('module_name'):
                start_info += f"📦 **Module:** {analysis['module_name']}\n"
        elif start_method == 'module':
            module_name = analysis.get('module_name', 'unknown')
            start_info = f"🔧 **Start Method:** Python Module\n📦 **Module:** `python -m {module_name}`\n"
        elif start_method == 'direct':
            main_file = analysis.get('main_file', 'unknown')
            start_info = f"🔧 **Start Method:** Direct Execution\n📄 **Main File:** {main_file}\n"
        
        success_text = f"""
✅ **Bot Code Deployed Successfully!**

**Deployment Information:**
🤖 **Bot ID:** `{bot_id}`
🐍 **Type:** {deployment_result.get('bot_type', 'unknown').title()}
{start_info}
**Dependencies:** {len(analysis.get('dependencies', []))} installed

**⚠️ Important: Bot Token Required**

Your bot code has been deployed, but you need to provide a Telegram Bot Token for it to function.

**What's Next:**
1. Get a bot token from @BotFather
2. Send the token to configure your bot
3. Start your bot

**Ready to configure your bot token?**
        """
        
        keyboard = [
            [
                InlineKeyboardButton("🔑 Configure Token", callback_data=f"configure_token_{bot_id}"),
                InlineKeyboardButton("❓ How to get token?", callback_data="token_help")
            ],
            [
                InlineKeyboardButton("📊 View Details", callback_data=f"bot_details_{bot_id}"),
                InlineKeyboardButton("🗑️ Delete Bot", callback_data=f"delete_bot_{bot_id}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await message.edit_text(
            success_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
        
    async def send_deployment_error(self, message, deployment_result):
        """Send deployment error message"""
        error_text = f"""
❌ **Deployment Failed**

**Error Details:**
{deployment_result['error']}

**Common Solutions:**
• Ensure your ZIP file contains all necessary files
• Check that requirements.txt or package.json is valid
• Verify your bot code doesn't have syntax errors
• Make sure file size is under 100MB

**Need Help?**
• Check our troubleshooting guide: /help
• Join support chat: @billacore  
• Contact developer: @x_ifeelram
        """
        
        keyboard = [
            [
                InlineKeyboardButton("🔄 Try Again", callback_data="deploy_menu"),
                InlineKeyboardButton("❓ Get Help", callback_data="help")
            ],
            [InlineKeyboardButton("📞 Support Chat", url="https://t.me/billacore")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await message.edit_text(
            error_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
        
    async def handle_token_collection(self, update, context, bot_id):
        """Handle bot token collection after deployment"""
        token_text = """
🔑 **Bot Token Required**

Your bot has been deployed successfully, but it needs a Telegram Bot Token to function.

**How to get a Bot Token:**
1. Message @BotFather on Telegram
2. Send `/newbot` command
3. Follow the instructions to create your bot
4. Copy the token (format: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

**Security Note:**
• Your token will be stored securely
• Only you can access your bot's token
• Tokens are never shared or logged

**Send your bot token now:**
        """
        
        keyboard = [
            [
                InlineKeyboardButton("❓ How to get token?", callback_data="token_help"),
                InlineKeyboardButton("❌ Cancel", callback_data=f"delete_bot_{bot_id}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Store that we're waiting for token
        context.user_data['waiting_for_token'] = bot_id
        
        if update.callback_query:
            await update.callback_query.edit_message_text(
                token_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(
                token_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
            
    async def send_upgrade_message(self, update):
        """Send upgrade message for users who hit limits"""
        upgrade_text = """
💎 **Upgrade Required**

You've reached the deployment limit for free users.

**Free Plan Limits:**
• 1 bot deployment
• Basic support
• Standard resources

**Premium Benefits:**
• ♾️ Unlimited deployments
• 🚀 Priority support  
• 💾 Enhanced resources
• 📊 Advanced monitoring
• 🔧 Custom configurations

**Ready to upgrade?** Contact our developer to unlock premium features!
        """
        
        keyboard = [
            [
                InlineKeyboardButton("💎 Upgrade Now", url="https://t.me/x_ifeelram"),
                InlineKeyboardButton("📞 Support", url="https://t.me/billacore")
            ],
            [InlineKeyboardButton("📱 Manage Existing Bots", callback_data="my_bots")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            upgrade_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
        
    async def send_upload_instructions(self, update):
        """Send detailed upload instructions"""
        instructions_text = """
📦 **How to Deploy Your Bot**

**Step 1: Prepare Your Files**
Create a ZIP file containing:
• Your bot's source code
• requirements.txt (Python) or package.json (Node.js)
• Configuration files (.env, config files)
• Any additional assets

**Step 2: Upload**
Simply send the ZIP file to this chat!

**Supported Bot Types:**
🐍 **Python** - Include requirements.txt
📦 **Node.js** - Include package.json  
☕ **Java** - JAR files or Maven projects
⚡ **Cloudflare Workers** - Include wrangler.toml

**Python Module Support:**
✅ Direct execution: `python main.py`
✅ Module execution: `python -m ModuleName`
✅ Script execution: `./start.sh` or `./start`

**File Requirements:**
• Maximum size: 100MB
• Format: ZIP only
• Include main executable file


**Ready?** Upload your ZIP file now!
        """
        
        keyboard = [
            [
                InlineKeyboardButton("📋 View Examples", callback_data="deployment_examples"),
                InlineKeyboardButton("❓ Need Help?", callback_data="help")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            instructions_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        
        )
