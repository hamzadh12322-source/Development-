"""
💳 تكامل API الدفع
====================
يدعم API منفصل لسرياتيل كاش وشام كاش
"""

import requests
import json
from datetime import datetime

from config import (
    SYRIATEL_API_KEY, SYRIATEL_API_URL,
    SHAM_API_KEY, SHAM_API_URL,
    SYRIATEL_NUMBER, SHAM_NUMBER,
    MIN_DEPOSIT, MAX_DEPOSIT, DEFAULT_CURRENCY
)

# ───────────────────────────────────────────
# 🔧 دوال مساعدة
# ───────────────────────────────────────────

def get_headers(api_key):
    """إنشاء Headers"""
    return {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

def get_payment_methods():
    """طرق الدفع المتاحة"""
    methods = []
    if SYRIATEL_NUMBER:
        methods.append({
            "id": "syriatel",
            "name": "📱 سرياتيل كاش",
            "number": SYRIATEL_NUMBER,
            "min": MIN_DEPOSIT,
            "max": MAX_DEPOSIT
        })
    if SHAM_NUMBER:
        methods.append({
            "id": "sham",
            "name": "📱 شام كاش",
            "number": SHAM_NUMBER,
            "min": MIN_DEPOSIT,
            "max": MAX_DEPOSIT
        })
    return methods

# ───────────────────────────────────────────
# 🎯 إنشاء طلب دفع
# ───────────────────────────────────────────

def create_payment(amount, phone, method="syriatel", user_id=None, description=""):
    """إنشاء طلب دفع"""

    # التحقق من المبلغ
    if amount < MIN_DEPOSIT:
        return {"success": False, "error": f"الحد الأدنى {MIN_DEPOSIT:,} ل.س"}
    if amount > MAX_DEPOSIT:
        return {"success": False, "error": f"الحد الأقصى {MAX_DEPOSIT:,} ل.س"}

    # اختيار API حسب الطريقة
    if method == "syriatel":
        api_url = SYRIATEL_API_URL
        api_key = SYRIATEL_API_KEY
        provider_name = "سرياتيل كاش"
        account_number = SYRIATEL_NUMBER
    elif method == "sham":
        api_url = SHAM_API_URL
        api_key = SHAM_API_KEY
        provider_name = "شام كاش"
        account_number = SHAM_NUMBER
    else:
        return {"success": False, "error": "طريقة دفع غير معروفة"}

    # ── وضع التجربة (Mock) ──
    if not api_key or api_key == "your_syriatel_api_key_here" or api_key == "your_sham_api_key_here":
        payment_id = f"MOCK_{method.upper()}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{user_id or '0'}"

        instructions = f"""
📱 *تعليمات الدفع عبر {provider_name}:*

1️⃣ افتح تطبيق {provider_name}
2️⃣ اختر "تحويل رصيد"
3️⃣ أرسل المبلغ إلى:
   📞 *{account_number}*
4️⃣ المبلغ: *{amount:,} ل.س*
5️⃣ في حقل "ملاحظات" اكتب: `{payment_id}`

⏰ *الطلب صالح لمدة 30 دقيقة*

✅ بعد الدفع، اضغط "تم الدفع" أدناه.
"""
        return {
            "success": True,
            "payment_id": payment_id,
            "status": "pending",
            "amount": amount,
            "payment_url": None,
            "qr_code": None,
            "instructions": instructions,
            "expires_at": "30_minutes",
            "raw_response": {"mock": True, "method": method}
        }

    # ── API حقيقي ──
    try:
        endpoint = f"{api_url}/payments/create"

        payload = {
            "amount": amount,
            "currency": DEFAULT_CURRENCY,
            "phone": phone,
            "method": method,
            "external_id": str(user_id),
            "description": description or f"شحن رصيد - {amount:,} ل.س",
            "callback_url": "https://your-domain.com/webhook/payment",
            "metadata": {
                "user_id": str(user_id),
                "telegram_user_id": str(user_id),
                "requested_at": datetime.now().isoformat()
            }
        }

        response = requests.post(endpoint, headers=get_headers(api_key), json=payload, timeout=30)
        response_data = response.json()

        if response.status_code == 200 and response_data.get("success"):
            return {
                "success": True,
                "payment_id": response_data.get("payment_id"),
                "status": response_data.get("status", "pending"),
                "amount": amount,
                "payment_url": response_data.get("payment_url"),
                "qr_code": response_data.get("qr_code"),
                "instructions": response_data.get("instructions", ""),
                "expires_at": response_data.get("expires_at"),
                "raw_response": response_data
            }
        else:
            return {
                "success": False,
                "error": response_data.get("message", "خطأ غير معروف"),
                "raw_response": response_data
            }

    except requests.exceptions.RequestException as e:
        return {"success": False, "error": f"خطأ في الاتصال: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": f"خطأ غير متوقع: {str(e)}"}

# ───────────────────────────────────────────
# 🔍 التحقق من حالة الدفع
# ───────────────────────────────────────────

def check_payment_status(payment_id):
    """التحقق من حالة الدفع"""

    # تحديد API حسب رقم الطلب
    if "SYRIATEL" in payment_id or payment_id.startswith("MOCK_SYRIATEL"):
        api_url = SYRIATEL_API_URL
        api_key = SYRIATEL_API_KEY
    elif "SHAM" in payment_id or payment_id.startswith("MOCK_SHAM"):
        api_url = SHAM_API_URL
        api_key = SHAM_API_KEY
    else:
        api_url = SYRIATEL_API_URL
        api_key = SYRIATEL_API_KEY

    # ── وضع التجربة ──
    if not api_key or "MOCK_" in payment_id:
        return {
            "success": True,
            "status": "paid",
            "amount": 0,
            "paid_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "transaction_id": payment_id,
            "raw_response": {"mock": True, "status": "paid"}
        }

    # ── API حقيقي ──
    try:
        endpoint = f"{api_url}/payments/{payment_id}/status"

        response = requests.get(endpoint, headers=get_headers(api_key), timeout=30)
        response_data = response.json()

        if response.status_code == 200:
            return {
                "success": True,
                "status": response_data.get("status", "unknown"),
                "amount": response_data.get("amount", 0),
                "paid_at": response_data.get("paid_at"),
                "transaction_id": response_data.get("transaction_id"),
                "raw_response": response_data
            }
        else:
            return {
                "success": False,
                "error": response_data.get("message", "خطأ في التحقق"),
                "raw_response": response_data
            }

    except Exception as e:
        return {"success": False, "error": f"خطأ: {str(e)}"}

# ───────────────────────────────────────────
# 🔔 معالجة Webhook
# ───────────────────────────────────────────

def process_webhook(payload, headers=None):
    """معالجة إشعار Webhook"""

    try:
        payment_id = payload.get("payment_id") or payload.get("id")
        status = payload.get("status")
        amount = payload.get("amount", 0)
        user_id = payload.get("metadata", {}).get("user_id") or payload.get("external_id")
        transaction_id = payload.get("transaction_id")

        return {
            "valid": True,
            "payment_id": payment_id,
            "status": status,
            "amount": amount,
            "user_id": user_id,
            "transaction_id": transaction_id,
            "processed": status in ["paid", "completed", "success"]
        }

    except Exception as e:
        return {"valid": False, "error": f"خطأ في المعالجة: {str(e)}"}
