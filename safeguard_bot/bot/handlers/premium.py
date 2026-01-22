"""
Premium Handler
===============
Handles premium subscription features, payments, and premium-exclusive features.
"""

import logging
import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from bot.config import config
from bot.services import (
    get_text, db, detect_lang,
    crypto_pay, init_crypto_pay, get_plan_details, get_all_plans,
    PremiumPlan, PREMIUM_PLANS
)
from bot.utils import get_user_display_name

logger = logging.getLogger(__name__)


# Premium features list
PREMIUM_FEATURES = [
    "unlimited_groups",      # Unlimited group management
    "custom_welcome",        # Custom welcome messages with media
    "advanced_captcha",      # Advanced captcha types
    "priority_support",      # Priority support
    "no_ads",               # No promotional messages
    "custom_rules",         # Custom rules templates
    "analytics",            # Advanced analytics & reports
    "auto_moderation",      # AI-powered auto moderation
    "export_logs",          # Export moderation logs
    "custom_commands",      # Custom bot commands
]


async def premium_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /premium command - Show premium info and purchase options"""
    user = update.effective_user
    chat = update.effective_chat
    
    # Only in private chat
    if chat.type != "private":
        await update.message.reply_text(
            get_text("errors.private_only", user),
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Ensure user exists in bot_users
    db.create_or_update_bot_user(
        user.id,
        username=user.username,
        full_name=user.full_name
    )
    
    # Check current premium status
    premium_info = db.get_premium_info(user.id)
    is_premium = premium_info and premium_info.get('is_premium', False)
    
    await show_premium_menu(update, context, is_premium, premium_info)


async def show_premium_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                           is_premium: bool = False, premium_info: dict = None):
    """Show premium menu with options"""
    user = update.effective_user
    
    # Build premium info text
    if is_premium and premium_info:
        premium_until = premium_info.get('premium_until', 'N/A')
        try:
            if isinstance(premium_until, str):
                end_date = datetime.fromisoformat(premium_until)
            else:
                end_date = premium_until
            days_left = (end_date - datetime.now()).days
            premium_status = get_text("premium.status_active", user, 
                                     until=end_date.strftime("%d %B %Y"),
                                     days=days_left)
        except:
            premium_status = get_text("premium.status_active_simple", user)
    else:
        premium_status = get_text("premium.status_inactive", user)
    
    text = get_text("premium.title", user) + "\n\n"
    text += premium_status + "\n\n"
    text += get_text("premium.features_title", user) + "\n"
    text += get_text("premium.features_list", user) + "\n\n"
    text += get_text("premium.pricing_title", user) + "\n"
    
    # Show pricing
    for plan_key, plan in PREMIUM_PLANS.items():
        if plan.discount_percent > 0:
            text += f"• {plan.description}: ~${plan.original_price:.0f}~ **${plan.price:.0f}** ({plan.discount_percent}% OFF)\n"
        else:
            text += f"• {plan.description}: **${plan.price:.0f}**\n"
    
    text += "\n" + get_text("premium.payment_method", user)
    
    # Build keyboard
    keyboard = []
    
    # Plan buttons
    keyboard.append([
        InlineKeyboardButton(
            f"1 Bulan - ${PREMIUM_PLANS['monthly'].price:.0f}",
            callback_data="premium_buy_monthly"
        )
    ])
    keyboard.append([
        InlineKeyboardButton(
            f"3 Bulan - ${PREMIUM_PLANS['quarterly'].price:.0f} (40% OFF)",
            callback_data="premium_buy_quarterly"
        )
    ])
    keyboard.append([
        InlineKeyboardButton(
            f"6 Bulan - ${PREMIUM_PLANS['biannual'].price:.0f} (50% OFF)",
            callback_data="premium_buy_biannual"
        )
    ])
    
    # Additional buttons
    keyboard.append([
        InlineKeyboardButton(
            get_text("premium.check_payment", user),
            callback_data="premium_check_payment"
        )
    ])
    
    if is_premium:
        keyboard.append([
            InlineKeyboardButton(
                get_text("premium.my_subscription", user),
                callback_data="premium_my_sub"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton(
            get_text("buttons.back", user),
            callback_data="premium_close"
        )
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Send or edit message
    if update.callback_query:
        try:
            await update.callback_query.edit_message_text(
                text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
        except:
            await update.callback_query.message.reply_text(
                text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
    else:
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )


async def premium_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle premium-related callbacks"""
    query = update.callback_query
    user = update.effective_user
    data = query.data
    
    await query.answer()
    
    if data == "premium_close":
        await query.message.delete()
        return
    
    elif data.startswith("premium_buy_"):
        plan = data.replace("premium_buy_", "")
        await process_purchase(update, context, plan)
    
    elif data == "premium_check_payment":
        await check_pending_payments(update, context)
    
    elif data == "premium_my_sub":
        await show_subscription_info(update, context)
    
    elif data.startswith("premium_pay_"):
        invoice_id = data.replace("premium_pay_", "")
        await check_specific_payment(update, context, invoice_id)
    
    elif data == "premium_menu":
        premium_info = db.get_premium_info(user.id)
        is_premium = premium_info and premium_info.get('is_premium', False)
        await show_premium_menu(update, context, is_premium, premium_info)


async def process_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE, plan: str):
    """Process premium purchase"""
    query = update.callback_query
    user = update.effective_user
    
    plan_details = get_plan_details(plan)
    if not plan_details:
        await query.answer(get_text("premium.invalid_plan", user), show_alert=True)
        return
    
    # Check if CryptoBot is configured
    if not config.crypto_pay_token:
        await query.edit_message_text(
            get_text("premium.payment_unavailable", user),
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Initialize crypto pay if needed
    global crypto_pay
    from bot.services.payment import crypto_pay as cp, init_crypto_pay
    if cp is None:
        init_crypto_pay(config.crypto_pay_token, config.crypto_pay_testnet)
        from bot.services.payment import crypto_pay as cp
    
    # Show processing message
    await query.edit_message_text(
        get_text("premium.creating_invoice", user),
        parse_mode=ParseMode.MARKDOWN
    )
    
    try:
        # Create invoice via CryptoBot
        bot_info = await context.bot.get_me()
        paid_btn_url = f"https://t.me/{bot_info.username}?start=check_payment"
        
        invoice = await cp.create_invoice(
            user_id=user.id,
            plan=plan,
            description=f"Safeguard Bot {plan_details.description}",
            payload=f"{user.id}:{plan}",
            paid_btn_name="callback",
            paid_btn_url=paid_btn_url
        )
        
        if not invoice:
            await query.edit_message_text(
                get_text("premium.invoice_failed", user),
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # Save invoice to database
        db.create_invoice(
            user_id=user.id,
            invoice_id=str(invoice.get('invoice_id')),
            amount=plan_details.price,
            currency="USD",
            plan=plan,
            pay_url=invoice.get('pay_url', invoice.get('mini_app_invoice_url', ''))
        )
        
        # Show payment button
        pay_url = invoice.get('pay_url') or invoice.get('mini_app_invoice_url')
        
        text = get_text("premium.invoice_created", user,
                       plan=plan_details.description,
                       amount=plan_details.price)
        text += "\n\n" + get_text("premium.invoice_expires", user)
        
        keyboard = [
            [InlineKeyboardButton(
                get_text("premium.pay_now", user) + f" ${plan_details.price:.0f}",
                url=pay_url
            )],
            [InlineKeyboardButton(
                get_text("premium.check_payment", user),
                callback_data=f"premium_pay_{invoice.get('invoice_id')}"
            )],
            [InlineKeyboardButton(
                get_text("buttons.back", user),
                callback_data="premium_menu"
            )]
        ]
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        logger.error(f"Error creating invoice: {e}")
        await query.edit_message_text(
            get_text("premium.invoice_failed", user),
            parse_mode=ParseMode.MARKDOWN
        )


async def check_pending_payments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check all pending payments for user"""
    query = update.callback_query
    user = update.effective_user
    
    pending = db.get_pending_invoices(user.id)
    
    if not pending:
        await query.answer(get_text("premium.no_pending", user), show_alert=True)
        return
    
    # Check each pending invoice
    from bot.services.payment import crypto_pay as cp
    if cp is None:
        await query.answer(get_text("premium.payment_unavailable", user), show_alert=True)
        return
    
    found_paid = False
    
    for inv in pending:
        invoice_id = inv.get('invoice_id')
        try:
            status = await cp.get_invoice_status(invoice_id)
            
            if status == "paid":
                # Process successful payment
                await process_successful_payment(user.id, inv)
                found_paid = True
                
            elif status == "expired":
                db.update_invoice_status(invoice_id, "expired")
                
        except Exception as e:
            logger.error(f"Error checking invoice {invoice_id}: {e}")
    
    if found_paid:
        await query.edit_message_text(
            get_text("premium.payment_success", user),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(
                    get_text("premium.back_to_menu", user),
                    callback_data="premium_menu"
                )
            ]])
        )
    else:
        await query.answer(get_text("premium.no_paid_found", user), show_alert=True)


async def check_specific_payment(update: Update, context: ContextTypes.DEFAULT_TYPE, invoice_id: str):
    """Check specific payment status"""
    query = update.callback_query
    user = update.effective_user
    
    from bot.services.payment import crypto_pay as cp
    if cp is None:
        await query.answer(get_text("premium.payment_unavailable", user), show_alert=True)
        return
    
    try:
        status = await cp.get_invoice_status(invoice_id)
        
        if status == "paid":
            inv = db.get_invoice(invoice_id)
            if inv:
                await process_successful_payment(user.id, inv)
                
                await query.edit_message_text(
                    get_text("premium.payment_success", user),
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton(
                            get_text("premium.back_to_menu", user),
                            callback_data="premium_menu"
                        )
                    ]])
                )
            return
        
        elif status == "expired":
            db.update_invoice_status(invoice_id, "expired")
            await query.answer(get_text("premium.invoice_expired", user), show_alert=True)
            
        else:  # active/pending
            await query.answer(get_text("premium.payment_pending", user), show_alert=True)
            
    except Exception as e:
        logger.error(f"Error checking invoice {invoice_id}: {e}")
        await query.answer(get_text("errors.generic", user), show_alert=True)


async def process_successful_payment(user_id: int, invoice: dict):
    """Process a successful payment"""
    plan = invoice.get('plan')
    amount = invoice.get('amount', 0)
    invoice_id = invoice.get('invoice_id')
    
    plan_details = get_plan_details(plan)
    if not plan_details:
        logger.error(f"Invalid plan in invoice: {plan}")
        return
    
    # Update invoice status
    db.update_invoice_status(invoice_id, "paid")
    
    # Grant premium to user
    db.set_user_premium(
        user_id=user_id,
        plan=plan,
        duration_days=plan_details.duration_days,
        amount=amount
    )
    
    logger.info(f"Premium granted to user {user_id}: {plan} for {plan_details.duration_days} days")


async def show_subscription_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's subscription information"""
    query = update.callback_query
    user = update.effective_user
    
    premium_info = db.get_premium_info(user.id)
    
    if not premium_info or not premium_info.get('is_premium'):
        text = get_text("premium.no_subscription", user)
    else:
        try:
            premium_until = premium_info.get('premium_until')
            if isinstance(premium_until, str):
                end_date = datetime.fromisoformat(premium_until)
            else:
                end_date = premium_until
            
            days_left = (end_date - datetime.now()).days
            
            text = get_text("premium.subscription_info", user,
                           plan=premium_info.get('premium_plan', 'Premium'),
                           until=end_date.strftime("%d %B %Y"),
                           days=days_left,
                           total=premium_info.get('total_spent', 0))
        except Exception as e:
            logger.error(f"Error formatting subscription info: {e}")
            text = get_text("premium.subscription_active", user)
    
    keyboard = [[
        InlineKeyboardButton(
            get_text("premium.renew", user),
            callback_data="premium_menu"
        )
    ]]
    
    await query.edit_message_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# Premium feature checker decorator
def premium_required(func):
    """Decorator to check if user has premium"""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = update.effective_user
        
        if not db.check_premium_status(user.id):
            # Check if user is bot admin (bypass)
            if user.id in config.admin_ids:
                return await func(update, context, *args, **kwargs)
            
            text = get_text("premium.required", user)
            keyboard = [[
                InlineKeyboardButton(
                    get_text("premium.get_premium", user),
                    callback_data="premium_menu"
                )
            ]]
            
            if update.callback_query:
                await update.callback_query.answer(
                    get_text("premium.required_short", user),
                    show_alert=True
                )
            else:
                await update.message.reply_text(
                    text,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            return
        
        return await func(update, context, *args, **kwargs)
    
    return wrapper


async def check_payment_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start check_payment deep link"""
    user = update.effective_user
    
    # Check pending payments
    pending = db.get_pending_invoices(user.id)
    
    if not pending:
        await update.message.reply_text(
            get_text("premium.no_pending", user),
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    from bot.services.payment import crypto_pay as cp
    if cp is None:
        return
    
    for inv in pending:
        invoice_id = inv.get('invoice_id')
        try:
            status = await cp.get_invoice_status(invoice_id)
            
            if status == "paid":
                await process_successful_payment(user.id, inv)
                
                await update.message.reply_text(
                    get_text("premium.payment_success", user),
                    parse_mode=ParseMode.MARKDOWN
                )
                return
                
        except Exception as e:
            logger.error(f"Error checking invoice: {e}")
    
    await update.message.reply_text(
        get_text("premium.payment_pending", user),
        parse_mode=ParseMode.MARKDOWN
    )
