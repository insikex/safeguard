"""
Moderation Handlers
===================
Handlers for automatic moderation: anti-spam, anti-flood, anti-link, etc.
"""

import re
import time
from typing import Dict, List
from collections import defaultdict
from datetime import datetime, timedelta

from telegram import Update, ChatPermissions
from telegram.ext import ContextTypes
from telegram.constants import ParseMode, ChatMemberStatus

from bot.services import get_text, db, detect_lang
from bot.utils import is_link, contains_bad_word, format_duration


# In-memory flood tracking (per user per chat)
flood_tracker: Dict[str, Dict[int, List[float]]] = defaultdict(lambda: defaultdict(list))


async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all text messages for moderation"""
    if not update.message or not update.message.text:
        return
    
    user = update.effective_user
    chat = update.effective_chat
    
    if chat.type == "private":
        return
    
    # Skip if user is admin
    try:
        member = await chat.get_member(user.id)
        if member.status in [ChatMemberStatus.CREATOR, ChatMemberStatus.ADMINISTRATOR]:
            # Still track message count
            db.increment_stat(chat.id, "messages")
            return
    except:
        pass
    
    # Get group config
    group = db.get_group(chat.id)
    if not group:
        group = db.create_or_update_group(chat.id, title=chat.title)
    
    # Run moderation checks
    message_text = update.message.text
    
    # Check anti-flood
    if group.get('antiflood_enabled', True):
        if await check_flood(update, context, group):
            return  # Message handled (deleted + user muted)
    
    # Check anti-link
    if group.get('antilink_enabled', False):
        if await check_link(update, context, group):
            return  # Message deleted
    
    # Check anti-spam
    if group.get('antispam_enabled', True):
        if await check_spam(update, context, group):
            return  # Message deleted
    
    # Check anti-bad word
    if group.get('antibadword_enabled', False):
        if await check_badword(update, context, group):
            return  # Message deleted
    
    # Track message count
    db.increment_stat(chat.id, "messages")
    
    # Update user last message
    db.create_or_update_user(
        user.id,
        chat.id,
        last_message=datetime.now().isoformat(),
        message_count=db.get_user(user.id, chat.id).get('message_count', 0) + 1 if db.get_user(user.id, chat.id) else 1
    )


async def check_flood(update: Update, context: ContextTypes.DEFAULT_TYPE, group: dict) -> bool:
    """
    Check for message flooding.
    Returns True if flood detected and handled.
    """
    user = update.effective_user
    chat = update.effective_chat
    
    flood_limit = group.get('flood_limit', 5)
    flood_window = group.get('flood_time_window', 10)
    
    chat_key = str(chat.id)
    current_time = time.time()
    
    # Add current message timestamp
    flood_tracker[chat_key][user.id].append(current_time)
    
    # Remove old timestamps outside the time window
    flood_tracker[chat_key][user.id] = [
        ts for ts in flood_tracker[chat_key][user.id]
        if current_time - ts < flood_window
    ]
    
    # Check if flood
    if len(flood_tracker[chat_key][user.id]) > flood_limit:
        # Flood detected!
        try:
            # Delete the message
            await update.message.delete()
        except:
            pass
        
        # Mute user for 5 minutes
        mute_duration = 300  # 5 minutes
        
        try:
            until_date = datetime.now() + timedelta(seconds=mute_duration)
            await context.bot.restrict_chat_member(
                chat.id,
                user.id,
                permissions=ChatPermissions(can_send_messages=False),
                until_date=until_date
            )
            
            db.mute_user(user.id, chat.id, mute_duration)
            db.increment_stat(chat.id, "flood_blocked")
            
            lang = detect_lang(user)
            await context.bot.send_message(
                chat.id,
                get_text(
                    "protection.flood_detected",
                    user,
                    user=user.mention_html(),
                    duration=mute_duration
                ),
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            print(f"Failed to mute flood user: {e}")
        
        # Clear flood tracker for this user
        flood_tracker[chat_key][user.id] = []
        
        return True
    
    return False


async def check_link(update: Update, context: ContextTypes.DEFAULT_TYPE, group: dict) -> bool:
    """
    Check for unauthorized links.
    Returns True if link found and handled.
    """
    user = update.effective_user
    chat = update.effective_chat
    message_text = update.message.text
    
    # Check if message contains links
    if not is_link(message_text):
        return False
    
    # Link detected!
    try:
        await update.message.delete()
    except:
        pass
    
    db.increment_stat(chat.id, "links_blocked")
    
    try:
        await context.bot.send_message(
            chat.id,
            get_text(
                "protection.link_deleted",
                user,
                user=user.mention_html()
            ),
            parse_mode=ParseMode.HTML
        )
    except:
        pass
    
    return True


async def check_spam(update: Update, context: ContextTypes.DEFAULT_TYPE, group: dict) -> bool:
    """
    Check for spam patterns.
    Returns True if spam detected and handled.
    """
    user = update.effective_user
    chat = update.effective_chat
    message_text = update.message.text
    
    # Spam patterns to check
    spam_patterns = [
        r'(.)\1{10,}',  # Repeated characters (10+ times)
        r'(\b\w+\b)(\s+\1){5,}',  # Repeated words (5+ times)
        r'[A-Z\s]{50,}',  # Long ALL CAPS text
        r'(?:crypto|bitcoin|earn|money|investment|profit).{0,50}(?:http|www|t\.me)',  # Crypto scam patterns
        r'(?:join|click|visit).{0,30}(?:http|www|t\.me).{0,50}(?:free|bonus|reward)',  # Click bait
        r'@\w+\s*@\w+\s*@\w+\s*@\w+',  # Multiple mentions (4+)
    ]
    
    for pattern in spam_patterns:
        if re.search(pattern, message_text, re.IGNORECASE):
            # Spam detected!
            try:
                await update.message.delete()
            except:
                pass
            
            db.increment_stat(chat.id, "spam_blocked")
            
            try:
                await context.bot.send_message(
                    chat.id,
                    get_text(
                        "protection.spam_detected",
                        user,
                        user=user.mention_html()
                    ),
                    parse_mode=ParseMode.HTML
                )
            except:
                pass
            
            return True
    
    return False


async def check_badword(update: Update, context: ContextTypes.DEFAULT_TYPE, group: dict) -> bool:
    """
    Check for bad words.
    Returns True if bad word found and handled.
    """
    user = update.effective_user
    chat = update.effective_chat
    message_text = update.message.text
    
    # Get bad words list from group config
    import json
    bad_words_json = group.get('badwords', '[]')
    try:
        bad_words = json.loads(bad_words_json) if isinstance(bad_words_json, str) else bad_words_json
    except:
        bad_words = []
    
    # Default bad words if none configured
    if not bad_words:
        bad_words = [
            # Add some default bad words (keep it minimal)
            "spam", "scam"
        ]
    
    if contains_bad_word(message_text, bad_words):
        # Bad word detected!
        try:
            await update.message.delete()
        except:
            pass
        
        db.increment_stat(chat.id, "badword_blocked")
        
        try:
            await context.bot.send_message(
                chat.id,
                get_text(
                    "protection.badword_detected",
                    user,
                    user=user.mention_html()
                ),
                parse_mode=ParseMode.HTML
            )
        except:
            pass
        
        return True
    
    return False


async def check_new_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check if new member is a suspicious bot"""
    for member in update.message.new_chat_members:
        if not member.is_bot:
            continue
        
        chat = update.effective_chat
        user = update.effective_user
        
        # Get who added the bot
        adder = update.effective_user
        
        # Check if adder is admin
        try:
            adder_member = await chat.get_member(adder.id)
            if adder_member.status not in [ChatMemberStatus.CREATOR, ChatMemberStatus.ADMINISTRATOR]:
                # Non-admin added a bot - kick the bot
                try:
                    await context.bot.ban_chat_member(chat.id, member.id)
                    await context.bot.unban_chat_member(chat.id, member.id)
                    
                    db.increment_stat(chat.id, "bots_removed")
                    
                    await context.bot.send_message(
                        chat.id,
                        get_text(
                            "protection.bot_detected",
                            user,
                            user=member.mention_html()
                        ),
                        parse_mode=ParseMode.HTML
                    )
                except:
                    pass
        except:
            pass
