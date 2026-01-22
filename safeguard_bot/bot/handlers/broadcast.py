"""
Broadcast Handler
=================
Handler for owner-only broadcast feature.
Broadcasts messages and photos to all bot users.
"""

import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from telegram.constants import ParseMode
from telegram.error import Forbidden, BadRequest

from bot.config import config
from bot.services import get_text, db, detect_lang

logger = logging.getLogger(__name__)

# Conversation states
WAITING_BROADCAST_CONTENT = 1
CONFIRM_BROADCAST = 2


def owner_only(func):
    """Decorator to restrict command to owner only"""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not config.is_owner(user.id):
            await update.message.reply_text(
                get_text("broadcast.not_owner", user),
                parse_mode=ParseMode.MARKDOWN
            )
            return ConversationHandler.END
        return await func(update, context)
    return wrapper


@owner_only
async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /broadcast command - Start broadcast process"""
    user = update.effective_user
    
    # Get user count
    user_count = db.get_bot_users_count(include_blocked=False)
    
    text = get_text(
        "broadcast.start",
        user,
        count=user_count
    )
    
    keyboard = [
        [InlineKeyboardButton(
            get_text("broadcast.cancel_btn", user),
            callback_data="broadcast_cancel"
        )]
    ]
    
    await update.message.reply_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    return WAITING_BROADCAST_CONTENT


async def receive_broadcast_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive broadcast content (text or photo with caption)"""
    user = update.effective_user
    message = update.message
    
    # Store broadcast content
    context.user_data['broadcast'] = {
        'text': None,
        'photo_file_id': None,
        'caption': None
    }
    
    if message.photo:
        # Photo with optional caption
        context.user_data['broadcast']['photo_file_id'] = message.photo[-1].file_id
        context.user_data['broadcast']['caption'] = message.caption or ""
        context.user_data['broadcast']['text'] = message.caption or ""
    elif message.text:
        # Text only
        context.user_data['broadcast']['text'] = message.text
    else:
        await message.reply_text(
            get_text("broadcast.invalid_content", user),
            parse_mode=ParseMode.MARKDOWN
        )
        return WAITING_BROADCAST_CONTENT
    
    # Get user count
    user_count = db.get_bot_users_count(include_blocked=False)
    
    # Show preview and confirmation
    preview_text = get_text(
        "broadcast.preview",
        user,
        count=user_count
    )
    
    keyboard = [
        [
            InlineKeyboardButton(
                get_text("broadcast.confirm_btn", user),
                callback_data="broadcast_confirm"
            ),
            InlineKeyboardButton(
                get_text("broadcast.cancel_btn", user),
                callback_data="broadcast_cancel"
            )
        ]
    ]
    
    # Send preview
    if context.user_data['broadcast']['photo_file_id']:
        await message.reply_photo(
            photo=context.user_data['broadcast']['photo_file_id'],
            caption=preview_text + "\n\n" + (context.user_data['broadcast']['caption'] or ""),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await message.reply_text(
            preview_text + "\n\n---\n\n" + context.user_data['broadcast']['text'],
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    return CONFIRM_BROADCAST


async def confirm_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle broadcast confirmation"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    
    if query.data == "broadcast_cancel":
        await query.edit_message_text(
            get_text("broadcast.cancelled", user),
            parse_mode=ParseMode.MARKDOWN
        )
        context.user_data.pop('broadcast', None)
        return ConversationHandler.END
    
    if query.data == "broadcast_confirm":
        broadcast_data = context.user_data.get('broadcast')
        if not broadcast_data:
            await query.edit_message_text(
                get_text("broadcast.error", user),
                parse_mode=ParseMode.MARKDOWN
            )
            return ConversationHandler.END
        
        # Start broadcast
        await query.edit_message_text(
            get_text("broadcast.sending", user),
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Get all users
        users = db.get_all_bot_users(include_blocked=False)
        total_users = len(users)
        
        # Create broadcast record
        broadcast_id = db.create_broadcast(
            message_text=broadcast_data['text'] or broadcast_data['caption'] or "",
            photo_file_id=broadcast_data['photo_file_id'],
            total_users=total_users
        )
        
        success_count = 0
        failed_count = 0
        
        # Send to all users
        for bot_user in users:
            try:
                if broadcast_data['photo_file_id']:
                    # Send photo
                    sent_message = await context.bot.send_photo(
                        chat_id=bot_user['user_id'],
                        photo=broadcast_data['photo_file_id'],
                        caption=broadcast_data['caption'],
                        parse_mode=ParseMode.MARKDOWN
                    )
                else:
                    # Send text
                    sent_message = await context.bot.send_message(
                        chat_id=bot_user['user_id'],
                        text=broadcast_data['text'],
                        parse_mode=ParseMode.MARKDOWN
                    )
                
                success_count += 1
                
                # Small delay to avoid rate limiting
                await asyncio.sleep(0.05)
                
            except Forbidden:
                # User blocked the bot
                db.mark_user_blocked(bot_user['user_id'])
                failed_count += 1
                logger.info(f"User {bot_user['user_id']} blocked the bot")
            except BadRequest as e:
                failed_count += 1
                logger.warning(f"Bad request for user {bot_user['user_id']}: {e}")
            except Exception as e:
                failed_count += 1
                logger.error(f"Error sending to user {bot_user['user_id']}: {e}")
        
        # Update broadcast stats
        db.update_broadcast_stats(broadcast_id, success_count, failed_count)
        
        # Send completion message
        await context.bot.send_message(
            chat_id=user.id,
            text=get_text(
                "broadcast.complete",
                user,
                total=total_users,
                success=success_count,
                failed=failed_count
            ),
            parse_mode=ParseMode.MARKDOWN
        )
        
        context.user_data.pop('broadcast', None)
        return ConversationHandler.END
    
    return CONFIRM_BROADCAST


async def cancel_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel broadcast operation"""
    user = update.effective_user
    context.user_data.pop('broadcast', None)
    
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            get_text("broadcast.cancelled", user),
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await update.message.reply_text(
            get_text("broadcast.cancelled", user),
            parse_mode=ParseMode.MARKDOWN
        )
    
    return ConversationHandler.END


# Broadcast conversation handler factory function
def create_broadcast_conversation() -> ConversationHandler:
    """Create and return the broadcast ConversationHandler.
    
    This is a factory function to avoid weak reference issues
    with python-telegram-bot 21.x when ConversationHandler is
    created at module level.
    """
    return ConversationHandler(
        entry_points=[CommandHandler("broadcast", broadcast_command)],
        states={
            WAITING_BROADCAST_CONTENT: [
                MessageHandler(filters.PHOTO | (filters.TEXT & ~filters.COMMAND), receive_broadcast_content)
            ],
            CONFIRM_BROADCAST: [
                CallbackQueryHandler(confirm_broadcast, pattern=r"^broadcast_")
            ]
        },
        fallbacks=[
            CommandHandler("cancel", cancel_broadcast),
            CallbackQueryHandler(cancel_broadcast, pattern=r"^broadcast_cancel$")
        ],
        per_user=True,
        per_message=False
    )
