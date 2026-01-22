"""
Handlers Package
================
Contains all handler modules for the Safeguard Bot.
"""

from .start import start_command, help_command, rules_command, mystatus_command, start_callback
from .admin import (
    warn_command,
    unwarn_command,
    kick_command,
    ban_command,
    unban_command,
    mute_command,
    unmute_command,
    stats_command
)
from .verification import (
    new_member_handler,
    verification_callback,
    verification_timeout_callback,
    portal_verification_handler
)
from .settings import settings_command, settings_callback
from .moderation import message_handler, check_new_bot
from .broadcast import (
    create_broadcast_conversation,
    unpin_expired_messages
)
from .premium import (
    premium_command,
    premium_callback,
    check_expired_subscriptions,
    is_premium_user
)

__all__ = [
    # Start handlers
    "start_command",
    "help_command",
    "rules_command",
    "mystatus_command",
    "start_callback",
    
    # Admin handlers
    "warn_command",
    "unwarn_command",
    "kick_command",
    "ban_command",
    "unban_command",
    "mute_command",
    "unmute_command",
    "stats_command",
    
    # Verification handlers
    "new_member_handler",
    "verification_callback",
    "verification_timeout_callback",
    "portal_verification_handler",
    
    # Settings handlers
    "settings_command",
    "settings_callback",
    
    # Moderation handlers
    "message_handler",
    "check_new_bot",
    
    # Broadcast handlers
    "create_broadcast_conversation",
    "unpin_expired_messages",
    
    # Premium handlers
    "premium_command",
    "premium_callback",
    "check_expired_subscriptions",
    "is_premium_user",
]
