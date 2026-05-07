"""
⚙️ إعدادات البوت
================
الملف بيقرأ تلقائياً من .env
"""

import os

# محاولة قراءة .env
if os.path.exists('.env'):
    with open('.env', 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()

# ───────────────────────────────────────────
# 🔑 إعدادات البوت
# ───────────────────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
ADMIN_ID = int(os.getenv("ADMIN_ID", "123456789"))

# ───────────────────────────────────────────
# 💳 إعدادات API سرياتيل كاش
# ───────────────────────────────────────────
SYRIATEL_API_KEY = os.getenv("SYRIATEL_API_KEY", "")
SYRIATEL_API_URL = os.getenv("SYRIATEL_API_URL", "https://api.syriatel-payment.com/v1")

# ───────────────────────────────────────────
# 💳 إعدادات API شام كاش
# ───────────────────────────────────────────
SHAM_API_KEY = os.getenv("SHAM_API_KEY", "")
SHAM_API_URL = os.getenv("SHAM_API_URL", "https://api.shamcash-payment.com/v1")

# ───────────────────────────────────────────
# 📱 أرقام التحويل
# ───────────────────────────────────────────
SYRIATEL_NUMBER = os.getenv("SYRIATEL_NUMBER", "0987654321")
SHAM_NUMBER = os.getenv("SHAM_NUMBER", "0998765432")

# ───────────────────────────────────────────
# 🌐 إعدادات عامة
# ───────────────────────────────────────────
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")
MIN_DEPOSIT = 10000
MAX_DEPOSIT = 1000000
DEFAULT_CURRENCY = "SYP"

# التحقق من الإعدادات
if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
    print("⚠️ تحذير: لم يتم تعيين BOT_TOKEN!")
    print("أنشئ ملف .env وضع فيه: BOT_TOKEN=your_token_here")
