"""
🤖 بوت متجر الخدمات + نظام المحفظة
====================================

📦 الملفات:
-----------
• config.py          ← إعداداتك (Token, API keys)
• wallet_manager.py  ← إدارة المحافظ والمعاملات
• payment_api.py     ← تكامل API الدفع
• wallet_store_bot.py ← البوت الرئيسي

🚀 خطوات التشغيل:
----------------
1. تثبيت المكتبة:
   pip install python-telegram-bot requests

2. تعديل config.py:
   - ضع توكن البوت (من @BotFather)
   - ضع آيدي الأدمن (من @userinfobot)
   - ضع معلومات API الدفع

3. تشغيل البوت:
   python wallet_store_bot.py

📱 مميزات البوت:
---------------
✅ شحن رصيد تلقائي (سرياتيل كاش / شام كاش)
✅ متجر خدمات بـ 5 أقسام
✅ سلة مشتريات + دفع من الرصيد
✅ سجل المعاملات
✅ تواصل مع الدعم
✅ لوحة تحكم الأدمن كاملة

🔧 تخصيص API الدفع:
------------------
في payment_api.py، عدل:
- PAYMENT_PROVIDER: "custom" لـ API حقيقي
- create_payment(): أضف كود API الخاص بك
- check_payment_status(): أضف منطق التحقق

⚠️ ملاحظة:
----------
• لا تبعث secrets في المحادثات
• احفظ config.py بعيداً عن Git
• اختبر بـ Mock mode أولاً
"""
