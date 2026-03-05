# لا تنسى ذكر الله 🤍
# ELITE HOST BOT v3.0

import telebot, os, json, subprocess, sys, psutil, shutil, logging, threading, time, re
from telebot import types
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

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
TOKEN     = "8675185329:AAH3_fSw5wU8FSHYlukQAqnxrGI2TZqEuuo"
ADMIN_ID  = 6918240643
ADMIN_IDS = [6918240643]   # ← أضف أدمن: [6918240643, 123456789]

bot      = telebot.TeleBot(TOKEN, threaded=True, num_threads=160)
executor = ThreadPoolExecutor(max_workers=160)

for d in ["ELITE_HOST","GHOST_VOLUMES","SYSTEM_CORES","LOGS","QUARANTINE"]:
    os.makedirs(d, exist_ok=True)

# ══════════════════════════════════════════════════════════════
#  قاعدة البيانات
# ══════════════════════════════════════════════════════════════
DB_FILE = "elite_db.json"

def load_db():
    default = {
        "users":     {},   # uid -> {name, joined, role, uploads}
        "files":     {},   # fname -> {owner,active,path,size,ext,uploaded_at,auto_restart}
        "envs":      {},   # fname -> {KEY:VAL}
        "scheduled": [],
        "quarantine":[],   # ملفات محجوزة تنتظر موافقة
        "stats":     {"uploads":0,"kills":0,"commands":0,"restarts":0,"blocked":0}
    }
    if not os.path.exists(DB_FILE): return default
    try:
        with open(DB_FILE,'r',encoding='utf-8') as f: data=json.load(f)
        for k,v in default.items():
            if k not in data: data[k]=v
        return data
    except: return default

db = load_db()

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
        db["users"][uid] = {
            "name":    name,
            "joined":  datetime.now().strftime('%Y-%m-%d %H:%M'),
            "role":    ROLE_USER,
            "uploads": 0
        }
        save()
    return uid

# ══════════════════════════════════════════════════════════════
#  فاحص الملفات
# ══════════════════════════════════════════════════════════════
# ── أنماط الخطر الحقيقي فقط (مش كل حاجة) ──
DANGER_PATTERNS = [
    (r"os\.system\s*\(['\"]?\s*rm\s+-rf",        "حذف ملفات النظام بـ os.system"),
    (r"shutil\.rmtree\s*\(['\"]?/",              "حذف مجلد جذر النظام"),
    (r"eval\s*\(\s*base64",                      "تنفيذ كود مشفر base64"),
    (r"exec\s*\(\s*base64",                      "تنفيذ كود مشفر base64"),
    (r"__import__\s*\(['\"]os['\"]",             "استيراد os بشكل مخفي"),
    (r"fork\s*\(\s*\).*while",                   "fork bomb محتمل"),
    (r"while\s+True\s*:\s*\n\s*(os\.fork|subprocess)", "fork bomb loop"),
    (r"cryptominer|xmrig|minerd|stratum\+tcp",   "تعدين عملات مشفرة"),
    (r"(DROP\s+TABLE|DELETE\s+FROM.*WHERE\s+1)", "حذف قاعدة بيانات"),
    (r"(\/etc\/passwd|\/etc\/shadow)",           "الوصول لملفات النظام الحساسة"),
    (r"keylog|keystroke|pynput.*Listener",       "كيلوجر / تتبع لوحة المفاتيح"),
    (r"reverse.?shell|bind.?shell",              "reverse shell"),
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

# ══════════════════════════════════════════════════════════════
#  تثبيت المكاتب
# ══════════════════════════════════════════════════════════════
def install_pkgs(pkgs:list, chat_id:int=None) -> bool:
    if not pkgs: return True
    try:
        if chat_id: bot.send_message(chat_id, f"📦 جارٍ تثبيت:\n`{' '.join(pkgs)}`", parse_mode="Markdown")
        r = subprocess.run([sys.executable,"-m","pip","install"]+pkgs+["--quiet"],
                           capture_output=True, text=True, timeout=180)
        if r.returncode == 0:
            if chat_id: bot.send_message(chat_id, "✅ تم تثبيت المكاتب!", parse_mode="Markdown")
            return True
        else:
            out = (r.stdout+r.stderr).strip()
            if chat_id: bot.send_message(chat_id, f"⚠️ خطأ:\n```\n{out[-1500:]}\n```", parse_mode="Markdown")
            return False
    except subprocess.TimeoutExpired:
        if chat_id: bot.send_message(chat_id, "⏱ انتهى وقت التثبيت")
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
        if name and name in db.get("envs",{}): env.update(db["envs"][name])
        cmds    = {".py":[sys.executable,path], ".js":["node",path], ".sh":["bash",path]}
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
        try: info["proc"].terminate()
        except: pass
    if name in db["files"]:
        db["files"][name]["active"] = False; save()

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

# ══════════════════════════════════════════════════════════════
#  لوحات المفاتيح
# ══════════════════════════════════════════════════════════════
def kb_owner():
    m = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    m.add(types.KeyboardButton("📤 رفع ملف للاستضافة", request_document=True))
    m.add(
        "🖥 الاستضافة",     "⚙️ الحاويات",      "🔍 مراقبة العمليات",
        "📡 موارد السيرفر", "📋 السجلات",        "📊 الإحصائيات",
        "👥 المستخدمون",    "🔐 لوحة الأدمن",    "🧹 تطهير",
        "🖥️ Shell",         "📁 الملفات",        "⏰ المجدولة",
        "🚨 الحجر الصحي",   "💀 إيقاف الكل",
    )
    return m

def kb_admin():
    m = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    m.add(types.KeyboardButton("📤 رفع ملف للاستضافة", request_document=True))
    m.add(
        "🖥 الاستضافة",     "⚙️ الحاويات",      "🔍 مراقبة العمليات",
        "📡 موارد السيرفر", "📋 السجلات",        "📊 الإحصائيات",
        "👥 المستخدمون",    "📁 الملفات",        "⏰ المجدولة",
        "💀 إيقاف الكل",
    )
    return m

def kb_vip():
    m = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    m.add(types.KeyboardButton("📤 رفع ملف للاستضافة", request_document=True))
    m.add("📂 ملفاتي", "📡 السيرفر", "ℹ️ مساعدة")
    return m

def kb_user():
    m = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    m.add(types.KeyboardButton("📤 رفع ملف للاستضافة", request_document=True))
    m.add("📂 ملفاتي", "ℹ️ مساعدة")
    return m

def get_kb(uid:str):
    r = get_role(uid)
    if r == ROLE_OWNER: return kb_owner()
    if r == ROLE_ADMIN: return kb_admin()
    if r == ROLE_VIP:   return kb_vip()
    return kb_user()

def kb_file(fname):
    m = types.InlineKeyboardMarkup(row_width=3)
    active = db["files"].get(fname,{}).get("active",False)
    ar     = db["files"].get(fname,{}).get("auto_restart",False)
    m.add(
        types.InlineKeyboardButton("⏹ إيقاف" if active else "▶️ تشغيل", callback_data=f"tog_{fname}"),
        types.InlineKeyboardButton("🔄 إعادة",  callback_data=f"rst_{fname}"),
        types.InlineKeyboardButton("🗑 حذف",    callback_data=f"del_{fname}"),
    )
    m.add(
        types.InlineKeyboardButton("📋 لوج",    callback_data=f"log_{fname}"),
        types.InlineKeyboardButton("📥 تحميل",  callback_data=f"dwn_{fname}"),
        types.InlineKeyboardButton("🔁 Auto" if not ar else "🔁 إيقاف Auto", callback_data=f"ar_{fname}"),
    )
    m.add(
        types.InlineKeyboardButton("🌍 ENV",    callback_data=f"env_{fname}"),
        types.InlineKeyboardButton("📊 موارد",  callback_data=f"res_{fname}"),
        types.InlineKeyboardButton("📦 مكاتب",  callback_data=f"pip_{fname}"),
    )
    m.add(
        types.InlineKeyboardButton("⏰ جدولة",  callback_data=f"sched_{fname}"),
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

    bot.send_message(m.chat.id,
        f"{role_emoji} *أهلاً {name}!*\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"📊 صلاحيتك: `{role.upper()}`\n"
        f"📂 الملفات: `{len(db['files'])}`\n"
        f"⚡ عمليات نشطة: `{len(running_procs)}`",
        parse_mode="Markdown", reply_markup=get_kb(uid))

@bot.message_handler(commands=['myfiles'])
def cmd_myfiles(m):
    _show_files(m)

@bot.message_handler(commands=['id'])
def cmd_id(m):
    bot.reply_to(m, f"🆔 ID بتاعك: `{m.from_user.id}`", parse_mode="Markdown")

# ══════════════════════════════════════════════════════════════
#  رفع الملفات
# ══════════════════════════════════════════════════════════════
@bot.message_handler(content_types=['document'])
def handle_upload(m):
    uid  = reg_user(m)
    role = get_role(uid)

    def deploy():
        try:
            fname = m.document.file_name
            ext   = os.path.splitext(fname)[1].lower()
            raw   = bot.download_file(bot.get_file(m.document.file_id).file_path)

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
            path = f"ELITE_HOST/{fname}"
            with open(path,'wb') as f: f.write(raw)
            db["files"][fname] = {
                "owner": uid, "active": False, "path": path,
                "size": len(raw), "auto_restart": False,
                "uploaded_at": datetime.now().strftime('%Y-%m-%d %H:%M'), "ext": ext
            }
            db["stats"]["uploads"] = db["stats"].get("uploads",0)+1
            db["users"][uid]["uploads"] = db["users"].get(uid,{}).get("uploads",0)+1
            save()

            # ── فحص الأمان + اكتشاف المكاتب ──────────
            if ext == ".py":
                scan = scan_file(path)

                # بناء رسالة الفحص
                scan_txt = "✅ *آمن*" if scan["safe"] else "⚠️ *فيه مشاكل!*"
                libs_txt  = f"\n📦 مكاتب مكتشفة: `{', '.join(scan['to_install']) or 'لا شيء'}`" if scan["to_install"] else "\n📦 لا تحتاج مكاتب إضافية"
                danger_txt = ("\n🔴 " + "\n🔴 ".join(scan["danger"])) if scan["danger"] else ""

                bot.reply_to(m,
                    f"✅ *تم الرفع:* `{fname}`\n📦 `{len(raw)//1024} KB`\n\n"
                    f"🔍 *الفحص:* {scan_txt}{libs_txt}{danger_txt}",
                    parse_mode="Markdown",
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

    # ══ لوحة الأدمن ══════════════════════
    elif act == "ap":
        if only_owner(): return
        bot.answer_callback_query(call.id)
        sub = tgt  # الأمر الفرعي

        if sub == "list_all":
            lines = [f"{'👑' if get_role(u)=='admin' else '⭐' if get_role(u)=='vip' else '👤'} `{u}` — {info.get('name','؟')}"
                     for u,info in list(db["users"].items())[:20]]
            bot.send_message(call.message.chat.id,
                f"📜 *كل المستخدمين ({len(db['users'])}):*\n" + "\n".join(lines),
                parse_mode="Markdown")

        elif sub == "list_admins":
            admins = [f"`{u}` — {info.get('name','؟')}" for u,info in db["users"].items() if info.get("role")==ROLE_ADMIN]
            admins += [f"`{ADMIN_ID}` — المالك"]
            bot.send_message(call.message.chat.id,
                f"👑 *الأدمنز:*\n" + "\n".join(admins) if admins else "لا يوجد أدمن.",
                parse_mode="Markdown")

        elif sub == "list_vip":
            vips = [f"`{u}` — {info.get('name','؟')}" for u,info in db["users"].items() if info.get("role")==ROLE_VIP]
            bot.send_message(call.message.chat.id,
                f"⭐ *VIP ({len(vips)}):*\n" + "\n".join(vips) if vips else "لا يوجد VIP.",
                parse_mode="Markdown")

        elif sub == "list_banned":
            banned = [f"`{u}` — {info.get('name','؟')}" for u,info in db["users"].items() if info.get("role")=="banned"]
            bot.send_message(call.message.chat.id,
                f"🚫 *محظورون ({len(banned)}):*\n" + "\n".join(banned) if banned else "لا يوجد محظورون.",
                parse_mode="Markdown")

        elif sub == "stats":
            roles = {}
            for u,info in db["users"].items():
                r = info.get("role","user")
                roles[r] = roles.get(r,0)+1
            bot.send_message(call.message.chat.id,
                f"📊 *إحصائيات المستخدمين*\n━━━━━━━━━━━━━━━━━\n"
                f"👥 الكل: `{len(db['users'])}`\n"
                f"👑 أدمن: `{roles.get('admin',0)}`\n"
                f"⭐ VIP: `{roles.get('vip',0)}`\n"
                f"👤 عادي: `{roles.get('user',0)}`\n"
                f"🚫 محظور: `{roles.get('banned',0)}`",
                parse_mode="Markdown")

        elif sub in ["set_admin","set_vip","set_user","ban","unban","delete_user"]:
            action_map = {
                "set_admin": "تعيين أدمن",  "set_vip": "تعيين VIP",
                "set_user":  "تخفيض User",  "ban":     "حظر",
                "unban":     "رفع حظر",     "delete_user": "حذف مستخدم"
            }
            user_states[uid] = {"action": f"panel_{sub}"}
            bot.send_message(call.message.chat.id,
                f"🔐 *{action_map[sub]}*\nأرسل ID المستخدم:", parse_mode="Markdown")

        elif sub == "broadcast":
            user_states[uid] = {"action": "broadcast"}
            bot.send_message(call.message.chat.id,
                "📢 اكتب الرسالة الجماعية:", parse_mode="Markdown")

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
    if text == "📤 رفع ملف للاستضافة":
        bot.reply_to(m,
            "📤 *أرسل الملف الآن!*\n"
            "━━━━━━━━━━━━━━━━━\n"
            "• `.py` — بايثون\n"
            "• `.js` — جافاسكريبت\n"
            "• `.sh` — باش\n"
            "• `requirements.txt` — مكاتب\n\n"
            "سيتم فحصه واكتشاف مكاتبه وتشغيله تلقائياً ✅",
            parse_mode="Markdown")
        return
    if text == "📂 ملفاتي" or text == "/myfiles":
        _show_files(m); return
    if text in ["ℹ️ مساعدة","ℹ️ المساعدة"]:
        _help(m); return
    if text in ["📡 السيرفر","📡 موارد السيرفر"]:
        _server_stats(m); return

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
        c = 0
        for n in list(running_procs.keys()): stop_file(n); c+=1
        db["stats"]["kills"] = db["stats"].get("kills",0)+1; save()
        bot.reply_to(m, f"💀 *أُوقفت {c} عملية.*", parse_mode="Markdown")

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
    bot.send_message(m.chat.id,
        f"📖 *المساعدة*\n━━━━━━━━━━━━━━━━━\n"
        f"• أرسل `.py` `.js` `.sh` لرفعه وتشغيله\n"
        f"• أرسل `requirements.txt` لتثبيت المكاتب\n"
        f"• `/id` — معرفة ID بتاعك\n"
        f"• `/myfiles` — ملفاتك\n"
        f"• `/start` — الرئيسية\n"
        f"\n🆔 ID بتاعك: `{m.from_user.id}`",
        parse_mode="Markdown")

# ══════════════════════════════════════════════════════════════
#  التشغيل
# ══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    log.info("🚀 ELITE HOST BOT v3.0")
    try:
        bot.send_message(ADMIN_ID,
            f"🟢 *ELITE HOST v3.0 يعمل!*\n🕐 {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            parse_mode="Markdown", reply_markup=kb_owner())
    except Exception as e:
        log.warning(f"Startup: {e}")
    bot.infinity_polling(skip_pending=True, timeout=60, long_polling_timeout=60)
