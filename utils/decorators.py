from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes
import config

def authorized_only(func):
    """Decorator to restrict access to authorized users only"""
    @wraps(func)
    async def wrapper(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        
        if user_id not in [config.OWNER_ID, config.DEV_ID] + config.ADMIN_IDS:
            await update.message.reply_text("❌ You are not authorized to use this command.")
            return
            
        return await func(self, update, context)
    return wrapper

def subscription_required(func):
    """Decorator to check subscription requirements for deployments"""
    @wraps(func)
    async def wrapper(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        
        # Check deployment limit
        can_deploy = await self.subscription_manager.check_deployment_limit(user_id)
        
        if not can_deploy:
            await update.message.reply_text(
                "❌ **Deployment Limit Reached**\n\n"
                "Free users can only deploy 1 bot.\n"
                "Contact @x_ifeelram for premium access!",
                parse_mode="Markdown"
            )
            return
            
        return await func(self, update, context)
    return wrapper

def banned_check(func):
    """Decorator to check if user is banned"""
    @wraps(func)
    async def wrapper(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        
        if await self.db.is_user_banned(user_id):
            await update.message.reply_text(
                "🚫 **You are banned from using this bot!**\n\n"
                "Contact @x_ifeelram if you think this is a mistake.",
                parse_mode="Markdown"
            )
            return
            
        return await func(self, update, context)
    return wrapper

def admin_required(func):
    """Decorator for admin-only commands"""
    @wraps(func)
    async def wrapper(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        
        if user_id != config.OWNER_ID and user_id not in config.ADMIN_IDS:
            await update.message.reply_text("❌ Admin access required.")
            return
            
        return await func(self, update, context)
    return wrapper

def owner_only(func):
    """Decorator for owner-only commands"""
    @wraps(func)
    async def wrapper(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        
        if user_id != config.OWNER_ID:
            await update.message.reply_text("❌ Owner access required.")
            return
            
        return await func(self, update, context)
    return wrapper
