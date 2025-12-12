"""
User Service - Handles user credits, tiers, and usage tracking.

Tiers:
- Free: 5 videos/month (resets monthly)
- Basic: 5 one-time credits ($3)
- Pro: 50 videos/month, resets monthly ($20/month)
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from .database import get_database


# Tier definitions
TIERS = {
    "free": {
        "monthly_limit": 5,
        "max_length": "Long (1m)",  # Max 1 minute for free
        "quality": "720p30"
    },
    "basic": {
        "credits": 5,  # One-time purchase
        "max_length": "Extended (5m)",  # Up to 5 minutes
        "quality": "1080p60"
    },
    "pro": {
        "monthly_limit": 50,
        "max_length": "Extended (5m)",  # Up to 5 minutes
        "quality": "4k60"
    }
}


async def get_users_collection():
    """Get the users collection."""
    db = await get_database()
    return db["users"]


async def get_or_create_user(clerk_id: str) -> Dict[str, Any]:
    """
    Get user from database or create a new free user.
    Returns user document with usage info.
    """
    users = await get_users_collection()
    user = await users.find_one({"clerk_id": clerk_id})
    
    if user is None:
        # Create new free user
        now = datetime.utcnow()
        user = {
            "clerk_id": clerk_id,
            "tier": "free",
            "basic_credits": 0,  # One-time purchased credits
            "monthly_count": 0,  # Videos generated this month
            "month_reset_date": get_next_month_reset(now),
            "created_at": now,
            "updated_at": now
        }
        await users.insert_one(user)
        print(f"✅ Created new user: {clerk_id}")
    
    return user


def get_next_month_reset(from_date: datetime) -> datetime:
    """Get the 1st of next month as reset date (for free tier)."""
    if from_date.month == 12:
        return datetime(from_date.year + 1, 1, 1)
    return datetime(from_date.year, from_date.month + 1, 1)


def get_subscription_reset(from_date: datetime) -> datetime:
    """Get the date exactly 30 days from now (for Pro subscription)."""
    return from_date + timedelta(days=30)


async def check_and_reset_monthly(user: Dict[str, Any]) -> Dict[str, Any]:
    """Reset monthly count if past reset date."""
    now = datetime.utcnow()
    reset_date = user.get("month_reset_date")
    
    if reset_date and now >= reset_date:
        users = await get_users_collection()
        new_reset = get_next_month_reset(now)
        
        await users.update_one(
            {"clerk_id": user["clerk_id"]},
            {
                "$set": {
                    "monthly_count": 0,
                    "month_reset_date": new_reset,
                    "updated_at": now
                }
            }
        )
        user["monthly_count"] = 0
        user["month_reset_date"] = new_reset
        print(f"🔄 Reset monthly count for user: {user['clerk_id']}")
    
    return user


async def check_can_generate(clerk_id: str) -> Dict[str, Any]:
    """
    Check if user can generate a video.
    Returns: {"allowed": bool, "reason": str, "remaining": int, "tier": str}
    """
    user = await get_or_create_user(clerk_id)
    user = await check_and_reset_monthly(user)
    
    tier = user.get("tier", "free")
    monthly_count = user.get("monthly_count", 0)
    basic_credits = user.get("basic_credits", 0)
    
    # Pro users: 50 videos/month
    if tier == "pro":
        limit = TIERS["pro"]["monthly_limit"]
        remaining = limit - monthly_count
        if monthly_count >= limit:
            return {
                "allowed": False,
                "reason": f"Pro monthly limit reached (50 videos). Resets on {user['month_reset_date'].strftime('%B 1')}.",
                "remaining": 0,
                "tier": "pro"
            }
        return {
            "allowed": True,
            "reason": "Pro user",
            "remaining": remaining,
            "tier": "pro"
        }
    
    # Check if user has basic credits (one-time purchase)
    if basic_credits > 0:
        return {
            "allowed": True,
            "reason": "Using Basic credits",
            "remaining": basic_credits,
            "tier": "basic"
        }
    
    # Free tier: 5 videos/month
    limit = TIERS["free"]["monthly_limit"]
    remaining = limit - monthly_count
    
    if monthly_count >= limit:
        return {
            "allowed": False,
            "reason": f"Free tier limit reached (5 videos/month). Upgrade to continue or wait until {user['month_reset_date'].strftime('%B 1')}.",
            "remaining": 0,
            "tier": "free"
        }
    
    return {
        "allowed": True,
        "reason": "Free tier",
        "remaining": remaining,
        "tier": "free"
    }


async def increment_usage(clerk_id: str) -> bool:
    """
    Increment usage after successful video generation.
    Uses basic credits first if available, otherwise monthly count.
    """
    user = await get_or_create_user(clerk_id)
    users = await get_users_collection()
    now = datetime.utcnow()
    
    tier = user.get("tier", "free")
    basic_credits = user.get("basic_credits", 0)
    
    # If user has basic credits, use those first
    if basic_credits > 0:
        await users.update_one(
            {"clerk_id": clerk_id},
            {
                "$inc": {"basic_credits": -1},
                "$set": {"updated_at": now}
            }
        )
        print(f"💳 Used 1 Basic credit for {clerk_id}, {basic_credits - 1} remaining")
        return True
    
    # Otherwise increment monthly count
    await users.update_one(
        {"clerk_id": clerk_id},
        {
            "$inc": {"monthly_count": 1},
            "$set": {"updated_at": now}
        }
    )
    print(f"📊 Incremented monthly count for {clerk_id}")
    return True


async def add_basic_credits(clerk_id: str, credits: int = 5) -> bool:
    """Add one-time Basic credits after purchase."""
    user = await get_or_create_user(clerk_id)
    users = await get_users_collection()
    
    await users.update_one(
        {"clerk_id": clerk_id},
        {
            "$inc": {"basic_credits": credits},
            "$set": {"updated_at": datetime.utcnow()}
        }
    )
    print(f"💰 Added {credits} Basic credits to {clerk_id}")
    return True


async def set_pro_subscription(clerk_id: str, active: bool = True) -> bool:
    """Set or remove Pro subscription status."""
    user = await get_or_create_user(clerk_id)
    users = await get_users_collection()
    now = datetime.utcnow()
    
    if active:
        await users.update_one(
            {"clerk_id": clerk_id},
            {
                "$set": {
                    "tier": "pro",
                    "monthly_count": 0,  # Reset on activation
                    "month_reset_date": get_subscription_reset(now),  # 30 days from purchase
                    "updated_at": now
                }
            }
        )
        print(f"⭐ Activated Pro subscription for {clerk_id}")
    else:
        await users.update_one(
            {"clerk_id": clerk_id},
            {
                "$set": {
                    "tier": "free",
                    "updated_at": now
                }
            }
        )
        print(f"📉 Downgraded {clerk_id} to Free tier")
    
    return True


async def get_user_usage(clerk_id: str) -> Dict[str, Any]:
    """Get user's current usage and tier info."""
    user = await get_or_create_user(clerk_id)
    user = await check_and_reset_monthly(user)
    
    tier = user.get("tier", "free")
    monthly_count = user.get("monthly_count", 0)
    basic_credits = user.get("basic_credits", 0)
    
    if tier == "pro":
        limit = TIERS["pro"]["monthly_limit"]
        return {
            "tier": "pro",
            "used": monthly_count,
            "limit": limit,
            "remaining": limit - monthly_count,
            "basic_credits": basic_credits,
            "reset_date": user.get("month_reset_date", "").isoformat() if user.get("month_reset_date") else None
        }
    
    limit = TIERS["free"]["monthly_limit"]
    return {
        "tier": tier,
        "used": monthly_count,
        "limit": limit,
        "remaining": limit - monthly_count,
        "basic_credits": basic_credits,
        "reset_date": user.get("month_reset_date", "").isoformat() if user.get("month_reset_date") else None
    }
