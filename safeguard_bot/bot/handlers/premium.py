"""
Premium Handler
===============
Handler for premium subscription features with Pakasir QRIS payment integration.
Supports Indonesian users with QRIS payment method.
"""

import logging
import io
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from bot.config import config
from bot.services import get_text, db, detect_lang
from bot.services.pakasir import (
    pakasir_service, 
    PREMIUM_PLANS_IDR, 
    get_premium_features_id,
    format_rupiah
)

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
        features = get_premium_features_id()
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
        # Show available plans with IDR pricing
        is_renewal = db.has_previous_subscription(user.id)
        
        text = get_text("premium.select_plan", user)
        
        keyboard = []
        for plan_type, plan_info in PREMIUM_PLANS_IDR.items():
            price = pakasir_service.get_plan_price(plan_type, is_renewal)
            name = plan_info['name_id']
            
            # Build button text with IDR price
            if plan_info['discount'] > 0:
                btn_text = f"{name} - {format_rupiah(price)} ({plan_info['discount']}% OFF)"
            else:
                btn_text = f"{name} - {format_rupiah(price)}"
            
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
            features = get_premium_features_id()
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
        
        if plan_type not in PREMIUM_PLANS_IDR:
            await query.answer(get_text("premium.invalid_plan", user), show_alert=True)
            return
        
        # Check if Pakasir is configured
        if not pakasir_service.is_configured:
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
        
        # Create QRIS payment via Pakasir
        payment = await pakasir_service.create_qris_payment(
            user_id=user.id,
            plan_type=plan_type,
            is_renewal=is_renewal
        )
        
        if not payment:
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
        plan_info = PREMIUM_PLANS_IDR[plan_type]
        name = plan_info['name_id']
        
        # Generate QR code image
        qr_image = pakasir_service.generate_qr_image_bytes(payment.qr_string)
        
        # Delete the loading message
        try:
            await query.message.delete()
        except:
            pass
        
        # Build payment info text
        text = get_text(
            "premium.qris_payment_info",
            user,
            plan=name,
            price=format_rupiah(payment.amount),
            fee=format_rupiah(payment.fee),
            total=format_rupiah(payment.total_payment),
            duration=plan_info['duration_days'],
            order_id=payment.order_id
        )
        
        keyboard = [
            [InlineKeyboardButton(
                get_text("premium.check_payment_btn", user),
                callback_data=f"premium_qris_check_{payment.order_id}"
            )],
            [InlineKeyboardButton(
                get_text("premium.cancel_btn", user),
                callback_data="premium_plans"
            )]
        ]
        
        if qr_image:
            # Send QR code as photo with caption
            await context.bot.send_photo(
                chat_id=user.id,
                photo=InputFile(io.BytesIO(qr_image), filename="qris_payment.png"),
                caption=text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            # Fallback: Send text only if QR generation fails
            text += f"\n\n⚠️ QR Code tidak dapat ditampilkan. Gunakan string berikut di aplikasi QRIS:\n`{payment.qr_string[:50]}...`"
            await context.bot.send_message(
                chat_id=user.id,
                text=text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        return
    
    if data.startswith("premium_qris_check_"):
        order_id = data.replace("premium_qris_check_", "")
        
        # Get payment from database
        payment_record = db.get_pakasir_payment_by_order(order_id)
        if not payment_record:
            await query.answer(
                get_text("premium.invalid_data", user),
                show_alert=True
            )
            return
        
        # Check payment status
        status = await pakasir_service.check_payment_status(
            order_id=order_id,
            amount=payment_record['amount']
        )
        
        if status and status.status == "completed":
            # Process payment
            success = await pakasir_service.process_payment(order_id)
            
            if success:
                plan_info = PREMIUM_PLANS_IDR.get(payment_record['plan_type'], {})
                name = plan_info.get('name_id', payment_record['plan_type'])
                
                # Delete the QR code message
                try:
                    await query.message.delete()
                except:
                    pass
                
                # Send success message
                await context.bot.send_message(
                    chat_id=user.id,
                    text=get_text(
                        "premium.payment_success",
                        user,
                        plan=name,
                        duration=plan_info.get('duration_days', 30)
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
        elif status and status.status == "pending":
            await query.answer(
                get_text("premium.payment_pending", user),
                show_alert=True
            )
        elif status and status.status == "expired":
            # Delete the QR code message
            try:
                await query.message.delete()
            except:
                pass
            
            # Send expired message
            await context.bot.send_message(
                chat_id=user.id,
                text=get_text("premium.payment_expired", user),
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


async def handle_pakasir_webhook(webhook_data: dict) -> bool:
    """
    Handle Pakasir webhook callback when payment is completed.
    Called from web server endpoint.
    """
    try:
        order_id = webhook_data.get("order_id")
        amount = webhook_data.get("amount")
        status = webhook_data.get("status")
        project = webhook_data.get("project")
        
        if not all([order_id, amount, status]):
            logger.error(f"Invalid webhook data: {webhook_data}")
            return False
        
        # Verify project matches our configuration
        if project != pakasir_service.project_slug:
            logger.warning(f"Project mismatch: {project} != {pakasir_service.project_slug}")
            return False
        
        if status != "completed":
            logger.info(f"Webhook status not completed: {status}")
            return False
        
        # Process payment
        success = await pakasir_service.process_payment(order_id)
        
        if success:
            logger.info(f"Premium activated for order {order_id} via webhook")
            return True
        
        return False
        
    except Exception as e:
        logger.error(f"Error handling Pakasir webhook: {e}")
        return False


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
                text="Langganan premium Anda telah berakhir. Perpanjang sekarang untuk terus menikmati fitur premium!\n\nGunakan /premium untuk melihat paket yang tersedia.",
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            logger.warning(f"Could not notify user {sub['user_id']} about expiration: {e}")
    
    if expired:
        logger.info(f"Processed {len(expired)} expired subscriptions")
    
    # Also cleanup expired Pakasir payments
    db.cleanup_expired_pakasir_payments()


def is_premium_user(user_id: int) -> bool:
    """Check if user has active premium subscription"""
    return db.is_premium_user(user_id)
