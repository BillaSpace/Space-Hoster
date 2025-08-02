from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
import config

class Database:
    def __init__(self):
        self.client = AsyncIOMotorClient(config.MONGODB_URI)
        self.db     = self.client[config.DATABASE_NAME]

    async def init_indexes(self):
        await self.db.users.create_index("user_id", unique=True)
        await self.db.bots.create_index("bot_id", unique=True)

    # ── users ──────────────────────────────────────────
    async def register_user(self, uid: int, username: str, name: str):
        await self.db.users.update_one(
            {"user_id": uid},
            {"$setOnInsert": {"first_name": name, "username": username,
                              "created_at": datetime.utcnow()}},
            upsert=True)

    async def banned(self, uid: int) -> bool:
        return await self.db.bans.count_documents({"user_id": uid}) > 0

    # ── bots ───────────────────────────────────────────
    async def add_bot(self, uid: int, bot_doc: dict):
        await self.db.bots.insert_one(bot_doc)

    async def get_bot(self, uid: int, bot_id: str):
        return await self.db.bots.find_one({"user_id": uid, "bot_id": bot_id})

    async def set_bot_status(self, uid: int, bot_id: str, status: str):
        await self.db.bots.update_one({"user_id": uid, "bot_id": bot_id},
                                      {"$set": {"status": status,
                                                "updated_at": datetime.utcnow()}})
