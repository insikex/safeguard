"""
Settings Handlers
=================
Handlers for group settings management with inline keyboard.
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode, ChatMemberStatus

from bot.services import get_text, db, detect_lang, set_lang
from bot.utils import admin_required, group_only
from bot.config import SUPPORTED_LANGUAGES


@group_only
@admin_required
async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /settings command"""
    await show_settings_menu(update, context)


async def show_settings_menu(update_or_query, context: ContextTypes.DEFAULT_TYPE, edit: bool = False):
    """Show main settings menu"""
    if hasattr(update_or_query, 'callback_query'):
        query = update_or_query.callback_query
        user = query.from_user
        chat = update_or_query.effective_chat
    elif hasattr(update_or_query, 'message'):
        user = update_or_query.effective_user
        chat = update_or_query.effective_chat
        query = None
    else:
        query = update_or_query
        user = query.from_user
        chat = query.message.chat
    
    # Get group config
    group = db.get_group(chat.id)
    if not group:
        group = db.create_or_update_group(chat.id, title=chat.title)
    
    # Build keyboard
    keyboard = build_settings_keyboard(user, group)
    
    text = get_text("settings.title", user)
    
    if edit and query:
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
    elif query:
        await query.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await update_or_query.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )


def build_settings_keyboard(user, group: dict) -> list:
    """Build settings keyboard based on group config"""
    
    def status_icon(enabled: bool) -> str:
        return "✅" if enabled else "❌"
    
    keyboard = [
        # Welcome Message Toggle
        [InlineKeyboardButton(
            f"{status_icon(group.get('welcome_enabled', True))} {get_text('settings.welcome_toggle', user)}",
            callback_data="settings_toggle_welcome"
        )],
        
        # Verification Toggle
        [InlineKeyboardButton(
            f"{status_icon(group.get('verification_enabled', True))} {get_text('settings.verify_toggle', user)}",
            callback_data="settings_toggle_verify"
        )],
        
        # Anti-Flood Toggle
        [InlineKeyboardButton(
            f"{status_icon(group.get('antiflood_enabled', True))} {get_text('settings.antiflood_toggle', user)}",
            callback_data="settings_toggle_antiflood"
        )],
        
        # Anti-Link Toggle
        [InlineKeyboardButton(
            f"{status_icon(group.get('antilink_enabled', False))} {get_text('settings.antilink_toggle', user)}",
            callback_data="settings_toggle_antilink"
        )],
        
        # Anti-Spam Toggle
        [InlineKeyboardButton(
            f"{status_icon(group.get('antispam_enabled', True))} {get_text('settings.antispam_toggle', user)}",
            callback_data="settings_toggle_antispam"
        )],
        
        # Anti-Bad Word Toggle
        [InlineKeyboardButton(
            f"{status_icon(group.get('antibadword_enabled', False))} {get_text('settings.antibadword_toggle', user)}",
            callback_data="settings_toggle_antibadword"
        )],
        
        # Verification Type
        [InlineKeyboardButton(
            get_text(
                "settings.verify_type",
                user,
                type=get_text(f"settings.verify_types.{group.get('verification_type', 'button')}", user)
            ),
            callback_data="settings_verify_type"
        )],
        
        # Warning Limit
        [InlineKeyboardButton(
            get_text("settings.warn_limit", user, limit=group.get('warn_limit', 3)),
            callback_data="settings_warn_limit"
        )],
        
        # Language
        [InlineKeyboardButton(
            get_text("settings.language", user, lang=SUPPORTED_LANGUAGES.get(group.get('language', 'en'), 'English')),
            callback_data="settings_language"
        )],
        
        # Close Button
        [InlineKeyboardButton(
            get_text("settings.close_btn", user),
            callback_data="settings_close"
        )]
    ]
    
    return keyboard


async def settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle settings callback queries"""
    query = update.callback_query
    user = query.from_user
    chat = update.effective_chat
    data = query.data
    
    # Check if user is admin
    member = await chat.get_member(user.id)
    if member.status not in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR]:
        await query.answer(
            get_text("admin.not_admin", user),
            show_alert=True
        )
        return
    
    # Handle different callbacks
    if data.startswith("settings_toggle_"):
        await handle_toggle_setting(query, chat, user, data)
    
    elif data == "settings_verify_type":
        await show_verify_type_menu(query, user)
    
    elif data.startswith("settings_vtype_"):
        await handle_verify_type_selection(query, chat, user, data)
    
    elif data == "settings_warn_limit":
        await show_warn_limit_menu(query, user)
    
    elif data.startswith("settings_wlimit_"):
        await handle_warn_limit_selection(query, chat, user, data)
    
    elif data == "settings_language":
        await show_language_menu(query, user)
    
    elif data.startswith("settings_lang_"):
        await handle_language_selection(query, chat, user, data)
    
    elif data == "settings_back":
        await show_settings_menu(query, context, edit=True)
    
    elif data == "settings_close":
        await query.delete_message()
    
    await query.answer()


async def handle_toggle_setting(query, chat, user, data: str):
    """Handle toggle setting callbacks"""
    setting_map = {
        "settings_toggle_welcome": "welcome_enabled",
        "settings_toggle_verify": "verification_enabled",
        "settings_toggle_antiflood": "antiflood_enabled",
        "settings_toggle_antilink": "antilink_enabled",
        "settings_toggle_antispam": "antispam_enabled",
        "settings_toggle_antibadword": "antibadword_enabled"
    }
    
    setting_name = setting_map.get(data)
    if not setting_name:
        return
    
    # Get current value
    group = db.get_group(chat.id)
    current_value = group.get(setting_name, False) if group else False
    
    # Toggle value
    new_value = 0 if current_value else 1
    db.update_group_setting(chat.id, setting_name, new_value)
    
    # Refresh menu
    group = db.get_group(chat.id)
    keyboard = build_settings_keyboard(user, group)
    
    await query.edit_message_text(
        get_text("settings.title", user),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )


async def show_verify_type_menu(query, user):
    """Show verification type selection menu"""
    types = ["button", "math", "emoji", "portal"]
    
    keyboard = []
    for vtype in types:
        keyboard.append([InlineKeyboardButton(
            get_text(f"settings.verify_types.{vtype}", user),
            callback_data=f"settings_vtype_{vtype}"
        )])
    
    keyboard.append([InlineKeyboardButton(
        get_text("settings.back_btn", user),
        callback_data="settings_back"
    )])
    
    await query.edit_message_text(
        get_text("settings.select_verify_type", user),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )


async def handle_verify_type_selection(query, chat, user, data: str):
    """Handle verification type selection"""
    vtype = data.replace("settings_vtype_", "")
    
    db.update_group_setting(chat.id, "verification_type", vtype)
    
    # Show updated text
    await query.answer(get_text("settings.updated", user))
    
    # Return to main settings
    group = db.get_group(chat.id)
    keyboard = build_settings_keyboard(user, group)
    
    await query.edit_message_text(
        get_text("settings.title", user),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )


async def show_warn_limit_menu(query, user):
    """Show warning limit selection menu"""
    limits = [1, 2, 3, 4, 5]
    
    keyboard = []
    row = []
    for limit in limits:
        row.append(InlineKeyboardButton(
            str(limit),
            callback_data=f"settings_wlimit_{limit}"
        ))
        if len(row) == 3:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton(
        get_text("settings.back_btn", user),
        callback_data="settings_back"
    )])
    
    await query.edit_message_text(
        get_text("settings.select_warn_limit", user),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )


async def handle_warn_limit_selection(query, chat, user, data: str):
    """Handle warning limit selection"""
    limit = int(data.replace("settings_wlimit_", ""))
    
    db.update_group_setting(chat.id, "warn_limit", limit)
    
    await query.answer(get_text("settings.updated", user))
    
    # Return to main settings
    group = db.get_group(chat.id)
    keyboard = build_settings_keyboard(user, group)
    
    await query.edit_message_text(
        get_text("settings.title", user),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )


async def show_language_menu(query, user):
    """Show language selection menu"""
    keyboard = []
    
    for lang_code, lang_name in SUPPORTED_LANGUAGES.items():
        keyboard.append([InlineKeyboardButton(
            f"{'🇮🇩' if lang_code == 'id' else '🇺🇸'} {lang_name}",
            callback_data=f"settings_lang_{lang_code}"
        )])
    
    keyboard.append([InlineKeyboardButton(
        get_text("settings.back_btn", user),
        callback_data="settings_back"
    )])
    
    await query.edit_message_text(
        get_text("settings.select_language", user),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )


async def handle_language_selection(query, chat, user, data: str):
    """Handle language selection"""
    lang_code = data.replace("settings_lang_", "")
    
    if lang_code not in SUPPORTED_LANGUAGES:
        return
    
    db.update_group_setting(chat.id, "language", lang_code)
    
    # Also set user's language preference
    set_lang(user.id, lang_code)
    
    await query.answer(get_text("settings.updated", user))
    
    # Return to main settings with new language
    group = db.get_group(chat.id)
    keyboard = build_settings_keyboard(user, group)
    
    await query.edit_message_text(
        get_text("settings.title", user),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )
