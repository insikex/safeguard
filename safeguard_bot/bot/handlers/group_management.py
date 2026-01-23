"""
Group Management Handlers
=========================
Handlers for managing groups from private chat.
Allows admins to execute commands via bot's private chat.
"""

import logging
from typing import Dict, List, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode, ChatMemberStatus

from bot.config import config
from bot.services import get_text, db, detect_lang
from bot.utils import get_user_display_name

logger = logging.getLogger(__name__)

# Conversation states
SELECT_GROUP, CONFIRM_ACTION = range(2)

# Store pending actions
pending_actions: Dict[int, Dict] = {}


async def bot_added_to_group_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle when bot is added to a group"""
    chat = update.effective_chat
    
    if chat.type == "private":
        return
    
    for member in update.message.new_chat_members:
        # Check if the new member is this bot
        if member.id == context.bot.id:
            # Bot was added to the group
            logger.info(f"Bot @SafeRobot added to group: {chat.title} ({chat.id})")
            
            # Store group in database
            db.create_or_update_group(chat.id, title=chat.title)
            
            # Get the user who added the bot
            adder = update.effective_user
            lang = detect_lang(adder)
            
            # Send welcome message
            welcome_text = get_text(
                "group_management.bot_added",
                adder,
                group=chat.title,
                adder=adder.mention_html() if adder else "Someone"
            )
            
            keyboard = [[
                InlineKeyboardButton(
                    get_text("group_management.settings_btn", adder),
                    callback_data="settings_main"
                )
            ]]
            
            try:
                await context.bot.send_message(
                    chat.id,
                    welcome_text,
                    parse_mode=ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            except Exception as e:
                logger.error(f"Failed to send welcome message: {e}")


async def get_user_admin_groups(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> List[Dict]:
    """Get all groups where the user is an admin and bot is also present"""
    admin_groups = []
    
    # Get all groups from database
    all_groups = db.get_all_groups()
    
    for group in all_groups:
        chat_id = group['chat_id']
        try:
            # Check if user is admin in this group
            member = await context.bot.get_chat_member(chat_id, user_id)
            if member.status in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR]:
                # Get chat info
                try:
                    chat = await context.bot.get_chat(chat_id)
                    admin_groups.append({
                        'chat_id': chat_id,
                        'title': chat.title or group.get('title', 'Unknown'),
                        'member_count': await chat.get_member_count() if hasattr(chat, 'get_member_count') else 0
                    })
                except Exception as e:
                    # Bot might have been removed from the group
                    logger.warning(f"Could not get chat info for {chat_id}: {e}")
                    continue
        except Exception as e:
            # User might not be in the group or bot was removed
            continue
    
    return admin_groups


async def mygroups_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /mygroups command - Show user's groups where they are admin"""
    user = update.effective_user
    chat = update.effective_chat
    
    if chat.type != "private":
        await update.message.reply_text(
            get_text("errors.private_only", user),
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Register user for broadcast
    db.register_bot_user(
        user_id=user.id,
        username=user.username,
        full_name=user.full_name,
        language=detect_lang(user)
    )
    
    await update.message.reply_text(
        get_text("group_management.loading_groups", user),
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Get user's admin groups
    admin_groups = await get_user_admin_groups(user.id, context)
    
    if not admin_groups:
        await update.message.reply_text(
            get_text("group_management.no_groups", user),
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Build group list
    text = get_text("group_management.your_groups", user, count=len(admin_groups)) + "\n\n"
    
    keyboard = []
    for i, group in enumerate(admin_groups[:20], 1):  # Limit to 20 groups
        text += f"{i}. **{group['title']}**\n"
        keyboard.append([
            InlineKeyboardButton(
                f"📋 {group['title'][:30]}",
                callback_data=f"grpmgmt_select_{group['chat_id']}"
            )
        ])
    
    if len(admin_groups) > 20:
        text += f"\n... and {len(admin_groups) - 20} more groups"
    
    text += "\n\n" + get_text("group_management.select_group_hint", user)
    
    await update.message.reply_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def group_action_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle group action commands in private chat
    Commands: /kick, /ban, /unban, /mute, /unmute, /warn
    
    Usage: /kick @username or /kick user_id
    """
    user = update.effective_user
    chat = update.effective_chat
    command = update.message.text.split()[0][1:]  # Get command without /
    
    # If in group, let the normal handler process it
    if chat.type != "private":
        return False  # Signal that this handler didn't process it
    
    # Parse arguments
    args = context.args
    if not args:
        await update.message.reply_text(
            get_text("group_management.action_usage", user, command=command),
            parse_mode=ParseMode.MARKDOWN
        )
        return True
    
    # Extract target user
    target = args[0]
    reason = " ".join(args[1:]) if len(args) > 1 else "No reason provided"
    
    # Get target user ID
    target_user_id = None
    target_username = None
    
    if target.startswith("@"):
        target_username = target[1:]
    elif target.isdigit():
        target_user_id = int(target)
    else:
        await update.message.reply_text(
            get_text("group_management.invalid_target", user),
            parse_mode=ParseMode.MARKDOWN
        )
        return True
    
    # Register user
    db.register_bot_user(
        user_id=user.id,
        username=user.username,
        full_name=user.full_name,
        language=detect_lang(user)
    )
    
    # Get user's admin groups
    admin_groups = await get_user_admin_groups(user.id, context)
    
    if not admin_groups:
        await update.message.reply_text(
            get_text("group_management.no_groups", user),
            parse_mode=ParseMode.MARKDOWN
        )
        return True
    
    # Store pending action
    pending_actions[user.id] = {
        'command': command,
        'target_user_id': target_user_id,
        'target_username': target_username,
        'reason': reason,
        'groups': admin_groups
    }
    
    if len(admin_groups) == 1:
        # Only one group, execute directly
        group = admin_groups[0]
        await execute_group_action(update, context, user, group['chat_id'], group['title'])
    else:
        # Multiple groups, show selection
        text = get_text(
            "group_management.select_group_for_action",
            user,
            command=command,
            target=target
        )
        
        keyboard = []
        for group in admin_groups[:10]:  # Limit to 10 groups
            keyboard.append([
                InlineKeyboardButton(
                    f"📋 {group['title'][:30]}",
                    callback_data=f"grpact_{group['chat_id']}"
                )
            ])
        
        keyboard.append([
            InlineKeyboardButton(
                get_text("buttons.cancel", user),
                callback_data="grpact_cancel"
            )
        ])
        
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    return True


async def execute_group_action(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    user,
    chat_id: int,
    chat_title: str
):
    """Execute the pending group action"""
    if user.id not in pending_actions:
        return
    
    action = pending_actions[user.id]
    command = action['command']
    target_user_id = action['target_user_id']
    target_username = action['target_username']
    reason = action['reason']
    
    # Get target user ID from username if needed
    if target_username and not target_user_id:
        try:
            # Try to get user by username
            # Note: This requires the user to have interacted with the bot
            # or be in a group with the bot
            # For now, we'll search in the group
            # This is a limitation of Telegram API
            await update.message.reply_text(
                get_text("group_management.searching_user", user, username=target_username),
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Try to find user in database
            user_from_db = db.get_user_by_username(target_username)
            if user_from_db:
                target_user_id = user_from_db['user_id']
            else:
                await update.message.reply_text(
                    get_text("group_management.user_not_found", user, username=target_username),
                    parse_mode=ParseMode.MARKDOWN
                )
                del pending_actions[user.id]
                return
        except Exception as e:
            logger.error(f"Error finding user by username: {e}")
            await update.message.reply_text(
                get_text("group_management.user_not_found", user, username=target_username),
                parse_mode=ParseMode.MARKDOWN
            )
            del pending_actions[user.id]
            return
    
    # Check if target is admin
    try:
        target_member = await context.bot.get_chat_member(chat_id, target_user_id)
        if target_member.status in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR]:
            await update.message.reply_text(
                get_text("admin.cannot_admin", user),
                parse_mode=ParseMode.MARKDOWN
            )
            del pending_actions[user.id]
            return
    except Exception as e:
        logger.warning(f"Could not check target member status: {e}")
    
    # Execute action
    try:
        target_user = await context.bot.get_chat(target_user_id)
        target_name = target_user.full_name or f"User {target_user_id}"
        target_mention = f"<a href='tg://user?id={target_user_id}'>{target_name}</a>"
    except:
        target_name = f"User {target_user_id}"
        target_mention = target_name
    
    success = False
    result_text = ""
    
    try:
        if command == "kick":
            await context.bot.ban_chat_member(chat_id, target_user_id)
            await context.bot.unban_chat_member(chat_id, target_user_id)
            db.increment_stat(chat_id, "kicked")
            db.log_action(chat_id, user.id, target_user_id, "kick", reason)
            result_text = get_text(
                "group_management.action_success",
                user,
                action="kicked",
                user=target_mention,
                group=chat_title,
                reason=reason
            )
            success = True
            
        elif command == "ban":
            await context.bot.ban_chat_member(chat_id, target_user_id)
            db.increment_stat(chat_id, "banned")
            db.log_action(chat_id, user.id, target_user_id, "ban", reason)
            result_text = get_text(
                "group_management.action_success",
                user,
                action="banned",
                user=target_mention,
                group=chat_title,
                reason=reason
            )
            success = True
            
        elif command == "unban":
            await context.bot.unban_chat_member(chat_id, target_user_id)
            db.log_action(chat_id, user.id, target_user_id, "unban", "")
            result_text = get_text(
                "group_management.action_success",
                user,
                action="unbanned",
                user=target_mention,
                group=chat_title,
                reason=""
            )
            success = True
            
        elif command == "mute":
            from datetime import datetime, timedelta
            from telegram import ChatPermissions
            
            mute_duration = 3600  # Default 1 hour
            until_date = datetime.now() + timedelta(seconds=mute_duration)
            
            await context.bot.restrict_chat_member(
                chat_id,
                target_user_id,
                permissions=ChatPermissions(can_send_messages=False),
                until_date=until_date
            )
            db.mute_user(target_user_id, chat_id, mute_duration)
            db.increment_stat(chat_id, "muted")
            db.log_action(chat_id, user.id, target_user_id, "mute", f"{mute_duration}s - {reason}")
            result_text = get_text(
                "group_management.action_success",
                user,
                action="muted",
                user=target_mention,
                group=chat_title,
                reason=reason
            )
            success = True
            
        elif command == "unmute":
            from telegram import ChatPermissions
            
            await context.bot.restrict_chat_member(
                chat_id,
                target_user_id,
                permissions=ChatPermissions(
                    can_send_messages=True,
                    can_send_audios=True,
                    can_send_documents=True,
                    can_send_photos=True,
                    can_send_videos=True,
                    can_send_video_notes=True,
                    can_send_voice_notes=True,
                    can_send_polls=True,
                    can_send_other_messages=True,
                    can_add_web_page_previews=True
                )
            )
            db.unmute_user(target_user_id, chat_id)
            db.log_action(chat_id, user.id, target_user_id, "unmute", "")
            result_text = get_text(
                "group_management.action_success",
                user,
                action="unmuted",
                user=target_mention,
                group=chat_title,
                reason=""
            )
            success = True
            
        elif command == "warn":
            group = db.get_group(chat_id)
            max_warns = group.get('warn_limit', 3) if group else 3
            
            db.create_or_update_user(
                target_user_id,
                chat_id,
                username=target_username,
                full_name=target_name
            )
            
            warn_count = db.add_warning(target_user_id, chat_id)
            db.increment_stat(chat_id, "warnings")
            db.log_action(chat_id, user.id, target_user_id, "warn", reason)
            
            if warn_count >= max_warns:
                # Kick user
                await context.bot.ban_chat_member(chat_id, target_user_id)
                await context.bot.unban_chat_member(chat_id, target_user_id)
                db.reset_warnings(target_user_id, chat_id)
                db.increment_stat(chat_id, "kicked")
                
                result_text = get_text(
                    "group_management.warn_kicked",
                    user,
                    user=target_mention,
                    group=chat_title,
                    max=max_warns
                )
            else:
                result_text = get_text(
                    "group_management.warn_success",
                    user,
                    user=target_mention,
                    group=chat_title,
                    current=warn_count,
                    max=max_warns,
                    reason=reason
                )
            success = True
            
    except Exception as e:
        logger.error(f"Failed to execute action {command}: {e}")
        result_text = get_text("admin.action_failed", user, error=str(e))
    
    # Clean up
    if user.id in pending_actions:
        del pending_actions[user.id]
    
    # Send result
    if hasattr(update, 'callback_query') and update.callback_query:
        await update.callback_query.edit_message_text(
            result_text,
            parse_mode=ParseMode.HTML
        )
    else:
        await update.message.reply_text(
            result_text,
            parse_mode=ParseMode.HTML
        )


async def group_action_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle group action selection callbacks"""
    query = update.callback_query
    user = query.from_user
    data = query.data
    
    await query.answer()
    
    if data == "grpact_cancel":
        if user.id in pending_actions:
            del pending_actions[user.id]
        
        await query.edit_message_text(
            get_text("group_management.action_cancelled", user),
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    if data.startswith("grpact_"):
        chat_id = int(data.split("_")[1])
        
        if user.id not in pending_actions:
            await query.edit_message_text(
                get_text("group_management.action_expired", user),
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # Find the group title
        groups = pending_actions[user.id].get('groups', [])
        group_title = "Unknown"
        for g in groups:
            if g['chat_id'] == chat_id:
                group_title = g['title']
                break
        
        # Create a fake update object for the execute function
        class FakeUpdate:
            callback_query = query
            message = None
        
        await execute_group_action(FakeUpdate(), context, user, chat_id, group_title)


async def group_management_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle group management callbacks from /mygroups"""
    query = update.callback_query
    user = query.from_user
    data = query.data
    
    await query.answer()
    
    if data.startswith("grpmgmt_select_"):
        chat_id = int(data.split("_")[2])
        
        try:
            chat = await context.bot.get_chat(chat_id)
            member_count = await chat.get_member_count()
            
            # Get group settings
            group = db.get_group(chat_id)
            
            text = get_text(
                "group_management.group_info",
                user,
                title=chat.title,
                chat_id=chat_id,
                members=member_count,
                verification="✅" if group.get('verification_enabled', True) else "❌",
                antiflood="✅" if group.get('antiflood_enabled', True) else "❌",
                antilink="✅" if group.get('antilink_enabled', False) else "❌",
                antispam="✅" if group.get('antispam_enabled', True) else "❌"
            )
            
            keyboard = [
                [InlineKeyboardButton(
                    get_text("group_management.open_settings", user),
                    url=f"https://t.me/{context.bot.username}?start=settings_{chat_id}"
                )],
                [InlineKeyboardButton(
                    get_text("settings.back_btn", user),
                    callback_data="grpmgmt_back"
                )]
            ]
            
            await query.edit_message_text(
                text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            logger.error(f"Error getting group info: {e}")
            await query.edit_message_text(
                get_text("group_management.group_not_accessible", user),
                parse_mode=ParseMode.MARKDOWN
            )
    
    elif data == "grpmgmt_back":
        # Go back to group list
        admin_groups = await get_user_admin_groups(user.id, context)
        
        if not admin_groups:
            await query.edit_message_text(
                get_text("group_management.no_groups", user),
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        text = get_text("group_management.your_groups", user, count=len(admin_groups)) + "\n\n"
        
        keyboard = []
        for i, group in enumerate(admin_groups[:20], 1):
            text += f"{i}. **{group['title']}**\n"
            keyboard.append([
                InlineKeyboardButton(
                    f"📋 {group['title'][:30]}",
                    callback_data=f"grpmgmt_select_{group['chat_id']}"
                )
            ])
        
        text += "\n\n" + get_text("group_management.select_group_hint", user)
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


async def owner_list_groups_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /listgroups command - Owner only - List all groups bot is in"""
    user = update.effective_user
    
    # Check if user is owner
    if not config.is_owner(user.id):
        await update.message.reply_text(
            get_text("owner_panel.not_owner", user),
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Get all groups
    all_groups = db.get_all_groups()
    
    if not all_groups:
        await update.message.reply_text(
            get_text("group_management.owner_no_groups", user),
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    text = get_text("group_management.owner_groups_title", user, count=len(all_groups)) + "\n\n"
    
    active_groups = []
    inactive_groups = []
    
    # Check which groups bot is still active in
    for group in all_groups[:50]:  # Limit to 50 groups
        chat_id = group['chat_id']
        try:
            chat = await context.bot.get_chat(chat_id)
            member_count = await chat.get_member_count()
            active_groups.append({
                'chat_id': chat_id,
                'title': chat.title or group.get('title', 'Unknown'),
                'members': member_count
            })
        except Exception as e:
            # Bot was removed or chat doesn't exist
            inactive_groups.append({
                'chat_id': chat_id,
                'title': group.get('title', 'Unknown')
            })
    
    if active_groups:
        text += "**✅ Active Groups:**\n"
        for i, g in enumerate(active_groups[:25], 1):
            text += f"{i}. {g['title']} | `{g['chat_id']}` | 👥 {g['members']}\n"
        
        if len(active_groups) > 25:
            text += f"... and {len(active_groups) - 25} more active groups\n"
    
    if inactive_groups:
        text += f"\n**❌ Inactive/Removed ({len(inactive_groups)}):**\n"
        for i, g in enumerate(inactive_groups[:10], 1):
            text += f"{i}. {g['title']} | `{g['chat_id']}`\n"
        
        if len(inactive_groups) > 10:
            text += f"... and {len(inactive_groups) - 10} more\n"
    
    text += f"\n**📊 Summary:**\n"
    text += f"Total in DB: {len(all_groups)}\n"
    text += f"Active: {len(active_groups)}\n"
    text += f"Inactive: {len(inactive_groups)}"
    
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
