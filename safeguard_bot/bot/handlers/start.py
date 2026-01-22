"""
Start & Help Handlers
=====================
Handlers for /start and /help commands.
"""

from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from bot.config import config
from bot.services import get_text, db, detect_lang
from bot.utils import get_user_display_name


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user = update.effective_user
    chat = update.effective_chat
    
    if chat.type == "private":
        # Private chat - show full welcome message
        text = get_text(
            "welcome.start_private",
            user,
            name=get_user_display_name(user)
        )
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    else:
        # Group chat
        # Ensure group exists in database
        db.create_or_update_group(chat.id, title=chat.title)
        
        text = get_text("welcome.start_group", user)
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    user = update.effective_user
    
    text = (
        get_text("help.title", user) +
        get_text("help.admin_commands", user) +
        "\n\n"
    )
    
    # Show owner commands only to bot owners
    if user.id in config.admin_ids:
        text += get_text("help.owner_commands", user) + "\n\n"
    
    text += (
        get_text("help.user_commands", user) +
        get_text("help.footer", user)
    )
    
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def rules_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /rules command"""
    user = update.effective_user
    chat = update.effective_chat
    
    if chat.type == "private":
        await update.message.reply_text(
            get_text("errors.group_only", user),
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Get group rules
    group = db.get_group(chat.id)
    rules = group.get('rules', '') if group else ''
    
    if rules:
        text = get_text("rules.title", user, rules=rules)
    else:
        text = get_text("rules.not_set", user)
    
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def mystatus_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /mystatus command"""
    user = update.effective_user
    chat = update.effective_chat
    
    if chat.type == "private":
        await update.message.reply_text(
            get_text("errors.group_only", user),
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Get user data
    user_data = db.get_user(user.id, chat.id)
    group = db.get_group(chat.id)
    member = await chat.get_member(user.id)
    
    # Determine role
    role_map = {
        "creator": "Owner",
        "administrator": "Admin",
        "member": "Member",
        "restricted": "Restricted",
        "left": "Left",
        "kicked": "Banned"
    }
    role = role_map.get(member.status, "Member")
    
    # Build status text
    text = get_text("status.title", user)
    text += get_text("status.user", user, name=get_user_display_name(user))
    text += get_text("status.id", user, id=user.id)
    
    if user_data:
        warn_count = user_data.get('warnings', 0)
        max_warns = group.get('warn_limit', 3) if group else 3
        text += get_text("status.warnings", user, count=warn_count, max=max_warns)
        
        if user_data.get('is_verified'):
            text += get_text("status.verified", user)
        
        if user_data.get('is_muted'):
            text += get_text("status.muted", user)
    else:
        max_warns = group.get('warn_limit', 3) if group else 3
        text += get_text("status.warnings", user, count=0, max=max_warns)
    
    text += get_text("status.role", user, role=role)
    
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
