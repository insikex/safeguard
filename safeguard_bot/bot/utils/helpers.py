"""
Helper Functions
================
Utility functions for the bot.
"""

import re
from typing import Optional, Tuple
from datetime import timedelta

from telegram import User, Chat, ChatMember
from telegram.constants import ChatMemberStatus


def get_user_mention(user: User) -> str:
    """Get user mention HTML"""
    return user.mention_html()


def get_user_link(user: User) -> str:
    """Get user link"""
    return f"tg://user?id={user.id}"


def get_user_display_name(user: User) -> str:
    """Get user display name (full name or username)"""
    if user.full_name:
        return user.full_name
    elif user.username:
        return f"@{user.username}"
    else:
        return f"User {user.id}"


def parse_duration(duration_str: str) -> Optional[int]:
    """
    Parse duration string to seconds.
    
    Supported formats:
    - 30s, 30sec, 30 seconds
    - 5m, 5min, 5 minutes
    - 1h, 1hr, 1 hour
    - 1d, 1 day
    
    Returns:
        Duration in seconds, or None if invalid
    """
    if not duration_str:
        return None
    
    duration_str = duration_str.lower().strip()
    
    patterns = [
        (r'^(\d+)\s*s(?:ec(?:ond)?s?)?$', 1),           # seconds
        (r'^(\d+)\s*m(?:in(?:ute)?s?)?$', 60),          # minutes
        (r'^(\d+)\s*h(?:(?:ou)?rs?)?$', 3600),          # hours
        (r'^(\d+)\s*d(?:ays?)?$', 86400),               # days
        (r'^(\d+)$', 60),                               # default to minutes
    ]
    
    for pattern, multiplier in patterns:
        match = re.match(pattern, duration_str)
        if match:
            return int(match.group(1)) * multiplier
    
    return None


def format_duration(seconds: int, language: str = "en") -> str:
    """
    Format duration in seconds to human readable string.
    
    Args:
        seconds: Duration in seconds
        language: Language code ('en' or 'id')
    """
    if seconds < 60:
        unit = "detik" if language == "id" else "seconds"
        return f"{seconds} {unit}"
    elif seconds < 3600:
        minutes = seconds // 60
        unit = "menit" if language == "id" else "minutes"
        return f"{minutes} {unit}"
    elif seconds < 86400:
        hours = seconds // 3600
        unit = "jam" if language == "id" else "hours"
        return f"{hours} {unit}"
    else:
        days = seconds // 86400
        unit = "hari" if language == "id" else "days"
        return f"{days} {unit}"


def is_admin(member: ChatMember) -> bool:
    """Check if chat member is admin or creator"""
    return member.status in [ChatMemberStatus.CREATOR, ChatMemberStatus.ADMINISTRATOR]


def is_creator(member: ChatMember) -> bool:
    """Check if chat member is creator"""
    return member.status == ChatMemberStatus.CREATOR


def can_restrict_member(bot_member: ChatMember, target_member: ChatMember) -> bool:
    """Check if bot can restrict target member"""
    # Can't restrict admins
    if is_admin(target_member):
        return False
    
    # Bot must have restrict permission
    if not getattr(bot_member, 'can_restrict_members', False):
        return False
    
    return True


def can_delete_messages(bot_member: ChatMember) -> bool:
    """Check if bot can delete messages"""
    return getattr(bot_member, 'can_delete_messages', False)


def extract_user_from_reply(update) -> Optional[User]:
    """Extract target user from reply message"""
    if update.message.reply_to_message:
        return update.message.reply_to_message.from_user
    return None


def extract_reason_from_args(args: list) -> str:
    """Extract reason from command arguments"""
    if args:
        return " ".join(args)
    return "No reason provided"


def is_link(text: str) -> bool:
    """Check if text contains links"""
    link_patterns = [
        r'https?://',
        r't\.me/',
        r'telegram\.me/',
        r'@\w+',  # Username mentions that might be channels
    ]
    
    for pattern in link_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    
    return False


def contains_bad_word(text: str, bad_words: list) -> bool:
    """Check if text contains bad words"""
    text_lower = text.lower()
    
    for word in bad_words:
        if word.lower() in text_lower:
            return True
    
    return False


def escape_markdown(text: str) -> str:
    """Escape markdown special characters"""
    escape_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    
    for char in escape_chars:
        text = text.replace(char, f'\\{char}')
    
    return text


def truncate_text(text: str, max_length: int = 100) -> str:
    """Truncate text to max length"""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


def get_chat_type_name(chat: Chat) -> str:
    """Get human readable chat type name"""
    type_names = {
        "private": "Private Chat",
        "group": "Group",
        "supergroup": "Supergroup",
        "channel": "Channel"
    }
    return type_names.get(chat.type, "Unknown")
