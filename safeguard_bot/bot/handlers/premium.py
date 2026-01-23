"""
Premium Handler
===============
Handler for premium subscription features with:
- Pakasir QRIS payment integration for Indonesian users
- Crypto Pay (CryptoBot) payment integration for international users

Payment Methods:
- Indonesian users: QRIS (IDR prices calculated from USD * real-time exchange rate)
- International users: Cryptocurrency via Crypto Pay API (USDT, TON, BTC, etc.)
"""

import logging
import io
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from bot.config import config, INDONESIAN_CODES
from bot.services import get_text, db, detect_lang
from bot.services.pakasir import (
    pakasir_service, 
    PREMIUM_PLANS_IDR,
    PREMIUM_PLANS_USD,
    get_premium_features_id,
    get_premium_features_en,
    format_rupiah,
    format_usd
)
from bot.services.exchange_rate import exchange_rate_service
from bot.services.payment import payment_service, PREMIUM_PLANS

logger = logging.getLogger(__name__)


def is_indonesian_user(user) -> bool:
    """Check if user is Indonesian based on Telegram language settings"""
    if user is None:
        return False
    lang_code = getattr(user, 'language_code', None) or ''
    lang_code = lang_code.lower().split('-')[0]
    return lang_code in INDONESIAN_CODES


async def premium_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /premium command - Show premium menu"""
    user = update.effective_user
    lang = detect_lang(user)
    is_indonesian = is_indonesian_user(user)
    
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
        # Show premium features and plans based on language
        if is_indonesian:
            features = get_premium_features_id()
        else:
            features = get_premium_features_en()
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
        # Show available plans - IDR for Indonesian users, USD for international
        is_renewal = db.has_previous_subscription(user.id)
        is_indonesian = is_indonesian_user(user)
        
        # Get current exchange rate
        rate, rate_source = await exchange_rate_service.get_usd_to_idr_rate()
        
        # Get all plans with dynamic pricing
        plans_with_prices = await pakasir_service.get_all_plans_with_prices(lang)
        
        # Build header based on user region
        text = get_text("premium.select_plan", user)
        
        if is_indonesian:
            # Show exchange rate info for Indonesian users
            text += f"\n\n📈 **Kurs USD/IDR:** Rp {rate:,.0f}".replace(",", ".")
            text += f"\n_(Update: {rate_source})_"
        
        keyboard = []
        for plan_type, plan_info in plans_with_prices.items():
            price_idr = plan_info['price_idr']
            price_usd = plan_info['price_usd']
            name = plan_info['name']
            discount = plan_info['discount']
            
            # Build button text based on user region
            if is_indonesian:
                # Indonesian users: Show IDR only
                if discount > 0:
                    btn_text = f"{name} - {format_rupiah(price_idr)} (-{discount}%)"
                else:
                    btn_text = f"{name} - {format_rupiah(price_idr)}"
            else:
                # International users: Show USD only
                if discount > 0:
                    btn_text = f"{name} - ${price_usd:.0f} (-{discount}%)"
                else:
                    btn_text = f"{name} - ${price_usd:.0f}"
            
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
        is_indonesian = is_indonesian_user(user)
        
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
            # Show features based on language
            if is_indonesian:
                features = get_premium_features_id()
            else:
                features = get_premium_features_en()
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
        is_indonesian = is_indonesian_user(user)
        
        if plan_type not in PREMIUM_PLANS_USD:
            await query.answer(get_text("premium.invalid_plan", user), show_alert=True)
            return
        
        # For Indonesian users, use QRIS payment
        # For international users, use Crypto Pay API
        if not is_indonesian:
            # International users: Use Crypto Pay (CryptoBot) API
            plan_info = PREMIUM_PLANS_USD[plan_type]
            price_usd = plan_info['price_usd']
            name = plan_info['name']
            discount = plan_info['discount']
            
            # Check if Crypto Pay is configured
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
            
            # Create Crypto Pay invoice
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
            
            # Build payment info text
            text = f"**💳 Crypto Payment**\n\n"
            text += f"📦 Plan: **{name}**\n"
            text += f"💵 Price: **${price_usd:.0f} USDT**\n"
            if discount > 0:
                text += f"🏷️ Discount: **{discount}% OFF!**\n"
            text += f"⏱️ Duration: **{plan_info['duration_days']} days**\n"
            text += f"🆔 Invoice ID: `{invoice.invoice_id}`\n\n"
            text += "**💰 Supported Cryptocurrencies:**\n"
            text += "USDT, TON, BTC, ETH, LTC, BNB, TRX, USDC\n\n"
            text += "**📋 How to Pay:**\n"
            text += "1️⃣ Click 'Pay with Crypto' button below\n"
            text += "2️⃣ Select your preferred cryptocurrency\n"
            text += "3️⃣ Complete the payment\n"
            text += "4️⃣ Click 'Check Payment' after paying\n\n"
            text += f"⏰ Invoice expires in 1 hour"
            
            keyboard = [
                [InlineKeyboardButton(
                    "💳 Pay with Crypto",
                    url=invoice.bot_invoice_url
                )],
                [InlineKeyboardButton(
                    get_text("premium.check_payment_btn", user),
                    callback_data=f"premium_crypto_check_{invoice.invoice_id}"
                )],
                [InlineKeyboardButton(
                    get_text("premium.cancel_btn", user),
                    callback_data="premium_crypto_cancel"
                )]
            ]
            
            await query.edit_message_text(
                text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return
        
        # Indonesian users: Process QRIS payment
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
        
        # Get plan info with dynamic pricing before creating payment
        plan_info_dynamic = await pakasir_service.get_plan_info_dynamic(plan_type, lang)
        
        # Create QRIS payment via Pakasir (uses real-time exchange rate)
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
        plan_info = PREMIUM_PLANS_USD[plan_type]
        name = plan_info['name_id']
        price_usd = plan_info['price_usd']
        
        # Generate QR code image
        qr_image = pakasir_service.generate_qr_image_bytes(payment.qr_string)
        
        # Delete the loading message
        try:
            await query.message.delete()
        except:
            pass
        
        # Get exchange rate for display
        rate = plan_info_dynamic.get('exchange_rate', 16000) if plan_info_dynamic else 16000
        
        # Build payment info text for Indonesian users (IDR only)
        text = f"**📱 Pembayaran QRIS**\n\n"
        text += f"📦 Paket: **{name}**\n"
        text += f"💰 Harga: **{format_rupiah(payment.amount)}**\n"
        text += f"💳 Biaya Admin: **{format_rupiah(payment.fee)}**\n"
        text += f"💰 Total Bayar: **{format_rupiah(payment.total_payment)}**\n"
        text += f"⏱️ Durasi: **{plan_info['duration_days']} hari**\n"
        text += f"📈 Kurs: **Rp {rate:,.0f}/USD**\n".replace(",", ".")
        text += f"🆔 Order ID: `{payment.order_id}`\n\n"
        text += "**Cara Pembayaran:**\n"
        text += "1️⃣ Scan QR Code di atas\n"
        text += "2️⃣ Buka aplikasi e-wallet/mobile banking\n"
        text += "3️⃣ Pilih menu 'Scan QR' atau 'QRIS'\n"
        text += "4️⃣ Bayar sesuai nominal\n"
        text += "5️⃣ Klik 'Cek Pembayaran' setelah bayar\n\n"
        text += "✅ Mendukung: GoPay, OVO, DANA, ShopeePay, LinkAja, BCA, Mandiri, BRI, BNI, dll."
        
        keyboard = [
            [InlineKeyboardButton(
                get_text("premium.check_payment_btn", user),
                callback_data=f"premium_qris_check_{payment.order_id}"
            )],
            [InlineKeyboardButton(
                get_text("premium.cancel_btn", user),
                callback_data="premium_qris_cancel"
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
        return
    
    # Handle Crypto Pay check
    if data.startswith("premium_crypto_check_"):
        invoice_id = int(data.replace("premium_crypto_check_", ""))
        
        # Get payment from database
        payment_record = db.get_payment_by_invoice(invoice_id)
        if not payment_record:
            await query.answer(
                get_text("premium.invalid_data", user),
                show_alert=True
            )
            return
        
        # Check if already processed
        if payment_record['status'] == 'paid':
            await query.answer(
                "Payment already processed!",
                show_alert=True
            )
            return
        
        # Check invoice status with Crypto Pay
        status = await payment_service.check_invoice(invoice_id)
        
        if status == 'paid':
            # Process payment
            success = await payment_service.process_payment(invoice_id)
            
            if success:
                plan_info = PREMIUM_PLANS.get(payment_record['plan_type'], {})
                name = plan_info.get('name', payment_record['plan_type'])
                
                # Edit the message to show success
                await query.edit_message_text(
                    get_text(
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
        elif status == 'active':
            await query.answer(
                get_text("premium.payment_pending", user),
                show_alert=True
            )
        elif status == 'expired':
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
        return
    
    # Handle Crypto Pay cancel - go back to plans
    if data == "premium_crypto_cancel":
        # This is a text message, so we can edit it directly
        is_indonesian = is_indonesian_user(user)
        
        # Get current exchange rate
        rate, rate_source = await exchange_rate_service.get_usd_to_idr_rate()
        
        # Get all plans with dynamic pricing
        plans_with_prices = await pakasir_service.get_all_plans_with_prices(lang)
        
        # Build header based on user region
        text = get_text("premium.select_plan", user)
        
        if is_indonesian:
            text += f"\n\n📈 **Kurs USD/IDR:** Rp {rate:,.0f}".replace(",", ".")
            text += f"\n_(Update: {rate_source})_"
        
        keyboard = []
        for plan_type, plan_info in plans_with_prices.items():
            price_idr = plan_info['price_idr']
            price_usd = plan_info['price_usd']
            name = plan_info['name']
            discount = plan_info['discount']
            
            if is_indonesian:
                if discount > 0:
                    btn_text = f"{name} - {format_rupiah(price_idr)} (-{discount}%)"
                else:
                    btn_text = f"{name} - {format_rupiah(price_idr)}"
            else:
                if discount > 0:
                    btn_text = f"{name} - ${price_usd:.0f} (-{discount}%)"
                else:
                    btn_text = f"{name} - ${price_usd:.0f}"
            
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
    
    # Handle QRIS cancel - this is for photo messages
    if data == "premium_qris_cancel":
        # Delete the photo message first
        try:
            await query.message.delete()
        except Exception as e:
            logger.warning(f"Could not delete QRIS photo message: {e}")
        
        is_indonesian = is_indonesian_user(user)
        
        # Get current exchange rate
        rate, rate_source = await exchange_rate_service.get_usd_to_idr_rate()
        
        # Get all plans with dynamic pricing
        plans_with_prices = await pakasir_service.get_all_plans_with_prices(lang)
        
        # Build header based on user region
        text = get_text("premium.select_plan", user)
        
        if is_indonesian:
            text += f"\n\n📈 **Kurs USD/IDR:** Rp {rate:,.0f}".replace(",", ".")
            text += f"\n_(Update: {rate_source})_"
        
        keyboard = []
        for plan_type, plan_info in plans_with_prices.items():
            price_idr = plan_info['price_idr']
            price_usd = plan_info['price_usd']
            name = plan_info['name']
            discount = plan_info['discount']
            
            if is_indonesian:
                if discount > 0:
                    btn_text = f"{name} - {format_rupiah(price_idr)} (-{discount}%)"
                else:
                    btn_text = f"{name} - {format_rupiah(price_idr)}"
            else:
                if discount > 0:
                    btn_text = f"{name} - ${price_usd:.0f} (-{discount}%)"
                else:
                    btn_text = f"{name} - ${price_usd:.0f}"
            
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
        
        # Send a new message instead of editing (since we deleted the photo)
        await context.bot.send_message(
            chat_id=user.id,
            text=text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return


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
