from datetime import datetime, timedelta
import config

class SubscriptionManager:
    def __init__(self, db):
        self.db = db
        
    async def get_user_subscription(self, user_id: int):
        """Get user's subscription status"""
        subscription = await self.db.db.subscriptions.find_one({"user_id": user_id})
        
        if not subscription:
            return None
            
        # Check if subscription is still active
        if subscription['expires_at'] > datetime.utcnow():
            subscription['active'] = True
        else:
            subscription['active'] = False
            # Update database
            await self.db.db.subscriptions.update_one(
                {"user_id": user_id},
                {"$set": {"active": False}}
            )
            
        return subscription
        
    async def create_subscription(self, user_id: int, plan: str, duration_days: int):
        """Create a new subscription"""
        expires_at = datetime.utcnow() + timedelta(days=duration_days)
        
        subscription_data = {
            "user_id": user_id,
            "plan": plan,
            "created_at": datetime.utcnow(),
            "expires_at": expires_at,
            "active": True,
            "auto_renew": False
        }
        
        await self.db.db.subscriptions.update_one(
            {"user_id": user_id},
            {"$set": subscription_data},
            upsert=True
        )
        
        return subscription_data
        
    async def extend_subscription(self, user_id: int, days: int):
        """Extend existing subscription"""
        subscription = await self.get_user_subscription(user_id)
        
        if subscription and subscription['active']:
            new_expires = subscription['expires_at'] + timedelta(days=days)
        else:
            new_expires = datetime.utcnow() + timedelta(days=days)
            
        await self.db.db.subscriptions.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "expires_at": new_expires,
                    "active": True
                }
            }
        )
        
    async def cancel_subscription(self, user_id: int):
        """Cancel user's subscription"""
        await self.db.db.subscriptions.update_one(
            {"user_id": user_id},
            {"$set": {"active": False, "auto_renew": False}}
        )
        
    async def check_deployment_limit(self, user_id: int) -> bool:
        """Check if user can deploy more bots"""
        subscription = await self.get_user_subscription(user_id)
        user_bots = await self.db.get_user_bots(user_id)
        
        if subscription and subscription['active']:
            return True  # Premium users have unlimited deployments
        else:
            return len(user_bots) < config.MAX_BOTS_FREE
            
    async def get_subscription_stats(self):
        """Get subscription statistics for admin"""
        total_subs = await self.db.db.subscriptions.count_documents({})
        active_subs = await self.db.db.subscriptions.count_documents({"active": True})
        
        # Get plan breakdown
        plans = {}
        cursor = self.db.db.subscriptions.find({"active": True})
        async for sub in cursor:
            plan = sub.get('plan', 'unknown')
            plans[plan] = plans.get(plan, 0) + 1
            
        return {
            "total_subscriptions": total_subs,
            "active_subscriptions": active_subs,
            "plan_breakdown": plans
        }
        
    async def get_expiring_subscriptions(self, days: int = 7):
        """Get subscriptions expiring within specified days"""
        cutoff_date = datetime.utcnow() + timedelta(days=days)
        
        cursor = self.db.db.subscriptions.find({
            "active": True,
            "expires_at": {"$lte": cutoff_date}
        })
        
        expiring_subs = []
        async for sub in cursor:
            expiring_subs.append({
                "user_id": sub['user_id'],
                "plan": sub['plan'],
                "expires_at": sub['expires_at']
            })
            
        return expiring_subs
        
    async def notify_expiring_subscriptions(self, bot_application):
        """Send notifications for expiring subscriptions"""
        expiring = await self.get_expiring_subscriptions(3)  # 3 days warning
        
        for sub in expiring:
            try:
                message = f"""
🔔 **Subscription Expiring Soon**

Your {sub['plan']} subscription will expire on {sub['expires_at'].strftime('%B %d, %Y')}.

**Renew now to continue enjoying:**
• Unlimited bot deployments
• Priority support
• Advanced features

Contact @x_ifeelram to renew your subscription.
                """
                
                await bot_application.bot.send_message(
                    chat_id=sub['user_id'],
                    text=message,
                    parse_mode='Markdown'
                )
                
            except Exception as e:
                logger.error(f"Failed to notify user {sub['user_id']}: {str(e)}")
