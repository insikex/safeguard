"""
Broadcast Handler
=================
Handles broadcast messages from bot owner to all users.
Supports text and photo broadcasts with special formatting.
"""

import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters
from telegram.constants import ParseMode
from telegram.error import Forbidden, BadRequest

from bot.config import config
from bot.services import get_text, db, detect_lang
from bot.utils import get_user_display_name

logger = logging.getLogger(__name__)

# Conversation states
WAITING_BROADCAST_CONTENT = 1
CONFIRM_BROADCAST = 2


def owner_only(func):
    """Decorator to restrict command to bot owner only"""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = update.effective_user
        
        # Check if user is in admin_ids (first admin is considered owner)
        if not config.admin_ids or user.id != config.admin_ids[0]:
            await update.message.reply_text(
                get_text("broadcast.owner_only", user),
                parse_mode=ParseMode.MARKDOWN
            )
            return ConversationHandler.END
        
        return await func(update, context, *args, **kwargs)
    
    return wrapper


@owner_only
async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /broadcast command - Start broadcast process"""
    user = update.effective_user
    chat = update.effective_chat
    
    # Only in private chat
    if chat.type != "private":
        await update.message.reply_text(
            get_text("errors.private_only", user),
            parse_mode=ParseMode.MARKDOWN
        )
        return ConversationHandler.END
    
    # Get user count
    user_count = db.get_bot_users_count()
    
    text = get_text("broadcast.start", user, count=user_count)
    text += "\n\n" + get_text("broadcast.send_content", user)
    
    keyboard = [[
        InlineKeyboardButton(
            get_text("buttons.cancel", user),
            callback_data="broadcast_cancel"
        )
    ]]
    
    await update.message.reply_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    return WAITING_BROADCAST_CONTENT


async def receive_broadcast_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive broadcast content (text or photo)"""
    user = update.effective_user
    message = update.message
    
    # Store content in context
    context.user_data['broadcast'] = {}
    
    if message.photo:
        # Photo with caption
        context.user_data['broadcast']['type'] = 'photo'
        context.user_data['broadcast']['photo_id'] = message.photo[-1].file_id
        context.user_data['broadcast']['caption'] = message.caption or ""
        context.user_data['broadcast']['text'] = message.caption or ""
        
        preview_text = get_text("broadcast.preview_photo", user)
        if message.caption:
            preview_text += f"\n\n{message.caption}"
        
    elif message.text:
        # Text only
        context.user_data['broadcast']['type'] = 'text'
        context.user_data['broadcast']['text'] = message.text
        
        preview_text = get_text("broadcast.preview_text", user)
        preview_text += f"\n\n{message.text}"
    
    else:
        await message.reply_text(
            get_text("broadcast.unsupported_content", user),
            parse_mode=ParseMode.MARKDOWN
        )
        return WAITING_BROADCAST_CONTENT
    
    # Get user count
    user_count = db.get_bot_users_count()
    
    # Show preview and confirmation
    confirm_text = preview_text + "\n\n"
    confirm_text += get_text("broadcast.confirm", user, count=user_count)
    
    keyboard = [
        [
            InlineKeyboardButton(
                get_text("broadcast.send_all", user),
                callback_data="broadcast_confirm_all"
            )
        ],
        [
            InlineKeyboardButton(
                get_text("broadcast.send_premium", user),
                callback_data="broadcast_confirm_premium"
            )
        ],
        [
            InlineKeyboardButton(
                get_text("buttons.cancel", user),
                callback_data="broadcast_cancel"
            )
        ]
    ]
    
    if context.user_data['broadcast']['type'] == 'photo':
        await message.reply_photo(
            photo=context.user_data['broadcast']['photo_id'],
            caption=confirm_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await message.reply_text(
            confirm_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    return CONFIRM_BROADCAST


async def broadcast_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle broadcast confirmation callbacks"""
    query = update.callback_query
    user = update.effective_user
    data = query.data
    
    await query.answer()
    
    if data == "broadcast_cancel":
        context.user_data.pop('broadcast', None)
        await query.edit_message_text(
            get_text("broadcast.cancelled", user),
            parse_mode=ParseMode.MARKDOWN
        )
        return ConversationHandler.END
    
    elif data in ["broadcast_confirm_all", "broadcast_confirm_premium"]:
        # Start broadcasting
        broadcast_data = context.user_data.get('broadcast', {})
        
        if not broadcast_data:
            await query.edit_message_text(
                get_text("broadcast.no_content", user),
                parse_mode=ParseMode.MARKDOWN
            )
            return ConversationHandler.END
        
        # Get target users
        if data == "broadcast_confirm_premium":
            users = db.get_premium_users()
            target = "premium"
        else:
            users = db.get_all_bot_users()
            target = "all"
        
        if not users:
            await query.edit_message_text(
                get_text("broadcast.no_users", user),
                parse_mode=ParseMode.MARKDOWN
            )
            return ConversationHandler.END
        
        # Update message to show sending status
        await query.edit_message_text(
            get_text("broadcast.sending", user, count=len(users)),
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Create broadcast record
        broadcast_id = db.create_broadcast(
            admin_id=user.id,
            message_text=broadcast_data.get('text', ''),
            photo_file_id=broadcast_data.get('photo_id'),
            total_users=len(users)
        )
        
        # Send broadcasts
        success_count = 0
        failed_count = 0
        
        # Format broadcast message with special header
        broadcast_header = "📢 **BROADCAST MESSAGE**\n" + "─" * 20 + "\n\n"
        broadcast_footer = "\n\n" + "─" * 20 + "\n_dari Admin Safeguard Bot_"
        
        for bot_user in users:
            target_user_id = bot_user.get('user_id')
            
            try:
                if broadcast_data['type'] == 'photo':
                    caption = broadcast_header + broadcast_data.get('caption', '') + broadcast_footer
                    await context.bot.send_photo(
                        chat_id=target_user_id,
                        photo=broadcast_data['photo_id'],
                        caption=caption,
                        parse_mode=ParseMode.MARKDOWN
                    )
                else:
                    text = broadcast_header + broadcast_data['text'] + broadcast_footer
                    await context.bot.send_message(
                        chat_id=target_user_id,
                        text=text,
                        parse_mode=ParseMode.MARKDOWN
                    )
                
                success_count += 1
                
                # Small delay to avoid flood limits
                if success_count % 30 == 0:
                    await asyncio.sleep(1)
                    
            except Forbidden:
                # User blocked the bot
                failed_count += 1
                logger.debug(f"User {target_user_id} blocked the bot")
                
            except BadRequest as e:
                failed_count += 1
                logger.warning(f"Bad request for user {target_user_id}: {e}")
                
            except Exception as e:
                failed_count += 1
                logger.error(f"Failed to send broadcast to {target_user_id}: {e}")
            
            # Update progress every 50 users
            if (success_count + failed_count) % 50 == 0:
                db.update_broadcast_progress(broadcast_id, success=1 if success_count else 0, 
                                            failed=1 if failed_count else 0)
        
        # Complete broadcast
        db.update_broadcast_progress(broadcast_id, success=success_count, failed=failed_count)
        db.complete_broadcast(broadcast_id)
        
        # Send completion message
        result_text = get_text(
            "broadcast.completed", user,
            total=len(users),
            success=success_count,
            failed=failed_count
        )
        
        try:
            await query.edit_message_text(
                result_text,
                parse_mode=ParseMode.MARKDOWN
            )
        except:
            await context.bot.send_message(
                chat_id=user.id,
                text=result_text,
                parse_mode=ParseMode.MARKDOWN
            )
        
        # Cleanup
        context.user_data.pop('broadcast', None)
        return ConversationHandler.END
    
    return CONFIRM_BROADCAST


async def cancel_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel broadcast operation"""
    user = update.effective_user
    context.user_data.pop('broadcast', None)
    
    await update.message.reply_text(
        get_text("broadcast.cancelled", user),
        parse_mode=ParseMode.MARKDOWN
    )
    
    return ConversationHandler.END


# Stats command for owner
@owner_only
async def broadcast_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /botstats command - Show bot statistics"""
    user = update.effective_user
    
    # Get statistics
    total_users = db.get_bot_users_count()
    premium_users = len(db.get_premium_users())
    
    text = get_text("broadcast.stats_title", user) + "\n\n"
    text += get_text("broadcast.stats_users", user, count=total_users) + "\n"
    text += get_text("broadcast.stats_premium", user, count=premium_users) + "\n"
    
    # Calculate revenue (optional)
    # This would require additional database query
    
    await update.message.reply_text(
        text,
        parse_mode=ParseMode.MARKDOWN
    )


def get_broadcast_conversation_handler():
    """Get conversation handler for broadcast"""
    return ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex(r'^/broadcast$'), broadcast_command)
        ],
        states={
            WAITING_BROADCAST_CONTENT: [
                MessageHandler(filters.PHOTO | filters.TEXT & ~filters.COMMAND, 
                              receive_broadcast_content),
            ],
            CONFIRM_BROADCAST: [
                # Handled by callback
            ]
        },
        fallbacks=[
            MessageHandler(filters.Regex(r'^/cancel$'), cancel_broadcast),
        ],
        allow_reentry=True
    )
