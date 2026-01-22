"""
Admin Command Handlers
======================
Handlers for admin commands: warn, unwarn, kick, ban, mute, unmute, broadcast, etc.
"""

import logging
from telegram import Update, ChatPermissions
from telegram.ext import ContextTypes
from telegram.constants import ParseMode, ChatMemberStatus
from telegram.error import TelegramError
from datetime import datetime, timedelta

from bot.services import get_text, db, detect_lang
from bot.utils import (
    admin_required,
    group_only,
    get_user_display_name,
    parse_duration,
    format_duration,
    extract_reason_from_args,
    bot_owner_required
)

logger = logging.getLogger(__name__)


@group_only
@admin_required
async def warn_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /warn command"""
    user = update.effective_user
    chat = update.effective_chat
    lang = detect_lang(user)
    
    # Check if replying to a message
    if not update.message.reply_to_message:
        await update.message.reply_text(
            get_text("admin.need_reply", user),
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    target = update.message.reply_to_message.from_user
    
    # Can't warn self
    if target.id == user.id:
        await update.message.reply_text(
            get_text("admin.cannot_self", user),
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Can't warn admins
    target_member = await chat.get_member(target.id)
    if target_member.status in [ChatMemberStatus.CREATOR, ChatMemberStatus.ADMINISTRATOR]:
        await update.message.reply_text(
            get_text("admin.cannot_admin", user),
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Get reason
    reason = extract_reason_from_args(context.args)
    
    # Get group config
    group = db.get_group(chat.id)
    max_warns = group.get('warn_limit', 3) if group else 3
    
    # Ensure user exists in database
    db.create_or_update_user(
        target.id,
        chat.id,
        username=target.username,
        full_name=target.full_name
    )
    
    # Add warning
    warn_count = db.add_warning(target.id, chat.id)
    
    # Update statistics
    db.increment_stat(chat.id, "warnings")
    
    # Log action
    db.log_action(chat.id, user.id, target.id, "warn", reason)
    
    if warn_count >= max_warns:
        # Kick user
        try:
            await context.bot.ban_chat_member(chat.id, target.id)
            await context.bot.unban_chat_member(chat.id, target.id)  # Allow rejoin
            
            db.reset_warnings(target.id, chat.id)
            db.increment_stat(chat.id, "kicked")
            db.log_action(chat.id, user.id, target.id, "kick", f"Reached warn limit ({max_warns})")
            
            await update.message.reply_text(
                get_text(
                    "admin.warn_kicked",
                    user,
                    user=target.mention_html(),
                    max=max_warns
                ),
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            await update.message.reply_text(
                get_text("admin.action_failed", user, error=str(e)),
                parse_mode=ParseMode.MARKDOWN
            )
    else:
        remaining = max_warns - warn_count
        await update.message.reply_text(
            get_text(
                "admin.warn_success",
                user,
                current=warn_count,
                max=max_warns,
                user=target.mention_html(),
                reason=reason,
                remaining=remaining
            ),
            parse_mode=ParseMode.HTML
        )


@group_only
@admin_required
async def unwarn_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /unwarn command"""
    user = update.effective_user
    chat = update.effective_chat
    
    if not update.message.reply_to_message:
        await update.message.reply_text(
            get_text("admin.need_reply", user),
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    target = update.message.reply_to_message.from_user
    
    # Get current warnings
    user_data = db.get_user(target.id, chat.id)
    current_warns = user_data.get('warnings', 0) if user_data else 0
    
    if current_warns == 0:
        await update.message.reply_text(
            get_text("admin.unwarn_none", user, user=target.mention_html()),
            parse_mode=ParseMode.HTML
        )
        return
    
    # Remove warning
    new_count = db.remove_warning(target.id, chat.id)
    
    # Get max warns
    group = db.get_group(chat.id)
    max_warns = group.get('warn_limit', 3) if group else 3
    
    # Log action
    db.log_action(chat.id, user.id, target.id, "unwarn", "")
    
    await update.message.reply_text(
        get_text(
            "admin.unwarn_success",
            user,
            user=target.mention_html(),
            remaining=new_count,
            max=max_warns
        ),
        parse_mode=ParseMode.HTML
    )


@group_only
@admin_required
async def kick_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /kick command"""
    user = update.effective_user
    chat = update.effective_chat
    
    if not update.message.reply_to_message:
        await update.message.reply_text(
            get_text("admin.need_reply", user),
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    target = update.message.reply_to_message.from_user
    
    # Can't kick self
    if target.id == user.id:
        await update.message.reply_text(
            get_text("admin.cannot_self", user),
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Can't kick admins
    target_member = await chat.get_member(target.id)
    if target_member.status in [ChatMemberStatus.CREATOR, ChatMemberStatus.ADMINISTRATOR]:
        await update.message.reply_text(
            get_text("admin.cannot_admin", user),
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    reason = extract_reason_from_args(context.args)
    
    try:
        await context.bot.ban_chat_member(chat.id, target.id)
        await context.bot.unban_chat_member(chat.id, target.id)  # Allow rejoin
        
        db.increment_stat(chat.id, "kicked")
        db.log_action(chat.id, user.id, target.id, "kick", reason)
        
        await update.message.reply_text(
            get_text(
                "admin.kick_success",
                user,
                user=target.mention_html(),
                admin=user.mention_html(),
                reason=reason
            ),
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        await update.message.reply_text(
            get_text("admin.action_failed", user, error=str(e)),
            parse_mode=ParseMode.MARKDOWN
        )


@group_only
@admin_required
async def ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /ban command"""
    user = update.effective_user
    chat = update.effective_chat
    
    if not update.message.reply_to_message:
        await update.message.reply_text(
            get_text("admin.need_reply", user),
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    target = update.message.reply_to_message.from_user
    
    # Can't ban self
    if target.id == user.id:
        await update.message.reply_text(
            get_text("admin.cannot_self", user),
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Can't ban admins
    target_member = await chat.get_member(target.id)
    if target_member.status in [ChatMemberStatus.CREATOR, ChatMemberStatus.ADMINISTRATOR]:
        await update.message.reply_text(
            get_text("admin.cannot_admin", user),
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    reason = extract_reason_from_args(context.args)
    
    try:
        await context.bot.ban_chat_member(chat.id, target.id)
        
        db.increment_stat(chat.id, "banned")
        db.log_action(chat.id, user.id, target.id, "ban", reason)
        
        await update.message.reply_text(
            get_text(
                "admin.ban_success",
                user,
                user=target.mention_html(),
                admin=user.mention_html(),
                reason=reason
            ),
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        await update.message.reply_text(
            get_text("admin.action_failed", user, error=str(e)),
            parse_mode=ParseMode.MARKDOWN
        )


@group_only
@admin_required
async def unban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /unban command"""
    user = update.effective_user
    chat = update.effective_chat
    
    if not update.message.reply_to_message:
        await update.message.reply_text(
            get_text("admin.need_reply", user),
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    target = update.message.reply_to_message.from_user
    
    try:
        await context.bot.unban_chat_member(chat.id, target.id)
        
        db.log_action(chat.id, user.id, target.id, "unban", "")
        
        await update.message.reply_text(
            get_text(
                "admin.unban_success",
                user,
                user=target.mention_html(),
                admin=user.mention_html()
            ),
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        await update.message.reply_text(
            get_text("admin.action_failed", user, error=str(e)),
            parse_mode=ParseMode.MARKDOWN
        )


@group_only
@admin_required
async def mute_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /mute command"""
    user = update.effective_user
    chat = update.effective_chat
    lang = detect_lang(user)
    
    if not update.message.reply_to_message:
        await update.message.reply_text(
            get_text("admin.need_reply", user),
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    target = update.message.reply_to_message.from_user
    
    # Can't mute self
    if target.id == user.id:
        await update.message.reply_text(
            get_text("admin.cannot_self", user),
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Can't mute admins
    target_member = await chat.get_member(target.id)
    if target_member.status in [ChatMemberStatus.CREATOR, ChatMemberStatus.ADMINISTRATOR]:
        await update.message.reply_text(
            get_text("admin.cannot_admin", user),
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Parse duration (default 1 hour)
    duration = 3600  # Default 1 hour
    reason = "No reason"
    
    if context.args:
        parsed = parse_duration(context.args[0])
        if parsed:
            duration = parsed
            reason = extract_reason_from_args(context.args[1:])
        else:
            reason = extract_reason_from_args(context.args)
    
    try:
        until_date = datetime.now() + timedelta(seconds=duration)
        
        await context.bot.restrict_chat_member(
            chat.id,
            target.id,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=until_date
        )
        
        db.mute_user(target.id, chat.id, duration)
        db.increment_stat(chat.id, "muted")
        db.log_action(chat.id, user.id, target.id, "mute", f"{duration}s - {reason}")
        
        await update.message.reply_text(
            get_text(
                "admin.mute_success",
                user,
                user=target.mention_html(),
                admin=user.mention_html(),
                duration=format_duration(duration, lang),
                reason=reason
            ),
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        await update.message.reply_text(
            get_text("admin.action_failed", user, error=str(e)),
            parse_mode=ParseMode.MARKDOWN
        )


@group_only
@admin_required
async def unmute_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /unmute command"""
    user = update.effective_user
    chat = update.effective_chat
    
    if not update.message.reply_to_message:
        await update.message.reply_text(
            get_text("admin.need_reply", user),
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    target = update.message.reply_to_message.from_user
    
    try:
        await context.bot.restrict_chat_member(
            chat.id,
            target.id,
            permissions=ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True,
                can_send_polls=True
            )
        )
        
        db.unmute_user(target.id, chat.id)
        db.log_action(chat.id, user.id, target.id, "unmute", "")
        
        await update.message.reply_text(
            get_text(
                "admin.unmute_success",
                user,
                user=target.mention_html(),
                admin=user.mention_html()
            ),
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        await update.message.reply_text(
            get_text("admin.action_failed", user, error=str(e)),
            parse_mode=ParseMode.MARKDOWN
        )


@group_only
@admin_required
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /stats command"""
    user = update.effective_user
    chat = update.effective_chat
    
    # Get statistics
    stats = db.get_stats(chat.id, days=1)
    
    # Get member count
    try:
        member_count = await chat.get_member_count()
    except:
        member_count = "N/A"
    
    text = get_text("stats.title", user)
    text += get_text("stats.total_members", user, count=member_count) + "\n"
    text += get_text("stats.verified_today", user, count=stats.get("verified", 0)) + "\n"
    text += get_text("stats.kicked_today", user, count=stats.get("kicked", 0)) + "\n"
    text += get_text("stats.warnings_today", user, count=stats.get("warnings", 0)) + "\n"
    text += get_text("stats.messages_today", user, count=stats.get("messages", 0)) + "\n"
    text += get_text("stats.spam_blocked", user, count=stats.get("spam_blocked", 0)) + "\n"
    text += get_text("stats.links_blocked", user, count=stats.get("links_blocked", 0))
    
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


@bot_owner_required
async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /broadcast command - Send broadcast message with optional photo to all groups
    
    Usage:
    - /broadcast <message> - Send text broadcast
    - Reply to photo with /broadcast [caption] - Send photo broadcast
    
    Messages will be auto-pinned for 24 hours
    """
    user = update.effective_user
    message = update.message
    
    # Get broadcast content
    broadcast_text = None
    photo = None
    
    # Check if replying to a photo
    if message.reply_to_message and message.reply_to_message.photo:
        photo = message.reply_to_message.photo[-1].file_id  # Get highest resolution
        # Use caption from reply or from command args
        if context.args:
            broadcast_text = " ".join(context.args)
        elif message.reply_to_message.caption:
            broadcast_text = message.reply_to_message.caption
    elif context.args:
        broadcast_text = " ".join(context.args)
    
    # If no content provided, show usage
    if not broadcast_text and not photo:
        await message.reply_text(
            get_text("broadcast.usage", user),
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Get all groups
    groups = db.get_all_groups()
    
    if not groups:
        await message.reply_text(
            get_text("broadcast.no_groups", user),
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Format broadcast message with header and footer
    header = get_text("broadcast.header", user)
    footer = get_text("broadcast.footer", user)
    
    if broadcast_text:
        full_message = f"{header}{broadcast_text}{footer}"
    else:
        full_message = f"{header}{footer}"
    
    # Send status message
    total_groups = len(groups)
    status_message = await message.reply_text(
        get_text("broadcast.sending", user, total=total_groups),
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Track results
    success_count = 0
    failed_count = 0
    pinned_count = 0
    
    # Send broadcast to all groups
    for i, group in enumerate(groups):
        chat_id = group['chat_id']
        
        try:
            # Send the message
            if photo:
                sent_message = await context.bot.send_photo(
                    chat_id=chat_id,
                    photo=photo,
                    caption=full_message,
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                sent_message = await context.bot.send_message(
                    chat_id=chat_id,
                    text=full_message,
                    parse_mode=ParseMode.MARKDOWN
                )
            
            success_count += 1
            
            # Try to pin the message
            try:
                await context.bot.pin_chat_message(
                    chat_id=chat_id,
                    message_id=sent_message.message_id,
                    disable_notification=False
                )
                
                # Track the pinned message for auto-unpin after 24 hours
                db.add_pinned_broadcast(chat_id, sent_message.message_id, duration_hours=24)
                pinned_count += 1
                
            except TelegramError as pin_error:
                # Bot might not have pin permission, log but continue
                logger.warning(f"Failed to pin message in {chat_id}: {pin_error}")
            
            # Update progress every 10 groups
            if (i + 1) % 10 == 0:
                try:
                    await status_message.edit_text(
                        get_text("broadcast.progress", user, current=i+1, total=total_groups),
                        parse_mode=ParseMode.MARKDOWN
                    )
                except:
                    pass
                    
        except TelegramError as e:
            failed_count += 1
            logger.error(f"Failed to send broadcast to {chat_id}: {e}")
    
    # Send completion message
    await status_message.edit_text(
        get_text(
            "broadcast.completed",
            user,
            success=success_count,
            failed=failed_count,
            pinned=pinned_count
        ),
        parse_mode=ParseMode.MARKDOWN
    )


async def unpin_expired_broadcasts(context: ContextTypes.DEFAULT_TYPE):
    """
    Job to unpin expired broadcast messages
    This function is called periodically by the job queue
    """
    expired_pins = db.get_expired_pins()
    
    for pin in expired_pins:
        try:
            await context.bot.unpin_chat_message(
                chat_id=pin['chat_id'],
                message_id=pin['message_id']
            )
            logger.info(f"Unpinned broadcast in {pin['chat_id']}")
        except TelegramError as e:
            logger.warning(f"Failed to unpin message in {pin['chat_id']}: {e}")
        finally:
            # Remove from database regardless of result
            db.delete_pinned_broadcast(pin['chat_id'], pin['message_id'])
    
    # Cleanup any remaining expired records
    db.cleanup_expired_pins()
