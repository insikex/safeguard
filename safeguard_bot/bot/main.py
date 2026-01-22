"""
Safeguard Bot - Main Application
================================
Main entry point for the Telegram Safeguard Bot.
"""

import logging
import sys
from datetime import timedelta
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters
)

from bot.config import config
from bot.handlers import (
    # Start handlers
    start_command,
    help_command,
    rules_command,
    mystatus_command,
    start_callback,
    
    # Admin handlers
    warn_command,
    unwarn_command,
    kick_command,
    ban_command,
    unban_command,
    mute_command,
    unmute_command,
    stats_command,
    
    # Verification handlers
    new_member_handler,
    verification_callback,
    
    # Settings handlers
    settings_command,
    settings_callback,
    
    # Moderation handlers
    message_handler,
    check_new_bot,
    
    # Broadcast handlers
    create_broadcast_conversation,
    
    # Premium handlers
    premium_command,
    premium_callback,
    check_expired_subscriptions
)


# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=getattr(logging, config.log_level, logging.INFO),
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bot.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


def create_application() -> Application:
    """Create and configure the bot application"""
    
    # Validate config
    config.validate()
    
    # Create application
    application = Application.builder().token(config.token).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("rules", rules_command))
    application.add_handler(CommandHandler("mystatus", mystatus_command))
    
    # Admin commands
    application.add_handler(CommandHandler("settings", settings_command))
    application.add_handler(CommandHandler("warn", warn_command))
    application.add_handler(CommandHandler("unwarn", unwarn_command))
    application.add_handler(CommandHandler("kick", kick_command))
    application.add_handler(CommandHandler("ban", ban_command))
    application.add_handler(CommandHandler("unban", unban_command))
    application.add_handler(CommandHandler("mute", mute_command))
    application.add_handler(CommandHandler("unmute", unmute_command))
    application.add_handler(CommandHandler("stats", stats_command))
    
    # Premium command
    application.add_handler(CommandHandler("premium", premium_command))
    
    # Broadcast conversation handler (must be before other handlers)
    application.add_handler(create_broadcast_conversation())
    
    # Callback query handlers
    application.add_handler(CallbackQueryHandler(
        verification_callback,
        pattern=r"^verify_"
    ))
    application.add_handler(CallbackQueryHandler(
        settings_callback,
        pattern=r"^settings_"
    ))
    application.add_handler(CallbackQueryHandler(
        premium_callback,
        pattern=r"^premium_"
    ))
    application.add_handler(CallbackQueryHandler(
        start_callback,
        pattern=r"^start_"
    ))
    
    # New member handler
    application.add_handler(MessageHandler(
        filters.StatusUpdate.NEW_CHAT_MEMBERS,
        new_member_handler
    ))
    
    # Bot added to group (check for suspicious bots)
    application.add_handler(MessageHandler(
        filters.StatusUpdate.NEW_CHAT_MEMBERS,
        check_new_bot
    ))
    
    # Message handler for moderation (must be last)
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        message_handler
    ))
    
    # Error handler
    application.add_error_handler(error_handler)
    
    # Schedule jobs
    job_queue = application.job_queue
    
    # Job to check expired subscriptions (every 6 hours)
    job_queue.run_repeating(
        check_expired_subscriptions,
        interval=timedelta(hours=6),
        first=timedelta(minutes=10),
        name="check_expired_subscriptions"
    )
    
    logger.info("Scheduled jobs: check_expired_subscriptions")
    
    return application


async def error_handler(update: Update, context):
    """Handle errors"""
    logger.error(f"Exception while handling an update: {context.error}")
    
    # Log the error details
    if update:
        logger.error(f"Update that caused error: {update}")
    
    # Don't propagate the error
    return


def run_bot():
    """Run the bot"""
    logger.info("Starting Safeguard Bot...")
    
    # Create application
    application = create_application()
    
    # Run polling
    logger.info("Bot started! Running polling...")
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True
    )


if __name__ == "__main__":
    run_bot()
