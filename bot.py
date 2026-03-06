# لا تنسى ذكر الله 🤍
# ELITE HOST BOT v5.0 — ULTRA EDITION

import telebot, os, json, subprocess, sys, psutil, shutil, logging, threading, time, re, hashlib, socket, random, string, zipfile
from telebot import types
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from collections import defaultdict

# ══════════════════════════════════════════════════════════════
#  السجل
# ══════════════════════════════════════════════════════════════
os.makedirs("LOGS", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler("LOGS/bot.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger("ELITE")

# ══════════════════════════════════════════════════════════════
#  الإعدادات
# ══════════════════════════════════════════════════════════════
TOKEN     = os.environ.get("TOKEN", "8675185329:AAEjB2PoLaqfxl9FDxI_cKkJHu-3xfKOMbM")
ADMIN_ID  = int(os.environ.get("ADMIN_ID", "6918240643"))
ADMIN_IDS = [int(x) for x in os.environ.get("ADMIN_IDS", "6918240643").split(",")]

bot      = telebot.TeleBot(TOKEN, threaded=True, num_threads=160)
executor = ThreadPoolExecutor(max_workers=160)
BOT_START_TIME = time.time()

for d in ["ELITE_HOST","GHOST_VOLUMES","SYSTEM_CORES","LOGS","QUARANTINE","BACKUPS"]:
    os.makedirs(d, exist_ok=True)

# ══════════════════════════════════════════════════════════════
#  نظام الأمان المتقدم
# ══════════════════════════════════════════════════════════════

# ── Rate Limiting متعدد المستويات ──────────────────────────
spam_counter   = defaultdict(list)
upload_counter = defaultdict(list)
spam_blocked   = {}          # uid -> unblock_time
failed_cmds    = defaultdict(int)   # uid -> عدد المحاولات الفاشلة
suspicious     = set()       # مستخدمون مشبوهون

# إعدادات
SPAM_LIMIT        = 8        # رسايل في
SPAM_WINDOW       = 10       # ثواني
SPAM_BAN_TIME     = 60       # ثانية حظر
UPLOAD_LIMIT      = 5        # رفعات في
UPLOAD_WINDOW     = 60       # ثانية
MAX_FAILED_CMDS   = 10       # محاولات فاشلة قبل الحظر

def is_spam(uid:str) -> bool:
    if uid in spam_blocked:
        if time.time() < spam_blocked[uid]: return True
        else: del spam_blocked[uid]
    now = time.time()
    spam_counter[uid] = [t for t in spam_counter[uid] if now-t < SPAM_WINDOW]
    spam_counter[uid].append(now)
    if len(spam_counter[uid]) > SPAM_LIMIT:
        spam_blocked[uid] = now + SPAM_BAN_TIME
        log.warning(f"SPAM blocked: {uid}")
        # أبلغ الأدمن لو تكرر
        failed_cmds[uid] += 1
        if failed_cmds[uid] >= 3:
            suspicious.add(uid)
            try: bot.send_message(ADMIN_ID, f"🚨 مستخدم مشبوه: `{uid}` — spam متكرر", parse_mode="Markdown")
            except: pass
        return True
    return False

def is_upload_spam(uid:str) -> bool:
    now = time.time()
    upload_counter[uid] = [t for t in upload_counter[uid] if now-t < UPLOAD_WINDOW]
    upload_counter[uid].append(now)
    return len(upload_counter[uid]) > UPLOAD_LIMIT

def check_suspicious(uid:str, action:str=""):
    """تتبع المحاولات المشبوهة"""
    failed_cmds[uid] += 1
    if failed_cmds[uid] >= MAX_FAILED_CMDS:
        suspicious.add(uid)
        add_to_blacklist(uid)
        try: bot.send_message(ADMIN_ID,
            f"🔴 حظر تلقائي: `{uid}`\n"
            f"سبب: {MAX_FAILED_CMDS} محاولة مشبوهة\n"
            f"آخر فعل: {action}", parse_mode="Markdown")
        except: pass

def validate_file(raw:bytes, fname:str, uid:str) -> tuple:
    """التحقق من الملف قبل الرفع — يرجع (ok, reason)"""
    # فحص الحجم
    max_kb = db["settings"].get("max_file_size_kb", 500)
    if len(raw) > max_kb * 1024:
        return False, f"الملف كبير ({len(raw)//1024}KB) — الحد {max_kb}KB"

    # فحص عدد الملفات للمستخدم العادي
    role = get_role(uid)
    if role == ROLE_USER:
        user_files = sum(1 for v in db["files"].values() if v.get("owner")==uid)
        max_files  = db["settings"].get("max_files_per_user", 5)
        if user_files >= max_files:
            return False, f"وصلت للحد الأقصى ({max_files} ملفات)"

    # فحص rate limit للرفع
    if is_upload_spam(uid):
        return False, f"كتير رفعات — انتظر دقيقة"

    # فحص امتداد الملف
    allowed = [".py", ".js", ".sh", ".json", ".txt", ".env", ".toml", ".yaml", ".yml"]
    ext = os.path.splitext(fname)[1].lower()
    if ext not in allowed:
        return False, f"امتداد {ext} مش مدعوم"

    return True, "ok"

# ── فاحص محتوى URL في الرسائل ─────────────────────────────
PHISHING_PATTERNS = [
    r"bit\.ly|tinyurl|t\.co",         # روابط مختصرة
    r"free.*hack|hack.*free",          # مواقع هكر
    r"win.*prize|claim.*reward",       # نصب
]

def contains_suspicious_url(text:str) -> bool:
    for p in PHISHING_PATTERNS:
        if re.search(p, text, re.IGNORECASE):
            return True
    return False

# ══════════════════════════════════════════════════════════════
#  معالج الأخطاء العام
# ══════════════════════════════════════════════════════════════
def handle_error(e: Exception, context: str = ""):
    log.error(f"ERROR [{context}]: {e}")
    try:
        bot.send_message(ADMIN_ID,
            f"🔴 خطأ في البوت\n"
            f"📍 {context}\n"
            f"❌ {str(e)[:300]}")
    except: pass

# ══════════════════════════════════════════════════════════════
#  مراقبة الصحة التلقائية
# ══════════════════════════════════════════════════════════════
HEALTH_LOG = []   # آخر 50 قراءة

def health_monitor():
    while True:
        time.sleep(60)
        try:
            cpu = psutil.cpu_percent(interval=1)
            mem = psutil.virtual_memory().percent
            disk= psutil.disk_usage('/').percent
            HEALTH_LOG.append({
                "time": datetime.now().strftime('%H:%M'),
                "cpu": cpu, "mem": mem, "disk": disk
            })
            if len(HEALTH_LOG) > 50: HEALTH_LOG.pop(0)

            # تحذير لو الموارد عالية
            if cpu > 90:
                bot.send_message(ADMIN_ID, f"🔥 تحذير: CPU وصل {cpu}%!")
            if mem > 90:
                bot.send_message(ADMIN_ID, f"🔥 تحذير: RAM وصل {mem}%!")
            if disk > 90:
                bot.send_message(ADMIN_ID, f"🔥 تحذير: Disk وصل {disk}%!")

            # تحقق من العمليات المتوقفة
            for name, info in list(running_procs.items()):
                if info["proc"].poll() is not None:
                    if name in db["files"] and not db["files"][name].get("auto_restart"):
                        db["files"][name]["active"] = False
                        running_procs.pop(name, None)
                        save()
                        bot.send_message(ADMIN_ID, f"⚠️ توقف: `{name}` — يمكنك إعادة تشغيله", parse_mode="Markdown")
        except Exception as e:
            log.error(f"Health monitor: {e}")

threading.Thread(target=health_monitor, daemon=True).start()

# ══════════════════════════════════════════════════════════════
#  باك أب تلقائي
# ══════════════════════════════════════════════════════════════
def auto_backup():
    while True:
        time.sleep(3600 * int(os.environ.get("BACKUP_HOURS","6")))
        try:
            if not os.path.exists(DB_FILE): continue
            ts  = datetime.now().strftime('%Y%m%d_%H%M')
            dst = f"BACKUPS/elite_db_{ts}.json"
            shutil.copy2(DB_FILE, dst)
            # احتفظ بآخر 10 باك أب بس
            backups = sorted([f for f in os.listdir("BACKUPS") if f.endswith(".json")])
            for old in backups[:-10]:
                os.remove(f"BACKUPS/{old}")
            with open(dst,'rb') as f:
                bot.send_document(ADMIN_ID, f,
                    caption=f"💾 باك أب تلقائي\n🕐 {datetime.now().strftime('%Y-%m-%d %H:%M')}")
            log.info(f"Auto backup: {dst}")
        except Exception as e:
            log.error(f"Auto backup: {e}")

threading.Thread(target=auto_backup, daemon=True).start()

# ══════════════════════════════════════════════════════════════
#  قاعدة البيانات
# ══════════════════════════════════════════════════════════════
DB_FILE = "elite_db.json"

def load_db():
    default = {
        "users":     {},
        "files":     {},
        "envs":      {},
        "scheduled": [],
        "quarantine":[],
        "tickets":   {},   # ticket_id -> {uid, msg, status, replies, created}
        "blacklist": [],   # قائمة IPs/UIDs المحظورة
        "alerts":    [],   # إشعارات مخصصة
        "file_versions": {},  # fname -> [list of old versions]
        "stats":     {"uploads":0,"kills":0,"commands":0,"restarts":0,"blocked":0,"total_credits_given":0,"tickets_opened":0},
        "settings":  {
            "max_files_per_user":   5,
            "max_file_size_kb":     500,
            "credits_per_upload":   0,       # لا نقاط على الرفع
            "upload_cost":          6,       # رفع ملف يكلف 6 نقاط
            "credits_for_referral": 2,       # نقطتين لكل إحالة
            "vip_min_credits":      500,
            "welcome_credits":      0,       # بدون نقاط ترحيب
            "maintenance":          False,
            "auto_vip":             True,
            "notify_on_crash":      True,
            "notify_on_new_user":   True,
            "max_crashes_before_disable": 5,
        },
        "referral_codes": {},
        "notes":     [],
        "locked":    False,
        "daily_report_time": "08:00",
    }
    if not os.path.exists(DB_FILE): return default
    try:
        with open(DB_FILE,'r',encoding='utf-8') as f: data=json.load(f)
        for k,v in default.items():
            if k not in data: data[k]=v
        if "settings" not in data: data["settings"] = default["settings"]
        for k,v in default["settings"].items():
            if k not in data["settings"]: data["settings"][k] = v
        return data
    except: return default

db = load_db()

# ── تحديث الإعدادات القديمة بالقوة ──────────────────────────
db["settings"]["credits_per_upload"]   = 0
db["settings"]["upload_cost"]          = 6
db["settings"]["credits_for_referral"] = 2
db["settings"]["welcome_credits"]      = 0
db["settings"]["vip_min_credits"]      = 500
# صفّر النقاط الترحيبية للمستخدمين اللي عندهم 20 بس (ما دعوش حد)
for u, info in db["users"].items():
    if info.get("credits", 0) == 20 and info.get("total_referred", 0) == 0 and info.get("uploads", 0) == 0:
        info["credits"] = 0
save()

def save():
    with open(DB_FILE,'w',encoding='utf-8') as f:
        json.dump(db,f,ensure_ascii=False,indent=2)

# ══════════════════════════════════════════════════════════════
#  الصلاحيات
# ══════════════════════════════════════════════════════════════
ROLE_OWNER = "owner"
ROLE_ADMIN = "admin"
ROLE_VIP   = "vip"
ROLE_USER  = "user"

def get_role(uid:str) -> str:
    if int(uid) == ADMIN_ID:           return ROLE_OWNER
    if int(uid) in ADMIN_IDS:          return ROLE_ADMIN
    u = db["users"].get(uid,{})
    return u.get("role", ROLE_USER)

def is_staff(uid:str) -> bool:
    return get_role(uid) in [ROLE_OWNER, ROLE_ADMIN]

def reg_user(m):
    uid  = str(m.from_user.id)
    name = m.from_user.first_name or "مستخدم"
    if uid not in db["users"]:
        ref_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        db["users"][uid] = {
            "name":           name,
            "joined":         datetime.now().strftime('%Y-%m-%d %H:%M'),
            "role":           ROLE_USER,
            "uploads":        0,
            "credits":        db["settings"].get("welcome_credits", 20),
            "referral_code":  ref_code,
            "referred_by":    None,
            "total_referred": 0,
        }
        db["referral_codes"][ref_code] = uid
        save()
        try:
            bot.send_message(ADMIN_ID,
                f"👤 مستخدم جديد: {name} ({uid})\n"
                f"💎 نقطة ترحيبي: {db['settings']['welcome_credits']}")
        except: pass
    else:
        db["users"][uid]["name"] = name
        if "credits"       not in db["users"][uid]: db["users"][uid]["credits"] = 20
        if "referral_code" not in db["users"][uid]:
            rc = ''.join(random.choices(string.ascii_uppercase+string.digits, k=8))
            db["users"][uid]["referral_code"] = rc
            db["referral_codes"][rc] = uid
    return uid

def add_credits(uid:str, amount:int, reason:str=""):
    db["users"].setdefault(uid, {})["credits"] = db["users"][uid].get("credits",0) + amount
    save()
    try:
        bot.send_message(int(uid),
            f"💎 +{amount} نقطة! {reason}\n"
            f"رصيدك: {db['users'][uid]['credits']}")
    except: pass
    check_vip_upgrade(uid)

def check_vip_upgrade(uid:str):
    if get_role(uid) == ROLE_USER:
        if db["users"][uid].get("credits",0) >= db["settings"].get("vip_min_credits",200):
            db["users"][uid]["role"] = ROLE_VIP; save()
            try:
                bot.send_message(int(uid),
                    "🌟 تهانينا! ترقيت لـ VIP تلقائياً!\n"
                    "استمتع بالمميزات الإضافية 🎉",
                    reply_markup=get_kb(uid))
            except: pass

# ══════════════════════════════════════════════════════════════
#  فاحص الملفات
# ══════════════════════════════════════════════════════════════
# ── أنماط الخطر الحقيقي فقط (مش كل حاجة) ──
DANGER_PATTERNS = [
    # حذف ملفات
    (r"os\.system\s*\(['\"]?\s*rm\s+-rf",        "حذف ملفات النظام بـ os.system"),
    (r"shutil\.rmtree\s*\(['\"]?/",              "حذف مجلد جذر النظام"),
    # تنفيذ كود مشفر
    (r"eval\s*\(\s*base64",                      "تنفيذ كود مشفر base64"),
    (r"exec\s*\(\s*base64",                      "تنفيذ كود مشفر base64"),
    (r"exec\s*\(\s*__import__",                  "تنفيذ كود ديناميكي خطير"),
    (r"compile\s*\(.*exec",                      "تجميع وتنفيذ كود خطير"),
    # استيراد مخفي
    (r"__import__\s*\(['\"]os['\"]",             "استيراد os بشكل مخفي"),
    (r"__import__\s*\(['\"]subprocess",          "استيراد subprocess بشكل مخفي"),
    (r"importlib\.import_module.*subprocess",    "استيراد subprocess ديناميكي"),
    # Fork Bomb
    (r"fork\s*\(\s*\).*while",                   "fork bomb محتمل"),
    (r"while\s+True\s*:\s*\n\s*(os\.fork|subprocess)", "fork bomb loop"),
    (r"os\.fork\(\).*os\.fork\(\)",             "fork bomb مزدوج"),
    # تعدين
    (r"cryptominer|xmrig|minerd|stratum\+tcp",   "تعدين عملات مشفرة"),
    (r"hashlib\.sha256.*nonce.*target",          "خوارزمية تعدين"),
    # قواعد بيانات
    (r"(DROP\s+TABLE|DELETE\s+FROM.*WHERE\s+1=1)", "حذف قاعدة بيانات"),
    (r"TRUNCATE\s+TABLE",                         "تفريغ جدول قاعدة بيانات"),
    # ملفات النظام
    (r"(\/etc\/passwd|\/etc\/shadow)",           "الوصول لملفات النظام الحساسة"),
    (r"(\/proc\/self|\/sys\/kernel)",            "الوصول لنواة النظام"),
    # تجسس
    (r"keylog|keystroke|pynput.*Listener",       "كيلوجر / تتبع لوحة المفاتيح"),
    (r"screenshot.*loop|mss.*grab.*while",       "تقاط صور متكررة"),
    (r"cv2\.VideoCapture\(0\).*while",           "تشغيل الكاميرا سرياً"),
    # شبكة خطيرة
    (r"reverse.?shell|bind.?shell",              "reverse shell"),
    (r"socket\.connect.*4444|socket\.connect.*1337", "اتصال بمنفذ مشبوه"),
    (r"paramiko.*exec_command.*rm\s+-rf",        "أوامر خطيرة عبر SSH"),
    # رانسوموير
    (r"Fernet.*encrypt.*os\.walk",               "تشفير ملفات (ransomware محتمل)"),
    (r"AES.*encrypt.*os\.listdir",               "تشفير ملفات (ransomware محتمل)"),
]

# ── خريطة شاملة للمكاتب مع الإصدارات الصحيحة ──
IMPORT_MAP = {
    # تليجرام
    "telegram":       "python-telegram-bot==21.3",
    "telebot":        "pyTelegramBotAPI",
    "aiogram":        "aiogram==3.7.0",
    "telethon":       "telethon",
    "pyrogram":       "pyrogram tgcrypto",
    # HTTP
    "requests":       "requests",
    "aiohttp":        "aiohttp",
    "httpx":          "httpx==0.27.2",
    "urllib3":        "urllib3",
    "httplib2":       "httplib2",
    "websocket":      "websocket-client",
    "websockets":     "websockets",
    # ويب
    "flask":          "flask",
    "fastapi":        "fastapi uvicorn",
    "django":         "django",
    "starlette":      "starlette",
    "tornado":        "tornado",
    "quart":          "quart",
    "sanic":          "sanic",
    # قواعد بيانات
    "sqlalchemy":     "sqlalchemy",
    "aiosqlite":      "aiosqlite",
    "pymongo":        "pymongo",
    "motor":          "motor",
    "redis":          "redis",
    "aioredis":       "aioredis",
    "peewee":         "peewee",
    "tortoise":       "tortoise-orm",
    "databases":      "databases",
    # بيانات
    "numpy":          "numpy",
    "pandas":         "pandas",
    "scipy":          "scipy",
    "sklearn":        "scikit-learn",
    "matplotlib":     "matplotlib",
    "seaborn":        "seaborn",
    "plotly":         "plotly",
    # صور
    "PIL":            "Pillow",
    "cv2":            "opencv-python",
    "skimage":        "scikit-image",
    "imageio":        "imageio",
    # أدوات
    "dotenv":         "python-dotenv",
    "apscheduler":    "apscheduler",
    "bs4":            "beautifulsoup4",
    "lxml":           "lxml",
    "html5lib":       "html5lib",
    "loguru":         "loguru",
    "colorama":       "colorama",
    "psutil":         "psutil",
    "cryptography":   "cryptography",
    "nacl":           "PyNaCl",
    "jwt":            "PyJWT",
    "yaml":           "pyyaml",
    "toml":           "toml",
    "qrcode":         "qrcode",
    "barcode":        "python-barcode",
    "gtts":           "gTTS",
    "pydub":          "pydub",
    "schedule":       "schedule",
    "pytz":           "pytz",
    "dateutil":       "python-dateutil",
    "tqdm":           "tqdm",
    "rich":           "rich",
    "click":          "click",
    "typer":          "typer",
    "pydantic":       "pydantic",
    "attrs":          "attrs",
    "cachetools":     "cachetools",
    "aiofiles":       "aiofiles",
    "anyio":          "anyio",
    "trio":           "trio",
    "uvloop":         "uvloop",
    "paramiko":       "paramiko",
    "fabric":         "fabric",
    "boto3":          "boto3",
    "google":         "google-api-python-client",
    "tweepy":         "tweepy",
    "discord":        "discord.py",
    "slack_sdk":      "slack-sdk",
    "stripe":         "stripe",
    "paypalrestsdk":  "paypalrestsdk",
    "jwt":            "PyJWT",
    "passlib":        "passlib",
    "bcrypt":         "bcrypt",
    "arrow":          "arrow",
    "humanize":       "humanize",
    "emoji":          "emoji",
    "translate":      "translate",
    "deep_translator":"deep-translator",
    "googletrans":    "googletrans==4.0.0rc1",
    "openai":         "openai",
    "anthropic":      "anthropic",
    "groq":           "groq",
    "cohere":         "cohere",
    "transformers":   "transformers",
    "torch":          "torch",
    "tensorflow":     "tensorflow",
    "keras":          "keras",
    "celery":         "celery",
    "kombu":          "kombu",
    "pika":           "pika",
    "kafka":          "kafka-python",
    "nats":           "nats-py",
    "socketio":       "python-socketio",
    "pyserial":       "pyserial",
    "serial":         "pyserial",
    "RPi":            "RPi.GPIO",
}

BUILTIN = {
    "os","sys","re","json","time","math","random","string","hashlib","logging",
    "sqlite3","threading","traceback","io","datetime","collections","functools",
    "typing","pathlib","shutil","subprocess","asyncio","abc","copy","enum","gc",
    "glob","gzip","inspect","itertools","operator","pickle","platform","queue",
    "signal","socket","struct","tempfile","textwrap","urllib","uuid","warnings",
    "weakref","zipfile","base64","csv","html","http","email","concurrent",
    "contextlib","dataclasses","decimal","difflib","fractions","heapq","hmac",
    "ipaddress","keyword","locale","mimetypes","numbers","pprint","secrets",
    "stat","statistics","tarfile","types","builtins","__future__","argparse",
    "configparser","getpass","getopt","optparse","unittest","doctest","pdb",
    "profile","timeit","cProfile","dis","ast","tokenize","token","compileall",
    "py_compile","importlib","pkgutil","zipimport","site","code","codeop",
    "pprint","reprlib","textwrap","unicodedata","stringprep","readline","rlcompleter",
    "struct","codecs","io","abc","numbers","cmath","decimal","fractions","random",
    "statistics","array","queue","types","copy","pprint","enum","graphlib",
}

def _is_installed(pkg:str) -> bool:
    """تحقق هل المكتبة متثبتة أصلاً"""
    import importlib.util
    name = pkg.split("==")[0].split(">=")[0].split("<=")[0]
    # تحويل اسم pip لاسم import
    pip_to_import = {
        "pyTelegramBotAPI":"telebot", "python-telegram-bot":"telegram",
        "Pillow":"PIL", "beautifulsoup4":"bs4", "python-dotenv":"dotenv",
        "scikit-learn":"sklearn", "opencv-python":"cv2", "PyJWT":"jwt",
        "pyyaml":"yaml", "gTTS":"gtts", "python-dateutil":"dateutil",
        "aioredis":"aioredis",
    }
    import_name = pip_to_import.get(name, name.replace("-","_"))
    try:
        return importlib.util.find_spec(import_name) is not None
    except: return False

def scan_file(path:str) -> dict:
    """فحص ذكي للملف — يكتشف المكاتب ويتحقق من الأمان"""
    result = {"safe":True, "warnings":[], "danger":[], "imports":[], "to_install":[]}
    try:
        with open(path,'r',encoding='utf-8',errors='replace') as f:
            content = f.read()

        # ── فحص الأمان (أنماط الخطر الحقيقي فقط) ──
        for pattern, desc in DANGER_PATTERNS:
            if re.search(pattern, content, re.IGNORECASE|re.DOTALL):
                result["danger"].append(desc)
                result["safe"] = False

        # ── استخراج المكاتب بطريقة أذكى ──
        imports = set()
        for line in content.splitlines():
            stripped = line.strip()
            # تجاهل التعليقات
            if stripped.startswith("#"): continue
            # import x / import x.y
            m = re.match(r'^import\s+([\w]+)', stripped)
            if m: imports.add(m.group(1))
            # from x import y
            m = re.match(r'^from\s+([\w]+)', stripped)
            if m: imports.add(m.group(1))

        result["imports"] = sorted(imports - BUILTIN)

        # ── تحديد اللي محتاج تثبيت ──
        to_install = []
        for imp in imports:
            if imp in BUILTIN: continue
            if imp in IMPORT_MAP:
                pkgs = IMPORT_MAP[imp].split()
                for p in pkgs:
                    if not _is_installed(p):
                        to_install.append(p)
            else:
                # اسم غير معروف → جرّب بنفس الاسم لو مش متثبت
                if not _is_installed(imp):
                    to_install.append(imp)

        result["to_install"] = list(dict.fromkeys(to_install))  # بدون تكرار

    except Exception as e:
        result["warnings"].append(f"خطأ في الفحص: {e}")
    return result

def check_bot_config(path:str) -> dict:
    """فحص وجود التوكن والأدمن ID في ملف البوت"""
    result = {
        "has_token":   False,
        "has_admin":   False,
        "token_val":   None,
        "admin_val":   None,
        "token_type":  None,  # hardcoded / env
        "admin_type":  None,
        "warnings":    [],
        "suggestions": [],
    }
    try:
        with open(path,'r',encoding='utf-8',errors='replace') as f:
            content = f.read()

        # ── فحص التوكن ──────────────────────────────
        # Hardcoded token مثل "123456:ABC..."
        tok_match = re.search(r'["\'](\d{8,10}:[A-Za-z0-9_-]{35,})["\']', content)
        if tok_match:
            result["has_token"]  = True
            result["token_type"] = "hardcoded"
            result["token_val"]  = tok_match.group(1)[:20] + "..."
        # env مثل os.environ.get("BOT_TOKEN") أو os.getenv("TOKEN")
        elif re.search(r'(os\.environ|os\.getenv|environ\.get).*["\'][A-Z_]*TOKEN[A-Z_]*["\']', content, re.IGNORECASE):
            result["has_token"]  = True
            result["token_type"] = "env"
            result["token_val"]  = "من متغيرات البيئة"
        else:
            result["warnings"].append("❌ مفيش توكن — ابحث عن TOKEN في الكود وحطه")
            result["suggestions"].append("TOKEN = 'توكنك من @BotFather'")

        # ── فحص الأدمن ID ────────────────────────────
        admin_match = re.search(r'(ADMIN|OWNER|MASTER|admin_id|owner_id)\s*=\s*["\']?(\d{5,12})["\']?', content, re.IGNORECASE)
        if admin_match:
            result["has_admin"]  = True
            result["admin_type"] = "hardcoded"
            result["admin_val"]  = admin_match.group(2)
        elif re.search(r'(os\.environ|os\.getenv|environ\.get).*["\'][A-Z_]*(?:ADMIN|OWNER|MASTER)[A-Z_]*["\']', content, re.IGNORECASE):
            result["has_admin"]  = True
            result["admin_type"] = "env"
            result["admin_val"]  = "من متغيرات البيئة"
        else:
            result["warnings"].append("❌ مفيش ADMIN_ID — حط ID الأدمن في الكود")
            result["suggestions"].append("ADMIN_ID = رقمك (اكتب /id للبوت تعرفه)")

        # ── تحقق من صحة التوكن شكلاً ─────────────────
        if result["token_type"] == "hardcoded" and tok_match:
            tok = tok_match.group(1)
            if not re.match(r'^\d{8,10}:[A-Za-z0-9_-]{35,}$', tok):
                result["warnings"].append("⚠️ التوكن شكله غلط — تأكد منه من @BotFather")

    except Exception as e:
        result["warnings"].append(f"خطأ في الفحص: {e}")
    return result

# ══════════════════════════════════════════════════════════════
#  تثبيت المكاتب
# ══════════════════════════════════════════════════════════════
def install_pkgs(pkgs:list, chat_id:int=None) -> bool:
    if not pkgs: return True
    try:
        pkgs_txt = " ".join(pkgs)
        if chat_id: bot.send_message(chat_id, f"📦 جارٍ تثبيت {len(pkgs)} مكتبة...")
        r = subprocess.run([sys.executable,"-m","pip","install"]+pkgs+["--quiet"],
                           capture_output=True, text=True, timeout=300)
        if r.returncode == 0:
            if chat_id: bot.send_message(chat_id, f"✅ تم تثبيت {len(pkgs)} مكتبة بنجاح!")
            return True
        else:
            # استخراج المكاتب اللي فشلت فقط
            out = (r.stdout+r.stderr).strip()
            failed = re.findall(r"Failed building wheel for ([\w\-]+)", out)
            failed_txt = " | ".join(failed) if failed else "بعض المكاتب"
            if chat_id:
                bot.send_message(chat_id,
                    f"⚠️ فشل تثبيت: {failed_txt}\n"
                    f"السبب: محتاج C compiler غير متاح على السيرفر.\n"
                    f"الباقي اتثبّت بنجاح ✅")
            return False
    except subprocess.TimeoutExpired:
        if chat_id: bot.send_message(chat_id, "⏱ انتهى وقت التثبيت (5 دقايق)")
        return False
    except Exception as e:
        if chat_id: bot.send_message(chat_id, f"❌ خطأ: {e}")
        return False

def install_req_file(path:str, chat_id:int=None) -> bool:
    try:
        if chat_id: bot.send_message(chat_id, "📦 جارٍ تثبيت المكاتب من الملف...", parse_mode="Markdown")
        r = subprocess.run([sys.executable,"-m","pip","install","-r",path,"--quiet"],
                           capture_output=True, text=True, timeout=180)
        if r.returncode == 0:
            if chat_id: bot.send_message(chat_id, "✅ تم التثبيت!", parse_mode="Markdown")
            return True
        else:
            out = (r.stdout+r.stderr).strip()
            if chat_id: bot.send_message(chat_id, f"⚠️ خطأ:\n```\n{out[-1500:]}\n```", parse_mode="Markdown")
            return False
    except: return False

# ══════════════════════════════════════════════════════════════
#  تشغيل الملفات
# ══════════════════════════════════════════════════════════════
running_procs   = {}
restart_threads = {}

def launch(path:str, name:str=None):
    try:
        ext     = os.path.splitext(path)[1].lower()
        log_out = open(f"LOGS/{os.path.basename(path)}.log","w",encoding="utf-8")
        env     = os.environ.copy()
        env["PATH"] = "/opt/node/bin:" + env.get("PATH","")
        if name and name in db.get("envs",{}): env.update(db["envs"][name])
        # نسخ data.json لنفس مجلد الملف لو موجود
        file_dir = os.path.dirname(os.path.abspath(path))
        for extra in ["data.json","config.json",".env"]:
            for loc in [".", "ELITE_HOST"]:
                src = os.path.join(loc, extra)
                dst = os.path.join(file_dir, extra)
                if os.path.exists(src) and src != dst:
                    try: shutil.copy2(src, dst)
                    except: pass
        # اكتشاف node تلقائياً
        node_bin = "/opt/node/bin/node"
        if not os.path.exists(node_bin):
            node_bin = shutil.which("node") or "node"
        cmds    = {".py":[sys.executable,path], ".js":[node_bin,path], ".sh":["bash",path]}
        if ext not in cmds: return None
        if ext == ".sh": os.chmod(path, 0o755)
        proc = subprocess.Popen(cmds[ext], start_new_session=True,
                                stdout=log_out, stderr=subprocess.STDOUT, env=env)
        info = {"proc":proc, "pid":proc.pid, "started":time.time()}
        if name:
            running_procs[name] = info
            if name in db["files"]:
                db["files"][name]["active"] = True; save()
        log.info(f"Launch: {path} PID:{proc.pid}")
        return proc
    except Exception as e:
        log.error(f"Launch error: {e}"); return None

def stop_file(name:str):
    info = running_procs.pop(name, None)
    if info:
        pid = info.get("pid")
        try:
            import signal
            os.killpg(os.getpgid(pid), signal.SIGKILL)
        except:
            try: os.kill(pid, 9)
            except:
                try: info["proc"].kill()
                except: pass
        # تأكد إن العملية ماتت فعلاً
        try:
            import psutil as _ps
            p = _ps.Process(pid)
            p.wait(timeout=3)
        except: pass
    if name in db["files"]:
        db["files"][name]["active"] = False
        save()

def kill_all_procs():
    """إيقاف كل العمليات بالقوة"""
    import signal
    killed = 0
    # من القائمة المعروفة
    for name in list(running_procs.keys()):
        stop_file(name)
        killed += 1
    # فحص أي عملية من ELITE_HOST مش في القائمة
    try:
        for proc in psutil.process_iter(['pid','cmdline']):
            try:
                cmd = " ".join(proc.info['cmdline'] or [])
                if "ELITE_HOST" in cmd and proc.pid != os.getpid():
                    os.kill(proc.pid, signal.SIGKILL)
                    killed += 1
            except: pass
    except: pass
    return killed

def auto_restart_watcher(name:str, path:str):
    while True:
        time.sleep(5)
        if name not in db["files"]: break
        if not db["files"][name].get("auto_restart"): break
        if not db["files"][name].get("active"): break
        info = running_procs.get(name)
        if info and info["proc"].poll() is not None:
            db["stats"]["restarts"] = db["stats"].get("restarts",0)+1; save()
            launch(path, name)
            try: bot.send_message(ADMIN_ID, f"🔁 إعادة تشغيل تلقائية: `{name}`", parse_mode="Markdown")
            except: pass

def enable_ar(name:str, path:str):
    if name in restart_threads and restart_threads[name].is_alive(): return
    t = threading.Thread(target=auto_restart_watcher, args=(name,path), daemon=True)
    t.start(); restart_threads[name] = t

# ══════════════════════════════════════════════════════════════
#  المجدول
# ══════════════════════════════════════════════════════════════
def scheduler():
    while True:
        time.sleep(30)
        for task in list(db.get("scheduled",[])):
            try:
                if not task.get("done") and datetime.now() >= datetime.strptime(task["run_at"],"%Y-%m-%d %H:%M"):
                    if task["name"] in db["files"]:
                        launch(db["files"][task["name"]]["path"], task["name"])
                        task["done"] = True; save()
                        bot.send_message(ADMIN_ID, f"⏰ *نُفِّذت:* `{task['name']}`", parse_mode="Markdown")
            except: pass

threading.Thread(target=scheduler, daemon=True).start()

# ── باك أب تلقائي كل 6 ساعات ────────────────────────────────
def auto_backup():
    while True:
        time.sleep(6 * 3600)
        try:
            if os.path.exists(DB_FILE):
                with open(DB_FILE,'rb') as f:
                    bot.send_document(ADMIN_ID, f,
                        caption=f"💾 *باك أب تلقائي*\n🕐 {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                        parse_mode="Markdown")
        except: pass

threading.Thread(target=auto_backup, daemon=True).start()

# ── تقرير يومي ────────────────────────────────────────────────
def daily_report():
    while True:
        time.sleep(60)
        try:
            now = datetime.now().strftime('%H:%M')
            if now == db.get("daily_report_time","08:00"):
                s = db["stats"]
                roles = {}
                for u,info in db["users"].items():
                    roles[info.get("role","user")] = roles.get(info.get("role","user"),0)+1
                mem  = psutil.virtual_memory()
                disk = psutil.disk_usage('/')
                report = (
                    f"📊 *التقرير اليومي — {datetime.now().strftime('%Y-%m-%d')}*\n"
                    f"━━━━━━━━━━━━━━━━━\n"
                    f"👥 المستخدمون: `{len(db['users'])}`\n"
                    f"  ├ ⭐ VIP: `{roles.get('vip',0)}`\n"
                    f"  └ 👤 عادي: `{roles.get('user',0)}`\n\n"
                    f"📂 الملفات: `{len(db['files'])}` | ⚡ شغّالة: `{len(running_procs)}`\n"
                    f"📤 رفعات: `{s.get('uploads',0)}` | 🔁 إعادات: `{s.get('restarts',0)}`\n\n"
                    f"💻 CPU: `{psutil.cpu_percent()}%` | RAM: `{mem.percent}%` | Disk: `{disk.percent}%`"
                )
                for admin in ADMIN_IDS:
                    try: bot.send_message(admin, report, parse_mode="Markdown")
                    except: pass
                time.sleep(61)
        except Exception as e:
            log.error(f"Daily report: {e}")

threading.Thread(target=daily_report, daemon=True).start()

# ── مراقب الكراشات ────────────────────────────────────────────
def crash_watcher():
    notified = set()
    while True:
        time.sleep(10)
        try:
            for name, info in list(running_procs.items()):
                if info["proc"].poll() is not None and name not in notified:
                    notified.add(name)
                    owner = db["files"].get(name,{}).get("owner")
                    if name in db["files"]:
                        db["files"][name]["crashes"] = db["files"][name].get("crashes",0)+1
                        db["files"][name]["active"]  = False
                        save()
                    for admin in ADMIN_IDS:
                        try: bot.send_message(admin, f"💥 توقف: `{name}`", parse_mode="Markdown")
                        except: pass
                    if owner and owner not in [str(a) for a in ADMIN_IDS]:
                        try:
                            bot.send_message(int(owner),
                                f"⚠️ ملفك توقف: {name}\n"
                                f"اضغط ▶️ تشغيل ملف لإعادة تشغيله")
                        except: pass
            notified &= set(running_procs.keys())
        except Exception as e:
            log.error(f"Crash watcher: {e}")

threading.Thread(target=crash_watcher, daemon=True).start()

# ══════════════════════════════════════════════════════════════
#  نظام الإشعارات المتقدم
# ══════════════════════════════════════════════════════════════
def notify_all(msg:str, role_filter:str=None):
    """إرسال إشعار لكل المستخدمين أو فئة معينة"""
    count = 0
    for u, info in list(db["users"].items()):
        if role_filter and info.get("role") != role_filter: continue
        try:
            bot.send_message(int(u), msg)
            count += 1; time.sleep(0.05)
        except: pass
    return count

def send_alert(uid:str, msg:str, level:str="info"):
    icons = {"info":"ℹ️","warn":"⚠️","error":"🔴","success":"✅"}
    try: bot.send_message(int(uid), f"{icons.get(level,'ℹ️')} {msg}")
    except: pass

# ══════════════════════════════════════════════════════════════
#  نظام تذاكر الدعم
# ══════════════════════════════════════════════════════════════
def open_ticket(uid:str, msg:str) -> str:
    tid = f"T{int(time.time())}"[-8:]
    db["tickets"][tid] = {
        "uid":     uid,
        "msg":     msg,
        "status":  "open",
        "replies": [],
        "created": datetime.now().strftime('%Y-%m-%d %H:%M')
    }
    db["stats"]["tickets_opened"] = db["stats"].get("tickets_opened",0)+1
    save()
    # إشعار الأدمن
    mk = types.InlineKeyboardMarkup()
    mk.add(types.InlineKeyboardButton(f"📩 رد على {tid}", callback_data=f"treply_{tid}"))
    mk.add(types.InlineKeyboardButton(f"✅ إغلاق {tid}", callback_data=f"tclose_{tid}"))
    name = db["users"].get(uid,{}).get("name","؟")
    for admin in ADMIN_IDS:
        try:
            bot.send_message(admin,
                f"🎫 تذكرة جديدة #{tid}\n"
                f"👤 {name} ({uid})\n"
                f"🕐 {db['tickets'][tid]['created']}\n"
                f"📝 {msg[:300]}",
                reply_markup=mk)
        except: pass
    return tid

# ══════════════════════════════════════════════════════════════
#  نظام إصدارات الملفات
# ══════════════════════════════════════════════════════════════
def save_file_version(fname:str, path:str):
    """احتفظ بنسخة قديمة من الملف قبل الاستبدال"""
    if not os.path.exists(path): return
    os.makedirs("BACKUPS/versions", exist_ok=True)
    ts  = datetime.now().strftime('%Y%m%d_%H%M%S')
    dst = f"BACKUPS/versions/{fname}_{ts}"
    try:
        shutil.copy2(path, dst)
        versions = db["file_versions"].setdefault(fname, [])
        versions.append({"path":dst,"time":ts})
        if len(versions) > 5: # احتفظ بآخر 5 نسخ بس
            old = versions.pop(0)
            try: os.remove(old["path"])
            except: pass
        save()
    except: pass

# ══════════════════════════════════════════════════════════════
#  Blacklist
# ══════════════════════════════════════════════════════════════
def is_blacklisted(uid:str) -> bool:
    return uid in db.get("blacklist",[])

def add_to_blacklist(uid:str):
    bl = db.setdefault("blacklist",[])
    if uid not in bl: bl.append(uid); save()

def remove_from_blacklist(uid:str):
    bl = db.get("blacklist",[])
    if uid in bl: bl.remove(uid); save()
    while True:
        time.sleep(60)
        dead = []
        for name, info in list(running_procs.items()):
            try:
                p = psutil.Process(info["pid"])
                # لو العملية أكلت أكتر من 90% RAM → تحذير
                if p.memory_percent() > 90:
                    bot.send_message(ADMIN_ID,
                        f"⚠️ *تحذير RAM!*\n`{name}` بيستخدم `{p.memory_percent():.1f}%` من الذاكرة!",
                        parse_mode="Markdown")
            except psutil.NoSuchProcess:
                dead.append(name)
        for name in dead:
            if name in running_procs:
                running_procs.pop(name)
                if name in db["files"]:
                    db["files"][name]["active"] = False; save()

threading.Thread(target=health_monitor, daemon=True).start()

# ══════════════════════════════════════════════════════════════
#  لوحات المفاتيح
# ══════════════════════════════════════════════════════════════
def kb_owner():
    m = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    m.add(
        "🖥 الاستضافة",     "⚙️ الحاويات",      "🔍 مراقبة العمليات",
        "📡 موارد السيرفر", "📋 السجلات",        "📊 الإحصائيات",
        "👥 المستخدمون",    "🔐 لوحة الأدمن",    "🧹 تطهير",
        "🖥️ Shell",         "📁 الملفات",        "⏰ المجدولة",
        "🚨 الحجر الصحي",   "💀 إيقاف الكل",     "🔄 تحديث البوت",
        "💾 باك أب",        "📦 تثبيت مكاتب",    "🔎 فحص ملف",
        "📢 بث رسالة",      "🌐 فحص IP",         "📝 ملاحظات",
        "⚡ تسريع",         "🔒 قفل البوت",      "🗑 مسح السجلات",
        "🕐 وقت التشغيل",   "🔑 توليد كلمة سر",  "📌 تثبيت رسالة",
        "🌡 درجة CPU",      "📋 نسخ السجل",      "🔃 إعادة تشغيل الكل",
        "⚙️ الإعدادات",     "💎 إدارة النقطة",   "📈 تقرير فوري",
        "🎫 التذاكر",        "🚫 القائمة السوداء",  "📜 إصدارات الملفات",
        "🏆 المتصدرون",      "🔎 بحث مستخدم",       "📣 إشعار عام",
        "🛡 لوحة الأمان",    "📡 المشبوهون",        "🔐 إعادة تعيين حماية",
    )
    return m

def kb_admin():
    m = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    m.add(
        "🖥 الاستضافة",     "⚙️ الحاويات",      "🔍 مراقبة العمليات",
        "📡 موارد السيرفر", "📋 السجلات",        "📊 الإحصائيات",
        "👥 المستخدمون",    "📁 الملفات",        "⏰ المجدولة",
        "💀 إيقاف الكل",    "💾 باك أب",         "📦 تثبيت مكاتب",
        "📢 بث رسالة",      "🔎 فحص ملف",        "🔃 إعادة تشغيل الكل",
        "🕐 وقت التشغيل",   "🌡 درجة CPU",       "🗑 مسح السجلات",
    )
    return m

def kb_vip():
    m = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    m.add(
        "📂 ملفاتي",        "📡 السيرفر",
        "🔎 فحص ملف",       "💎 نقاطي",
        "▶️ تشغيل ملف",     "⏹ إيقاف ملف",
        "📋 لوج ملفاتي",    "🔗 رابط الدعوة",
        "📊 إحصائياتي",     "🎫 تذكرة دعم",
        "🔑 توليد كلمة سر", "🕐 وقت التشغيل",
        "⭐ مميزات VIP",     "ℹ️ مساعدة",
    )
    return m

def kb_user():
    m = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    m.add(
        "🔗 احالة صديق",    "💎 نقاطي",
        "📂 ملفاتي",        "📊 إحصائياتي",
        "🔎 فحص ملف",       "▶️ تشغيل ملف",
        "⏹ إيقاف ملف",      "📋 لوج ملفاتي",
        "🎫 تذكرة دعم",     "🔑 توليد كلمة سر",
        "ℹ️ مساعدة",
    )
    return m

def get_kb(uid:str):
    r = get_role(uid)
    if r == ROLE_OWNER: return kb_owner()
    if r == ROLE_ADMIN: return kb_admin()
    if r == ROLE_VIP:   return kb_vip()
    return kb_user()

def kb_file(fname):
    m = types.InlineKeyboardMarkup(row_width=3)
    active  = db["files"].get(fname,{}).get("active",False)
    ar      = db["files"].get(fname,{}).get("auto_restart",False)
    pinned  = db["files"].get(fname,{}).get("pinned",False)
    m.add(
        types.InlineKeyboardButton("⏹ إيقاف" if active else "▶️ تشغيل", callback_data=f"tog_{fname}"),
        types.InlineKeyboardButton("🔄 إعادة",   callback_data=f"rst_{fname}"),
        types.InlineKeyboardButton("🗑 حذف",     callback_data=f"del_{fname}"),
    )
    m.add(
        types.InlineKeyboardButton("📋 لوج",     callback_data=f"log_{fname}"),
        types.InlineKeyboardButton("📥 تحميل",   callback_data=f"dwn_{fname}"),
        types.InlineKeyboardButton("🔁 Auto" if not ar else "⏹ Auto", callback_data=f"ar_{fname}"),
    )
    m.add(
        types.InlineKeyboardButton("🌍 ENV",     callback_data=f"env_{fname}"),
        types.InlineKeyboardButton("📊 موارد",   callback_data=f"res_{fname}"),
        types.InlineKeyboardButton("📦 مكاتب",   callback_data=f"pip_{fname}"),
    )
    m.add(
        types.InlineKeyboardButton("⏰ جدولة",   callback_data=f"sched_{fname}"),
        types.InlineKeyboardButton("📌 تثبيت" if not pinned else "📌 إلغاء", callback_data=f"pin_{fname}"),
        types.InlineKeyboardButton("🔎 فحص",     callback_data=f"chk_{fname}"),
    )
    m.add(
        types.InlineKeyboardButton("✏️ إعادة تسمية", callback_data=f"ren_{fname}"),
        types.InlineKeyboardButton("📋 نسخ مسار",    callback_data=f"pth_{fname}"),
    )
    return m

def kb_admin_panel():
    """لوحة إدارة المستخدمين الكبيرة"""
    m = types.InlineKeyboardMarkup(row_width=2)
    m.add(
        types.InlineKeyboardButton("👑 تعيين أدمن",       callback_data="ap_set_admin"),
        types.InlineKeyboardButton("⭐ تعيين VIP",         callback_data="ap_set_vip"),
        types.InlineKeyboardButton("👤 تخفيض لـ User",    callback_data="ap_set_user"),
        types.InlineKeyboardButton("🚫 حظر",              callback_data="ap_ban"),
        types.InlineKeyboardButton("✅ رفع حظر",           callback_data="ap_unban"),
        types.InlineKeyboardButton("📜 كل المستخدمين",    callback_data="ap_list_all"),
        types.InlineKeyboardButton("👑 الأدمنز",           callback_data="ap_list_admins"),
        types.InlineKeyboardButton("⭐ VIP قائمة",         callback_data="ap_list_vip"),
        types.InlineKeyboardButton("🚫 المحظورون",         callback_data="ap_list_banned"),
        types.InlineKeyboardButton("📊 إحصائيات Users",    callback_data="ap_stats"),
        types.InlineKeyboardButton("📢 رسالة جماعية",      callback_data="ap_broadcast"),
        types.InlineKeyboardButton("🗑 حذف مستخدم",        callback_data="ap_delete_user"),
    )
    return m

def kb_user_actions(target_uid:str, role:str):
    m = types.InlineKeyboardMarkup(row_width=2)
    if role != ROLE_ADMIN:
        m.add(types.InlineKeyboardButton("👑 أدمن",  callback_data=f"usr_admin_{target_uid}"))
    if role != ROLE_VIP:
        m.add(types.InlineKeyboardButton("⭐ VIP",   callback_data=f"usr_vip_{target_uid}"))
    if role != ROLE_USER:
        m.add(types.InlineKeyboardButton("👤 User",  callback_data=f"usr_user_{target_uid}"))
    m.add(
        types.InlineKeyboardButton("🚫 حظر",         callback_data=f"usr_ban_{target_uid}"),
        types.InlineKeyboardButton("✅ رفع حظر",      callback_data=f"usr_unban_{target_uid}"),
    )
    return m

# ══════════════════════════════════════════════════════════════
#  حالات المستخدم
# ══════════════════════════════════════════════════════════════
user_states = {}
shell_mode  = set()

# ══════════════════════════════════════════════════════════════
#  /start
# ══════════════════════════════════════════════════════════════
@bot.message_handler(commands=['start'])
def cmd_start(m):
    uid  = reg_user(m)
    name = m.from_user.first_name or "مستخدم"
    role = get_role(uid)
    role_emoji = {"owner":"🔱","admin":"👑","vip":"⭐","user":"👤"}.get(role,"👤")

    # معالجة كود الدعوة
    parts = m.text.split()
    if len(parts) > 1 and parts[1].startswith("ref_"):
        ref_code = parts[1][4:]
        referrer_uid = db["referral_codes"].get(ref_code)
        if referrer_uid and referrer_uid != uid and not db["users"][uid].get("referred_by"):
            db["users"][uid]["referred_by"] = referrer_uid
            db["users"][referrer_uid]["total_referred"] = db["users"][referrer_uid].get("total_referred",0)+1
            save()
            add_credits(referrer_uid, db["settings"].get("credits_for_referral", 2), "إحالة صديق 👥")
            add_credits(uid, 0, "")

    points   = db["users"][uid].get("credits", 0)
    vip_min  = db["settings"].get("vip_min_credits", 500)
    bar_len  = min(10, int(points / vip_min * 10)) if role == ROLE_USER else 10
    bar      = "█" * bar_len + "░" * (10 - bar_len)
    uid_files= [f for f,v in db["files"].items() if v.get("owner")==uid]
    active_f = sum(1 for f in uid_files if db["files"][f].get("active"))

    badges = []
    if role == ROLE_VIP:   badges.append("⭐ VIP")
    if role == ROLE_ADMIN: badges.append("👑 أدمن")
    if role == ROLE_OWNER: badges.append("🔱 مالك")
    if db["users"][uid].get("total_referred",0) >= 5: badges.append("🤝 سفير")
    if db["users"][uid].get("uploads",0) >= 10: badges.append("📤 محترف")
    badge_str = " ".join(badges) if badges else ""

    welcome = (
        f"{role_emoji} *أهلاً {name}!* {badge_str}\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"📊 الصلاحية: `{role.upper()}`\n"
        f"💎 النقاط: `{points}`"
    )
    if role == ROLE_USER:
        welcome += f"\n`{bar}` `{min(100,int(points/vip_min*100))}%` للـ VIP"
    welcome += (
        f"\n📂 ملفاتك: `{len(uid_files)}` | ⚡ شغّالة: `{active_f}`\n"
        f"👥 دعوت: `{db['users'][uid].get('total_referred',0)}` شخص\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"💡 `/ref` دعوة | `/credits` نقاطي | `/help` مساعدة"
    )
    bot.send_message(m.chat.id, welcome, parse_mode="Markdown", reply_markup=get_kb(uid))

@bot.message_handler(commands=['myfiles'])
def cmd_myfiles(m):
    _show_files(m)

@bot.message_handler(commands=['id'])
def cmd_id(m):
    bot.reply_to(m, f"🆔 ID بتاعك: `{m.from_user.id}`", parse_mode="Markdown")

@bot.message_handler(commands=['stats'])
def cmd_stats(m):
    _server_stats(m)

@bot.message_handler(commands=['stop'])
def cmd_stop(m):
    uid = reg_user(m)
    if not is_staff(uid): return
    parts = m.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(m, "الاستخدام: `/stop اسم_الملف`", parse_mode="Markdown"); return
    fname = parts[1].strip()
    if fname in db["files"]:
        stop_file(fname)
        bot.reply_to(m, f"⏹ تم إيقاف `{fname}`", parse_mode="Markdown")
    else:
        bot.reply_to(m, f"❌ الملف غير موجود")

@bot.message_handler(commands=['run'])
def cmd_run(m):
    uid = reg_user(m)
    if not is_staff(uid): return
    parts = m.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(m, "الاستخدام: `/run اسم_الملف`", parse_mode="Markdown"); return
    fname = parts[1].strip()
    if fname in db["files"]:
        launch(db["files"][fname]["path"], fname)
        bot.reply_to(m, f"🚀 تم تشغيل `{fname}`", parse_mode="Markdown")
    else:
        bot.reply_to(m, f"❌ الملف غير موجود")

@bot.message_handler(commands=['health'])
def cmd_health(m):
    uid = reg_user(m)
    if not is_staff(uid): return
    if not HEALTH_LOG:
        bot.reply_to(m, "⏳ لسه ما في بيانات، انتظر دقيقة."); return
    last = HEALTH_LOG[-1]
    avg_cpu = sum(h["cpu"] for h in HEALTH_LOG) / len(HEALTH_LOG)
    avg_mem = sum(h["mem"] for h in HEALTH_LOG) / len(HEALTH_LOG)
    bot.reply_to(m,
        f"🏥 *تقرير الصحة*\n━━━━━━━━━━━━━━━━━\n"
        f"📊 آخر قراءة ({last['time']}):\n"
        f"  CPU: `{last['cpu']}%` | RAM: `{last['mem']}%` | Disk: `{last['disk']}%`\n\n"
        f"📈 المتوسط ({len(HEALTH_LOG)} قراءة):\n"
        f"  CPU: `{avg_cpu:.1f}%` | RAM: `{avg_mem:.1f}%`",
        parse_mode="Markdown")

@bot.message_handler(commands=['backup'])
def cmd_backup(m):
    uid = reg_user(m)
    if not is_staff(uid): return
    if os.path.exists(DB_FILE):
        with open(DB_FILE,'rb') as f:
            bot.send_document(m.chat.id, f, caption=f"💾 باك أب يدوي — {datetime.now().strftime('%Y-%m-%d %H:%M')}")

@bot.message_handler(commands=['ref'])
def cmd_ref(m):
    uid  = reg_user(m)
    code = db["users"][uid].get("referral_code","")
    bot_info = bot.get_me()
    link = f"https://t.me/{bot_info.username}?start=ref_{code}"
    total = db["users"][uid].get("total_referred",0)
    bot.reply_to(m,
        f"🔗 *رابط الدعوة بتاعك:*\n`{link}`\n\n"
        f"👥 عدد من دعوتهم: `{total}`\n"
        f"💎 نقطة لكل دعوة: `{db['settings'].get('credits_for_referral',50)}`",
        parse_mode="Markdown")

@bot.message_handler(commands=['credits'])
def cmd_credits(m):
    uid     = reg_user(m)
    points  = db["users"][uid].get("credits", 0)
    vip_min = db["settings"].get("vip_min_credits", 500)
    role    = get_role(uid)
    pct     = min(100, int(points / vip_min * 100)) if vip_min > 0 else 100
    bar_len = min(20, int(pct / 5))
    bar     = "█" * bar_len + "░" * (20 - bar_len)
    uploads = db["users"][uid].get("uploads", 0)
    referred= db["users"][uid].get("total_referred", 0)
    if   role == ROLE_OWNER: status = "🔱 أنت المالك!"
    elif role == ROLE_ADMIN: status = "👑 أنت أدمن!"
    elif role == ROLE_VIP:   status = "⭐ أنت VIP بالفعل!"
    else: status = f"🎯 باقي {max(0, vip_min-points)} نقطة للـ VIP"
    bot.reply_to(m,
        f"💎 *نقاطك*\n━━━━━━━━━━━━━━━━━\n"
        f"`{bar}` `{pct}%`\n"
        f"النقاط: `{points}` / `{vip_min}`\n"
        f"{status}\n\n"
        f"📊 *إحصائياتك:*\n"
        f"📤 رفعات: `{uploads}` | 👥 دعوت: `{referred}`\n\n"
        f"🎁 *طرق كسب النقاط:*\n"
        f"📤 رفع ملف: `+{db['settings'].get('credits_per_upload',10)}`\n"
        f"👥 دعوة صديق: `+{db['settings'].get('credits_for_referral',50)}`",
        parse_mode="Markdown")

@bot.message_handler(commands=['help'])
def cmd_help(m):
    uid = reg_user(m)
    role = get_role(uid)
    cmds = (
        "📖 *الأوامر المتاحة:*\n━━━━━━━━━━━━━━━━━\n"
        "/start — الرئيسية\n"
        "/id — ID بتاعك\n"
        "/myfiles — ملفاتك\n"
        "/stats — موارد السيرفر\n"
        "/help — المساعدة\n"
    )
    if is_staff(uid):
        cmds += (
            "\n*للأدمن:*\n"
            "/run اسم — تشغيل ملف\n"
            "/stop اسم — إيقاف ملف\n"
            "/health — تقرير الصحة\n"
            "/backup — باك أب فوري\n"
        )
    cmds += f"\n🆔 ID: `{m.from_user.id}`"
    bot.reply_to(m, cmds, parse_mode="Markdown")

# ══════════════════════════════════════════════════════════════
#  رفع الملفات
# ══════════════════════════════════════════════════════════════
@bot.message_handler(content_types=['document'])
def handle_upload(m):
    uid  = reg_user(m)
    role = get_role(uid)

    # لو البوت مقفول والمستخدم مش أدمن
    if db.get("locked") and not is_staff(uid):
        bot.reply_to(m, "🔒 البوت مقفول حالياً. جرّب بعدين."); return

    def deploy():
        try:
            fname = m.document.file_name
            ext   = os.path.splitext(fname)[1].lower()
            raw   = bot.download_file(bot.get_file(m.document.file_id).file_path)

            # ── التحقق من الملف ────────────────────────
            ok, reason = validate_file(raw, fname, uid)
            if not ok:
                bot.reply_to(m, f"❌ {reason}"); return

            # ── وضع فحص فقط بدون رفع ─────────────────
            state = user_states.get(uid, {})
            if state.get("action") == "scan_only" and ext == ".py":
                user_states.pop(uid, None)
                tmp = f"/tmp/scan_{fname}"
                with open(tmp,'wb') as f: f.write(raw)
                scan   = scan_file(tmp)
                config = check_bot_config(tmp)
                os.remove(tmp)
                tok_icon   = "✅" if config['has_token'] else "❌"
                adm_icon   = "✅" if config['has_admin'] else "❌"
                tok_line   = f"{tok_icon} التوكن: {config['token_val'] or 'غير موجود'} ({config['token_type'] or '-'})"
                admin_line = f"{adm_icon} الأدمن ID: {config['admin_val'] or 'غير موجود'} ({config['admin_type'] or '-'})"
                sugg_lines = ("\n💡 " + " | ".join(config["suggestions"])) if config["suggestions"] else ""
                libs_txt   = f"\n📦 مكاتب: {', '.join(scan['to_install'])}" if scan["to_install"] else "\n📦 لا تحتاج مكاتب"
                danger_txt = ("\n🔴 " + "\n🔴 ".join(scan["danger"])) if scan["danger"] else ""
                bot.reply_to(m,
                    f"🔎 نتيجة الفحص: {fname}\n━━━━━━━━━━━━━━━━━\n"
                    f"🤖 إعدادات البوت:\n{tok_line}\n{admin_line}{sugg_lines}\n\n"
                    f"🔍 الأمان: {'✅ آمن' if scan['safe'] else '⚠️ مشاكل!'}{libs_txt}{danger_txt}")
                return

            # ── تحديث البوت ────────────────────────────
            if state.get("action") == "update_bot" and fname == "bot.py":
                user_states.pop(uid, None)
                new_path = "bot.py"
                with open(new_path,'wb') as f: f.write(raw)
                bot.reply_to(m,
                    "🔄 *تم استلام التحديث!*\n♻️ جارٍ إعادة التشغيل...",
                    parse_mode="Markdown")
                time.sleep(1)
                os.execv(sys.executable, [sys.executable, "bot.py"])
                return

            # ── requirements.txt ──────────────────────
            if fname == "requirements.txt":
                path = f"ELITE_HOST/{fname}"
                with open(path,'wb') as f: f.write(raw)
                bot.reply_to(m, "📦 *تم استلام requirements.txt*\nجارٍ التثبيت...", parse_mode="Markdown")
                pending = user_states.get(uid,{})
                pfile   = pending.get("pending_file") if pending.get("action") == "waiting_run" else None
                install_req_file(path, m.chat.id)
                if pfile and pfile in db["files"]:
                    user_states.pop(uid, None)
                    launch(db["files"][pfile]["path"], pfile)
                    bot.send_message(m.chat.id, f"🚀 تم تشغيل `{pfile}`!", parse_mode="Markdown")
                return

            # ── حفظ الملف ────────────────────────────
            # التحقق من النقاط (للمستخدمين العاديين فقط)
            if role == ROLE_USER:
                cost    = db["settings"].get("upload_cost", 6)
                points  = db["users"][uid].get("credits", 0)
                if points < cost:
                    needed = cost - points
                    bot.reply_to(m,
                        f"❌ نقاطك غير كافية!\n\n"
                        f"💎 نقاطك: {points}\n"
                        f"💸 تكلفة الرفع: {cost} نقاط\n"
                        f"📉 باقي: {needed} نقطة\n\n"
                        f"📨 ادعو أصدقاء لكسب النقاط!\n"
                        f"كل إحالة = {db['settings'].get('credits_for_referral',2)} نقاط\n\n"
                        f"رابطك: /ref")
                    return
                # خصم النقاط
                db["users"][uid]["credits"] = points - cost
                save()

            path = f"ELITE_HOST/{fname}"
            if os.path.exists(path):
                save_file_version(fname, path)
            with open(path,'wb') as f: f.write(raw)
            db["files"][fname] = {
                "owner": uid, "active": False, "path": path,
                "size": len(raw), "auto_restart": False,
                "uploaded_at": datetime.now().strftime('%Y-%m-%d %H:%M'), "ext": ext
            }
            db["stats"]["uploads"] = db["stats"].get("uploads",0)+1
            db["users"][uid]["uploads"] = db["users"].get(uid,{}).get("uploads",0)+1
            save()
            check_vip_upgrade(uid)

            # ── فحص الأمان + اكتشاف المكاتب ──────────
            if ext == ".py":
                scan   = scan_file(path)
                config = check_bot_config(path)

                # رسالة فحص التوكن والأدمن
                tok_icon   = "✅" if config['has_token'] else "❌"
                adm_icon   = "✅" if config['has_admin'] else "❌"
                tok_line   = f"{tok_icon} التوكن: {config['token_val'] or 'غير موجود'} ({config['token_type'] or '-'})"
                admin_line = f"{adm_icon} الأدمن ID: {config['admin_val'] or 'غير موجود'} ({config['admin_type'] or '-'})"
                sugg_lines = ("\n💡 " + " | ".join(config["suggestions"])) if config["suggestions"] else ""
                warn_lines = ("\n" + "\n".join(config["warnings"])) if config["warnings"] else ""

                # بناء رسالة الفحص
                scan_txt  = "✅ آمن" if scan["safe"] else "⚠️ فيه مشاكل!"
                libs_txt  = f"\n📦 مكاتب: {', '.join(scan['to_install'])}" if scan["to_install"] else "\n📦 لا تحتاج مكاتب إضافية"
                danger_txt = ("\n🔴 " + "\n🔴 ".join(scan["danger"])) if scan["danger"] else ""

                bot.reply_to(m,
                    f"✅ تم الرفع: {fname}\n📦 {len(raw)//1024} KB\n\n"
                    f"🤖 فحص البوت:\n{tok_line}\n{admin_line}"
                    f"{sugg_lines}{warn_lines}\n\n"
                    f"🔍 الأمان: {scan_txt}{libs_txt}{danger_txt}",
                    reply_markup=kb_file(fname) if is_staff(uid) else None
                )

                # لو فيه خطر → حجر صحي + إشعار أدمن
                if scan["danger"]:
                    db["stats"]["blocked"] = db["stats"].get("blocked",0)+1
                    db["quarantine"].append({
                        "fname": fname, "path": path, "uid": uid,
                        "dangers": scan["danger"],
                        "time": datetime.now().strftime('%Y-%m-%d %H:%M')
                    }); save()

                    markup = types.InlineKeyboardMarkup(row_width=2)
                    markup.add(
                        types.InlineKeyboardButton("✅ موافقة وتشغيل", callback_data=f"qapprove_{fname}"),
                        types.InlineKeyboardButton("🗑 حذف",           callback_data=f"qdelete_{fname}"),
                    )
                    uname = db["users"].get(uid,{}).get("name","؟")
                    bot.send_message(ADMIN_ID,
                        f"🚨 *تحذير أمني!*\n━━━━━━━━━━━━━━━━━━━\n"
                        f"📄 `{fname}`\n👤 {uname} (`{uid}`)\n"
                        f"🔴 " + "\n🔴 ".join(scan["danger"]) +
                        "\n\n⚠️ محجوز — وافق أو احذف.",
                        parse_mode="Markdown", reply_markup=markup
                    )
                    if not is_staff(uid):
                        bot.send_message(m.chat.id,
                            "🚨 *الملف فيه كود خطير!*\nتم إرساله للأدمن للمراجعة.",
                            parse_mode="Markdown")
                        return

                # ── تثبيت المكاتب وتشغيل لكل المستخدمين ──
                def install_and_run(scan=scan, path=path, fname=fname, chat_id=m.chat.id):
                    if scan["to_install"]:
                        bot.send_message(chat_id,
                            f"🔍 *مكاتب مكتشفة تلقائياً:*\n`{' '.join(scan['to_install'])}`\n📦 جارٍ التثبيت...",
                            parse_mode="Markdown")
                        ok = install_pkgs(scan["to_install"], None)
                        if ok:
                            bot.send_message(chat_id, "✅ تم تثبيت المكاتب!", parse_mode="Markdown")
                        else:
                            bot.send_message(chat_id, "⚠️ بعض المكاتب فشلت، جارٍ التشغيل على أي حال...", parse_mode="Markdown")
                    launch(path, fname)
                    bot.send_message(chat_id, f"🚀 *تم تشغيل* `{fname}`!", parse_mode="Markdown")
                executor.submit(install_and_run)

            else:
                bot.reply_to(m,
                    f"✅ *تم الرفع:* `{fname}`\n📦 `{len(raw)//1024} KB`",
                    parse_mode="Markdown",
                    reply_markup=kb_file(fname) if is_staff(uid) else None
                )
                if ext in [".js", ".sh"]:
                    launch(path, fname)
                    bot.send_message(m.chat.id, f"🚀 *تم تشغيل* `{fname}`!", parse_mode="Markdown")

            # إشعار الأدمن لو رفعه مستخدم عادي
            if not is_staff(uid):
                markup = types.InlineKeyboardMarkup(row_width=2)
                markup.add(
                    types.InlineKeyboardButton("▶️ تشغيل", callback_data=f"tog_{fname}"),
                    types.InlineKeyboardButton("🗑 حذف",   callback_data=f"del_{fname}"),
                )
                name = db["users"].get(uid,{}).get("name","؟")
                bot.send_message(ADMIN_ID,
                    f"📤 *ملف جديد*\n👤 {name} (`{uid}`)\n📄 `{fname}`\n📦 `{len(raw)//1024} KB`",
                    parse_mode="Markdown", reply_markup=markup)

        except Exception as e:
            log.error(f"Upload: {e}")
            bot.reply_to(m, f"❌ خطأ: `{e}`", parse_mode="Markdown")

    executor.submit(deploy)

# ══════════════════════════════════════════════════════════════
#  Callbacks
# ══════════════════════════════════════════════════════════════
@bot.callback_query_handler(func=lambda c: True)
def callbacks(call):
    uid   = str(call.from_user.id)
    role  = get_role(uid)
    data  = call.data

    # استخراج act و tgt بشكل صحيح
    # الأوامر المعروفة متعددة الكلمات
    KNOWN_ACTS = [
        "verget","treply","tclose","qapprove","qdelete","ustop","utog",
        "usr","tog","run","stop","log","dl","env","sched","scan","upd",
        "cfg","ver","bl","notif","ap","pth","ren","pgkill","autorst"
    ]
    act = ""
    tgt = ""
    for known in sorted(KNOWN_ACTS, key=len, reverse=True):
        if data.startswith(known + "_"):
            act = known
            tgt = data[len(known)+1:]
            break
        elif data == known:
            act = known
            tgt = ""
            break
    if not act:
        parts = data.split("_",1)
        act   = parts[0]
        tgt   = parts[1] if len(parts)>1 else ""

    def only_staff():
        if not is_staff(uid):
            bot.answer_callback_query(call.id,"❌ لا صلاحية"); return True
        return False

    def only_owner():
        if role != ROLE_OWNER:
            bot.answer_callback_query(call.id,"❌ للمالك فقط"); return True
        return False

    # ══ ملفات ══════════════════════════════
    if act == "tog":
        if only_staff(): return
        if tgt in db["files"]:
            if db["files"][tgt].get("active"):
                stop_file(tgt); bot.answer_callback_query(call.id,"⏹ متوقف")
            else:
                launch(db["files"][tgt]["path"], tgt)
                bot.answer_callback_query(call.id,"▶️ يعمل")
            try: bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=kb_file(tgt))
            except: pass

    elif act == "rst":
        if only_staff(): return
        if tgt in db["files"]:
            stop_file(tgt); time.sleep(0.3)
            launch(db["files"][tgt]["path"], tgt)
            bot.answer_callback_query(call.id,"🔄 تمت الإعادة")

    elif act == "del":
        if only_staff(): return
        if tgt in db["files"]:
            path = db["files"][tgt].get("path","")
            stop_file(tgt)
            try:
                if os.path.exists(path): os.remove(path)
            except: pass
            del db["files"][tgt]
            db.get("envs",{}).pop(tgt,None); save()
            bot.answer_callback_query(call.id,"🗑 حُذف")
            try: bot.edit_message_text(f"🗑 حُذف `{tgt}`", call.message.chat.id, call.message.message_id, parse_mode="Markdown")
            except: pass

    elif act == "log":
        bot.answer_callback_query(call.id)
        lp = f"LOGS/{tgt}.log"
        if os.path.exists(lp):
            with open(lp,'r',encoding='utf-8',errors='replace') as f:
                lines = f.readlines()[-30:]
            out = "".join(lines).strip() or "(فارغ)"
            if len(out)>3500: out="..."+out[-3500:]
            bot.send_message(call.message.chat.id, f"📋 *{tgt}*\n```\n{out}\n```", parse_mode="Markdown")
        else:
            bot.send_message(call.message.chat.id,"📋 لا يوجد لوج.")

    elif act == "dwn":
        bot.answer_callback_query(call.id)
        if tgt in db["files"]:
            p = db["files"][tgt].get("path","")
            if os.path.exists(p):
                with open(p,'rb') as f:
                    bot.send_document(call.message.chat.id, f, caption=f"📥 `{tgt}`", parse_mode="Markdown")

    elif act == "ar":
        if only_staff(): return
        if tgt in db["files"]:
            cur = db["files"][tgt].get("auto_restart",False)
            db["files"][tgt]["auto_restart"] = not cur; save()
            if not cur: enable_ar(tgt, db["files"][tgt]["path"])
            bot.answer_callback_query(call.id, "🔁 مفعّل" if not cur else "⏹ متوقف")
            try: bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=kb_file(tgt))
            except: pass

    elif act == "res":
        bot.answer_callback_query(call.id)
        info = running_procs.get(tgt)
        if not info:
            bot.send_message(call.message.chat.id, f"❌ `{tgt}` غير مشغّل.", parse_mode="Markdown"); return
        try:
            p = psutil.Process(info["pid"])
            up = int(time.time()-info["started"])
            h,r=divmod(up,3600); mn,s=divmod(r,60)
            bot.send_message(call.message.chat.id,
                f"📊 *{tgt}*\nPID:`{info['pid']}` CPU:`{p.cpu_percent(0.5)}%` RAM:`{p.memory_info().rss//1024//1024}MB` ⏱`{h:02d}:{mn:02d}:{s:02d}`",
                parse_mode="Markdown")
        except psutil.NoSuchProcess:
            bot.send_message(call.message.chat.id,"⚠️ انتهت.")

    elif act == "pip":
        if only_staff(): return
        bot.answer_callback_query(call.id)
        user_states[uid] = {"action":"pip_install","file":tgt}
        bot.send_message(call.message.chat.id,
            f"📦 اكتب المكاتب:\nمثال: `requests flask aiohttp`", parse_mode="Markdown")

    elif act == "env":
        if only_staff(): return
        bot.answer_callback_query(call.id)
        envs = db.get("envs",{}).get(tgt,{})
        text = "\n".join([f"`{k}`=`{v}`" for k,v in envs.items()]) or "لا توجد."
        mk = types.InlineKeyboardMarkup(row_width=2)
        mk.add(
            types.InlineKeyboardButton("➕ إضافة",    callback_data=f"envadd_{tgt}"),
            types.InlineKeyboardButton("🗑 مسح",      callback_data=f"envclear_{tgt}")
        )
        bot.send_message(call.message.chat.id, f"🌍 *ENV: {tgt}*\n{text}", parse_mode="Markdown", reply_markup=mk)

    elif act == "envadd":
        if only_staff(): return
        bot.answer_callback_query(call.id)
        user_states[uid] = {"action":"add_env","file":tgt}
        bot.send_message(call.message.chat.id, "🌍 أرسل: `KEY=VALUE`", parse_mode="Markdown")

    elif act == "envclear":
        if only_staff(): return
        db.setdefault("envs",{})[tgt]={}; save()
        bot.answer_callback_query(call.id,"🗑 تم")

    elif act == "sched":
        if only_staff(): return
        bot.answer_callback_query(call.id)
        user_states[uid] = {"action":"schedule","file":tgt}
        bot.send_message(call.message.chat.id, f"⏰ أرسل الوقت:\n`YYYY-MM-DD HH:MM`", parse_mode="Markdown")

    elif act == "runnow":
        if only_staff(): return
        user_states.pop(uid,None)
        if tgt in db["files"]:
            launch(db["files"][tgt]["path"], tgt)
            bot.answer_callback_query(call.id,"🚀 يشتغل")

    # ══ الحجر الصحي ═══════════════════════
    elif act == "qapprove":
        if only_owner(): return
        entry = next((e for e in db["quarantine"] if e["fname"]==tgt), None)
        if entry:
            db["quarantine"].remove(entry); save()
            launch(entry["path"], tgt)
            bot.answer_callback_query(call.id,"✅ موافقة")
            try: bot.edit_message_text(f"✅ وافقت على `{tgt}` وتم تشغيله.", call.message.chat.id, call.message.message_id, parse_mode="Markdown")
            except: pass

    elif act == "qdelete":
        if only_owner(): return
        entry = next((e for e in db["quarantine"] if e["fname"]==tgt), None)
        if entry:
            db["quarantine"].remove(entry)
            if tgt in db["files"]: del db["files"][tgt]
            try:
                if os.path.exists(entry["path"]): os.remove(entry["path"])
            except: pass
            save()
            bot.answer_callback_query(call.id,"🗑 حُذف")
            try: bot.edit_message_text(f"🗑 تم حذف `{tgt}` من الحجر.", call.message.chat.id, call.message.message_id, parse_mode="Markdown")
            except: pass

    elif act == "qdelete":
        if only_owner(): return
        entry = next((e for e in db["quarantine"] if e["fname"]==tgt), None)
        if entry:
            db["quarantine"].remove(entry)
            if tgt in db["files"]: del db["files"][tgt]
            try:
                if os.path.exists(entry["path"]): os.remove(entry["path"])
            except: pass
            save()
            bot.answer_callback_query(call.id,"🗑 حُذف")
            try: bot.edit_message_text(f"🗑 تم حذف `{tgt}` من الحجر.", call.message.chat.id, call.message.message_id, parse_mode="Markdown")
            except: pass

    # ── تثبيت الملف (pin) ────────────────────
    elif act == "pin":
        if only_staff(): return
        if tgt in db["files"]:
            cur = db["files"][tgt].get("pinned", False)
            db["files"][tgt]["pinned"] = not cur; save()
            bot.answer_callback_query(call.id, "📌 تم التثبيت" if not cur else "📌 إلغاء التثبيت")
            try: bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=kb_file(tgt))
            except: pass

    # ── فحص الملف (chk) ──────────────────────
    elif act == "chk":
        if only_staff(): return
        bot.answer_callback_query(call.id)
        if tgt in db["files"]:
            path = db["files"][tgt].get("path","")
            if os.path.exists(path):
                scan   = scan_file(path)
                config = check_bot_config(path)
                tok    = f"{'✅' if config['has_token'] else '❌'} التوكن: `{config['token_val'] or 'غير موجود'}`"
                adm    = f"{'✅' if config['has_admin'] else '❌'} الأدمن: `{config['admin_val'] or 'غير موجود'}`"
                libs   = f"📦 `{', '.join(scan['to_install'])}`" if scan["to_install"] else "📦 لا تحتاج مكاتب"
                danger = ("\n🔴 " + "\n🔴 ".join(scan["danger"])) if scan["danger"] else "\n✅ آمن"
                bot.send_message(call.message.chat.id,
                    f"🔎 *فحص: {tgt}*\n━━━━━━━━━━━━━━━━━\n{tok}\n{adm}\n{libs}{danger}",
                    parse_mode="Markdown")

    # ── إعادة تسمية (ren) ────────────────────
    elif act == "ren":
        if only_staff(): return
        bot.answer_callback_query(call.id)
        user_states[uid] = {"action":"rename_file","file":tgt}
        bot.send_message(call.message.chat.id,
            f"✏️ اكتب الاسم الجديد لـ `{tgt}`:", parse_mode="Markdown")

    # ── مسار الملف (pth) ─────────────────────
    elif act == "pth":
        bot.answer_callback_query(call.id)
        if tgt in db["files"]:
            path = db["files"][tgt].get("path","")
            bot.send_message(call.message.chat.id,
                f"📋 *مسار الملف:*\n`{path}`", parse_mode="Markdown")

    # ── لوحة الأدمن (ap) ─────────────────────
    elif act == "ap":
        if only_owner(): return
        bot.answer_callback_query(call.id)
        sub = tgt

        if sub == "list_all":
            lines = []
            for u,info in list(db["users"].items())[:20]:
                e = {"owner":"🔱","admin":"👑","vip":"⭐","user":"👤","banned":"🚫"}.get(info.get("role","user"),"👤")
                lines.append(f"{e} `{u}` — {info.get('name','؟')}")
            bot.send_message(call.message.chat.id,
                f"📜 *كل المستخدمين ({len(db['users'])}):*\n" + "\n".join(lines),
                parse_mode="Markdown")

        elif sub == "list_admins":
            admins = [f"`{u}` — {info.get('name','؟')}" for u,info in db["users"].items() if info.get("role")==ROLE_ADMIN]
            admins += [f"`{ADMIN_ID}` — المالك 🔱"]
            bot.send_message(call.message.chat.id,
                f"👑 *الأدمنز ({len(admins)}):*\n" + "\n".join(admins),
                parse_mode="Markdown")

        elif sub == "list_vip":
            vips = [f"`{u}` — {info.get('name','؟')}" for u,info in db["users"].items() if info.get("role")==ROLE_VIP]
            bot.send_message(call.message.chat.id,
                (f"⭐ *VIP ({len(vips)}):*\n" + "\n".join(vips)) if vips else "لا يوجد VIP.",
                parse_mode="Markdown")

        elif sub == "list_banned":
            banned = [f"`{u}` — {info.get('name','؟')}" for u,info in db["users"].items() if info.get("role")=="banned"]
            bot.send_message(call.message.chat.id,
                (f"🚫 *محظورون ({len(banned)}):*\n" + "\n".join(banned)) if banned else "✅ لا يوجد محظورون.",
                parse_mode="Markdown")

        elif sub == "stats":
            roles = {}
            for u,info in db["users"].items():
                r = info.get("role","user")
                roles[r] = roles.get(r,0)+1
            bot.send_message(call.message.chat.id,
                f"📊 *إحصائيات المستخدمين*\n━━━━━━━━━━━━━━━━━\n"
                f"👥 الكل: `{len(db['users'])}`\n"
                f"🔱 مالك: `{roles.get('owner',1)}`\n"
                f"👑 أدمن: `{roles.get('admin',0)}`\n"
                f"⭐ VIP: `{roles.get('vip',0)}`\n"
                f"👤 عادي: `{roles.get('user',0)}`\n"
                f"🚫 محظور: `{roles.get('banned',0)}`",
                parse_mode="Markdown")

        elif sub in ["set_admin","set_vip","set_user","ban","unban","delete_user"]:
            action_map = {
                "set_admin":   "👑 تعيين أدمن",
                "set_vip":     "⭐ تعيين VIP",
                "set_user":    "👤 تخفيض لـ User",
                "ban":         "🚫 حظر مستخدم",
                "unban":       "✅ رفع حظر",
                "delete_user": "🗑 حذف مستخدم"
            }
            user_states[uid] = {"action": f"panel_{sub}"}
            bot.send_message(call.message.chat.id,
                f"*{action_map[sub]}*\nأرسل ID المستخدم:", parse_mode="Markdown")

        elif sub == "broadcast":
            user_states[uid] = {"action": "broadcast"}
            bot.send_message(call.message.chat.id,
                "📢 اكتب الرسالة الجماعية:")

    # ══ الأمان ════════════════════════════
    elif act == "sec":
        if only_owner(): return
        bot.answer_callback_query(call.id)
        if tgt == "clear_sus":
            suspicious.clear(); failed_cmds.clear()
            bot.send_message(call.message.chat.id, "✅ تم مسح قائمة المشبوهين")
        elif tgt == "ban_all_sus":
            count = 0
            for u in list(suspicious):
                add_to_blacklist(u)
                if u in db["users"]: db["users"][u]["role"]="banned"
                count += 1
            suspicious.clear(); save()
            bot.send_message(call.message.chat.id, f"🚫 تم حظر {count} مستخدم مشبوه")

    # ══ إعدادات البوت ════════════════════
    elif act == "cfg":
        if only_owner(): return
        bot.answer_callback_query(call.id)
        cfg_labels = {
            "max_files_per_user":   "حد الملفات لكل مستخدم",
            "max_file_size_kb":     "الحجم الأقصى للملف (KB)",
            "credits_per_upload":   "نقطة لكل رفع",
            "credits_for_referral": "نقطة لكل دعوة",
            "vip_min_credits":      "نقطة الترقية لـ VIP",
            "welcome_credits":      "نقطة الترحيب",
            "report_time":          "وقت التقرير اليومي (مثال: 08:00)",
        }
        if tgt == "toggle_lock":
            db["locked"] = not db.get("locked", False); save()
            state_txt = "🔒 مقفول" if db["locked"] else "🔓 مفتوح"
            bot.send_message(call.message.chat.id, f"البوت الآن: {state_txt}")
        elif tgt == "toggle_maintenance":
            db["settings"]["maintenance"] = not db["settings"].get("maintenance", False); save()
            state_txt = "🔧 صيانة مفعّلة" if db["settings"]["maintenance"] else "✅ صيانة إيقاف"
            bot.send_message(call.message.chat.id, f"{state_txt}")
        elif tgt in cfg_labels:
            user_states[uid] = {"action": f"cfg_set_{tgt}"}
            bot.send_message(call.message.chat.id,
                f"✏️ {cfg_labels[tgt]}\nالقيمة الحالية: {db['settings'].get(tgt, db.get('daily_report_time','08:00'))}\n\nابعت القيمة الجديدة:")
    # ══ إشعار عام ════════════════════════
    elif act == "notif":
        if only_owner(): return
        bot.answer_callback_query(call.id)
        role_map = {"all":None,"vip":ROLE_VIP,"user":ROLE_USER}
        user_states[uid] = {"action":"send_notif","filter":role_map.get(tgt)}
        labels = {"all":"الكل","vip":"VIP فقط","user":"عادي فقط"}
        bot.send_message(call.message.chat.id,
            f"📣 إشعار لـ {labels.get(tgt,'الكل')}\nاكتب نص الإشعار:")

    # ══ تذاكر الدعم ══════════════════════
        if not is_staff(uid): return
        bot.answer_callback_query(call.id)
        user_states[uid] = {"action":"ticket_reply","ticket_id":tgt}
        bot.send_message(call.message.chat.id, f"📩 اكتب ردك على التذكرة #{tgt}:")

    elif act == "tclose":
        if not is_staff(uid): return
        bot.answer_callback_query(call.id, "✅ تم إغلاق التذكرة")
        if tgt in db["tickets"]:
            db["tickets"][tgt]["status"] = "closed"; save()
            ticket_uid = db["tickets"][tgt]["uid"]
            try:
                bot.send_message(int(ticket_uid),
                    f"🎫 تذكرتك #{tgt} تم إغلاقها من الأدمن ✅")
            except: pass

    # ══ Blacklist ════════════════════════
    elif act == "bl":
        if only_owner(): return
        bot.answer_callback_query(call.id)
        if tgt == "add":
            user_states[uid] = {"action":"bl_add"}
            bot.send_message(call.message.chat.id, "ابعت ID المستخدم اللي عايز تحظره:")

    # ══ إصدارات الملفات ══════════════════
    elif act == "ver":
        if not is_staff(uid): return
        bot.answer_callback_query(call.id)
        versions = db.get("file_versions",{}).get(tgt,[])
        if not versions:
            bot.send_message(call.message.chat.id, "لا توجد إصدارات محفوظة."); return
        mk = types.InlineKeyboardMarkup(row_width=1)
        for v in versions[-5:]:
            mk.add(types.InlineKeyboardButton(
                f"📥 {v['time']}", callback_data=f"verget_{tgt}|{v['time']}"))
        bot.send_message(call.message.chat.id,
            f"📜 إصدارات {tgt}:", reply_markup=mk)

    elif act == "verget":
        if not is_staff(uid): return
        parts = tgt.split("|",1)
        fname = parts[0]; ts = parts[1] if len(parts)>1 else ""
        versions = db.get("file_versions",{}).get(fname,[])
        ver = next((v for v in versions if v["time"]==ts), None)
        if ver and os.path.exists(ver["path"]):
            bot.answer_callback_query(call.id, "📥 جارٍ الإرسال...")
            with open(ver["path"],'rb') as f:
                bot.send_document(call.message.chat.id, f,
                    caption=f"📜 إصدار قديم من {fname}\n🕐 {ts}")
        else:
            bot.answer_callback_query(call.id, "❌ الملف غير موجود")
    elif act == "utog":
        fname = tgt
        if fname not in db["files"] or db["files"][fname].get("owner") != uid:
            bot.answer_callback_query(call.id, "❌ مش ملفك"); return
        bot.answer_callback_query(call.id, f"▶️ جارٍ تشغيل {fname}")
        launch(db["files"][fname]["path"], fname)
        bot.send_message(call.message.chat.id, f"🚀 تم تشغيل {fname}")

    elif act == "ustop":
        fname = tgt
        if fname not in db["files"] or db["files"][fname].get("owner") != uid:
            bot.answer_callback_query(call.id, "❌ مش ملفك"); return
        bot.answer_callback_query(call.id, f"⏹ جارٍ إيقاف {fname}")
        stop_file(fname)
        bot.send_message(call.message.chat.id, f"⏹ تم إيقاف {fname}")

    # ══ إجراءات على مستخدم مباشرة ══════════
    elif act == "usr":
        if only_owner(): return
        sub_parts = tgt.split("_",1)
        sub_act   = sub_parts[0]
        target_uid = sub_parts[1] if len(sub_parts)>1 else ""
        _apply_user_action(call, uid, sub_act, target_uid)

    bot.answer_callback_query(call.id) if call.id else None

def _apply_user_action(call, admin_uid, action, target_uid):
    """تطبيق إجراء على مستخدم"""
    if target_uid not in db["users"]:
        bot.answer_callback_query(call.id,"❌ مستخدم غير موجود"); return
    role_map = {"admin": ROLE_ADMIN, "vip": ROLE_VIP, "user": ROLE_USER, "ban": "banned"}
    notify_map = {
        "admin": "👑 تمت ترقيتك لـ أدمن!",
        "vip":   "⭐ تمت ترقيتك لـ VIP!",
        "user":  "👤 تم تغيير دورك لـ User.",
        "ban":   "🚫 تم حظرك.",
        "unban": "✅ رُفع الحظر عنك."
    }
    if action == "unban":
        db["users"][target_uid]["role"] = ROLE_USER
    elif action in role_map:
        db["users"][target_uid]["role"] = role_map[action]
    save()
    try: bot.send_message(int(target_uid), notify_map.get(action,""), reply_markup=get_kb(target_uid))
    except: pass
    bot.answer_callback_query(call.id, f"✅ تم")
    try:
        bot.edit_message_text(
            f"✅ تم تطبيق `{action}` على `{target_uid}`",
            call.message.chat.id, call.message.message_id, parse_mode="Markdown")
    except: pass

# ══════════════════════════════════════════════════════════════
#  Shell
# ══════════════════════════════════════════════════════════════
def run_shell(chat_id, cmd):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        out = (r.stdout+r.stderr).strip() or "(لا يوجد output)"
        db["stats"]["commands"] = db["stats"].get("commands",0)+1; save()
        if len(out)>3500: out=out[-3500:]+"\n...(مقطوع)"
        bot.send_message(chat_id, f"```\n{out}\n```", parse_mode="Markdown")
    except subprocess.TimeoutExpired:
        bot.send_message(chat_id,"⏱ 30 ثانية انتهت")
    except Exception as e:
        bot.send_message(chat_id, f"❌ `{e}`", parse_mode="Markdown")

# ══════════════════════════════════════════════════════════════
#  المعالج الرئيسي
# ══════════════════════════════════════════════════════════════
@bot.message_handler(func=lambda m: True)
def main_handler(m):
    uid  = reg_user(m)
    role = get_role(uid)
    text = m.text or ""

    # ══ وضع الصيانة ══════════════════════
    if db["settings"].get("maintenance") and role not in [ROLE_OWNER, ROLE_ADMIN]:
        bot.reply_to(m, "🔧 البوت في وضع الصيانة حالياً. حاول لاحقاً ✅"); return

    # ══ Blacklist ══════════════════════════
    if is_blacklisted(uid):
        bot.reply_to(m, "🚫 أنت محظور من استخدام البوت."); return

    # ══ فحص الروابط المشبوهة ══════════════
    if text and contains_suspicious_url(text) and role == ROLE_USER:
        check_suspicious(uid, f"رابط مشبوه: {text[:50]}")
        bot.reply_to(m, "⚠️ الرسالة دي فيها روابط مشبوهة."); return

    # ══ Anti-Spam ════════════════════════
    if role not in [ROLE_OWNER, ROLE_ADMIN]:
        if is_spam(uid):
            bot.reply_to(m, "⏳ كثير رسايل — انتظر دقيقة")
            return

    # ══ لو البوت مقفول ════════════════════
    if db.get("locked") and role == ROLE_USER:
        bot.reply_to(m, "🔒 البوت مقفول حالياً."); return

    # ══ States ════════════════════════════
    if uid in user_states:
        state = user_states.pop(uid)
        act   = state.get("action","")

        if act == "add_env":
            if "=" in text:
                k,v = text.split("=",1)
                db.setdefault("envs",{}).setdefault(state["file"],{})[k.strip()] = v.strip(); save()
                bot.reply_to(m, f"✅ `{k.strip()}={v.strip()}`", parse_mode="Markdown")
            else:
                bot.reply_to(m,"❌ الصيغة: `KEY=VALUE`", parse_mode="Markdown")

        elif act == "pip_install":
            def do_pip():
                install_pkgs(text.strip().split(), m.chat.id)
            executor.submit(do_pip)

        elif act == "schedule":
            try:
                datetime.strptime(text.strip(),"%Y-%m-%d %H:%M")
                db.setdefault("scheduled",[]).append({"name":state["file"],"run_at":text.strip(),"done":False}); save()
                bot.reply_to(m, f"⏰ جُدوِل `{state['file']}` في `{text.strip()}`", parse_mode="Markdown")
            except:
                bot.reply_to(m,"❌ الصيغة: `YYYY-MM-DD HH:MM`", parse_mode="Markdown")

        elif act == "broadcast":
            if not is_staff(uid): return
            count = 0
            for u in list(db["users"].keys()):
                try:
                    bot.send_message(int(u), f"📢 *رسالة من الإدارة:*\n{text}", parse_mode="Markdown")
                    count += 1; time.sleep(0.05)
                except: pass
            bot.reply_to(m, f"📢 *أُرسلت لـ {count} مستخدم.*", parse_mode="Markdown")

        elif act == "check_ip":
            def do_ip():
                try:
                    import urllib.request
                    target = text.strip()
                    url = f"http://ip-api.com/json/{target}?fields=status,country,regionName,city,isp,org,as,query,lat,lon,timezone"
                    with urllib.request.urlopen(url, timeout=10) as r:
                        data = json.loads(r.read())
                    if data.get("status") == "success":
                        bot.reply_to(m,
                            f"🌐 *فحص IP: {data.get('query')}*\n━━━━━━━━━━━━━━━━━\n"
                            f"🌍 الدولة: `{data.get('country')}`\n"
                            f"🏙 المدينة: `{data.get('city')}`\n"
                            f"📡 ISP: `{data.get('isp')}`\n"
                            f"🏢 المنظمة: `{data.get('org')}`\n"
                            f"🕐 التوقيت: `{data.get('timezone')}`\n"
                            f"📍 {data.get('lat')}, {data.get('lon')}",
                            parse_mode="Markdown")
                    else:
                        bot.reply_to(m, f"❌ مش قادر يفحص `{target}`", parse_mode="Markdown")
                except Exception as e:
                    bot.reply_to(m, f"❌ خطأ: `{e}`", parse_mode="Markdown")
            executor.submit(do_ip)

        elif act == "add_note":
            if text != "/skip":
                db.setdefault("notes",[]).append(f"{text} — {datetime.now().strftime('%d/%m %H:%M')}"); save()
                bot.reply_to(m, "📝 تم حفظ الملاحظة ✅", parse_mode="Markdown")

        elif act == "pin_msg":
            if role != ROLE_OWNER: return
            count = 0
            for u in list(db["users"].keys()):
                try:
                    bot.send_message(int(u), f"📌 رسالة مثبّتة:\n\n{text}")
                    count += 1; time.sleep(0.05)
                except: pass
            bot.reply_to(m, f"📌 تم الإرسال لـ {count} مستخدم")

        elif act == "give_credits":
            if role != ROLE_OWNER: return
            parts = text.strip().split(maxsplit=2)
            if len(parts) < 2:
                bot.reply_to(m, "❌ الصيغة: `ID النقطة السبب`", parse_mode="Markdown"); return
            target_uid = parts[0]
            try:
                amount = int(parts[1])
                reason = parts[2] if len(parts)>2 else "من الأدمن 🎁"
            except:
                bot.reply_to(m, "❌ النقطة لازم يكون رقم"); return
            if target_uid not in db["users"]:
                bot.reply_to(m, "❌ المستخدم مش موجود"); return
            add_credits(target_uid, amount, reason)
            bot.reply_to(m, f"✅ تم إرسال {amount} نقطة لـ {target_uid}")

        elif act == "open_ticket":
            tid = open_ticket(uid, text)
            bot.reply_to(m,
                f"🎫 تم فتح تذكرة #{tid}\n"
                f"الأدمن هيرد عليك قريباً ✅")

        elif act.startswith("cfg_set_"):
            if role != ROLE_OWNER: return
            key = act.replace("cfg_set_","")
            try:
                if key == "report_time":
                    db["daily_report_time"] = text.strip()
                    bot.reply_to(m, f"✅ وقت التقرير: {text.strip()}")
                else:
                    val = int(text.strip())
                    db["settings"][key] = val
                    bot.reply_to(m, f"✅ تم تغيير {key} إلى {val}")
                save()
            except:
                bot.reply_to(m, "❌ قيمة غير صحيحة")

        elif act == "search_user":
            if not is_staff(uid): return
            query = text.strip().lower()
            results = []
            for u, info in db["users"].items():
                if query in u or query in info.get("name","").lower():
                    r = info.get("role","user")
                    re_e = {"owner":"🔱","admin":"👑","vip":"⭐","user":"👤","banned":"🚫"}.get(r,"👤")
                    results.append(
                        f"{re_e} {info.get('name','؟')}\n"
                        f"   🆔 `{u}` | 💎{info.get('credits',0)} | 📤{info.get('uploads',0)}\n"
                        f"   📅 {info.get('joined','؟')}"
                    )
            if not results:
                bot.reply_to(m, "❌ مفيش نتيجة.")
            else:
                bot.reply_to(m,
                    f"🔎 نتائج ({len(results)}):\n━━━━━━━━━━━━━━━━━\n" + "\n\n".join(results[:5]),
                    parse_mode="Markdown")

        elif act == "send_notif":
            if role != ROLE_OWNER: return
            role_filter = state.get("filter")
            count = notify_all(f"📣 إشعار من الأدمن:\n\n{text}", role_filter)
            bot.reply_to(m, f"✅ تم إرسال الإشعار لـ {count} مستخدم")
        elif act == "bl_add":
            if role != ROLE_OWNER: return
            target = text.strip()
            add_to_blacklist(target)
            # حظر من البوت كمان
            if target in db["users"]:
                db["users"][target]["role"] = "banned"; save()
            bot.reply_to(m, f"🚫 تم إضافة {target} للقائمة السوداء")

        elif act == "ticket_reply":
            tid = state.get("ticket_id")
            if tid and tid in db["tickets"]:
                db["tickets"][tid]["replies"].append({
                    "from": "admin", "msg": text,
                    "time": datetime.now().strftime('%H:%M')
                })
                ticket_uid = db["tickets"][tid]["uid"]
                save()
                try:
                    bot.send_message(int(ticket_uid),
                        f"📩 رد من الأدمن على تذكرتك #{tid}:\n\n{text}")
                except: pass
                bot.reply_to(m, f"✅ تم الرد على التذكرة #{tid}")

        elif act == "rename_file":
            old_name = state["file"]
            new_name = text.strip()
            if old_name in db["files"] and new_name:
                old_path = db["files"][old_name]["path"]
                new_path = f"ELITE_HOST/{new_name}"
                try:
                    os.rename(old_path, new_path)
                    db["files"][new_name] = db["files"].pop(old_name)
                    db["files"][new_name]["path"] = new_path
                    if old_name in running_procs:
                        running_procs[new_name] = running_procs.pop(old_name)
                    save()
                    bot.reply_to(m, f"✅ تم تغيير الاسم:\n`{old_name}` ← `{new_name}`", parse_mode="Markdown")
                except Exception as e:
                    bot.reply_to(m, f"❌ `{e}`", parse_mode="Markdown")

        elif act.startswith("panel_"):
            if not is_staff(uid): return
            sub = act.replace("panel_","")
            target_uid = text.strip()
            if target_uid not in db["users"]:
                bot.reply_to(m,"❌ ID غير موجود."); return
            target_role = db["users"][target_uid].get("role","user")
            mk = kb_user_actions(target_uid, target_role)
            name = db["users"][target_uid].get("name","؟")
            bot.reply_to(m,
                f"👤 *المستخدم:* {name}\n🆔 `{target_uid}`\nالدور: `{target_role}`",
                parse_mode="Markdown", reply_markup=mk)
        return

    # ══ Shell Mode ════════════════════════
    if uid in shell_mode:
        if text == "❌ خروج Shell":
            shell_mode.discard(uid)
            bot.reply_to(m,"🔙 خرجت.", reply_markup=get_kb(uid))
        elif is_staff(uid):
            run_shell(m.chat.id, text)
        return

    # ══ كل المستخدمين ════════════════════
    if text == "📂 ملفاتي" or text == "/myfiles":
        _show_files(m); return
    if text in ["ℹ️ مساعدة","ℹ️ المساعدة"]:
        _help(m); return
    if text in ["📡 السيرفر","📡 موارد السيرفر"]:
        _server_stats(m); return

    if text == "💎 نقاطي" or text == "/credits":
        credits = db["users"][uid].get("credits",0)
        vip_min = db["settings"].get("vip_min_credits",200)
        role    = get_role(uid)
        bar_len = min(20, int(credits/vip_min*20)) if vip_min > 0 else 20
        bar     = "█"*bar_len + "░"*(20-bar_len)
        bot.reply_to(m,
            f"💎 رصيدك: {credits} نقطة\n"
            f"صلاحيتك: {role.upper()}\n\n"
            f"{'🌟 أنت VIP!' if role in [ROLE_VIP,ROLE_ADMIN,ROLE_OWNER] else f'للـ VIP: {max(0,vip_min-credits)} نقطة متبقي'}\n"
            f"{bar} {min(100,int(credits/vip_min*100))}%\n\n"
            f"📤 رفع ملف: +{db['settings'].get('credits_per_upload',10)}\n"
            f"👥 دعوة صديق: +{db['settings'].get('credits_for_referral',50)}"); return

    if text in ["🔗 احالة صديق", "🔗 رابط الدعوة"] or text == "/ref":
        code = db["users"][uid].get("referral_code","")
        try:
            bot_info = bot.get_me()
            link = f"https://t.me/{bot_info.username}?start=ref_{code}"
        except:
            link = f"ref_{code}"
        points   = db["users"][uid].get("credits", 0)
        total    = db["users"][uid].get("total_referred", 0)
        cost     = db["settings"].get("upload_cost", 6)
        per_ref  = db["settings"].get("credits_for_referral", 2)
        needed   = max(0, cost - points)
        refs_needed = -(-needed // per_ref)  # ceiling division
        bot.reply_to(m,
            f"🔗 رابط إحالتك:\n{link}\n\n"
            f"━━━━━━━━━━━━━━━━━\n"
            f"💎 نقاطك الحالية: {points}\n"
            f"💸 تكلفة رفع ملف: {cost} نقاط\n"
            f"🎁 كل إحالة: +{per_ref} نقاط\n"
            f"👥 دعوت: {total} شخص\n\n"
            f"{'✅ عندك نقاط كافية للرفع!' if points >= cost else f'⚠️ باقي {needed} نقطة — ادعو {refs_needed} شخص!'}"
        ); return

    if text == "📊 إحصائياتي":
        uid_files = [f for f,v in db["files"].items() if v.get("owner")==uid]
        active    = sum(1 for f in uid_files if db["files"][f].get("active"))
        crashes   = sum(db["files"][f].get("crashes",0) for f in uid_files)
        total_kb  = sum(db["files"][f].get("size",0) for f in uid_files) // 1024
        uploads   = db["users"].get(uid,{}).get("uploads",0)
        points    = db["users"][uid].get("credits",0)
        referred  = db["users"][uid].get("total_referred",0)
        bot.reply_to(m,
            f"📊 إحصائياتك\n━━━━━━━━━━━━━━━━━\n"
            f"📂 ملفاتك: {len(uid_files)} | ✅ شغالة: {active}\n"
            f"💥 كراشات: {crashes} | 📦 الحجم: {total_kb} KB\n"
            f"📤 رفعات: {uploads} | 👥 دعوت: {referred}\n"
            f"💎 نقاط: {points}\n"
            f"🆔 ID: {uid}"); return

    if text == "⭐ مميزات VIP":
        if role not in [ROLE_VIP, ROLE_ADMIN, ROLE_OWNER]:
            points  = db["users"][uid].get("credits",0)
            vip_min = db["settings"].get("vip_min_credits",500)
            bot.reply_to(m,
                f"⭐ مميزات VIP\n━━━━━━━━━━━━━━━━━\n"
                f"🚀 تشغيل ملفات أكثر\n"
                f"📡 إحصائيات السيرفر\n"
                f"🕐 وقت التشغيل\n"
                f"📋 لوج مباشر\n"
                f"⚡ أولوية في الدعم\n\n"
                f"💎 نقاطك: {points}/{vip_min}\n"
                f"ابعت `/ref` للدعوة وكسب النقاط!"); return
        bot.reply_to(m,
            f"⭐ أنت {role.upper()} — تستمتع بكل المميزات!\n"
            f"📂 ملفات غير محدودة\n"
            f"📡 موارد السيرفر\n"
            f"🕐 وقت التشغيل\n"
            f"⚡ أولوية في الدعم\n"
            f"💎 نقاط مضاعفة"); return

    if text == "▶️ تشغيل ملف":
        uid_files = [f for f,v in db["files"].items() if v.get("owner")==uid and not v.get("active")]
        if not uid_files:
            bot.reply_to(m, "✅ كل ملفاتك شغالة أو مفيش ملفات."); return
        mk = types.InlineKeyboardMarkup(row_width=2)
        for f in uid_files[:10]:
            mk.add(types.InlineKeyboardButton(f"▶️ {f}", callback_data=f"utog_{f}"))
        bot.reply_to(m, "اختار الملف اللي عايز تشغّله:", reply_markup=mk); return

    if text == "⏹ إيقاف ملف":
        uid_files = [f for f,v in db["files"].items() if v.get("owner")==uid and v.get("active")]
        if not uid_files:
            bot.reply_to(m, "❌ مفيش ملفات شغالة."); return
        mk = types.InlineKeyboardMarkup(row_width=2)
        for f in uid_files[:10]:
            mk.add(types.InlineKeyboardButton(f"⏹ {f}", callback_data=f"ustop_{f}"))
        bot.reply_to(m, "اختار الملف اللي عايز توقفه:", reply_markup=mk); return

    if text == "📋 لوج ملفاتي":
        uid_files = [f for f,v in db["files"].items() if v.get("owner")==uid]
        if not uid_files:
            bot.reply_to(m, "📂 مفيش ملفات."); return
        mk = types.InlineKeyboardMarkup(row_width=2)
        for f in uid_files[:10]:
            mk.add(types.InlineKeyboardButton(f"📋 {f}", callback_data=f"log_{f}"))
        bot.reply_to(m, "اختار الملف اللي عايز تشوف لوجه:", reply_markup=mk); return

    # ══ Staff فقط ════════════════════════
    if not is_staff(uid): return

    if text == "🖥 الاستضافة":
        total = sum(v.get("size",0) for v in db["files"].values())//1024
        bot.reply_to(m,
            f"⚡ *الاستضافة*\n━━━━━━━━━━━━━━━━━\n"
            f"📂 ملفات: `{len(db['files'])}` | 💾 `{total} KB`\n"
            f"🔄 نشط: `{len(running_procs)}`\n"
            f"🚨 حجر: `{len(db.get('quarantine',[]))}`",
            parse_mode="Markdown")

    elif text == "⚙️ الحاويات":
        if not db["files"]:
            bot.reply_to(m,"📂 لا توجد ملفات."); return
        for fname,info in db["files"].items():
            st = "✅ يعمل" if info.get("active") else "❌ متوقف"
            ar = " 🔁" if info.get("auto_restart") else ""
            bot.send_message(m.chat.id,
                f"📄 *{fname}*{ar}\n{st} | 👤`{info.get('owner','؟')}` | 📦`{info.get('size',0)//1024}KB`",
                parse_mode="Markdown", reply_markup=kb_file(fname))

    elif text == "💀 إيقاف الكل":
        c = kill_all_procs()
        db["stats"]["kills"] = db["stats"].get("kills",0)+1; save()
        bot.reply_to(m, f"💀 *أُوقفت {c} عملية بالقوة.*", parse_mode="Markdown")

    elif text == "📡 موارد السيرفر":
        _server_stats(m)

    elif text == "📋 السجلات":
        p = "LOGS/bot.log"
        if os.path.exists(p):
            with open(p,'r',encoding='utf-8',errors='replace') as f:
                lines = f.readlines()[-25:]
            out = "".join(lines)
            if len(out)>3800: out=out[-3800:]
            bot.reply_to(m, f"```\n{out}\n```", parse_mode="Markdown")

    elif text == "📊 الإحصائيات":
        s = db["stats"]
        bot.reply_to(m,
            f"📊 *الإحصائيات*\n━━━━━━━━━━━━━━━━━\n"
            f"📤 رفعات: `{s.get('uploads',0)}`\n"
            f"💀 إيقافات: `{s.get('kills',0)}`\n"
            f"🖥️ Shell: `{s.get('commands',0)}`\n"
            f"🔁 إعادات: `{s.get('restarts',0)}`\n"
            f"🚨 محجوز: `{s.get('blocked',0)}`\n"
            f"👥 مستخدمون: `{len(db['users'])}`",
            parse_mode="Markdown")

    elif text == "👥 المستخدمون":
        lines = []
        for u,info in list(db["users"].items())[:15]:
            r = info.get("role","user")
            e = {"owner":"🔱","admin":"👑","vip":"⭐","user":"👤","banned":"🚫"}.get(r,"👤")
            lines.append(f"{e} `{u}` — {info.get('name','؟')}")
        bot.reply_to(m,
            f"👥 *المستخدمون ({len(db['users'])}):*\n" + "\n".join(lines),
            parse_mode="Markdown")

    elif text == "🔐 لوحة الأدمن":
        if role != ROLE_OWNER:
            bot.reply_to(m,"❌ للمالك فقط."); return
        bot.reply_to(m,
            "🔐 *لوحة التحكم الكاملة*\n━━━━━━━━━━━━━━━━━\nاختر عملية:",
            parse_mode="Markdown", reply_markup=kb_admin_panel())

    elif text == "🧹 تطهير":
        for n in list(running_procs.keys()): stop_file(n)
        try:
            shutil.rmtree("ELITE_HOST"); os.makedirs("ELITE_HOST",exist_ok=True)
            db["files"].clear(); save()
        except Exception as e: log.error(f"Clean: {e}")
        bot.reply_to(m,"🧹 *تم التطهير.*", parse_mode="Markdown")

    elif text == "🖥️ Shell":
        mk = types.ReplyKeyboardMarkup(resize_keyboard=True)
        mk.add("❌ خروج Shell")
        shell_mode.add(uid)
        bot.reply_to(m,"🖥️ *Shell نشط* — اكتب أي أمر Linux.", parse_mode="Markdown", reply_markup=mk)

    elif text == "📁 الملفات":
        files = os.listdir("ELITE_HOST")
        if not files:
            bot.reply_to(m,"📁 فارغ."); return
        lines = [f"📄 `{f}` — {os.path.getsize(f'ELITE_HOST/{f}')//1024} KB" for f in files]
        mk = types.InlineKeyboardMarkup()
        for f in files[:8]:
            mk.add(types.InlineKeyboardButton(f"📥 {f}", callback_data=f"dwn_{f}"))
        bot.reply_to(m,"📁 *ELITE\\_HOST:*\n"+"\n".join(lines), parse_mode="Markdown", reply_markup=mk)

    elif text == "⏰ المجدولة":
        tasks = [t for t in db.get("scheduled",[]) if not t.get("done")]
        lines = [f"📄 `{t['name']}` ← `{t['run_at']}`" for t in tasks] or ["لا توجد."]
        bot.reply_to(m,"⏰ *المجدولة:*\n"+"\n".join(lines), parse_mode="Markdown")
        if db["files"]:
            mk = types.InlineKeyboardMarkup()
            for n in list(db["files"].keys())[:8]:
                mk.add(types.InlineKeyboardButton(f"⏰ {n}", callback_data=f"sched_{n}"))
            bot.send_message(m.chat.id,"اختر ملفاً:", reply_markup=mk)

    elif text == "🔍 مراقبة العمليات":
        if not running_procs:
            bot.reply_to(m,"🔍 لا توجد عمليات."); return
        lines = []
        for n,info in running_procs.items():
            up = int(time.time()-info.get("started",time.time()))
            h,r=divmod(up,3600); mn,s=divmod(r,60)
            try:
                p=psutil.Process(info["pid"])
                lines.append(f"📄`{n}` PID:`{info['pid']}` CPU:`{p.cpu_percent(0.1)}%` RAM:`{p.memory_info().rss//1024//1024}MB` ⏱`{h:02d}:{mn:02d}:{s:02d}`")
            except: lines.append(f"📄`{n}` ⚠️ انتهت")
        bot.reply_to(m,"🔍 *العمليات:*\n\n"+"\n\n".join(lines), parse_mode="Markdown")

    elif text == "🚨 الحجر الصحي":
        q = db.get("quarantine",[])
        if not q:
            bot.reply_to(m,"✅ الحجر فارغ."); return
        for entry in q:
            mk = types.InlineKeyboardMarkup(row_width=2)
            mk.add(
                types.InlineKeyboardButton("✅ موافقة",  callback_data=f"qapprove_{entry['fname']}"),
                types.InlineKeyboardButton("🗑 حذف",     callback_data=f"qdelete_{entry['fname']}")
            )
            bot.send_message(m.chat.id,
                f"🚨 *{entry['fname']}*\n"
                f"👤 `{entry['uid']}` | 🕐 {entry['time']}\n"
                f"🔴 " + "\n🔴 ".join(entry.get("dangers",[])),
                parse_mode="Markdown", reply_markup=mk)

    elif text == "💾 باك أب":
        if not is_staff(uid): return
        try:
            if os.path.exists(DB_FILE):
                with open(DB_FILE,'rb') as f:
                    bot.send_document(m.chat.id, f,
                        caption=f"💾 *باك أب قاعدة البيانات*\n🕐 {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                        parse_mode="Markdown")
            else:
                bot.reply_to(m,"❌ لا توجد قاعدة بيانات.")
        except Exception as e:
            bot.reply_to(m, f"❌ `{e}`", parse_mode="Markdown")

    elif text == "📦 تثبيت مكاتب":
        if not is_staff(uid): return
        user_states[uid] = {"action":"pip_install","file":None}
        bot.reply_to(m,
            "📦 اكتب المكاتب اللي عايز تثبّتها:\nمثال: `requests flask aiohttp`",
            parse_mode="Markdown")

    elif text == "🔎 فحص ملف":
        user_states[uid] = {"action":"scan_only"}
        bot.reply_to(m,
            "🔎 *ابعت الملف اللي عايز تفحصه*\n"
            "هيبعتلك:\n"
            "• ✅ آمن أو ⚠️ مشاكل\n"
            "• 🤖 وجود التوكن والأدمن ID\n"
            "• 📦 المكاتب المحتاجة\n"
            "بدون ما يتشغّل أو يترفع",
            parse_mode="Markdown")

    elif text == "🔄 تحديث البوت":
        if role != ROLE_OWNER: return
        bot.reply_to(m,
            "🔄 *تحديث البوت*\n━━━━━━━━━━━━━━━━━\n"
            "ابعت الملف الجديد `bot.py` وهيتحدث تلقائياً.\n"
            "⚠️ البيانات مش هتتحذف.",
            parse_mode="Markdown")
        user_states[uid] = {"action":"update_bot"}

    elif text == "📢 بث رسالة":
        if not is_staff(uid): return
        user_states[uid] = {"action":"broadcast"}
        bot.reply_to(m, "📢 اكتب الرسالة اللي عايز تبعتها لكل المستخدمين:", parse_mode="Markdown")

    elif text == "🌐 فحص IP":
        if not is_staff(uid): return
        user_states[uid] = {"action":"check_ip"}
        bot.reply_to(m, "🌐 ابعت IP أو دومين عايز تفحصه:", parse_mode="Markdown")

    elif text == "📝 ملاحظات":
        if role != ROLE_OWNER: return
        notes = db.get("notes", [])
        if not notes:
            bot.reply_to(m, "📝 لا توجد ملاحظات.")
        else:
            txt = "\n".join([f"• {n}" for n in notes[-10:]])
            bot.reply_to(m, f"📝 *الملاحظات:*\n{txt}", parse_mode="Markdown")
        user_states[uid] = {"action":"add_note"}
        bot.send_message(m.chat.id, "اكتب ملاحظة جديدة أو /skip للتخطي:")

    elif text == "⚡ تسريع":
        if role != ROLE_OWNER: return
        import gc
        collected = gc.collect()
        bot.reply_to(m,
            f"⚡ *تم تنظيف الذاكرة*\n"
            f"🗑 محذوف: `{collected}` كائن\n"
            f"🔧 Threads: `{threading.active_count()}`\n"
            f"💾 RAM: `{psutil.virtual_memory().percent}%`",
            parse_mode="Markdown")

    elif text == "🔒 قفل البوت":
        if role != ROLE_OWNER: return
        locked = db.get("locked", False)
        db["locked"] = not locked; save()
        state = "🔒 مقفول" if not locked else "🔓 مفتوح"
        bot.reply_to(m, f"البوت الآن: *{state}*\n{'المستخدمون الجدد لن يستطيعوا الرفع' if not locked else 'المستخدمون يستطيعون الرفع'}", parse_mode="Markdown")

    elif text == "🗑 مسح السجلات":
        if role != ROLE_OWNER: return
        try:
            import glob as gl
            for f in gl.glob("LOGS/*.log"):
                open(f,'w').close()
            bot.reply_to(m, "🗑 *تم مسح كل السجلات.*", parse_mode="Markdown")
        except Exception as e:
            bot.reply_to(m, f"❌ `{e}`", parse_mode="Markdown")

    elif text == "🕐 وقت التشغيل":
        up = int(time.time() - BOT_START_TIME)
        d, r = divmod(up, 86400)
        h, r = divmod(r, 3600)
        mn, s = divmod(r, 60)
        bot.reply_to(m,
            f"🕐 *وقت التشغيل*\n━━━━━━━━━━━━━━━━━\n"
            f"⏱ `{d}` يوم `{h}` ساعة `{mn}` دقيقة `{s}` ثانية\n"
            f"🚀 بدأ: `{datetime.fromtimestamp(BOT_START_TIME).strftime('%Y-%m-%d %H:%M')}`\n"
            f"⚡ عمليات نشطة: `{len(running_procs)}`\n"
            f"🔧 Threads: `{threading.active_count()}`",
            parse_mode="Markdown")

    elif text == "🔑 توليد كلمة سر":
        import secrets, string
        chars = string.ascii_letters + string.digits + "!@#$%^&*"
        pwd8  = ''.join(secrets.choice(chars) for _ in range(8))
        pwd16 = ''.join(secrets.choice(chars) for _ in range(16))
        pwd32 = ''.join(secrets.choice(chars) for _ in range(32))
        bot.reply_to(m,
            f"🔑 *كلمات سر عشوائية:*\n━━━━━━━━━━━━━━━━━\n"
            f"8 حروف: `{pwd8}`\n"
            f"16 حرف: `{pwd16}`\n"
            f"32 حرف: `{pwd32}`",
            parse_mode="Markdown")

    elif text == "📌 تثبيت رسالة":
        if role != ROLE_OWNER: return
        user_states[uid] = {"action":"pin_msg"}
        bot.reply_to(m, "📌 اكتب الرسالة اللي عايز تثبّتها للكل:")

    elif text == "🌡 درجة CPU":
        try:
            temps = psutil.sensors_temperatures() if hasattr(psutil,'sensors_temperatures') else {}
            cpu_freq = psutil.cpu_freq()
            cpu_pct  = psutil.cpu_percent(interval=1, percpu=True)
            cores_txt = " | ".join([f"C{i}:`{p}%`" for i,p in enumerate(cpu_pct)])
            freq_txt  = f"`{cpu_freq.current:.0f}` MHz" if cpu_freq else "غير متاح"
            temp_txt  = "غير متاح"
            if temps:
                for k,v in temps.items():
                    if v: temp_txt = f"`{v[0].current}°C`"; break
            bot.reply_to(m,
                f"🌡 *مراقبة CPU*\n━━━━━━━━━━━━━━━━━\n"
                f"🔥 درجة الحرارة: {temp_txt}\n"
                f"⚡ التردد: {freq_txt}\n"
                f"📊 النوى: {cores_txt}",
                parse_mode="Markdown")
        except Exception as e:
            bot.reply_to(m, f"❌ `{e}`", parse_mode="Markdown")

    elif text == "📋 نسخ السجل":
        if not is_staff(uid): return
        p = "LOGS/bot.log"
        if os.path.exists(p):
            with open(p,'rb') as f:
                bot.send_document(m.chat.id, f, caption="📋 السجل الكامل")
        else:
            bot.reply_to(m, "❌ لا يوجد سجل.")

    elif text == "🔃 إعادة تشغيل الكل":
        if not is_staff(uid): return
        count = 0
        for fname, info in list(db["files"].items()):
            if info.get("active"):
                stop_file(fname)
                time.sleep(0.2)
                launch(info["path"], fname)
                count += 1
        bot.reply_to(m, f"🔃 تمت إعادة تشغيل {count} ملف", parse_mode="Markdown")

    elif text == "💎 إدارة النقطة":
        if role != ROLE_OWNER: return
        user_states[uid] = {"action":"give_credits"}
        bot.reply_to(m,
            "💎 ابعت: `ID النقطة السبب`\nمثال: `123456 100 جائزة`",
            parse_mode="Markdown")

    elif text == "📈 تقرير فوري":
        if not is_staff(uid): return
        s = db["stats"]
        roles = {}
        for u,info in db["users"].items():
            roles[info.get("role","user")] = roles.get(info.get("role","user"),0)+1
        mem  = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        up   = int(time.time()-BOT_START_TIME)
        h,r  = divmod(up,3600); mn,sc = divmod(r,60)
        bot.reply_to(m,
            f"📈 تقرير فوري\n━━━━━━━━━━━━━━━━━\n"
            f"🕐 تشغيل: {h}س {mn}د\n"
            f"👥 مستخدمون: {len(db['users'])} | ⭐ VIP: {roles.get('vip',0)}\n"
            f"📂 ملفات: {len(db['files'])} | ⚡ نشطة: {len(running_procs)}\n"
            f"📤 رفعات: {s.get('uploads',0)} | 🔁 إعادات: {s.get('restarts',0)}\n"
            f"🎫 تذاكر: {s.get('tickets_opened',0)} | 💎 نقطة: {s.get('total_credits_given',0)}\n"
            f"CPU: {psutil.cpu_percent()}% | RAM: {mem.percent}% | Disk: {disk.percent}%")

    elif text == "🎫 التذاكر":
        if not is_staff(uid): return
        open_tickets = [(tid,t) for tid,t in db["tickets"].items() if t.get("status")=="open"]
        if not open_tickets:
            bot.reply_to(m, "✅ لا توجد تذاكر مفتوحة."); return
        for tid, t in open_tickets[:5]:
            name = db["users"].get(t["uid"],{}).get("name","؟")
            mk = types.InlineKeyboardMarkup()
            mk.add(
                types.InlineKeyboardButton("📩 رد", callback_data=f"treply_{tid}"),
                types.InlineKeyboardButton("✅ إغلاق", callback_data=f"tclose_{tid}")
            )
            bot.send_message(m.chat.id,
                f"🎫 #{tid}\n👤 {name} ({t['uid']})\n🕐 {t['created']}\n📝 {t['msg'][:200]}",
                reply_markup=mk)

    elif text == "🎫 تذكرة دعم":
        user_states[uid] = {"action":"open_ticket"}
        bot.reply_to(m,
            "🎫 اكتب مشكلتك أو سؤالك وهيوصل للأدمن فوراً:")

    elif text == "🚫 القائمة السوداء":
        if role != ROLE_OWNER: return
        bl = db.get("blacklist",[])
        if not bl:
            bot.reply_to(m, "✅ القائمة السوداء فارغة."); return
        lines = []
        for u in bl:
            name = db["users"].get(u,{}).get("name","؟")
            lines.append(f"🚫 `{u}` — {name}")
        mk = types.InlineKeyboardMarkup()
        mk.add(types.InlineKeyboardButton("➕ حظر جديد", callback_data="bl_add"))
        bot.reply_to(m,
            f"🚫 القائمة السوداء ({len(bl)}):\n" + "\n".join(lines),
            parse_mode="Markdown", reply_markup=mk)

    elif text == "🛡 لوحة الأمان":
        if role != ROLE_OWNER: return
        s = db["settings"]
        bot.reply_to(m,
            f"🛡 لوحة الأمان\n━━━━━━━━━━━━━━━━━\n"
            f"🚫 القائمة السوداء: {len(db.get('blacklist',[]))}\n"
            f"🚨 مشبوهون: {len(suspicious)}\n"
            f"⏳ محظورون مؤقتاً: {len(spam_blocked)}\n"
            f"📦 حجم أقصى: {s.get('max_file_size_kb',500)} KB\n"
            f"📂 ملفات/مستخدم: {s.get('max_files_per_user',5)}\n"
            f"📤 رفعات/دقيقة: {UPLOAD_LIMIT}\n"
            f"💬 رسايل/10ث: {SPAM_LIMIT}\n"
            f"🔒 مقفول: {'نعم' if db.get('locked') else 'لا'}\n"
            f"🔧 صيانة: {'نعم' if s.get('maintenance') else 'لا'}")

    elif text == "📡 المشبوهون":
        if role != ROLE_OWNER: return
        if not suspicious:
            bot.reply_to(m, "✅ لا يوجد مستخدمون مشبوهون."); return
        lines = []
        for u in list(suspicious)[:15]:
            name = db["users"].get(u,{}).get("name","؟")
            fails = failed_cmds.get(u,0)
            lines.append(f"⚠️ `{u}` — {name} ({fails} محاولة)")
        mk = types.InlineKeyboardMarkup(row_width=2)
        mk.add(
            types.InlineKeyboardButton("🧹 مسح القائمة", callback_data="sec_clear_sus"),
            types.InlineKeyboardButton("🚫 حظر الكل", callback_data="sec_ban_all_sus"),
        )
        bot.reply_to(m,
            f"📡 المشبوهون ({len(suspicious)}):\n" + "\n".join(lines),
            parse_mode="Markdown", reply_markup=mk)

    elif text == "🔐 إعادة تعيين حماية":
        if role != ROLE_OWNER: return
        spam_blocked.clear()
        spam_counter.clear()
        upload_counter.clear()
        failed_cmds.clear()
        bot.reply_to(m, "🔐 تم إعادة تعيين كل حدود الحماية ✅")
        if not is_staff(uid): return
        versions = db.get("file_versions",{})
        if not versions:
            bot.reply_to(m, "📜 لا توجد إصدارات محفوظة."); return
        lines = []
        for fname, vers in list(versions.items())[:10]:
            lines.append(f"📄 {fname} — {len(vers)} نسخة")
        mk = types.InlineKeyboardMarkup(row_width=1)
        for fname in list(versions.keys())[:5]:
            mk.add(types.InlineKeyboardButton(f"📄 {fname}", callback_data=f"ver_{fname}"))
        bot.reply_to(m,
            "📜 الملفات التي لها إصدارات محفوظة:\n" + "\n".join(lines),
            reply_markup=mk)

    elif text == "⚙️ الإعدادات":
        if role != ROLE_OWNER: return
        s = db["settings"]
        mk = types.InlineKeyboardMarkup(row_width=2)
        mk.add(
            types.InlineKeyboardButton("📂 حد الملفات",    callback_data="cfg_max_files_per_user"),
            types.InlineKeyboardButton("📦 الحجم الأقصى",  callback_data="cfg_max_file_size_kb"),
            types.InlineKeyboardButton("💎 نقطة/رفع",     callback_data="cfg_credits_per_upload"),
            types.InlineKeyboardButton("👥 نقطة/دعوة",    callback_data="cfg_credits_for_referral"),
            types.InlineKeyboardButton("🌟 نقطة VIP",     callback_data="cfg_vip_min_credits"),
            types.InlineKeyboardButton("🎁 نقطة ترحيبي",  callback_data="cfg_welcome_credits"),
            types.InlineKeyboardButton(
                "🔒 قفل البوت" if not db.get("locked") else "🔓 فتح البوت",
                callback_data="cfg_toggle_lock"),
            types.InlineKeyboardButton(
                "🔧 تفعيل الصيانة" if not s.get("maintenance") else "✅ إيقاف الصيانة",
                callback_data="cfg_toggle_maintenance"),
            types.InlineKeyboardButton("⏰ وقت التقرير",   callback_data="cfg_report_time"),
        )
        bot.reply_to(m,
            f"⚙️ إعدادات البوت\n━━━━━━━━━━━━━━━━━\n"
            f"📂 حد ملفات/مستخدم: {s.get('max_files_per_user',5)}\n"
            f"📦 حجم أقصى: {s.get('max_file_size_kb',500)} KB\n"
            f"💎 نقطة/رفع: {s.get('credits_per_upload',10)}\n"
            f"👥 نقطة/دعوة: {s.get('credits_for_referral',50)}\n"
            f"🌟 نقطة VIP: {s.get('vip_min_credits',200)}\n"
            f"🎁 نقطة ترحيبي: {s.get('welcome_credits',20)}\n"
            f"🔒 مقفول: {'نعم' if db.get('locked') else 'لا'}\n"
            f"🔧 صيانة: {'نعم' if s.get('maintenance') else 'لا'}\n"
            f"⏰ وقت التقرير: {db.get('daily_report_time','08:00')}\n\n"
            f"اضغط على أي إعداد لتعديله:",
            reply_markup=mk)

    elif text == "🏆 المتصدرون":
        if not is_staff(uid): return
        sorted_users = sorted(db["users"].items(), key=lambda x: x[1].get("credits",0), reverse=True)[:10]
        medals = ["🥇","🥈","🥉","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]
        lines = []
        for i,(u,info) in enumerate(sorted_users):
            re_e = {"owner":"🔱","admin":"👑","vip":"⭐","user":"👤"}.get(info.get("role","user"),"👤")
            lines.append(f"{medals[i]} {re_e} {info.get('name','؟')} — 💎{info.get('credits',0)} | 📤{info.get('uploads',0)}")
        bot.reply_to(m, "🏆 أعلى 10 مستخدمين\n━━━━━━━━━━━━━━━━━\n" + "\n".join(lines))

    elif text == "🔎 بحث مستخدم":
        if not is_staff(uid): return
        user_states[uid] = {"action":"search_user"}
        bot.reply_to(m, "🔎 ابعت اسم أو ID المستخدم:")

    elif text == "📣 إشعار عام":
        if role != ROLE_OWNER: return
        mk = types.InlineKeyboardMarkup(row_width=2)
        mk.add(
            types.InlineKeyboardButton("👥 الكل",     callback_data="notif_all"),
            types.InlineKeyboardButton("⭐ VIP فقط",  callback_data="notif_vip"),
            types.InlineKeyboardButton("👤 عادي فقط", callback_data="notif_user"),
        )
        bot.reply_to(m, "📣 لمن تريد الإشعار؟", reply_markup=mk)

# ══════════════════════════════════════════════════════════════
#  دوال مساعدة
# ══════════════════════════════════════════════════════════════
def _show_files(m):
    uid = reg_user(m); role = get_role(uid)
    files = [f for f,v in db["files"].items()
             if v.get("owner")==uid or is_staff(uid)]
    if not files:
        bot.send_message(m.chat.id,"📂 لا توجد ملفات."); return
    for fname in files:
        info = db["files"][fname]
        st = "✅" if info.get("active") else "❌"
        ar = " 🔁" if info.get("auto_restart") else ""
        bot.send_message(m.chat.id,
            f"📄 *{fname}*{ar} {st}\n📦`{info.get('size',0)//1024}KB` | 🕐{info.get('uploaded_at','؟')}",
            parse_mode="Markdown",
            reply_markup=kb_file(fname) if is_staff(uid) else None)

def _server_stats(m):
    mem=psutil.virtual_memory(); disk=psutil.disk_usage('/'); net=psutil.net_io_counters()
    bot.reply_to(m,
        f"📊 *السيرفر*\n━━━━━━━━━━━━━━━━━\n"
        f"🖥️ CPU: `{psutil.cpu_percent(1)}%`\n"
        f"💾 RAM: `{mem.percent}%` ({mem.used//1024//1024}/{mem.total//1024//1024}MB)\n"
        f"💿 Disk: `{disk.percent}%` ({disk.used//1024//1024//1024}/{disk.total//1024//1024//1024}GB)\n"
        f"🌐 ↑`{net.bytes_sent//1024//1024}MB` ↓`{net.bytes_recv//1024//1024}MB`\n"
        f"⚡ عمليات: `{len(running_procs)}` | 🔧 Threads: `{threading.active_count()}`",
        parse_mode="Markdown")

def _help(m):
    uid = reg_user(m); role = get_role(uid)
    if role in [ROLE_USER, ROLE_VIP]:
        bot.send_message(m.chat.id,
            f"👋 *أهلاً! إليك ما تقدر تعمله:*\n"
            f"━━━━━━━━━━━━━━━━━\n"
            f"📂 *ملفاتي* — شوف الملفات اللي رفعتها\n"
            f"🔎 *فحص ملف* — افحص ملف قبل ما ترفعه\n"
            f"🔑 *توليد كلمة سر* — كلمة سر عشوائية آمنة\n"
            f"📡 *السيرفر* — إحصائيات السيرفر\n\n"
            f"📤 *رفع ملف:*\n"
            f"ابعت أي ملف `.py` `.js` `.sh` مباشرة\n"
            f"وهيتفحص وينزّل المكاتب ويشتغل تلقائياً ✅\n\n"
            f"⚡ *أوامر:*\n"
            f"/id — ID بتاعك\n"
            f"/myfiles — ملفاتك\n"
            f"/start — الرئيسية\n\n"
            f"🆔 ID: `{m.from_user.id}`",
            parse_mode="Markdown")
    else:
        cmds = (
            "📖 *الأوامر المتاحة:*\n━━━━━━━━━━━━━━━━━\n"
            "/start — الرئيسية\n"
            "/id — ID بتاعك\n"
            "/myfiles — ملفاتك\n"
            "/stats — موارد السيرفر\n"
            "/help — المساعدة\n"
            "\n*للأدمن:*\n"
            "/run اسم — تشغيل ملف\n"
            "/stop اسم — إيقاف ملف\n"
            "/health — تقرير الصحة\n"
            "/backup — باك أب فوري\n"
        )
        cmds += f"\n🆔 ID: `{m.from_user.id}`"
        bot.reply_to(m, cmds, parse_mode="Markdown")

# ══════════════════════════════════════════════════════════════
#  التشغيل
# ══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    log.info("🚀 ELITE HOST BOT v5.0 ULTRA EDITION")
    try:
        bot.set_my_commands([
            types.BotCommand("/start",   "الرئيسية"),
            types.BotCommand("/id",      "معرفة ID"),
            types.BotCommand("/myfiles", "ملفاتي"),
            types.BotCommand("/credits", "رصيد النقطة"),
            types.BotCommand("/ref",     "رابط الدعوة"),
            types.BotCommand("/stats",   "موارد السيرفر"),
            types.BotCommand("/health",  "تقرير الصحة"),
            types.BotCommand("/backup",  "باك أب فوري"),
            types.BotCommand("/run",     "تشغيل ملف"),
            types.BotCommand("/stop",    "إيقاف ملف"),
            types.BotCommand("/help",    "المساعدة"),
        ])
    except: pass

    startup_msg = (
        f"🟢 ELITE HOST v5.0 ULTRA يعمل!\n"
        f"━━━━━━━━━━━━━━━━━\n"
        f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        f"📂 ملفات: {len(db['files'])} | 👥 مستخدمون: {len(db['users'])}\n"
        f"💎 نقطة | 🔗 دعوة | 💥 كراش واتشر | 📊 تقرير يومي"
    )
    for admin in ADMIN_IDS:
        try:
            bot.send_message(admin, startup_msg,
                reply_markup=kb_owner() if admin == ADMIN_ID else kb_admin())
        except Exception as e:
            log.warning(f"Startup notify {admin}: {e}")

    bot.infinity_polling(skip_pending=True, timeout=60, long_polling_timeout=60)
