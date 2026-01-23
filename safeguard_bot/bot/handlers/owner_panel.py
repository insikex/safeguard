"""
Owner Panel Handler
====================
Owner-only admin panel for managing premium users and bot settings.
Only the bot owner (OWNER_ID) can access these commands.
"""

import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from bot.config import config
from bot.services import get_text, db, detect_lang

logger = logging.getLogger(__name__)


def owner_only(func):
    """Decorator to check if user is the bot owner"""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = update.effective_user
        if not config.is_owner(user.id):
            await update.message.reply_text(
                get_text("owner_panel.not_owner", user),
                parse_mode=ParseMode.MARKDOWN
            )
            return
        return await func(update, context, *args, **kwargs)
    return wrapper


@owner_only
async def admin_panel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /adminpanel command - Show owner admin panel"""
    user = update.effective_user
    
    # Get some statistics
    total_users = db.get_total_bot_users()
    total_premium = db.get_total_premium_users()
    total_groups = db.get_total_groups()
    
    text = get_text(
        "owner_panel.main_menu",
        user,
        total_users=total_users,
        total_premium=total_premium,
        total_groups=total_groups
    )
    
    keyboard = [
        [InlineKeyboardButton(
            get_text("owner_panel.add_premium_btn", user),
            callback_data="owner_add_premium"
        )],
        [InlineKeyboardButton(
            get_text("owner_panel.remove_premium_btn", user),
            callback_data="owner_remove_premium"
        )],
        [InlineKeyboardButton(
            get_text("owner_panel.list_premium_btn", user),
            callback_data="owner_list_premium"
        )],
        [InlineKeyboardButton(
            get_text("owner_panel.list_groups_btn", user),
            callback_data="owner_list_groups"
        )],
        [InlineKeyboardButton(
            get_text("owner_panel.bot_stats_btn", user),
            callback_data="owner_bot_stats"
        )],
        [InlineKeyboardButton(
            get_text("owner_panel.close_btn", user),
            callback_data="owner_close"
        )]
    ]
    
    await update.message.reply_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


@owner_only
async def add_premium_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /addpremium command - Add premium manually
    Usage: /addpremium <user_id> <days>
    """
    user = update.effective_user
    
    if len(context.args) < 2:
        await update.message.reply_text(
            get_text("owner_panel.addpremium_usage", user),
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    try:
        target_user_id = int(context.args[0])
        days = int(context.args[1])
    except ValueError:
        await update.message.reply_text(
            get_text("owner_panel.invalid_args", user),
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    if days < 1 or days > 365:
        await update.message.reply_text(
            get_text("owner_panel.invalid_days", user),
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Add premium subscription
    success = add_premium_to_user(target_user_id, days, "manual")
    
    if success:
        # Try to get user info
        try:
            target_user = await context.bot.get_chat(target_user_id)
            target_name = target_user.full_name or f"User {target_user_id}"
        except:
            target_name = f"User {target_user_id}"
        
        await update.message.reply_text(
            get_text(
                "owner_panel.premium_added",
                user,
                user_name=target_name,
                user_id=target_user_id,
                days=days
            ),
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Try to notify the user
        try:
            await context.bot.send_message(
                chat_id=target_user_id,
                text=get_text("owner_panel.premium_granted", user, days=days),
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            logger.warning(f"Could not notify user {target_user_id} about premium: {e}")
    else:
        await update.message.reply_text(
            get_text("owner_panel.premium_add_failed", user),
            parse_mode=ParseMode.MARKDOWN
        )


@owner_only
async def remove_premium_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /removepremium command - Remove premium from user
    Usage: /removepremium <user_id>
    """
    user = update.effective_user
    
    if len(context.args) < 1:
        await update.message.reply_text(
            get_text("owner_panel.removepremium_usage", user),
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    try:
        target_user_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text(
            get_text("owner_panel.invalid_user_id", user),
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Check if user has premium
    subscription = db.get_premium_subscription(target_user_id)
    if not subscription:
        await update.message.reply_text(
            get_text("owner_panel.no_premium", user, user_id=target_user_id),
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Remove premium
    db.deactivate_subscription(subscription['id'])
    
    # Try to get user info
    try:
        target_user = await context.bot.get_chat(target_user_id)
        target_name = target_user.full_name or f"User {target_user_id}"
    except:
        target_name = f"User {target_user_id}"
    
    await update.message.reply_text(
        get_text(
            "owner_panel.premium_removed",
            user,
            user_name=target_name,
            user_id=target_user_id
        ),
        parse_mode=ParseMode.MARKDOWN
    )


@owner_only
async def list_premium_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /listpremium command - List all premium users"""
    user = update.effective_user
    
    premium_users = db.get_all_active_premium_users()
    
    if not premium_users:
        await update.message.reply_text(
            get_text("owner_panel.no_premium_users", user),
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    text = get_text("owner_panel.premium_list_title", user) + "\n\n"
    
    for i, sub in enumerate(premium_users[:20], 1):  # Limit to 20 to avoid message length issues
        end_date = datetime.fromisoformat(sub['end_date'])
        days_left = (end_date - datetime.now()).days
        
        text += f"{i}. `{sub['user_id']}` - {sub.get('plan_type', 'manual')} ({days_left} days left)\n"
    
    if len(premium_users) > 20:
        text += f"\n... and {len(premium_users) - 20} more users"
    
    text += f"\n\n**Total: {len(premium_users)} premium users**"
    
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def owner_panel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle owner panel callback queries"""
    query = update.callback_query
    user = update.effective_user
    data = query.data
    
    # Check if user is owner
    if not config.is_owner(user.id):
        await query.answer(
            get_text("owner_panel.not_owner", user),
            show_alert=True
        )
        return
    
    await query.answer()
    
    if data == "owner_close":
        await query.message.delete()
        return
    
    if data == "owner_add_premium":
        text = get_text("owner_panel.add_premium_help", user)
        
        keyboard = [[InlineKeyboardButton(
            get_text("owner_panel.back_btn", user),
            callback_data="owner_back"
        )]]
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    if data == "owner_remove_premium":
        text = get_text("owner_panel.remove_premium_help", user)
        
        keyboard = [[InlineKeyboardButton(
            get_text("owner_panel.back_btn", user),
            callback_data="owner_back"
        )]]
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    if data == "owner_list_premium":
        premium_users = db.get_all_active_premium_users()
        
        if not premium_users:
            text = get_text("owner_panel.no_premium_users", user)
        else:
            text = get_text("owner_panel.premium_list_title", user) + "\n\n"
            
            for i, sub in enumerate(premium_users[:15], 1):
                end_date = datetime.fromisoformat(sub['end_date'])
                days_left = (end_date - datetime.now()).days
                text += f"{i}. `{sub['user_id']}` - {sub.get('plan_type', 'manual')} ({days_left}d)\n"
            
            if len(premium_users) > 15:
                text += f"\n... +{len(premium_users) - 15} more"
            
            text += f"\n\n**Total: {len(premium_users)}**"
        
        keyboard = [[InlineKeyboardButton(
            get_text("owner_panel.back_btn", user),
            callback_data="owner_back"
        )]]
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    if data == "owner_bot_stats":
        total_users = db.get_total_bot_users()
        total_premium = db.get_total_premium_users()
        total_groups = db.get_total_groups()
        
        text = get_text(
            "owner_panel.bot_stats",
            user,
            total_users=total_users,
            total_premium=total_premium,
            total_groups=total_groups
        )
        
        keyboard = [[InlineKeyboardButton(
            get_text("owner_panel.back_btn", user),
            callback_data="owner_back"
        )]]
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    if data == "owner_list_groups":
        # Get all groups from database
        all_groups = db.get_all_groups()
        
        if not all_groups:
            text = get_text("group_management.owner_no_groups", user)
        else:
            text = get_text("owner_panel.groups_list_title", user, count=len(all_groups)) + "\n\n"
            
            # Check active groups (limit to 15 for callback)
            active_count = 0
            for i, g in enumerate(all_groups[:15], 1):
                try:
                    chat = await context.bot.get_chat(g['chat_id'])
                    member_count = await chat.get_member_count()
                    text += f"{i}. {chat.title} | 👥 {member_count}\n"
                    active_count += 1
                except:
                    text += f"{i}. ❌ {g.get('title', 'Unknown')} (inactive)\n"
            
            if len(all_groups) > 15:
                text += f"\n... +{len(all_groups) - 15} more groups"
            
            text += f"\n\n**Total: {len(all_groups)} groups in database**"
        
        keyboard = [[InlineKeyboardButton(
            get_text("owner_panel.back_btn", user),
            callback_data="owner_back"
        )]]
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    if data == "owner_back":
        total_users = db.get_total_bot_users()
        total_premium = db.get_total_premium_users()
        total_groups = db.get_total_groups()
        
        text = get_text(
            "owner_panel.main_menu",
            user,
            total_users=total_users,
            total_premium=total_premium,
            total_groups=total_groups
        )
        
        keyboard = [
            [InlineKeyboardButton(
                get_text("owner_panel.add_premium_btn", user),
                callback_data="owner_add_premium"
            )],
            [InlineKeyboardButton(
                get_text("owner_panel.remove_premium_btn", user),
                callback_data="owner_remove_premium"
            )],
            [InlineKeyboardButton(
                get_text("owner_panel.list_premium_btn", user),
                callback_data="owner_list_premium"
            )],
            [InlineKeyboardButton(
                get_text("owner_panel.list_groups_btn", user),
                callback_data="owner_list_groups"
            )],
            [InlineKeyboardButton(
                get_text("owner_panel.bot_stats_btn", user),
                callback_data="owner_bot_stats"
            )],
            [InlineKeyboardButton(
                get_text("owner_panel.close_btn", user),
                callback_data="owner_close"
            )]
        ]
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return


def add_premium_to_user(user_id: int, days: int, plan_type: str = "manual") -> bool:
    """Add or extend premium subscription for a user"""
    try:
        # Check if user already has active subscription
        existing = db.get_premium_subscription(user_id)
        
        if existing:
            # Extend existing subscription
            current_end = datetime.fromisoformat(existing['end_date'])
            if current_end < datetime.now():
                current_end = datetime.now()
            new_end = current_end + timedelta(days=days)
            
            db.extend_subscription(existing['id'], new_end)
        else:
            # Create new subscription
            start_date = datetime.now()
            end_date = start_date + timedelta(days=days)
            
            db.create_premium_subscription_manual(
                user_id=user_id,
                plan_type=plan_type,
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat()
            )
        
        return True
    except Exception as e:
        logger.error(f"Failed to add premium for user {user_id}: {e}")
        return False
