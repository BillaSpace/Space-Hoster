from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes
import config

def authorized_only(func):
    @wraps(func)
    async def wrapper(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        uid = update.effective_user.id
        if uid not in [config.OWNER_ID, config.DEV_ID] + config.ADMIN_IDS:
            await update.message.reply_text("❌ You are not authorized.")
            return
        return await func(self, update, context)
    return wrapper
