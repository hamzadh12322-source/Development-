"""
🤖 بوت متجر الخدمات + نظام المحفظة
"""
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ConversationHandler, ContextTypes, filters
from config import BOT_TOKEN, ADMIN_ID
from wallet_manager import get_or_create_user, get_user, get_balance, add_balance, deduct_balance, get_user_transactions
from payment_api import create_payment, check_payment_status, get_payment_methods

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

CATEGORIES = {
    "design": {
        "name": "🎨 تصميم",
        "services": [
            {"id": "logo_design", "name": "🎨 تصميم شعار", "price": 50000, "desc": "تصميم شعار فريد"},
            {"id": "social_design", "name": "📱 منشورات سوشل", "price": 25000, "desc": "10 تصاميم"},
            {"id": "banner_design", "name": "🖼️ بانر وغلاف", "price": 35000, "desc": "غلاف يوتيوب"}
        ]
    },
    "writing": {
        "name": "✍️ كتابة",
        "services": [
            {"id": "article_write", "name": "📝 مقال SEO", "price": 30000, "desc": "مقال 1000 كلمة"},
            {"id": "script_write", "name": "📹 سكريبت", "price": 40000, "desc": "سكريبت فيديو"}
        ]
    },
    "programming": {
        "name": "💻 برمجة",
        "services": [
            {"id": "web_page", "name": "🌐 صفحة ويب", "price": 100000, "desc": "صفقة هبوط"},
            {"id": "bot_dev", "name": "🤖 بوت تلجرام", "price": 150000, "desc": "بوت مخصص"}
        ]
    },
    "translation": {
        "name": "🌍 ترجمة",
        "services": [
            {"id": "translate_en_ar", "name": "🇬🇧➡️🇸🇾 إنجليزي", "price": 20000, "desc": "1000 كلمة"},
            {"id": "translate_tr_ar", "name": "🇹🇷➡️🇸🇾 تركي", "price": 25000, "desc": "1000 كلمة"}
        ]
    },
    "marketing": {
        "name": "📢 تسويق",
        "services": [
            {"id": "ads_manage", "name": "📊 إدارة إعلانات", "price": 75000, "desc": "إدارة شهر كامل"},
            {"id": "seo_opt", "name": "🔍 SEO", "price": 60000, "desc": "تحسين محركات البحث"}
        ]
    }
}

MAIN_MENU, DEPOSIT_MENU, DEPOSIT_AMOUNT, DEPOSIT_CONFIRM, DEPOSIT_VERIFY = range(5)
STORE_MENU, CATEGORY_MENU, SERVICE_DETAILS, CART_VIEW, CHECKOUT_CONFIRM = range(5, 10)
SUPPORT_MESSAGE, ADMIN_PANEL = range(10, 12)

def format_price(price):
    return f"{price:,} ل.س"

def get_user_cart(user_id, context):
    key = f"cart_{user_id}"
    return context.bot_data.get(key, [])

def add_to_cart(user_id, service, context):
    key = f"cart_{user_id}"
    cart = context.bot_data.get(key, [])
    cart.append(service)
    context.bot_data[key] = cart

def remove_from_cart(user_id, index, context):
    key = f"cart_{user_id}"
    cart = context.bot_data.get(key, [])
    if 0 <= index < len(cart):
        cart.pop(index)
        context.bot_data[key] = cart
        return True
    return False

def clear_cart(user_id, context):
    key = f"cart_{user_id}"
    context.bot_data[key] = []

def get_cart_total(user_id, context):
    cart = get_user_cart(user_id, context)
    return sum(item["price"] for item in cart)

def find_service(service_id):
    for cat in CATEGORIES.values():
        for s in cat["services"]:
            if s["id"] == service_id:
                return s, cat
    return None, None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    db_user = get_or_create_user(user_id, user.first_name, user.username)
    balance = get_balance(user_id)
    
    welcome_text = f'''
👋 أهلاً *{user.first_name}*!

🏪 *متجر الخدمات الاحترافية*

💰 *رصيدك:* `{format_price(balance)}`

👇 اختر من القائمة:
'''
    
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

async def deposit_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    balance = get_balance(user_id)
    
    text = f'''
💰 *شحن رصيد*

رصيدك: `{format_price(balance)}`

💳 *طرق الدفع:*
'''
    
    methods = get_payment_methods()
    keyboard = []
    
    for method in methods:
        text += f'\n📱 *{method["name"]}*'
        text += f'\n   الحد الأدنى: {format_price(method["min"])}'
        keyboard.append([InlineKeyboardButton(f'💳 {method["name"]}', callback_data=f'deposit_method_{method["id"]}')])
    
    keyboard.extend([
        [InlineKeyboardButton("📜 سجل الشحن", callback_data="deposit_history")],
        [InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="main_menu")]
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    return DEPOSIT_MENU

async def deposit_select_method(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    method = query.data.replace("deposit_method_", "")
    context.user_data["deposit_method"] = method
    
    method_names = {"syriatel": "سرياتيل كاش", "sham": "شام كاش"}
    method_name = method_names.get(method, method)
    
    text = f'''
💰 *شحن عبر {method_name}*

أرسل المبلغ (بالأرقام):
مثال: `50000`
'''
    
    keyboard = [[InlineKeyboardButton("❌ إلغاء", callback_data="main_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    return DEPOSIT_AMOUNT

async def deposit_enter_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    try:
        amount = int(update.message.text.replace(",", "").replace(" ", ""))
        
        if amount < 10000:
            await update.message.reply_text("❌ الحد الأدنى 10,000 ل.س")
            return DEPOSIT_AMOUNT
        
        if amount > 1000000:
            await update.message.reply_text("❌ الحد الأقصى 1,000,000 ل.س")
            return DEPOSIT_AMOUNT
        
        context.user_data["deposit_amount"] = amount
        method = context.user_data.get("deposit_method", "syriatel")
        
        payment = create_payment(
            amount=amount,
            phone="",
            method=method,
            user_id=user_id,
            description=f"شحن رصيد - {amount:,} ل.س"
        )
        
        if not payment["success"]:
            await update.message.reply_text(f'❌ خطأ: {payment.get("error", "غير معروف")}')
            return DEPOSIT_AMOUNT
        
        context.user_data["payment_id"] = payment["payment_id"]
        
        text = f'''
💰 *طلب شحن جديد*

🆔 *رقم الطلب:* `{payment["payment_id"]}`
💰 *المبلغ:* `{format_price(amount)}`
📱 *الطريقة:* {method}

{payment["instructions"]}

✅ بعد الدفع، اضغط "تم الدفع" أدناه.
'''
        
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
    query = update.callback_query
    await query.answer("⏳ جاري التحقق...", show_alert=False)
    
    user_id = update.effective_user.id
    payment_id = context.user_data.get("payment_id")
    amount = context.user_data.get("deposit_amount", 0)
    
    if not payment_id:
        await query.edit_message_text("❌ لا يوجد طلب دفع نشط!")
        return MAIN_MENU
    
    status = check_payment_status(payment_id)
    
    if status["success"] and status["status"] in ["paid", "completed", "success"]:
        tx = add_balance(user_id, amount, f'شحن عبر {context.user_data.get("deposit_method", "unknown")}', payment_id)
        new_balance = get_balance(user_id)
        
        text = f'''
🎉 *تم شحن رصيدك بنجاح!*

✅ المبلغ: `{format_price(amount)}`
💰 الرصيد الجديد: `{format_price(new_balance)}`
🆔 المعاملة: `#{tx["id"]}`
'''
        
        try:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=f'''
💰 *شحن رصيد جديد!*

👤 المستخدم: `{user_id}`
💰 المبلغ: {format_price(amount)}
🆔 المعاملة: #{tx["id"]}
📱 الطريقة: {context.user_data.get("deposit_method", "unknown")}
''',
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Failed to notify admin: {e}")
        
        keyboard = [
            [InlineKeyboardButton("🛍️ تصفح المتجر", callback_data="browse_store")],
            [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu")]
        ]
        
    else:
        text = f'''
⏳ *الدفع قيد المراجعة*

لم نتمكن من التحقق تلقائياً.
سنراجعه يدوياً.

🆔 الطلب: `{payment_id}`
💰 المبلغ: {format_price(amount)}
'''
        
        keyboard = [
            [InlineKeyboardButton("🔄 تحقق مرة أخرى", callback_data="deposit_verify")],
            [InlineKeyboardButton("📞 التواصل مع الدعم", callback_data="support")],
            [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu")]
        ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    return DEPOSIT_VERIFY

async def deposit_verify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("⏳ جاري التحقق...")
    return await deposit_paid(update, context)

async def deposit_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
            text += f'💰 `{format_price(tx["amount"])}` | {tx["date"]}\n'
            text += f'   📝 {tx["reason"]}\n\n'
    
    keyboard = [
        [InlineKeyboardButton("💰 شحن رصيد", callback_data="deposit")],
        [InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="main_menu")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    return DEPOSIT_MENU

async def my_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    user = get_user(user_id)
    balance = get_balance(user_id)
    
    text = f'''
💳 *محفظتي*

💰 الرصيد: `{format_price(balance)}`
📊 إجمالي الشحن: `{format_price(user["total_deposited"])}`
📊 إجمالي الإنفاق: `{format_price(user["total_spent"])}`
📅 الانضمام: `{user["join_date"]}`
'''
    
    keyboard = [
        [InlineKeyboardButton("💰 شحن رصيد", callback_data="deposit")],
        [InlineKeyboardButton("📜 سجل المعاملات", callback_data="wallet_history")],
        [InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="main_menu")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    return MAIN_MENU

async def wallet_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    transactions = get_user_transactions(user_id, 15)
    
    if not transactions:
        text = "📭 لا توجد معاملات!"
    else:
        text = "📜 *سجل المعاملات:*\n\n"
        for tx in transactions:
            emoji = {"deposit": "💰", "withdrawal": "💸", "purchase": "🛒"}.get(tx["type"], "📝")
            text += f'{emoji} `{format_price(tx["amount"])}` | {tx["date"]}\n'
            text += f'   {tx["reason"]}\n\n'
    
    keyboard = [
        [InlineKeyboardButton("💳 محفظتي", callback_data="my_wallet")],
        [InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="main_menu")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    return MAIN_MENU

async def browse_store(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    balance = get_balance(user_id)
    
    text = f'''
🛍️ *أقسام المتجر*

💰 رصيدك: `{format_price(balance)}`

اختر القسم:
'''
    
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
    query = update.callback_query
    await query.answer()
    
    cat_id = query.data.replace("cat_", "")
    category = CATEGORIES.get(cat_id)
    
    if not category:
        await query.edit_message_text("❌ القسم غير موجود!")
        return STORE_MENU
    
    text = f'''
{category["name"]} *الخدمات المتاحة:*

'''
    
    keyboard = []
    for service in category["services"]:
        text += f'• *{service["name"]}*\n'
        text += f'  💰 {format_price(service["price"])}\n'
        text += f'  📝 {service["desc"]}\n\n'
        keyboard.append([InlineKeyboardButton(
            f'➕ {service["name"]}',
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
    query = update.callback_query
    await query.answer()
    
    service_id = query.data.replace("service_", "")
    service, category = find_service(service_id)
    
    if not service:
        await query.edit_message_text("❌ الخدمة غير موجودة!")
        return CATEGORY_MENU
    
    context.user_data["current_service"] = service
    
    text = f'''
📋 *{service["name"]}*

📝 {service["desc"]}

💰 *السعر:* `{format_price(service["price"])}`

هل تريد إضافتها للسلة؟
'''
    
    cat_id = [k for k, v in CATEGORIES.items() if v == category][0]
    
    keyboard = [
        [InlineKeyboardButton("🛒 إضافة للسلة", callback_data=f"addcart_{service_id}")],
        [InlineKeyboardButton("🔙 الخدمات", callback_data=f"cat_{cat_id}")],
        [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    return SERVICE_DETAILS

async def add_to_cart_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    service_id = query.data.replace("addcart_", "")
    service, _ = find_service(service_id)
    user_id = update.effective_user.id
    
    if service:
        add_to_cart(user_id, service, context)
        cart = get_user_cart(user_id, context)
        total = get_cart_total(user_id, context)
        
        text = f'''
✅ *تمت الإضافة!*

🛒 عدد الخدمات: *{len(cart)}*
💰 المجموع: *{format_price(total)}*
'''
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
        text = f'''
🛒 *سلة المشتريات*

💰 رصيدك: `{format_price(balance)}`
💸 المجموع: `{format_price(total)}`

'''
        keyboard = []
        for i, item in enumerate(cart, 1):
            text += f'{i}. {item["name"]} - {format_price(item["price"])}\n'
            keyboard.append([InlineKeyboardButton(
                f'❌ حذف {item["name"][:20]}',
                callback_data=f"remove_{i-1}"
            )])
        
        can_checkout = balance >= total
        checkout_btn = "💳 إتمام الشراء" if can_checkout else f'⚠️ رصيد ناقص ({format_price(total - balance)})'
        
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
    query = update.callback_query
    await query.answer()
    
    index = int(query.data.replace("remove_", ""))
    user_id = update.effective_user.id
    
    remove_from_cart(user_id, index, context)
    return await view_cart(update, context)

async def clear_cart_handler(update: Update, context: ContextTypes
