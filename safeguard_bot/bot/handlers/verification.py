"""
Verification Handlers
=====================
Handlers for new member verification with CAPTCHA.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional

from telegram import Update, ChatPermissions, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from bot.services import get_text, db, detect_lang, captcha_service, CaptchaType
from bot.utils import get_user_display_name, format_duration
from bot.config import config


async def new_member_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle new member joining the group"""
    chat = update.effective_chat
    
    if chat.type == "private":
        return
    
    # Ensure group exists in database
    group = db.create_or_update_group(chat.id, title=chat.title)
    
    if not group.get('verification_enabled', True):
        # Verification disabled, just send welcome if enabled
        if group.get('welcome_enabled', True):
            for member in update.message.new_chat_members:
                if member.is_bot:
                    continue
                
                text = get_text(
                    "welcome.new_member",
                    member,
                    name=member.mention_html(),
                    group=chat.title
                )
                await update.message.reply_text(text, parse_mode=ParseMode.HTML)
        return
    
    for member in update.message.new_chat_members:
        if member.is_bot:
            continue
        
        # Create/update user in database
        db.create_or_update_user(
            member.id,
            chat.id,
            username=member.username,
            full_name=member.full_name,
            language=detect_lang(member),
            is_verified=False
        )
        
        # Get verification type
        verify_type = group.get('verification_type', 'button')
        timeout = config.verification_timeout
        
        # Restrict user
        try:
            await context.bot.restrict_chat_member(
                chat.id,
                member.id,
                permissions=ChatPermissions(can_send_messages=False)
            )
        except Exception as e:
            print(f"Failed to restrict member: {e}")
            continue
        
        # Generate CAPTCHA
        captcha = captcha_service.generate(verify_type)
        
        # Build verification message and keyboard
        message, keyboard = await build_verification_message(
            member, chat, captcha, verify_type, timeout
        )
        
        # Send verification message
        sent_message = await update.message.reply_text(
            message,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
        
        # Store pending verification
        db.create_pending_verification(
            user_id=member.id,
            chat_id=chat.id,
            verification_type=verify_type,
            answer=captcha.answer,
            message_id=sent_message.message_id,
            timeout=timeout
        )
        
        # Schedule timeout job
        context.job_queue.run_once(
            verification_timeout_callback,
            timeout,
            data={
                'user_id': member.id,
                'chat_id': chat.id,
                'message_id': sent_message.message_id
            },
            name=f"verify_timeout_{chat.id}_{member.id}"
        )


async def build_verification_message(
    user, chat, captcha, verify_type: str, timeout: int
) -> tuple:
    """Build verification message and keyboard based on type"""
    lang = detect_lang(user)
    
    # Base welcome text
    welcome_text = get_text(
        "welcome.new_member_verify",
        user,
        name=user.mention_html(),
        group=chat.title,
        timeout=timeout
    )
    
    if verify_type == "button":
        # Simple button verification
        text = welcome_text + "\n\n" + get_text("verification.button_prompt", user)
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton(
                get_text("verification.button_text", user),
                callback_data=f"verify_btn_{user.id}"
            )
        ]])
    
    elif verify_type == "math":
        # Math CAPTCHA
        text = welcome_text + "\n\n" + get_text(
            "verification.math_prompt",
            user,
            num1=captcha.question.split()[0],
            operator=captcha.question.split()[1],
            num2=captcha.question.split()[2]
        )
        
        # Create buttons for options
        buttons = []
        row = []
        for option in captcha.options:
            row.append(InlineKeyboardButton(
                option,
                callback_data=f"verify_math_{user.id}_{option}"
            ))
            if len(row) == 2:
                buttons.append(row)
                row = []
        if row:
            buttons.append(row)
        
        keyboard = InlineKeyboardMarkup(buttons)
    
    elif verify_type == "emoji":
        # Emoji CAPTCHA
        text = welcome_text + "\n\n" + get_text(
            "verification.emoji_prompt",
            user,
            emoji=captcha.question
        )
        
        # Create buttons for emoji options
        buttons = [[
            InlineKeyboardButton(
                emoji,
                callback_data=f"verify_emoji_{user.id}_{emoji}"
            )
            for emoji in captcha.options
        ]]
        
        keyboard = InlineKeyboardMarkup(buttons)
    
    elif verify_type == "portal":
        # Portal verification
        portal_url = f"{config.web_url}/verify?token={captcha.answer}&chat_id={chat.id}&user_id={user.id}"
        
        text = welcome_text + "\n\n" + get_text("verification.portal_prompt", user)
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton(
                get_text("verification.portal_button", user),
                url=portal_url
            )
        ]])
    
    else:
        # Default to button
        text = welcome_text + "\n\n" + get_text("verification.button_prompt", user)
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton(
                get_text("verification.button_text", user),
                callback_data=f"verify_btn_{user.id}"
            )
        ]])
    
    return text, keyboard


async def verification_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle verification button callbacks"""
    query = update.callback_query
    user = query.from_user
    chat = update.effective_chat
    data = query.data
    
    # Parse callback data
    parts = data.split('_')
    verify_type = parts[1]  # btn, math, emoji
    target_user_id = int(parts[2])
    
    # Check if this is the correct user
    if user.id != target_user_id:
        await query.answer(
            get_text("verification.wrong_user", user),
            show_alert=True
        )
        return
    
    # Get pending verification
    pending = db.get_pending_verification(user.id, chat.id)
    
    if not pending:
        await query.answer(
            get_text("verification.already_verified", user),
            show_alert=True
        )
        return
    
    # Get user's answer
    if verify_type == "btn":
        user_answer = "verify"
    elif verify_type in ["math", "emoji"]:
        user_answer = parts[3]
    else:
        user_answer = ""
    
    correct_answer = pending['answer']
    max_attempts = config.max_verification_attempts
    
    # Check answer
    if str(user_answer).strip() == str(correct_answer).strip():
        # Correct answer - verify user
        await verify_user_success(query, context, user, chat)
    else:
        # Wrong answer
        attempts = db.increment_verification_attempts(user.id, chat.id)
        
        if attempts >= max_attempts:
            # Max attempts reached - kick user
            await kick_failed_verification(query, context, user, chat, max_attempts)
        else:
            remaining = max_attempts - attempts
            await query.answer(
                get_text("verification.failed", user, attempts=remaining),
                show_alert=True
            )


async def verify_user_success(query, context, user, chat):
    """Handle successful verification"""
    # Remove restriction
    try:
        await context.bot.restrict_chat_member(
            chat.id,
            user.id,
            permissions=ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True,
                can_send_polls=True
            )
        )
    except Exception as e:
        print(f"Failed to unrestrict user: {e}")
    
    # Update database
    db.verify_user(user.id, chat.id)
    db.delete_pending_verification(user.id, chat.id)
    db.increment_stat(chat.id, "verified")
    
    # Cancel timeout job
    jobs = context.job_queue.get_jobs_by_name(f"verify_timeout_{chat.id}_{user.id}")
    for job in jobs:
        job.schedule_removal()
    
    # Edit message
    await query.edit_message_text(
        get_text("verification.success", user, name=user.mention_html()),
        parse_mode=ParseMode.HTML
    )
    
    await query.answer()


async def kick_failed_verification(query, context, user, chat, max_attempts: int):
    """Handle failed verification (max attempts)"""
    # Delete pending verification
    db.delete_pending_verification(user.id, chat.id)
    
    # Cancel timeout job
    jobs = context.job_queue.get_jobs_by_name(f"verify_timeout_{chat.id}_{user.id}")
    for job in jobs:
        job.schedule_removal()
    
    # Kick user
    try:
        await context.bot.ban_chat_member(chat.id, user.id)
        await context.bot.unban_chat_member(chat.id, user.id)  # Allow rejoin
    except Exception as e:
        print(f"Failed to kick user: {e}")
    
    db.increment_stat(chat.id, "kicked")
    
    # Edit message
    await query.edit_message_text(
        get_text("verification.max_attempts", user, name=user.mention_html(), max=max_attempts),
        parse_mode=ParseMode.HTML
    )


async def verification_timeout_callback(context: ContextTypes.DEFAULT_TYPE):
    """Handle verification timeout"""
    job = context.job
    data = job.data
    
    user_id = data['user_id']
    chat_id = data['chat_id']
    message_id = data['message_id']
    
    # Check if still pending
    pending = db.get_pending_verification(user_id, chat_id)
    
    if not pending:
        return  # Already verified or handled
    
    # Delete pending verification
    db.delete_pending_verification(user_id, chat_id)
    
    # Kick user
    try:
        await context.bot.ban_chat_member(chat_id, user_id)
        await context.bot.unban_chat_member(chat_id, user_id)  # Allow rejoin
    except Exception as e:
        print(f"Failed to kick user on timeout: {e}")
    
    db.increment_stat(chat_id, "kicked")
    
    # Try to get user info for message
    try:
        user = await context.bot.get_chat_member(chat_id, user_id)
        user_mention = user.user.mention_html() if user.user else f"User {user_id}"
    except:
        user_mention = f"User {user_id}"
    
    # Edit verification message
    try:
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=f"⏱️ **Time's Up!**\n\n{user_mention} was removed for not completing verification in time.",
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        print(f"Failed to edit message: {e}")


async def portal_verification_handler(user_id: int, chat_id: int, token: str, context):
    """Handle portal verification (called from web server)"""
    # Get pending verification
    pending = db.get_pending_verification(user_id, chat_id)
    
    if not pending:
        return False, "No pending verification found"
    
    if pending['answer'] != token:
        return False, "Invalid token"
    
    # Verify user
    try:
        await context.bot.restrict_chat_member(
            chat_id,
            user_id,
            permissions=ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True,
                can_send_polls=True
            )
        )
    except Exception as e:
        return False, str(e)
    
    # Update database
    db.verify_user(user_id, chat_id)
    db.delete_pending_verification(user_id, chat_id)
    db.increment_stat(chat_id, "verified")
    
    # Cancel timeout job
    jobs = context.job_queue.get_jobs_by_name(f"verify_timeout_{chat_id}_{user_id}")
    for job in jobs:
        job.schedule_removal()
    
    # Edit message
    try:
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=pending['message_id'],
            text=f"✅ **Verification Successful!**\n\nUser has been verified via portal.",
            parse_mode=ParseMode.MARKDOWN
        )
    except:
        pass
    
    return True, "Verification successful"
