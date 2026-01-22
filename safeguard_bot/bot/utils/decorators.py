"""
Decorators
==========
Utility decorators for handler functions.
"""

from functools import wraps
from typing import Callable, List, Optional

from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ChatMemberStatus

from bot.services import get_text, db
from bot.config import config


def admin_required(func: Callable):
    """Decorator to check if user is admin"""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        if update.effective_chat.type == "private":
            await update.message.reply_text(
                get_text("errors.group_only", update.effective_user)
            )
            return
        
        user = await update.effective_chat.get_member(update.effective_user.id)
        
        if user.status not in [ChatMemberStatus.CREATOR, ChatMemberStatus.ADMINISTRATOR]:
            await update.message.reply_text(
                get_text("admin.not_admin", update.effective_user)
            )
            return
        
        return await func(update, context, *args, **kwargs)
    
    return wrapper


def creator_required(func: Callable):
    """Decorator to check if user is group creator"""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        if update.effective_chat.type == "private":
            await update.message.reply_text(
                get_text("errors.group_only", update.effective_user)
            )
            return
        
        user = await update.effective_chat.get_member(update.effective_user.id)
        
        if user.status != ChatMemberStatus.CREATOR:
            await update.message.reply_text(
                get_text("admin.not_creator", update.effective_user)
            )
            return
        
        return await func(update, context, *args, **kwargs)
    
    return wrapper


def group_only(func: Callable):
    """Decorator to ensure command is used in group only"""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        if update.effective_chat.type == "private":
            await update.message.reply_text(
                get_text("errors.group_only", update.effective_user)
            )
            return
        
        return await func(update, context, *args, **kwargs)
    
    return wrapper


def private_only(func: Callable):
    """Decorator to ensure command is used in private chat only"""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        if update.effective_chat.type != "private":
            await update.message.reply_text(
                get_text("errors.private_only", update.effective_user)
            )
            return
        
        return await func(update, context, *args, **kwargs)
    
    return wrapper


def ensure_group_config(func: Callable):
    """Decorator to ensure group config exists"""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        if update.effective_chat and update.effective_chat.type != "private":
            # Ensure group exists in database
            db.create_or_update_group(
                update.effective_chat.id,
                title=update.effective_chat.title
            )
        
        return await func(update, context, *args, **kwargs)
    
    return wrapper


def rate_limit(max_calls: int = 3, period: int = 60):
    """
    Decorator for rate limiting
    
    Args:
        max_calls: Maximum number of calls allowed
        period: Time period in seconds
    """
    def decorator(func: Callable):
        calls = {}  # user_id -> list of timestamps
        
        @wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            import time
            
            user_id = update.effective_user.id
            current_time = time.time()
            
            if user_id not in calls:
                calls[user_id] = []
            
            # Remove old calls
            calls[user_id] = [t for t in calls[user_id] if current_time - t < period]
            
            if len(calls[user_id]) >= max_calls:
                # Rate limited
                return
            
            calls[user_id].append(current_time)
            return await func(update, context, *args, **kwargs)
        
        return wrapper
    
    return decorator


def log_action(action_type: str):
    """Decorator to log admin actions"""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            result = await func(update, context, *args, **kwargs)
            
            # Log the action if it was successful
            if result and update.effective_chat:
                target_user = getattr(context, '_target_user', None)
                reason = getattr(context, '_action_reason', "")
                
                if target_user:
                    db.log_action(
                        chat_id=update.effective_chat.id,
                        admin_id=update.effective_user.id,
                        target_user_id=target_user.id,
                        action_type=action_type,
                        reason=reason
                    )
            
            return result
        
        return wrapper
    
    return decorator


def bot_owner_required(func: Callable):
    """Decorator to check if user is a bot owner (from ADMIN_IDS in config)"""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        
        if user_id not in config.admin_ids:
            await update.message.reply_text(
                get_text("broadcast.not_owner", update.effective_user)
            )
            return
        
        return await func(update, context, *args, **kwargs)
    
    return wrapper
