"""
💰 مدير المحافظ
================
إدارة رصيد المستخدمين والمعاملات
"""

import json
import os
from datetime import datetime

DATA_FILE = "wallet_data.json"

def load_data():
    """تحميل البيانات"""
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "users": {},
        "transactions": [],
        "deposits": [],
        "withdrawals": [],
        "transaction_counter": 100000
    }

def save_data(data):
    """حفظ البيانات"""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

data = load_data()

# ───────────────────────────────────────────
# 👤 إدارة المستخدمين
# ───────────────────────────────────────────

def get_or_create_user(user_id, name="", username=""):
    """إنشاء أو جلب مستخدم"""
    user_id = str(user_id)
    if user_id not in data["users"]:
        data["users"][user_id] = {
            "user_id": user_id,
            "name": name,
            "username": username,
            "balance": 0,
            "total_deposited": 0,
            "total_spent": 0,
            "join_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "last_activity": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "status": "active",
            "notes": ""
        }
        save_data(data)
    return data["users"][user_id]

def get_user(user_id):
    """جلب مستخدم"""
    return data["users"].get(str(user_id))

def update_user_activity(user_id):
    """تحديث آخر نشاط"""
    user = get_user(user_id)
    if user:
        user["last_activity"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        save_data(data)

# ───────────────────────────────────────────
# 💰 إدارة الرصيد
# ───────────────────────────────────────────

def get_balance(user_id):
    """الحصول على الرصيد"""
    user = get_user(user_id)
    return user["balance"] if user else 0

def add_balance(user_id, amount, reason="", transaction_id=None):
    """إضافة رصيد"""
    user = get_or_create_user(user_id)
    user["balance"] += amount
    user["total_deposited"] += amount

    # تسجيل المعاملة
    tx = create_transaction(user_id, "deposit", amount, reason, transaction_id)
    save_data(data)
    return tx

def deduct_balance(user_id, amount, reason="", order_id=None):
    """خصم رصيد"""
    user = get_user(user_id)
    if not user or user["balance"] < amount:
        return None

    user["balance"] -= amount
    user["total_spent"] += amount

    tx = create_transaction(user_id, "withdrawal", amount, reason, order_id)
    save_data(data)
    return tx

def transfer_balance(from_user, to_user, amount, reason=""):
    """تحويل رصيد بين مستخدمين"""
    sender = get_user(from_user)
    receiver = get_or_create_user(to_user)

    if not sender or sender["balance"] < amount:
        return False

    sender["balance"] -= amount
    receiver["balance"] += amount

    create_transaction(from_user, "transfer_out", amount, f"تحويل لـ {to_user}: {reason}")
    create_transaction(to_user, "transfer_in", amount, f"تحويل من {from_user}: {reason}")

    save_data(data)
    return True

# ───────────────────────────────────────────
# 📝 إدارة المعاملات
# ───────────────────────────────────────────

def create_transaction(user_id, tx_type, amount, reason="", reference_id=None):
    """إنشاء معاملة جديدة"""
    data["transaction_counter"] += 1
    tx_id = data["transaction_counter"]

    tx = {
        "id": tx_id,
        "user_id": str(user_id),
        "type": tx_type,  # deposit, withdrawal, transfer_in, transfer_out, purchase
        "amount": amount,
        "reason": reason,
        "reference_id": reference_id,
        "status": "completed",
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "timestamp": datetime.now().timestamp()
    }

    data["transactions"].append(tx)

    if tx_type == "deposit":
        data["deposits"].append(tx)
    elif tx_type in ["withdrawal", "purchase"]:
        data["withdrawals"].append(tx)

    save_data(data)
    return tx

def get_user_transactions(user_id, limit=20):
    """جلب معاملات المستخدم"""
    user_id = str(user_id)
    txs = [tx for tx in data["transactions"] if tx["user_id"] == user_id]
    return sorted(txs, key=lambda x: x["timestamp"], reverse=True)[:limit]

def get_transaction(tx_id):
    """جلب معاملة محددة"""
    return next((tx for tx in data["transactions"] if tx["id"] == tx_id), None)

# ───────────────────────────────────────────
# 📊 إحصائيات
# ───────────────────────────────────────────

def get_stats():
    """إحصائيات عامة"""
    total_users = len(data["users"])
    total_balance = sum(u["balance"] for u in data["users"].values())
    total_deposited = sum(u["total_deposited"] for u in data["users"].values())
    total_spent = sum(u["total_spent"] for u in data["users"].values())

    return {
        "total_users": total_users,
        "total_balance": total_balance,
        "total_deposited": total_deposited,
        "total_spent": total_spent,
        "total_transactions": len(data["transactions"]),
        "pending_deposits": len([d for d in data["deposits"] if d["status"] == "pending"])
    }

def get_top_users(limit=10):
    """أكثر المستخدمين إيداعاً"""
    users = sorted(
        data["users"].values(),
        key=lambda u: u["total_deposited"],
        reverse=True
    )[:limit]
    return users

# ───────────────────────────────────────────
# 🔍 دوال البحث
# ───────────────────────────────────────────

def search_user_by_username(username):
    """البحث عن مستخدم باليوزر"""
    for user_id, user in data["users"].items():
        if user.get("username") and username.lower() in user["username"].lower():
            return user
    return None

def search_user_by_name(name):
    """البحث عن مستخدم بالاسم"""
    results = []
    for user_id, user in data["users"].items():
        if name.lower() in user.get("name", "").lower():
            results.append(user)
    return results

# ───────────────────────────────────────────
# ⚙️ إدارة النظام
# ───────────────────────────────────────────

def ban_user(user_id, reason=""):
    """حظر مستخدم"""
    user = get_user(user_id)
    if user:
        user["status"] = "banned"
        user["notes"] = reason
        save_data(data)
        return True
    return False

def unban_user(user_id):
    """فك حظر مستخدم"""
    user = get_user(user_id)
    if user:
        user["status"] = "active"
        save_data(data)
        return True
    return False

def reset_user_balance(user_id):
    """تصفير رصيد مستخدم (للأدمن فقط)"""
    user = get_user(user_id)
    if user:
        user["balance"] = 0
        save_data(data)
        return True
    return False

def add_admin_note(user_id, note):
    """إضافة ملاحظة للمستخدم"""
    user = get_user(user_id)
    if user:
        user["notes"] = note
        save_data(data)
        return True
    return False
