"""
Premium Handler
===============
Handler for premium subscription features with CryptoBot payment integration.
"""

import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from bot.config import config
from bot.services import get_text, db, detect_lang
from bot.services.payment import payment_service, PREMIUM_PLANS, get_premium_features

logger = logging.getLogger(__name__)


async def premium_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /premium command - Show premium menu"""
    user = update.effective_user
    lang = detect_lang(user)
    
    # Check if user has active premium
    subscription = db.get_premium_subscription(user.id)
    
    if subscription:
        # Show premium status
        end_date = datetime.fromisoformat(subscription['end_date'])
        days_left = (end_date - datetime.now()).days
        
        text = get_text(
            "premium.active_status",
            user,
            plan=subscription['plan_type'].replace("_", " ").title(),
            end_date=end_date.strftime("%d %B %Y"),
            days_left=days_left
        )
        
        keyboard = [
            [InlineKeyboardButton(
                get_text("premium.extend_btn", user),
                callback_data="premium_plans"
            )],
            [InlineKeyboardButton(
                get_text("premium.close_btn", user),
                callback_data="premium_close"
            )]
        ]
    else:
        # Show premium features and plans
        features = get_premium_features(lang)
        features_text = "\n".join([f"• {f}" for f in features])
        
        text = get_text(
            "premium.intro",
            user,
            features=features_text
        )
        
        keyboard = [
            [InlineKeyboardButton(
                get_text("premium.view_plans_btn", user),
                callback_data="premium_plans"
            )],
            [InlineKeyboardButton(
                get_text("premium.close_btn", user),
                callback_data="premium_close"
            )]
        ]
    
    await update.message.reply_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def premium_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle premium-related callbacks"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    lang = detect_lang(user)
    data = query.data
    
    if data == "premium_close":
        await query.message.delete()
        return
    
    if data == "premium_plans":
        # Show available plans
        is_renewal = db.has_previous_subscription(user.id)
        
        text = get_text("premium.select_plan", user)
        
        keyboard = []
        for plan_type, plan_info in PREMIUM_PLANS.items():
            price = payment_service.get_plan_price(plan_type, is_renewal)
            name = plan_info['name_id'] if lang == 'id' else plan_info['name']
            
            # Build button text
            if plan_info['discount'] > 0:
                btn_text = f"{name} - ${price} ({plan_info['discount']}% OFF)"
            else:
                btn_text = f"{name} - ${price}"
            
            keyboard.append([
                InlineKeyboardButton(
                    btn_text,
                    callback_data=f"premium_buy_{plan_type}"
                )
            ])
        
        keyboard.append([
            InlineKeyboardButton(
                get_text("premium.back_btn", user),
                callback_data="premium_back"
            )
        ])
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    if data == "premium_back":
        # Go back to main premium menu
        subscription = db.get_premium_subscription(user.id)
        
        if subscription:
            end_date = datetime.fromisoformat(subscription['end_date'])
            days_left = (end_date - datetime.now()).days
            
            text = get_text(
                "premium.active_status",
                user,
                plan=subscription['plan_type'].replace("_", " ").title(),
                end_date=end_date.strftime("%d %B %Y"),
                days_left=days_left
            )
            
            keyboard = [
                [InlineKeyboardButton(
                    get_text("premium.extend_btn", user),
                    callback_data="premium_plans"
                )],
                [InlineKeyboardButton(
                    get_text("premium.close_btn", user),
                    callback_data="premium_close"
                )]
            ]
        else:
            features = get_premium_features(lang)
            features_text = "\n".join([f"• {f}" for f in features])
            
            text = get_text(
                "premium.intro",
                user,
                features=features_text
            )
            
            keyboard = [
                [InlineKeyboardButton(
                    get_text("premium.view_plans_btn", user),
                    callback_data="premium_plans"
                )],
                [InlineKeyboardButton(
                    get_text("premium.close_btn", user),
                    callback_data="premium_close"
                )]
            ]
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    if data.startswith("premium_buy_"):
        plan_type = data.replace("premium_buy_", "")
        
        if plan_type not in PREMIUM_PLANS:
            await query.answer(get_text("premium.invalid_plan", user), show_alert=True)
            return
        
        # Check if CryptoBot is configured
        if not payment_service.is_configured:
            await query.answer(
                get_text("premium.payment_not_configured", user),
                show_alert=True
            )
            return
        
        # Show loading message
        await query.edit_message_text(
            get_text("premium.creating_invoice", user),
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Check if renewal
        is_renewal = db.has_previous_subscription(user.id)
        
        # Create invoice
        invoice = await payment_service.create_invoice(
            user_id=user.id,
            plan_type=plan_type,
            is_renewal=is_renewal
        )
        
        if not invoice:
            await query.edit_message_text(
                get_text("premium.invoice_error", user),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(
                        get_text("premium.back_btn", user),
                        callback_data="premium_plans"
                    )
                ]])
            )
            return
        
        # Get plan info
        plan_info = PREMIUM_PLANS[plan_type]
        price = payment_service.get_plan_price(plan_type, is_renewal)
        name = plan_info['name_id'] if lang == 'id' else plan_info['name']
        
        text = get_text(
            "premium.payment_info",
            user,
            plan=name,
            price=price,
            duration=plan_info['duration_days']
        )
        
        keyboard = [
            [InlineKeyboardButton(
                get_text("premium.pay_btn", user),
                url=invoice.bot_invoice_url
            )],
            [InlineKeyboardButton(
                get_text("premium.check_payment_btn", user),
                callback_data=f"premium_check_{invoice.invoice_id}_{plan_type}"
            )],
            [InlineKeyboardButton(
                get_text("premium.cancel_btn", user),
                callback_data="premium_plans"
            )]
        ]
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    if data.startswith("premium_check_"):
        parts = data.split("_")
        if len(parts) < 4:
            await query.answer(get_text("premium.invalid_data", user), show_alert=True)
            return
        
        invoice_id = int(parts[2])
        plan_type = parts[3]
        
        # Check payment status
        status = await payment_service.check_invoice(invoice_id)
        
        if status == "paid":
            # Process payment
            success = await payment_service.process_payment(invoice_id)
            
            if success:
                plan_info = PREMIUM_PLANS[plan_type]
                name = plan_info['name_id'] if lang == 'id' else plan_info['name']
                
                await query.edit_message_text(
                    get_text(
                        "premium.payment_success",
                        user,
                        plan=name,
                        duration=plan_info['duration_days']
                    ),
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton(
                            get_text("premium.close_btn", user),
                            callback_data="premium_close"
                        )
                    ]])
                )
            else:
                await query.answer(
                    get_text("premium.processing_error", user),
                    show_alert=True
                )
        elif status == "active":
            await query.answer(
                get_text("premium.payment_pending", user),
                show_alert=True
            )
        elif status == "expired":
            await query.edit_message_text(
                get_text("premium.payment_expired", user),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(
                        get_text("premium.back_btn", user),
                        callback_data="premium_plans"
                    )
                ]])
            )
        else:
            await query.answer(
                get_text("premium.check_error", user),
                show_alert=True
            )


async def handle_paid_invoice(invoice):
    """Handle webhook callback when invoice is paid"""
    try:
        # Parse payload
        payload = invoice.payload
        parts = payload.split(":")
        if len(parts) != 3:
            logger.error(f"Invalid payload format: {payload}")
            return
        
        user_id = int(parts[0])
        plan_type = parts[1]
        is_renewal = parts[2] == "1"
        
        # Process payment
        success = await payment_service.process_payment(invoice.invoice_id)
        
        if success:
            logger.info(f"Premium activated for user {user_id} via webhook")
        
    except Exception as e:
        logger.error(f"Error handling paid invoice webhook: {e}")


async def check_expired_subscriptions(context: ContextTypes.DEFAULT_TYPE):
    """Job to check and deactivate expired subscriptions"""
    logger.info("Checking for expired subscriptions...")
    
    expired = db.get_expired_subscriptions()
    
    for sub in expired:
        db.deactivate_subscription(sub['id'])
        logger.info(f"Deactivated expired subscription for user {sub['user_id']}")
        
        # Optionally notify user
        try:
            await context.bot.send_message(
                chat_id=sub['user_id'],
                text="Your premium subscription has expired. Renew now to continue enjoying premium features!\n\nUse /premium to view available plans.",
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            logger.warning(f"Could not notify user {sub['user_id']} about expiration: {e}")
    
    if expired:
        logger.info(f"Processed {len(expired)} expired subscriptions")


def is_premium_user(user_id: int) -> bool:
    """Check if user has active premium subscription"""
    return db.is_premium_user(user_id)
