import requests
import json
import os
import random
import string
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.constants import ParseMode

# ============================================
# কনফিগ
# ============================================

API_BASE_URL = "https://jubayer-hosting-website.onrender.com"
BOT_TOKEN = "8752568477:AAEaFTaztdI81E6u70r2P8Abars0dRNbkcE"
ADMIN_IDS = [8254637769]
DB_FILE = "bot_database.json"
BOT_USERNAME = "ARAFAT_VPS_BOT"

FORCE_CHANNELS = [
    {"id": "@ARAFAT_SOURCE", "name": "Main Channel", "url": "https://t.me/ARAFAT_SOURCE"},
    {"id": "@ARAFAT_CODEX7", "name": "Main Channel", "url": "https://t.me/ARAFAT_CODEX7"},
    
    {"id": "@ARAFAT_FLEX", "name": "Channel 1", "url": "https://t.me/ARAFAT_FLEX"},
    {"id": "@ARAFAT_VPS_BOT", "name": "Channel 2", "url": "https://t.me/ARAFAT_VPS_BOT"}
]

# ============================================
# HTML Escape Helper
# ============================================

def h(text):
    """Safe HTML escape"""
    if not text:
        return ""
    return str(text).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

# ============================================
# ডাটাবেজ
# ============================================

def load_db():
    if not os.path.exists(DB_FILE):
        default = {"users": {}, "redeem_codes": {}, "total_panels": 0}
        save_db(default)
        return default
    with open(DB_FILE, 'r') as f:
        return json.load(f)

def save_db(data):
    with open(DB_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def get_user(user_id, first_name=None):
    db = load_db()
    user_id = str(user_id)
    if user_id not in db['users']:
        db['users'][user_id] = {
            'first_name': first_name,
            'username_tg': None,
            'referral_code': generate_referral_code(),
            'referral_count': 0,
            'total_referrals': 0,
            'panels': [],
            'redeem_used': False,
            'referred_by': None,
            'created_at': str(datetime.now())
        }
        save_db(db)
    elif first_name:
        db['users'][user_id]['first_name'] = first_name
        save_db(db)
    return db['users'][user_id]

def update_user(user_id, data):
    db = load_db()
    db['users'][str(user_id)] = data
    save_db(db)

def generate_referral_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

def generate_redeem_code():
    chars = string.ascii_uppercase + string.digits
    return f"J{''.join(random.choices(chars, k=4))}-{''.join(random.choices(chars, k=4))}-{''.join(random.choices(chars, k=4))}"

def is_admin(user_id):
    return user_id in ADMIN_IDS

# ============================================
# ফোর্স চ্যানেল
# ============================================

async def check_channel_subscription(context, user_id):
    not_subscribed = []
    for channel in FORCE_CHANNELS:
        try:
            member = await context.bot.get_chat_member(chat_id=channel['id'], user_id=user_id)
            if member.status in ['left', 'kicked']:
                not_subscribed.append(channel)
        except:
            not_subscribed.append(channel)
    return not_subscribed

async def show_subscription_message(update: Update, context: ContextTypes.DEFAULT_TYPE, not_subscribed):
    keyboard = []
    for channel in not_subscribed:
        keyboard.append([InlineKeyboardButton(f"📢 Join {channel['name']}", url=channel['url'])])
    keyboard.append([InlineKeyboardButton("✅ Verify", callback_data="check_sub")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    channels_text = '\n'.join([f"• {ch['name']}" for ch in not_subscribed])
    message_text = f"⚠️ <b>You must join our channels first!</b>\n\n{channels_text}\n\n<i>Join both then click ✅ Verify</i>"
    
    if update.callback_query:
        await update.callback_query.message.edit_text(message_text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
    elif update.message:
        await update.message.reply_text(message_text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
    return False

# ============================================
# API
# ============================================

def create_panel_api(username=None):
    try:
        params = {}
        if username:
            params['username'] = username
        resp = requests.get(f"{API_BASE_URL}/api/create", params=params, timeout=20)
        return resp.json()
    except Exception as e:
        return {'status': 'error', 'message': str(e)}

# ============================================
# মেনু
# ============================================

def get_user_menu():
    keyboard = [
        [KeyboardButton("🆕 Create Panel")],
        [KeyboardButton("📊 My Panels"), KeyboardButton("🔗 Referral")],
        [KeyboardButton("🎁 Redeem Code"), KeyboardButton("💳 Buy Panel")],
        [KeyboardButton("📞 Support"), KeyboardButton("👤 Profile")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_admin_menu():
    keyboard = [
        [KeyboardButton("🆕 Create Panel")],
        [KeyboardButton("📊 My Panels"), KeyboardButton("🔗 Referral")],
        [KeyboardButton("🎁 Redeem Code"), KeyboardButton("💳 Buy Panel")],
        [KeyboardButton("🎫 Generate Code")],
        [KeyboardButton("📋 All Panels"), KeyboardButton("👥 All Users")],
        [KeyboardButton("📞 Support"), KeyboardButton("👤 Profile")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ============================================
# ফর্ম্যাট
# ============================================

def format_panel(data):
    return (
        "<b>╔══════════════════════╗\n  ✅ Panel Created!\n╚══════════════════════╝</b>\n\n"
        f"🌐 <b>URL:</b> {h(data['full_url'])}\n"
        f"👤 <b>Username:</b> <code>{h(data['username'])}</code>\n"
        f"🔑 <b>Pass:</b> <code>{h(data['password'])}</code>\n"
        f"🆔 <b>Server ID:</b> <code>{h(data['server_id'].upper())}</code>\n"
        f"🖥️ <b>Type:</b> Python\n"
        f"💾 <b>RAM:</b> {h(data['ram'])} | 💿 <b>Disk:</b> {h(data['disk'])}\n"
        f"⏰ <b>Validity:</b> {h(data['validity'])}\n"
        f"📅 <b>Expiry:</b> {h(data['expiry_date'])}\n\n"
        "🔐 Login with details above!"
    )

# ============================================
# হ্যান্ডলার
# ============================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    
    not_subscribed = await check_channel_subscription(context, user_id)
    if not_subscribed:
        await show_subscription_message(update, context, not_subscribed)
        return
    
    first_name = user.first_name or "User"
    username_tg = user.username
    
    args = context.args
    referred_by = None
    
    if args:
        referral_code = args[0]
        db = load_db()
        
        existing_user = db['users'].get(str(user_id), {})
        already_referred = existing_user.get('referred_by') is not None
        
        if not already_referred:
            for uid, u_data in db['users'].items():
                if u_data.get('referral_code') == referral_code:
                    if str(user_id) != uid:
                        referred_by = uid
                        u_data['referral_count'] = u_data.get('referral_count', 0) + 1
                        u_data['total_referrals'] = u_data.get('total_referrals', 0) + 1
                        save_db(db)
                        
                        try:
                            can_claim = "🎁 You can claim a FREE panel!" if u_data['referral_count'] >= 5 else f"📌 Need {5 - u_data['referral_count']} more"
                            await context.bot.send_message(
                                chat_id=int(uid),
                                text=f"🔗 <b>New Referral!</b>\n👤 <b>User:</b> {h(first_name)}\n📊 <b>Available:</b> {u_data['referral_count']}/5\n\n{can_claim}",
                                parse_mode=ParseMode.HTML
                            )
                        except: pass
                    break
    
    db_user = get_user(user_id, first_name)
    db_user['username_tg'] = username_tg
    if referred_by and not db_user.get('referred_by'):
        db_user['referred_by'] = referred_by
    update_user(user_id, db_user)
    
    admin = is_admin(user_id)
    ref_code = db_user.get('referral_code', 'N/A')
    ref_link = f"https://t.me/{BOT_USERNAME}?start={ref_code}"
    
    if admin:
        msg = f"👑 Welcome Admin {h(first_name)}!"
        menu = get_admin_menu()
    else:
        msg = f"🚀 <b>Welcome {h(first_name)}!</b>\n\n🎁 5 Referrals = 1 FREE Panel!\n🔗 Ref Link: {ref_link}"
        menu = get_user_menu()
    
    await update.message.reply_text(msg, parse_mode=ParseMode.HTML, reply_markup=menu)

async def check_sub_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    
    not_subscribed = await check_channel_subscription(context, user_id)
    
    if not_subscribed:
        await show_subscription_message(update, context, not_subscribed)
        await query.answer("❌ Not joined yet!", show_alert=True)
    else:
        first_name = query.from_user.first_name or "User"
        db_user = get_user(user_id, first_name)
        ref_code = db_user.get('referral_code', 'N/A')
        ref_link = f"https://t.me/{BOT_USERNAME}?start={ref_code}"
        
        await query.message.edit_text("✅ <b>Verified!</b>", parse_mode=ParseMode.HTML)
        
        admin = is_admin(user_id)
        if admin:
            msg = f"👑 Welcome Admin {h(first_name)}!"
            menu = get_admin_menu()
        else:
            msg = f"🚀 <b>Welcome {h(first_name)}!</b>\n\n🎁 5 Referrals = 1 FREE Panel!\n🔗 Ref Link: {ref_link}"
            menu = get_user_menu()
        
        await context.bot.send_message(chat_id=user_id, text=msg, parse_mode=ParseMode.HTML, reply_markup=menu)
    
    await query.answer()

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user = update.effective_user
    user_id = user.id
    
    not_subscribed = await check_channel_subscription(context, user_id)
    if not_subscribed:
        await show_subscription_message(update, context, not_subscribed)
        return
    
    admin = is_admin(user_id)
    
    if text == "👤 Profile":
        db_user = get_user(user_id)
        ref_link = f"https://t.me/{BOT_USERNAME}?start={db_user.get('referral_code', 'N/A')}"
        
        msg = (
            f"👤 <b>Your Profile</b>\n"
            f"├─ ID: <code>{user_id}</code>\n"
            f"├─ Name: {h(user.first_name or 'N/A')}\n"
            f"├─ Available Referrals: {db_user.get('referral_count', 0)}/5\n"
            f"├─ Total Referrals: {db_user.get('total_referrals', 0)}\n"
            f"├─ Panels: {len(db_user.get('panels', []))}\n"
            f"└─ Ref Link: {ref_link}"
        )
        await update.message.reply_text(msg, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
    
    elif text == "🆕 Create Panel":
        db_user = get_user(user_id)
        ref_count = db_user.get('referral_count', 0)
        
        if not admin and ref_count < 5 and not db_user.get('redeem_used', False):
            remaining = 5 - ref_count
            await update.message.reply_text(
                f"⚠️ <b>Need 5 Referrals or Redeem Code!</b>\n\n📊 Available: {ref_count}/5\n📌 Need: {remaining} more\n\n💡 Share your referral link!\n🎁 Or use Redeem Code option",
                parse_mode=ParseMode.HTML
            )
            return
        
        msg = await update.message.reply_text("🔄 Creating panel...")
        result = create_panel_api(username=None)
        
        if result.get('status') == 'success':
            panel_data = {
                'server_id': result['server_id'], 'full_url': result['full_url'],
                'username': result['username'], 'password': result['password'],
                'created_at': str(datetime.now()), 'expiry': result['expiry_date']
            }
            
            if 'panels' not in db_user: db_user['panels'] = []
            if not any(p.get('server_id') == panel_data['server_id'] for p in db_user['panels']):
                db_user['panels'].append(panel_data)
            
            if not admin:
                if ref_count >= 5: db_user['referral_count'] = ref_count - 5
                db_user['redeem_used'] = False
            
            update_user(user_id, db_user)
            db = load_db()
            db['total_panels'] = db.get('total_panels', 0) + 1
            save_db(db)
            
            await msg.edit_text(format_panel(result), parse_mode=ParseMode.HTML)
            
            for aid in ADMIN_IDS:
                try:
                    await context.bot.send_message(aid, f"🆕 <b>New Panel!</b>\n👤 <code>{user_id}</code>\n🆔 <code>{h(result['server_id'])}</code>", parse_mode=ParseMode.HTML)
                except: pass
        else:
            await msg.edit_text(f"❌ {h(result.get('message', 'Failed!'))}", parse_mode=ParseMode.HTML)
    
    elif text == "📊 My Panels":
        db_user = get_user(user_id)
        panels = db_user.get('panels', [])
        if not panels:
            await update.message.reply_text("📊 No panels!")
            return
        msg = "📊 <b>Your Panels</b>\n\n"
        for i, p in enumerate(panels, 1):
            msg += f"<b>{i}.</b> 🆔 <code>{h(p['server_id'][:8].upper())}</code>\n   👤 <code>{h(p['username'])}</code> | 🔑 <code>{h(p['password'])}</code>\n   📅 {h(p.get('expiry', 'N/A'))}\n\n"
        await update.message.reply_text(msg, parse_mode=ParseMode.HTML)
    
    elif text == "🔗 Referral":
        db_user = get_user(user_id)
        ref_code = db_user.get('referral_code', 'N/A')
        ref_link = f"https://t.me/{BOT_USERNAME}?start={ref_code}"
        msg = f"🔗 <b>Your Referral</b>\n\n🎁 <b>5 Referrals = 1 FREE Panel</b>\n\n📊 Available: {db_user.get('referral_count', 0)}/5\n📈 Total: {db_user.get('total_referrals', 0)}\n\n🔗 <b>Link:</b> {ref_link}\n📋 <b>Code:</b> <code>{ref_code}</code>\n\n⚠️ Self-referral & duplicate not allowed!"
        await update.message.reply_text(msg, parse_mode=ParseMode.HTML)
    
    elif text == "🎁 Redeem Code":
        await update.message.reply_text("🎁 Send your redeem code:")
        context.user_data['awaiting_redeem'] = True
    
    elif text in ["💳 Buy Panel", "📞 Support"]:
        keyboard = [[InlineKeyboardButton("💬 Contact Admin", url="https://t.me/arafat_codex1")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        msg = "💳 <b>Buy Panel</b>\n\n├─ 3 Days: ৳50\n├─ 7 Days: ৳100\n└─ 30 Days: ৳300\n\n📞 Click below:" if text == "💳 Buy Panel" else "📞 <b>Support</b>\n\nClick below to contact!"
        await update.message.reply_text(msg, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
    
    elif text == "🎫 Generate Code" and admin:
        codes, db = [], load_db()
        for _ in range(5):
            code = generate_redeem_code()
            db['redeem_codes'][code] = {'used': False, 'used_by': None, 'created_at': str(datetime.now())}
            codes.append(code)
        save_db(db)
        await update.message.reply_text("🎫 <b>5 Codes!</b>\n\n" + '\n'.join(f"<code>{c}</code>" for c in codes), parse_mode=ParseMode.HTML)
    
    elif text == "📋 All Panels" and admin:
        db = load_db()
        msg = f"📋 <b>All Panels</b>\n👥 Users: {len(db['users'])}\n🖥️ Panels: {db.get('total_panels', 0)}\n\n"
        for uid, u_data in list(db['users'].items())[:10]:
            panels = u_data.get('panels', [])
            if panels:
                name = h(u_data.get('first_name', uid))
                msg += f"👤 <b>{name}</b> ({len(panels)})\n"
                for p in panels[-1:]: msg += f"  🆔 <code>{h(p['server_id'][:8].upper())}</code> | {h(p.get('expiry', 'N/A')[:10])}\n"
        await update.message.reply_text(msg, parse_mode=ParseMode.HTML)
    
    elif text == "👥 All Users" and admin:
        db = load_db()
        msg = "👥 <b>All Users</b>\n\n"
        for i, (uid, u_data) in enumerate(list(db['users'].items())[:20], 1):
            name = h(u_data.get('first_name', uid))
            msg += f"{i}. {name} - 🖥️{len(u_data.get('panels', []))} | 🔗{u_data.get('referral_count', 0)}/{u_data.get('total_referrals', 0)}\n"
        await update.message.reply_text(msg, parse_mode=ParseMode.HTML)
    
    elif context.user_data.get('awaiting_redeem'):
        code = text.strip().upper()
        db = load_db()
        if code in db['redeem_codes']:
            if not db['redeem_codes'][code]['used']:
                db['redeem_codes'][code]['used'] = True
                db['redeem_codes'][code]['used_by'] = str(user_id)
                save_db(db)
                db_user = get_user(user_id)
                db_user['redeem_used'] = True
                update_user(user_id, db_user)
                await update.message.reply_text("✅ Code Redeemed!\nUse 🆕 Create Panel now!", parse_mode=ParseMode.HTML)
            else:
                await update.message.reply_text("❌ Already used!")
        else:
            await update.message.reply_text("❌ Invalid code!")
        context.user_data['awaiting_redeem'] = False

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    pass

# ============================================
# মেইন
# ============================================

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(check_sub_callback, pattern="check_sub"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)
    
    print(f"🤖 Bot running...\nAPI: {API_BASE_URL}\nBot: @{BOT_USERNAME}")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == '__main__':
    main()