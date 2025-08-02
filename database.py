import asyncio
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
import config

class Database:
    def __init__(self):
        self.client = None
        self.db = None
        
    async def initialize(self):
        """Initialize database connection"""
        self.client = AsyncIOMotorClient(config.MONGODB_URI)
        self.db = self.client[config.DATABASE_NAME]
        
        # Create indexes
        await self.create_indexes()
        
    async def create_indexes(self):
        """Create database indexes"""
        # Users collection
        await self.db.users.create_index("user_id", unique=True)
        await self.db.users.create_index("username")
        
        # Bots collection
        await self.db.bots.create_index("user_id")
        await self.db.bots.create_index("bot_id", unique=True)
        
        # Subscriptions collection
        await self.db.subscriptions.create_index("user_id", unique=True)
        
        # Bans collection
        await self.db.bans.create_index("user_id", unique=True)
        
    async def register_user(self, user_id: int, username: str, first_name: str):
        """Register a new user"""
        user_data = {
            "user_id": user_id,
            "username": username,
            "first_name": first_name,
            "created_at": datetime.utcnow(),
            "last_active": datetime.utcnow(),
            "total_bots": 0,
            "active_bots": 0
        }
        
        await self.db.users.update_one(
            {"user_id": user_id},
            {"$setOnInsert": user_data},
            upsert=True
        )
        
    async def get_user(self, user_id: int):
        """Get user information"""
        return await self.db.users.find_one({"user_id": user_id})
        
    async def update_user_activity(self, user_id: int):
        """Update user's last activity"""
        await self.db.users.update_one(
            {"user_id": user_id},
            {"$set": {"last_active": datetime.utcnow()}}
        )
        
    async def ban_user(self, user_id: int, reason: str):
        """Ban a user"""
        ban_data = {
            "user_id": user_id,
            "reason": reason,
            "banned_at": datetime.utcnow(),
            "banned_by": "system"
        }
        
        await self.db.bans.update_one(
            {"user_id": user_id},
            {"$set": ban_data},
            upsert=True
        )
        
    async def unban_user(self, user_id: int):
        """Unban a user"""
        await self.db.bans.delete_one({"user_id": user_id})
        
    async def is_user_banned(self, user_id: int) -> bool:
        """Check if user is banned"""
        ban = await self.db.bans.find_one({"user_id": user_id})
        return ban is not None
        
    async def create_bot(self, user_id: int, bot_data: dict):
        """Create a new bot entry"""
        bot_data.update({
            "user_id": user_id,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "status": "created",
            "cpu_usage": 0,
            "memory_usage": 0,
            "uptime": "0s"
        })
        
        result = await self.db.bots.insert_one(bot_data)
        
        # Update user bot count
        await self.db.users.update_one(
            {"user_id": user_id},
            {"$inc": {"total_bots": 1}}
        )
        
        return str(result.inserted_id)
        
    async def get_user_bots(self, user_id: int):
        """Get all bots for a user"""
        cursor = self.db.bots.find({"user_id": user_id})
        return await cursor.to_list(length=None)
        
    async def get_bot_info(self, user_id: int, bot_id: str):
        """Get specific bot information"""
        return await self.db.bots.find_one({
            "user_id": user_id,
            "bot_id": bot_id
        })
        
    async def update_bot_status(self, user_id: int, bot_id: str, status: str):
        """Update bot status"""
        await self.db.bots.update_one(
            {"user_id": user_id, "bot_id": bot_id},
            {
                "$set": {
                    "status": status,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
    async def delete_bot(self, user_id: int, bot_id: str):
        """Delete a bot"""
        result = await self.db.bots.delete_one({
            "user_id": user_id,
            "bot_id": bot_id
        })
        
        if result.deleted_count > 0:
            # Update user bot count
            await self.db.users.update_one(
                {"user_id": user_id},
                {"$inc": {"total_bots": -1}}
            )
            
        return result.deleted_count > 0
        
    async def store_bot_token(self, user_id: int, bot_id: str, token: str, bot_info: dict):
        """Store bot token (plain text as per owner's request)"""
        await self.db.bots.update_one(
            {"user_id": user_id, "bot_id": bot_id},
            {
                "$set": {
                    "bot_token": token,
                    "bot_username": bot_info.get('username'),
                    "bot_name": bot_info['first_name'],
                    "telegram_bot_id": bot_info['id'],
                    "token_configured": True,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
    async def store_user_requirements(self, user_id: int, requirements: str):
        """Store user's requirements.txt"""
        await self.db.users.update_one(
            {"user_id": user_id},
            {"$set": {"custom_requirements": requirements}}
        )
        
    async def get_user_requirements(self, user_id: int):
        """Get user's custom requirements"""
        user = await self.db.users.find_one({"user_id": user_id})
        return user.get("custom_requirements", "") if user else ""
        
    async def get_total_stats(self):
        """Get total platform statistics"""
        total_users = await self.db.users.count_documents({})
        total_bots = await self.db.bots.count_documents({})
        active_bots = await self.db.bots.count_documents({"status": "running"})
        premium_users = await self.db.subscriptions.count_documents({"active": True})
        
        return {
            "total_users": total_users,
            "total_bots": total_bots,
            "active_bots": active_bots,
            "premium_users": premium_users
        }
