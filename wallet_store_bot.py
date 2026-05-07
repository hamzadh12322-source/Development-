"""
🤖 بوت متجر الخدمات + نظام المحفظة
=====================================
• شحن رصيد تلقائي (سرياتيل كاش / شام كاش)
• متجر خدمات بـ 5 أقسام
• سلة مشتريات
• نظام دعم فني
• لوحة تحكم الأدمن
"""

import logging
import asyncio
from datetime import datetime

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardRemove
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ConversationHandler, ContextTypes, filters
)

# استيراد الموديولات
from config import BOT_TOKEN, ADMIN_ID
from wallet_manager import (
    get_or_create_user, get_user, get_balance, add_balance,
    deduct_balance, get_user_transactions, get_stats, get_top_users,
    ban_user, unban_user, reset_user_balance, add_admin_note
)
from payment_api import (
    create_payment, check_payment_status, process_webhook,
    get_payment_methods, simulate_payment
)

# ───────────────────────────────────────────
# ⚙️ الإعدادات
# ───────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ───────────────────────────────────────────
# 🏪 بيانات المتجر (5 أقسام)
# ───────────────────────────────────────────
CATEGORIES = {
    "design": {
        "name": "🎨 تصميم",
        "services": [
            {
                "id": "logo_design",
                "name": "🎨 تصميم شعار احترافي",
                "price": 50000,
                "desc": "تصميم شعار فريد لعلامتك التجارية مع 3 تعديلات مجانية"
            },
            {
                "id": "social_design",
                "name": "📱 تصميم منشورات سوشل ميديا",
                "price": 25000,
                "desc": "10 تصاميم احترافية لمنشورات انستغرام وفيسبوك"
            },
            {
                "id": "banner_design",
                "name": "🖼️ تصميم بانر وغلاف",
                "price": 35000,
                "desc": "تصميم بانر لقناة يوتيوب أو غلاف فيسبوك"
            }
        ]
    },
    "writing": {
        "name": "✍️ كتابة محتوى",
        "services": [
            {
                "id": "article_write",
                "name": "📝 كتابة مقال SEO",
                "price": 30000,
                "desc": "مقال 1000 كلمة محسن لمحركات البحث مع صور"
            },
            {
                "id": "script_write",
                "name": "📹 كتابة سكريبت فيديو",
                "price": 40000,
                "desc": "سكريبت احترافي لفيديو يوتيوب أو تيك توك (2-5 دقائق)"
            }
        ]
    },
    "programming": {
        "name": "💻 برمجة",
        "services": [
            {
                "id": "web_page",
                "name": "🌐 تصميم صفحة ويب",
                "price": 100000,
                "desc": "صفحة هبوط احترافية متجاوبة مع جميع الأجهزة"
            },
            {
                "id": "bot_dev",
                "name": "🤖 برمجة بوت تلجرام",
                "price": 150000,
                "desc": "بوت تلجرام مخصص حسب طلبك مع لوحة تحكم"
            }
        ]
    },
    "translation": {
        "name": "🌍 ترجمة",
        "services": [
            {
                "id": "translate_en_ar",
                "name": "🇬🇧➡️🇸🇾 ترجمة إنجليزي-عربي",
                "price": 20000,
                "desc": "ترجمة احترافية لـ 1000 كلمة مع مراجعة لغوية"
            },
            {
                "id": "translate_tr_ar",
                "name": "🇹🇷➡️🇸🇾 ترجمة تركي-عربي",
                "price": 25000,
                "desc": "ترجمة احترافية لـ 1000 كلمة مع مراجعة لغوية"
            }
        ]
    },
    "marketing": {
        "name": "📢 تسويق",
        "services": [
            {
                "id": "ads_manage",
                "name": "📊 إدارة حملات إعلانية",
                "price": 75000,
                "desc": "إدارة حملات فيسبوك وانستغرام إعلانية لمدة شهر"
            },
            {
                "id": "seo_opt",
                "name": "🔍 تحسين SEO",
                "price": 60000,
                "desc": "تحسين موقعك لمحركات البحث مع تقرير شامل"
            }
        ]
    }
}

# ───────────────────────────────────────────
# 🔄 حالات المحادثة
# ───────────────────────────────────────────
(
    MAIN_MENU, DEPOSIT_MENU, DEPOSIT_AMOUNT, DEPOSIT_METHOD,
    DEPOSIT_CONFIRM, DEPOSIT_VERIFY, STORE_MENU, CATEGORY_MENU,
    SERVICE_DETAILS, CART_VIEW, CHECKOUT_CONFIRM, SUPPORT_MESSAGE,
    ADMIN_PANEL, ADMIN_USER_SEARCH, ADMIN_USER_ACTION,
    WALLET_HISTORY, TRANSFER_AMOUNT, TRANSFER_USER
) = range(18)

# ───────────────────────────────────────────
# 🔧 دوال مساعدة
# ───────────────────────────────────────────

def format_price(price):
    """تنسيق السعر"""
    return f"{price:,} ل.س"

def get_user_cart(user_id, context):
    """الحصول على سلة المستخدم"""
    key = f"cart_{user_id}"
    return context.bot_data.get(key, [])

def add_to_cart(user_id, service, context):
    """إضافة للسلة"""
    key = f"cart_{user_id}"
    cart = context.bot_data.get(key, [])
    cart.append(service)
    context.bot_data[key] = cart
    return True

def remove_from_cart(user_id, index, context):
    """حذف من السلة"""
    key = f"cart_{user_id}"
    cart = context.bot_data.get(key, [])
    if 0 <= index < len(cart):
        cart.pop(index)
        context.bot_data[key] = cart
        return True
    return False

def clear_cart(user_id, context):
    """إفراغ السلة"""
    key = f"cart_{user_id}"
    context.bot_data[key] = []

def get_cart_total(user_id, context):
    """مجموع السلة"""
    cart = get_user_cart(user_id, context)
    return sum(item["price"] for item in cart)

def find_service(service_id):
    """البحث عن خدمة"""
    for cat in CATEGORIES.values():
        for s in cat["services"]:
            if s["id"] == service_id:
                return s, cat
    return None, None

# ───────────────────────────────────────────
# 🏠 القائمة الرئيسية
# ───────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج /start"""
    user = update.effective_user
    user_id = user.id

    # تسجيل/تحديث المستخدم
    db_user = get_or_create_user(user_id, user.first_name, user.username)
    balance = get_balance(user_id)

    welcome_text = f"""
👋 أهلاً *{user.first_name}*!

🏪 *متجر الخدمات الاحترافية*

💰 *رصيدك الحالي:* `{format_price(balance)}`

🛒 *الخدمات المتاحة:*
• 🎨 تصميم جرافيك
• ✍️ كتابة محتوى
• 💻 برمجة وتطوير
• 🌍 ترجمة احترافية
• 📢 تسويق رقمي

👇 اختر من القائمة:
"""

    keyboard = [
        [InlineKeyboardButton("💰 شحن رصيد", callback_data="deposit")],
        [InlineKeyboardButton("🛍️ تصفح المتجر", callback_data="browse_store")],
        [InlineKeyboardButton("🛒 سلة المشتريات", callback_data="view_cart")],
        [InlineKeyboardButton("📋 طلباتي", callback_data="my_orders")],
        [InlineKeyboardButton("💳 محفظتي", callback_data="my_wallet")],
        [InlineKeyboardButton("📞 التواصل مع الدعم", callback_data="support")],
    ]

    if user.id == ADMIN_ID:
        keyboard.append([InlineKeyboardButton("⚙️ لوحة التحكم", callback_data="admin_panel")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.message:
        await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        await update.callback_query.edit_message_text(welcome_text, reply_markup=reply_markup, parse_mode="Markdown")

    return MAIN_MENU

# ───────────────────────────────────────────
# 💰 نظام الشحن (المحفظة)
# ───────────────────────────────────────────

async def deposit_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """قائمة الشحن"""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    balance = get_balance(user_id)

    text = f"""
💰 *شحن رصيد*

رصيدك الحالي: `{format_price(balance)}`

💳 *طرق الدفع المتاحة:*
"""

    methods = get_payment_methods()
    keyboard = []

    for method in methods:
        text += f"\n📱 *{method['name']}*"
        text += f"\n   الحد الأدنى: {format_price(method['min'])}"
        text += f"\n   الحد الأقصى: {format_price(method['max'])}"
        keyboard.append([InlineKeyboardButton(
            f"💳 {method['name']}",
            callback_data=f"deposit_method_{method['id']}"
        )])

    keyboard.extend([
        [InlineKeyboardButton("📜 سجل الشحن", callback_data="deposit_history")],
        [InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="main_menu")]
    ])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    return DEPOSIT_MENU

async def deposit_select_method(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """اختيار طريقة الشحن"""
    query = update.callback_query
    await query.answer()

    method = query.data.replace("deposit_method_", "")
    context.user_data["deposit_method"] = method

    method_names = {"syriatel": "سرياتيل كاش", "sham": "شام كاش"}
    method_name = method_names.get(method, method)

    text = f"""
💰 *شحن عبر {method_name}*

أرسل المبلغ اللي بدك تشحنه (بالأرقام):

مثال: `50000`
"""

    keyboard = [[InlineKeyboardButton("❌ إلغاء", callback_data="main_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")

    return DEPOSIT_AMOUNT

async def deposit_enter_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إدخال مبلغ الشحن"""
    user_id = update.effective_user.id

    try:
        amount = int(update.message.text.replace(",", "").replace(" ", ""))

        if amount < 10000:
            await update.message.reply_text("❌ الحد الأدنى للشحن هو 10,000 ل.س")
            return DEPOSIT_AMOUNT

        if amount > 1000000:
            await update.message.reply_text("❌ الحد الأقصى للشحن هو 1,000,000 ل.س")
            return DEPOSIT_AMOUNT

        context.user_data["deposit_amount"] = amount
        method = context.user_data.get("deposit_method", "syriatel")

        # إنشاء طلب دفع
        payment = create_payment(
            amount=amount,
            phone="",
            method=method,
            user_id=user_id,
            description=f"شحن رصيد - {amount:,} ل.س"
        )

        if not payment["success"]:
            await update.message.reply_text(f"❌ خطأ: {payment.get('error', 'غير معروف')}")
            return DEPOSIT_AMOUNT

        # حفظ معلومات الدفع
        context.user_data["payment_id"] = payment["payment_id"]

        text = f"""
💰 *طلب شحن جديد*

🆔 *رقم الطلب:* `{payment['payment_id']}`
💰 *المبلغ:* `{format_price(amount)}`
📱 *الطريقة:* {method}

{payment['instructions']}

✅ بعد إتمام الدفع، اضغط "تم الدفع" أدناه.
"""

        keyboard = [
            [InlineKeyboardButton("✅ تم الدفع", callback_data="deposit_paid")],
            [InlineKeyboardButton("🔄 تحقق من الدفع", callback_data="deposit_verify")],
            [InlineKeyboardButton("❌ إلغاء", callback_data="main_menu")]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")
        return DEPOSIT_CONFIRM

    except ValueError:
        await update.message.reply_text("❌ أرسل رقماً صحيحاً!")
        return DEPOSIT_AMOUNT

async def deposit_paid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """العميل ضغط "تم الدفع""""
    query = update.callback_query
    await query.answer("⏳ جاري التحقق...", show_alert=False)

    user_id = update.effective_user.id
    payment_id = context.user_data.get("payment_id")
    amount = context.user_data.get("deposit_amount", 0)

    if not payment_id:
        await query.edit_message_text("❌ لا يوجد طلب دفع نشط!")
        return MAIN_MENU

    # التحقق من حالة الدفع
    status = check_payment_status(payment_id)

    # إذا كان Mock أو نجح التحقق
    if status["success"] and status["status"] in ["paid", "completed", "success"]:
        # إضافة الرصيد
        tx = add_balance(user_id, amount, f"شحن عبر {context.user_data.get('deposit_method', 'unknown')}", payment_id)

        new_balance = get_balance(user_id)

        text = f"""
🎉 *تم شحن رصيدك بنجاح!*

✅ المبلغ المضاف: `{format_price(amount)}`
💰 رصيدك الجديد: `{format_price(new_balance)}`
🆔 رقم المعاملة: `#{tx['id']}`

شكراً لاستخدامك متجرنا! 🙏
"""

        # إشعار الأدمن
        try:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"""
💰 *شحن رصيد جديد!*

👤 المستخدم: `{user_id}`
💰 المبلغ: {format_price(amount)}
🆔 المعاملة: #{tx['id']}
📱 الطريقة: {context.user_data.get('deposit_method', 'unknown')}
""",
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Failed to notify admin: {e}")

        keyboard = [
            [InlineKeyboardButton("🛍️ تصفح المتجر", callback_data="browse_store")],
            [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu")]
        ]

    else:
        text = f"""
⏳ *الدفع قيد المراجعة*

لم نتمكن من التحقق من الدفع تلقائياً.
سنقوم بالمراجعة يدوياً وإضافة الرصيد خلال دقائق.

🆔 رقم الطلب: `{payment_id}`
💰 المبلغ: {format_price(amount)}

يمكنك الضغط على "تحقق مرة أخرى" لاحقاً.
"""

        keyboard = [
            [InlineKeyboardButton("🔄 تحقق مرة أخرى", callback_data="deposit_verify")],
            [InlineKeyboardButton("📞 التواصل مع الدعم", callback_data="support")],
            [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu")]
        ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    return DEPOSIT_VERIFY

async def deposit_verify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """التحقق اليدوي من الدفع"""
    query = update.callback_query
    await query.answer("⏳ جاري التحقق...")

    return await deposit_paid(update, context)

async def deposit_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """سجل الشحن"""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    transactions = get_user_transactions(user_id, 10)
    deposits = [tx for tx in transactions if tx["type"] == "deposit"]

    if not deposits:
        text = "📭 لا يوجد سجل شحن!"
    else:
        text = "📜 *سجل الشحن:*\n\n"
        for tx in deposits:
            text += f"💰 `{format_price(tx['amount'])}` | {tx['date']}\n"
            text += f"   📝 {tx['reason']}\n\n"

    keyboard = [
        [InlineKeyboardButton("💰 شحن رصيد", callback_data="deposit")],
        [InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="main_menu")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    return DEPOSIT_MENU

# ───────────────────────────────────────────
# 💳 محفظتي
# ───────────────────────────────────────────

async def my_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض المحفظة"""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    user = get_user(user_id)
    balance = get_balance(user_id)

    text = f"""
💳 *محفظتي*

💰 الرصيد الحالي: `{format_price(balance)}`
📊 إجمالي الشحن: `{format_price(user['total_deposited'])}`
📊 إجمالي الإنفاق: `{format_price(user['total_spent'])}`
📅 تاريخ الانضمام: `{user['join_date']}`

👇 اختر عملية:
"""

    keyboard = [
        [InlineKeyboardButton("💰 شحن رصيد", callback_data="deposit")],
        [InlineKeyboardButton("📜 سجل المعاملات", callback_data="wallet_history")],
        [InlineKeyboardButton("🔄 تحويل رصيد", callback_data="transfer_balance")],
        [InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="main_menu")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    return MAIN_MENU

async def wallet_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """سجل المعاملات"""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    transactions = get_user_transactions(user_id, 15)

    if not transactions:
        text = "📭 لا توجد معاملات!"
    else:
        text = "📜 *سجل المعاملات:*\n\n"
        for tx in transactions:
            emoji = {"deposit": "💰", "withdrawal": "💸", "purchase": "🛒",
                     "transfer_in": "📥", "transfer_out": "📤"}.get(tx["type"], "📝")
            text += f"{emoji} `{format_price(tx['amount'])}` | {tx['date']}\n"
            text += f"   {tx['reason']}\n\n"

    keyboard = [
        [InlineKeyboardButton("💳 محفظتي", callback_data="my_wallet")],
        [InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="main_menu")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    return WALLET_HISTORY

# ───────────────────────────────────────────
# 🛍️ المتجر
# ───────────────────────────────────────────

async def browse_store(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تصفح المتجر"""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    balance = get_balance(user_id)

    text = f"""
🛍️ *أقسام المتجر*

💰 رصيدك: `{format_price(balance)}`

اختر القسم:
"""

    keyboard = []
    for cat_id, cat_info in CATEGORIES.items():
        keyboard.append([InlineKeyboardButton(cat_info["name"], callback_data=f"cat_{cat_id}")])

    keyboard.extend([
        [InlineKeyboardButton("🛒 سلة المشتريات", callback_data="view_cart")],
        [InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="main_menu")]
    ])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    return STORE_MENU

async def show_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض خدمات القسم"""
    query = update.callback_query
    await query.answer()

    cat_id = query.data.replace("cat_", "")
    category = CATEGORIES.get(cat_id)

    if not category:
        await query.edit_message_text("❌ القسم غير موجود!")
        return STORE_MENU

    text = f"""
{category['name']} *الخدمات المتاحة:*

"""

    keyboard = []
    for service in category["services"]:
        text += f"• *{service['name']}*\n"
        text += f"  💰 {format_price(service['price'])}\n"
        text += f"  📝 {service['desc']}\n\n"
        keyboard.append([InlineKeyboardButton(
            f"➕ {service['name']}",
            callback_data=f"service_{service['id']}"
        )])

    keyboard.extend([
        [InlineKeyboardButton("🔙 الأقسام", callback_data="browse_store")],
        [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu")]
    ])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    return CATEGORY_MENU

async def service_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تفاصيل الخدمة"""
    query = update.callback_query
    await query.answer()

    service_id = query.data.replace("service_", "")
    service, category = find_service(service_id)

    if not service:
        await query.edit_message_text("❌ الخدمة غير موجودة!")
        return CATEGORY_MENU

    context.user_data["current_service"] = service

    text = f"""
📋 *{service['name']}*

📝 {service['desc']}

💰 *السعر:* `{format_price(service['price'])}`

هل تريد إضافتها للسلة؟
"""

    keyboard = [
        [InlineKeyboardButton("🛒 إضافة للسلة", callback_data=f"addcart_{service_id}")],
        [InlineKeyboardButton("🔙 الخدمات", callback_data=f"cat_{[k for k,v in CATEGORIES.items() if v==category][0]}")],
        [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    return SERVICE_DETAILS

async def add_to_cart_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إضافة للسلة"""
    query = update.callback_query
    await query.answer()

    service_id = query.data.replace("addcart_", "")
    service, _ = find_service(service_id)
    user_id = update.effective_user.id

    if service:
        add_to_cart(user_id, service, context)
        cart = get_user_cart(user_id, context)
        total = get_cart_total(user_id, context)

        text = f"""
✅ *تمت الإضافة!*

🛒 عدد الخدمات: *{len(cart)}*
💰 المجموع: *{format_price(total)}*
"""
        keyboard = [
            [InlineKeyboardButton("🛒 عرض السلة", callback_data="view_cart")],
            [InlineKeyboardButton("🛍️ مواصلة التسوق", callback_data="browse_store")],
            [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu")]
        ]
    else:
        text = "❌ خطأ!"
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    return MAIN_MENU

async def view_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض السلة"""
    query = update.callback_query
    if query:
        await query.answer()

    user_id = update.effective_user.id
    cart = get_user_cart(user_id, context)
    balance = get_balance(user_id)

    if not cart:
        text = "🛒 *السلة فارغة!*"
        keyboard = [
            [InlineKeyboardButton("🛍️ تصفح المتجر", callback_data="browse_store")],
            [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu")]
        ]
    else:
        total = get_cart_total(user_id, context)
        text = f"""
🛒 *سلة المشتريات*

💰 رصيدك: `{format_price(balance)}`
💸 المجموع: `{format_price(total)}`

"""
        keyboard = []
        for i, item in enumerate(cart, 1):
            text += f"*{i}.* {item['name']} - {format_price(item['price'])}\n"
            keyboard.append([InlineKeyboardButton(
                f"❌ حذف {item['name'][:20]}",
                callback_data=f"remove_{i-1}"
            )])

        can_checkout = balance >= total
        checkout_btn = "💳 إتمام الشراء" if can_checkout else f"⚠️ رصيد ناقص ({format_price(total - balance)})"

        keyboard.extend([
            [InlineKeyboardButton(checkout_btn, callback_data="checkout" if can_checkout else "deposit")],
            [InlineKeyboardButton("🗑️ إفراغ السلة", callback_data="clear_cart")],
            [InlineKeyboardButton("🛍️ مواصلة التسوق", callback_data="browse_store")],
            [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu")]
        ])

    reply_markup = InlineKeyboardMarkup(keyboard)

    if query:
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")

    return CART_VIEW

async def remove_from_cart_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """حذف من السلة"""
    query = update.callback_query
    await query.answer()

    index = int(query.data.replace("remove_", ""))
    user_id = update.effective_user.id

    remove_from_cart(user_id, index, context)
    return await view_cart(update, context)

async def clear_cart_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إفراغ السلة"""
    query = update.callback_query
    await query.answer()

    clear_cart(update.effective_user.id, context)

    text = "🗑️ *تم إفراغ السلة!*"
    keyboard = [
        [InlineKeyboardButton("🛍️ تصفح المتجر", callback_data="browse_store")],
        [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    return MAIN_MENU

async def checkout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إتمام الشراء"""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    cart = get_user_cart(user_id, context)
    total = get_cart_total(user_id, context)
    balance = get_balance(user_id)

    if not cart:
        await query.edit_message_text("❌ السلة فارغة!")
        return MAIN_MENU

    if balance < total:
        text = f"""
⚠️ *رصيد ناقص!*

💰 رصيدك: `{format_price(balance)}`
💸 المطلوب: `{format_price(total)}`
📉 النقص: `{format_price(total - balance)}`

بدك تشحن رصيد أولاً.
"""
        keyboard = [
            [InlineKeyboardButton("💰 شحن رصيد", callback_data="deposit")],
            [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")
        return MAIN_MENU

    # خصم الرصيد
    tx = deduct_balance(user_id, total, "شراء من المتجر")

    if not tx:
        await query.edit_message_text("❌ خطأ في الخصم!")
        return MAIN_MENU

    # إنشاء طلب
    order_items = "\n".join([f"• {item['name']} - {format_price(item['price'])}" for item in cart])

    text = f"""
🎉 *تم الشراء بنجاح!*

🆔 *رقم الطلب:* `#{tx['id']}`
💰 *المبلغ:* `{format_price(total)}`
📅 *التاريخ:* `{tx['date']}`

🛒 *الخدمات:*
{order_items}

💰 *رصيدك المتبقي:* `{format_price(get_balance(user_id))}`

شكراً لشرائك! 🙏
"""

    # إشعار الأدمن
    try:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"""
🛒 *طلب شراء جديد!*

👤 المستخدم: `{user_id}`
🆔 الطلب: #{tx['id']}
💰 المبلغ: {format_price(total)}

🛒 الخدمات:
{order_items}
""",
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Failed to notify admin: {e}")

    # إفراغ السلة
    clear_cart(user_id, context)

    keyboard = [
        [InlineKeyboardButton("🛍️ تصفح المتجر", callback_data="browse_store")],
        [InlineKeyboardButton("📋 طلباتي", callback_data="my_orders")],
        [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    return MAIN_MENU

# ───────────────────────────────────────────
# 📋 طلباتي
# ───────────────────────────────────────────

async def my_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض طلبات المستخدم"""
    query = update.callback_query
    await query.answer()

    user_id = str(update.effective_user.id)
    transactions = get_user_transactions(user_id, 20)
    purchases = [tx for tx in transactions if tx["type"] == "withdrawal" or "شراء" in tx.get("reason", "")]

    if not purchases:
        text = "📭 لا توجد طلبات سابقة!"
        keyboard = [
            [InlineKeyboardButton("🛍️ تصفح المتجر", callback_data="browse_store")],
            [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu")]
        ]
    else:
        text = "📋 *طلباتك:*\n\n"
        keyboard = []

        for tx in purchases[:10]:
            text += f"🆔 `#{tx['id']}` | {format_price(tx['amount'])} | {tx['date']}\n"
            text += f"   ✅ {tx['reason']}\n\n"

        keyboard.append([InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    return MAIN_MENU

# ───────────────────────────────────────────
# 📞 الدعم الفني
# ───────────────────────────────────────────

async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """التواصل مع الدعم"""
    query = update.callback_query
    await query.answer()

    text = """
📞 *التواصل مع الدعم*

✉️ أرسل رسالتك الآن وسنرد عليك في أقرب وقت:

⏰ *أوقات العمل:*
• السبت - الخميس: 9 ص - 9 م
• الجمعة: مغلق

💬 اكتب رسالتك أدناه:
"""

    keyboard = [[InlineKeyboardButton("❌ إلغاء", callback_data="main_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")

    return SUPPORT_MESSAGE

async def receive_support_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """استلام رسالة الدعم"""
    user = update.effective_user
    message_text = update.message.text

    # إرسال للأدمن
    admin_text = f"""
📩 *رسالة دعم جديدة!*

👤 *من:* {user.first_name}
👤 *آيدي:* `{user.id}`
👤 *يوزر:* @{user.username or 'لا يوجد'}

💬 *الرسالة:*
{message_text}
"""

    try:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=admin_text,
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Failed to send support: {e}")

    text = """
✅ *تم إرسال رسالتك!*

سنرد عليك في أقرب وقت.
"""

    keyboard = [
        [InlineKeyboardButton("📞 إرسال أخرى", callback_data="support")],
        [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")

    return MAIN_MENU

# ───────────────────────────────────────────
# ⚙️ لوحة تحكم الأدمن
# ───────────────────────────────────────────

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """لوحة التحكم"""
    query = update.callback_query
    await query.answer()

    if update.effective_user.id != ADMIN_ID:
        await query.edit_message_text("❌ غير مصرح!")
        return MAIN_MENU

    stats = get_stats()

    text = f"""
⚙️ *لوحة تحكم الأدمن*

📊 *الإحصائيات:*
• 👥 المستخدمين: `{stats['total_users']}`
• 💰 إجمالي الرصيد: `{format_price(stats['total_balance'])}`
• 📥 إجمالي الشحن: `{format_price(stats['total_deposited'])}`
• 📤 إجمالي الإنفاق: `{format_price(stats['total_spent'])}`
• 📋 المعاملات: `{stats['total_transactions']}`

🛠️ *الخيارات:*
"""

    keyboard = [
        [InlineKeyboardButton("👥 إدارة المستخدمين", callback_data="admin_users")],
        [InlineKeyboardButton("📋 جميع المعاملات", callback_data="admin_transactions")],
        [InlineKeyboardButton("💰 إضافة/خصم رصيد", callback_data="admin_adjust_balance")],
        [InlineKeyboardButton("📊 أفضل المستخدمين", callback_data="admin_top_users")],
        [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    return ADMIN_PANEL

async def admin_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إدارة المستخدمين"""
    query = update.callback_query
    await query.answer()

    text = """
👥 *إدارة المستخدمين*

أرسل آيدي المستخدم أو يوزره للبحث:
"""

    keyboard = [[InlineKeyboardButton("🔙 لوحة التحكم", callback_data="admin_panel")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")

    return ADMIN_USER_SEARCH

async def admin_user_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """البحث عن مستخدم"""
    search = update.message.text.strip()

    # البحث بالآيدي
    user = get_user(search)

    if not user:
        # البحث باليوزر
        user = search_user_by_username(search.replace("@", ""))

    if not user:
        await update.message.reply_text("❌ المستخدم غير موجود!")
        return ADMIN_PANEL

    context.user_data["admin_target_user"] = user["user_id"]

    status_emoji = "🟢" if user.get("status") == "active" else "🔴"

    text = f"""
👤 *معلومات المستخدم*

🆔 الآيدي: `{user['user_id']}`
👤 الاسم: {user['name']}
📱 اليوزر: @{user.get('username', 'لا يوجد')}
{status_emoji} الحالة: {user.get('status', 'active')}

💰 الرصيد: `{format_price(user['balance'])}`
📥 إجمالي الشحن: `{format_price(user['total_deposited'])}`
📤 إجمالي الإنفاق: `{format_price(user['total_spent'])}`
📅 الانضمام: {user['join_date']}

📝 ملاحظات: {user.get('notes', 'لا يوجد')}
"""

    keyboard = [
        [InlineKeyboardButton("💰 إضافة رصيد", callback_data="admin_add_balance")],
        [InlineKeyboardButton("💸 خصم رصيد", callback_data="admin_deduct_balance")],
        [InlineKeyboardButton("🔄 تصفير الرصيد", callback_data="admin_reset_balance")],
        [InlineKeyboardButton("🔒 حظر", callback_data="admin_ban")],
        [InlineKeyboardButton("🔓 فك حظر", callback_data="admin_unban")],
        [InlineKeyboardButton("🔙 لوحة التحكم", callback_data="admin_panel")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    return ADMIN_USER_ACTION

async def admin_user_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إجراء على مستخدم"""
    query = update.callback_query
    await query.answer()

    action = query.data.replace("admin_", "")
    target_id = context.user_data.get("admin_target_user")

    if not target_id:
        await query.edit_message_text("❌ لا يوجد مستخدم محدد!")
        return ADMIN_PANEL

    if action == "ban":
        ban_user(target_id, "محظور من الأدمن")
        await query.edit_message_text(f"🔒 تم حظر المستخدم `{target_id}`", parse_mode="Markdown")
    elif action == "unban":
        unban_user(target_id)
        await query.edit_message_text(f"🔓 تم فك حظر المستخدم `{target_id}`", parse_mode="Markdown")
    elif action == "reset_balance":
        reset_user_balance(target_id)
        await query.edit_message_text(f"🔄 تم تصفير رصيد المستخدم `{target_id}`", parse_mode="Markdown")
    else:
        await query.edit_message_text("✅ تم التنفيذ!")

    keyboard = [[InlineKeyboardButton("🔙 لوحة التحكم", callback_data="admin_panel")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_reply_markup(reply_markup)

    return ADMIN_PANEL

async def admin_transactions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض المعاملات"""
    query = update.callback_query
    await query.answer()

    from wallet_manager import data
    txs = data["transactions"][-20:]

    text = "📋 *آخر المعاملات:*\n\n"
    for tx in txs:
        emoji = {"deposit": "💰", "withdrawal": "💸"}.get(tx["type"], "📝")
        text += f"{emoji} `#{tx['id']}` | {tx['user_id']} | {format_price(tx['amount'])}\n"
        text += f"   {tx['type']} | {tx['date']}\n\n"

    keyboard = [[InlineKeyboardButton("🔙 لوحة التحكم", callback_data="admin_panel")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    return ADMIN_PANEL

async def admin_top_users_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أفضل المستخدمين"""
    query = update.callback_query
    await query.answer()

    users = get_top_users(10)

    text = "🏆 *أفضل المستخدمين:*\n\n"
    for i, user in enumerate(users, 1):
        text += f"{i}. {user['name']} | شحن: {format_price(user['total_deposited'])} | رصيد: {format_price(user['balance'])}\n"

    keyboard = [[InlineKeyboardButton("🔙 لوحة التحكم", callback_data="admin_panel")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    return ADMIN_PANEL

# ───────────────────────────────────────────
# 🔙 العودة للقائمة الرئيسية
# ───────────────────────────────────────────

async def main_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """العودة للرئيسية"""
    query = update.callback_query
    if query:
        await query.answer()
    return await start(update, context)

# ───────────────────────────────────────────
# ❌ إلغاء
# ───────────────────────────────────────────

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إلغاء"""
    await update.message.reply_text("❌ تم إلغاء العملية.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

# ───────────────────────────────────────────
# 🚀 الدالة الرئيسية
# ───────────────────────────────────────────

def main():
    """تشغيل البوت"""
    application = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CallbackQueryHandler(main_menu_handler, pattern="^main_menu$")
        ],
        states={
            MAIN_MENU: [
                CallbackQueryHandler(deposit_menu, pattern="^deposit$"),
                CallbackQueryHandler(browse_store, pattern="^browse_store$"),
                CallbackQueryHandler(view_cart, pattern="^view_cart$"),
                CallbackQueryHandler(my_orders, pattern="^my_orders$"),
                CallbackQueryHandler(my_wallet, pattern="^my_wallet$"),
                CallbackQueryHandler(support, pattern="^support$"),
                CallbackQueryHandler(admin_panel, pattern="^admin_panel$"),
            ],
            DEPOSIT_MENU: [
                CallbackQueryHandler(deposit_select_method, pattern="^deposit_method_"),
                CallbackQueryHandler(deposit_history, pattern="^deposit_history$"),
                CallbackQueryHandler(main_menu_handler, pattern="^main_menu$"),
            ],
            DEPOSIT_AMOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, deposit_enter_amount),
                CallbackQueryHandler(main_menu_handler, pattern="^main_menu$"),
            ],
            DEPOSIT_CONFIRM: [
                CallbackQueryHandler(deposit_paid, pattern="^deposit_paid$"),
                CallbackQueryHandler(deposit_verify, pattern="^deposit_verify$"),
                CallbackQueryHandler(main_menu_handler, pattern="^main_menu$"),
            ],
            DEPOSIT_VERIFY: [
                CallbackQueryHandler(deposit_verify, pattern="^deposit_verify$"),
                CallbackQueryHandler(support, pattern="^support$"),
                CallbackQueryHandler(main_menu_handler, pattern="^main_menu$"),
            ],
            STORE_MENU: [
                CallbackQueryHandler(show_category, pattern="^cat_"),
                CallbackQueryHandler(view_cart, pattern="^view_cart$"),
                CallbackQueryHandler(main_menu_handler, pattern="^main_menu$"),
            ],
            CATEGORY_MENU: [
                CallbackQueryHandler(service_details, pattern="^service_"),
                CallbackQueryHandler(browse_store, pattern="^browse_store$"),
                CallbackQueryHandler(main_menu_handler, pattern="^main_menu$"),
            ],
            SERVICE_DETAILS: [
                CallbackQueryHandler(add_to_cart_handler, pattern="^addcart_"),
                CallbackQueryHandler(show_category, pattern="^cat_"),
                CallbackQueryHandler(main_menu_handler, pattern="^main_menu$"),
            ],
            CART_VIEW: [
                CallbackQueryHandler(remove_from_cart_handler, pattern="^remove_"),
                CallbackQueryHandler(checkout, pattern="^checkout$"),
                CallbackQueryHandler(deposit_menu, pattern="^deposit$"),
                CallbackQueryHandler(clear_cart_handler, pattern="^clear_cart$"),
                CallbackQueryHandler(browse_store, pattern="^browse_store$"),
                CallbackQueryHandler(main_menu_handler, pattern="^main_menu$"),
            ],
            CHECKOUT_CONFIRM: [
                CallbackQueryHandler(main_menu_handler, pattern="^main_menu$"),
            ],
            SUPPORT_MESSAGE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_support_message),
                CallbackQueryHandler(main_menu_handler, pattern="^main_menu$"),
            ],
            WALLET_HISTORY: [
                CallbackQueryHandler(my_wallet, pattern="^my_wallet$"),
                CallbackQueryHandler(main_menu_handler, pattern="^main_menu$"),
            ],
            ADMIN_PANEL: [
                CallbackQueryHandler(admin_users, pattern="^admin_users$"),
                CallbackQueryHandler(admin_transactions, pattern="^admin_transactions$"),
                CallbackQueryHandler(admin_top_users_handler, pattern="^admin_top_users$"),
                CallbackQueryHandler(admin_user_action, pattern="^admin_(ban|unban|reset_balance|add_balance|deduct_balance)$"),
                CallbackQueryHandler(main_menu_handler, pattern="^main_menu$"),
            ],
            ADMIN_USER_SEARCH: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_user_search),
                CallbackQueryHandler(admin_panel, pattern="^admin_panel$"),
            ],
            ADMIN_USER_ACTION: [
                CallbackQueryHandler(admin_user_action, pattern="^admin_"),
                CallbackQueryHandler(admin_panel, pattern="^admin_panel$"),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CommandHandler("start", start),
        ],
        per_message=False,
    )

    application.add_handler(conv_handler)

    print("🤖 البوت يعمل الآن...")
    print("📁 البيانات تُحفظ في: wallet_data.json")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
