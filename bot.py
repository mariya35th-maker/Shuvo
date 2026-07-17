# -*- coding: utf-8 -*-

import telebot
import requests
import json
import pycountry
import phonenumbers
import threading
import time
import random
import logging
import traceback
import re
import hmac
import hashlib
import base64
import struct
from flask import Flask
from threading import Thread
from telebot import types
from datetime import datetime, date

# ===================== FLASK KEEP-ALIVE =====================
app = Flask('')

@app.route('/')
def home():
    return "Bot is Running Live!"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run_flask, daemon=True)
    t.start()

# ===================== CONFIGURATION =====================
API_KEY      = "nx_2KxBsj-RtOzFUtVKnxXrPv_M9hZo-8UdlTXJrg"
BOT_TOKEN    = "8738544813:AAE82mLikrBAnmW1IN6WPMv7Jiw8Rlk924U"

NUMBER_API   = "https://v2.nexus-x.site/api/v1"
NUMBER_KEY   = API_KEY
OTP_API      = "https://v2.nexus-x.site/api/v1"
OTP_KEY      = API_KEY

BASE_URL     = f"{NUMBER_API}"
HEADERS      = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
ADMIN_ID     = "6136815573"
GROUP_URL    = "https://t.me/tem_withh"
FIREBASE_URL = "https://shuvo-866aa-default-rtdb.firebaseio.com/"

REQUIRED_CHANNELS = ["@range_channele", "@tem_withh"]
FIXED_SERVICES = ["Facebook", "WhatsApp", "Telegram", "Instagram"]
OTP_PRICE = 0.40

# ===================== SESSION & BOT =====================
session = requests.Session()
session.headers.update(HEADERS)

logging.basicConfig(level=logging.ERROR, format="%(asctime)s - %(levelname)s - %(message)s")
bot = telebot.TeleBot(BOT_TOKEN, threaded=True, num_threads=20)

# ===================== IN-MEMORY STATE =====================
users           = {}
user_ranges     = {}
user_service    = {}
user_numbers    = {}       
user_countries  = {}       
received_otps   = {}
used_otps       = {}
otp_running     = {}
strd_running    = {}
withdraw_data   = {}
withdraw_status = {}       
user_names      = {}
admin_state     = {}
user_2fa_keys   = {}

# Today stats per user
today_earn      = {}       
today_otp_count = {}       
today_date      = {}       

global_used_otps = {}
service_countries = {s: [] for s in FIXED_SERVICES}

# LIVE TRAFFIC DATA
live_traffic = {s: {} for s in FIXED_SERVICES + ["Others"]}
traffic_last_reset = time.time()
OTP_GROUP_ID = -1002670575248  

COUNTRY_NAME_MAP = {
    "ivory coast": "CI", "ivory coast 2": "CI", "côte d'ivoire": "CI",
    "cote d'ivoire": "CI", "cote divoire": "CI", "guinea bissau": "GW",
    "guinea-bissau": "GW", "south korea": "KR", "north korea": "KP",
    "russia": "RU", "tanzania": "TZ", "syria": "SY", "iran": "IR",
    "vietnam": "VN", "laos": "LA", "moldova": "MD", "congo": "CG",
    "dr congo": "CD", "democratic republic of congress": "CD",
    "palestine": "PS", "kosovo": "XK", "taiwan": "TW", "cape verde": "CV",
    "east timor": "TL", "myanmar": "MM", "swaziland": "SZ", "eswatini": "SZ",
    "macau": "MO", "saint kitts": "KN", "saint lucia": "LC",
    "saint vincent": "VC", "micronesia": "FM", "curacao": "CW",
}

# ===================== KEYBOARD HELPERS =====================
def make_button(text, callback_data=None, url=None, style="primary", copy_text_val=None):
    d = {"text": text, "style": style}
    if callback_data: d["callback_data"] = callback_data
    if url: d["url"] = url
    if copy_text_val: d["copy_text"] = {"text": copy_text_val}
    return d

def build_inline_keyboard(rows):
    kb = types.InlineKeyboardMarkup()
    for row in rows:
        kb_row = []
        for d in row:
            if "url" in d:
                b = types.InlineKeyboardButton(text=d["text"], url=d["url"])
            elif "copy_text" in d:
                b = types.InlineKeyboardButton(text=d["text"], copy_text=types.CopyTextButton(text=d["copy_text"]["text"]))
            else:
                b = types.InlineKeyboardButton(text=d["text"], callback_data=d.get("callback_data", "noop"))
            if "style" in d:
                b.__dict__["style"] = d["style"]
            kb_row.append(b)
        kb.keyboard.append(kb_row)
    return kb

# ===================== FIREBASE CORE =====================
def _fb_get(path):
    try:
        r = session.get(f"{FIREBASE_URL}{path}.json", timeout=10)
        return r.json() if r.status_code == 200 else None
    except Exception: return None

def _fb_put(path, data):
    try: session.put(f"{FIREBASE_URL}{path}.json", data=json.dumps(data, ensure_ascii=False), timeout=10)
    except Exception: pass

def get_otp_price_from_firebase():
    val = _fb_get("/admin/otp_price")
    try:
        if val is not None: return float(val)
    except Exception: pass
    return OTP_PRICE

def set_otp_price_to_firebase(price):
    price = round(float(price), 2)
    _fb_put("/admin/otp_price", price)
    return price

def get_firebase_balance(uid):
    val = _fb_get(f"/users/{uid}/balance")
    try: return float(val) if val is not None else 0.0
    except Exception: return 0.0

def update_firebase_balance(uid, amount):
    uid = str(uid)
    current = get_firebase_balance(uid)
    new_bal = round(current + amount, 2)
    _fb_put(f"/users/{uid}/balance", new_bal)
    
    today_str = str(date.today())
    if today_date.get(uid) != today_str:
        today_date[uid] = today_str
        today_earn[uid] = 0.0
        today_otp_count[uid] = 0
    today_earn[uid] = round(today_earn.get(uid, 0.0) + amount, 2)
    today_otp_count[uid] = today_otp_count.get(uid, 0) + 1
    return new_bal

def set_firebase_balance(uid, val):
    uid = str(uid)
    new_bal = round(float(val), 2)
    _fb_put(f"/users/{uid}/balance", new_bal)
    return new_bal

def clear_all_balances():
    data = _fb_get("/users")
    if isinstance(data, dict):
        for uid in data: _fb_put(f"/users/{uid}/balance", 0)

def register_user(uid, name="User"):
    uid = str(uid)
    if uid not in users: users[uid] = {"balance": 0}
    if not _fb_get(f"/users/{uid}/registered"): _fb_put(f"/users/{uid}/registered", True)
    _fb_put(f"/users/{uid}/name", name)

def load_all_users_from_firebase():
    data = _fb_get("/users")
    if isinstance(data, dict):
        for uid, val in data.items():
            if uid not in users: users[uid] = {"balance": 0}
            if isinstance(val, dict) and val.get("name"): user_names[uid] = val["name"]

def load_countries_from_firebase():
    for sname in FIXED_SERVICES:
        data = _fb_get(f"/service_data/{sname}")
        if isinstance(data, list):
            service_countries[sname] = [c for c in data if isinstance(c, dict) and "name" in c and "rid" in c]
        elif isinstance(data, dict):
            service_countries[sname] = [v for v in data.values() if isinstance(v, dict) and "name" in v and "rid" in v]
        else:
            service_countries[sname] = []

def save_countries_to_firebase(service_name):
    _fb_put(f"/service_data/{service_name}", service_countries[service_name])

# Startup Loads
load_all_users_from_firebase()
load_countries_from_firebase()

# ===================== CRYPTO & EXTRACTIONS =====================
def _totp_generate(secret_b32: str, digits: int = 6, period: int = 30) -> str:
    try:
        secret_b32 = secret_b32.upper().strip().replace(" ", "")
        pad = (8 - len(secret_b32) % 8) % 8
        secret_bytes = base64.b32decode(secret_b32 + "=" * pad)
        counter = int(time.time()) // period
        counter_bytes = struct.pack(">Q", counter)
        h = hmac.new(secret_bytes, counter_bytes, hashlib.sha1).digest()
        offset = h[-1] & 0x0F
        code_int = struct.unpack(">I", h[offset:offset + 4])[0] & 0x7FFFFFFF
        return str(code_int % (10 ** digits)).zfill(digits)
    except Exception: return None

def extract_otp(message_text, phone_number=None):
    if not message_text: return None
    phone_digits = "".join(filter(str.isdigit, str(phone_number))) if phone_number else ""

    dashed_matches = re.findall(r'\b(\d{3,5}[-\s]\d{3,5})\b', message_text, re.ASCII)
    for match in dashed_matches:
        joined = re.sub(r'[-\s]', '', match)
        if joined.isdigit() and not (phone_digits and (joined in phone_digits or phone_digits in joined)) and 4 <= len(joined) <= 10:
            return joined

    spaced_matches = re.findall(r'\b(\d[\d ]{2,12}\d)\b', message_text, re.ASCII)
    for match in spaced_matches:
        joined = match.replace(" ", "")
        if joined.isdigit() and not (phone_digits and (joined in phone_digits or phone_digits in joined)) and 4 <= len(joined) <= 10:
            return joined

    keyword_patterns = [
        r'(?:code|otp|OTP|Code|verification|verify|passcode|password|কোড)[^\d]*(\d{4,8})',
        r'(\d{4,8})[^\d]*(?:is your|as your|কোড)',
    ]
    for pattern in keyword_patterns:
        match = re.search(pattern, message_text, re.IGNORECASE | re.ASCII)
        if match:
            candidate = match.group(1)
            if phone_digits and candidate in phone_digits: continue
            return candidate

    candidates = re.findall(r'\b(\d{4,10})\b', message_text, re.ASCII)
    for candidate in candidates:
        if phone_digits and (candidate in phone_digits or phone_digits in candidate or phone_digits[-10:] in candidate): continue
        if len(candidate) == 4 and candidate.startswith(('19', '20')): continue
        if 4 <= len(candidate) <= 10: return candidate

    all_digits = re.sub(r'\D', '', message_text)
    if phone_digits:
        all_digits = all_digits.replace(phone_digits, "")
        if len(phone_digits) >= 10: all_digits = all_digits.replace(phone_digits[-10:], "")
    if len(all_digits) >= 4: return all_digits[-6:] if len(all_digits) >= 6 else all_digits
    return None

def extract_country_from_otp_message(msg_text):
    if not msg_text: return None, None
    for i in range(len(msg_text) - 1):
        char1, char2 = msg_text[i], msg_text[i + 1]
        code1, code2 = ord(char1), ord(char2)
        if 0x1F1E6 <= code1 <= 0x1F1FF and 0x1F1E6 <= code2 <= 0x1F1FF:
            flag_emoji = char1 + char2
            country_code = chr(code1 - 0x1F1E6 + ord('A')) + chr(code2 - 0x1F1E6 + ord('A'))
            try:
                c = pycountry.countries.get(alpha_2=country_code)
                country_name = c.name if c else country_code
            except Exception: country_name = country_code
            return flag_emoji, country_name
    return None, None

def get_flag(country_name):
    if not country_name: return ""
    name_lower = country_name.lower().strip()
    if name_lower in COUNTRY_NAME_MAP:
        return "".join(chr(ord(x) + 127397) for x in COUNTRY_NAME_MAP[name_lower].upper())
    try:
        c = pycountry.countries.lookup(country_name)
        return "".join(chr(ord(x) + 127397) for x in c.alpha_2.upper())
    except Exception: pass
    try:
        results = pycountry.countries.search_fuzzy(country_name)
        if results: return "".join(chr(ord(x) + 127397) for x in results[0].alpha_2.upper())
    except Exception: pass
    return ""

def _normalize_inbox_items(data):
    items = []
    raw = []
    if isinstance(data, list): raw = data
    elif isinstance(data, dict):
        raw = data.get("data")
        if isinstance(raw, dict): raw = raw.get("otps", [])
        if not isinstance(raw, list): raw = data.get("otps") or data.get("result") or data.get("inbox") or []
    
    for entry in raw:
        if not isinstance(entry, dict): continue
        txt_field = entry.get("text") or entry.get("body") or entry.get("full_text") or entry.get("console") or ""
        if "otps" in entry:
            number = entry.get("number", "")
            for sub in entry.get("otps", []):
                items.append({"otp_id": sub.get("id"), "number": number, "message": sub.get("text") or sub.get("body") or text_field})
        else:
            items.append({"otp_id": entry.get("id") or entry.get("otp_id"), "number": entry.get("number", ""), "message": txt_field})
    return items

def is_joined(user_id):
    try:
        for ch in REQUIRED_CHANNELS:
            m = bot.get_chat_member(ch, user_id)
            if m.status not in ["member", "administrator", "creator"]: return False
        return True
    except Exception: return False

def is_admin(uid):
    return str(uid) == ADMIN_ID

def safe_execute(func):
    def wrapper(*args, **kwargs):
        try: return func(*args, **kwargs)
        except Exception: logging.error(traceback.format_exc())
    return wrapper

# ===================== TRAFFIC LOGIC =====================
def update_traffic(service_name, country, flag):
    global traffic_last_reset, live_traffic
    if time.time() - traffic_last_reset > 900:
        live_traffic = {s: {} for s in FIXED_SERVICES + ["Others"]}
        traffic_last_reset = time.time()
    if service_name not in live_traffic: service_name = "Others"
    key = f"{flag} {country}"
    live_traffic[service_name][key] = live_traffic[service_name].get(key, 0) + 1

def get_traffic_display():
    display = "📊 LIVE TRAFFIC\n\n"
    for service in FIXED_SERVICES + ["Others"]:
        display += f"{service}\n"
        if not live_traffic[service]:
            display += "  (কোনো OTP নেই)\n"
        else:
            sorted_countries = sorted(live_traffic[service].items(), key=lambda x: x[1], reverse=True)
            for country_key, count in sorted_countries[:5]:
                display += f"  {country_key} [{count}]\n"
        display += "\n"
    return display

# ===================== MARKUPS =====================
def join_markup():
    return build_inline_keyboard([
        [make_button("📢 Join Channel 1", url="https://t.me/range_channele")],
        [make_button("📢 Join Channel 2", url="https://t.me/tem_withh")],
        [make_button("✅ VERIFIED", callback_data="verify_join", style="success")]
    ])

def main_markup(uid=None):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    b1, b2 = types.KeyboardButton("GET NUMBER"), types.KeyboardButton("LIVE TRAFFIC")
    b3, b4 = types.KeyboardButton("GET 2FA CODE"), types.KeyboardButton("ADMIN SUPPORT")
    b5, b6 = types.KeyboardButton("BALANCE"), types.KeyboardButton("PROFILE")
    
    for b, s in [(b1, "primary"), (b2, "success"), (b3, "primary"), (b4, "success"), (b5, "success"), (b6, "primary")]:
        b.__dict__["style"] = s
        
    markup.row(b1, b2).row(b3, b4).row(b5, b6)
    if uid and is_admin(uid):
        bp = types.KeyboardButton("ADMIN PANEL")
        bp.__dict__["style"] = "danger"
        markup.add(bp)
    return markup

def service_menu_markup():
    return build_inline_keyboard([[make_button(s.upper(), callback_data=f"sv_{s}")] for s in FIXED_SERVICES])

def country_menu_markup(service_name):
    rows = []
    countries = service_countries.get(service_name, [])
    if not countries:
        rows.append([make_button("⚠️ কোনো দেশ এড হয়নি", callback_data="noop", style="danger")])
    else:
        for idx, c in enumerate(countries):
            flag = get_flag(c["name"])
            rows.append([make_button(f"{flag} {c['name']}" if flag else c["name"], callback_data=f"ct_{service_name}__{idx}", style="success")])
    rows.append([make_button("🔙 Back", callback_data="back_to_services", style="danger")])
    return build_inline_keyboard(rows)

def otp_result_markup(otp):
    return build_inline_keyboard([[make_button(otp, style="success", copy_text_val=otp)]])

def profile_markup():
    return build_inline_keyboard([[make_button("📩 OTP PRICE", callback_data="otp_price", style="success"), make_button("🔙 BACK", callback_data="back_to_main", style="danger")]])

def balance_markup(balance):
    return build_inline_keyboard([[make_button("💶 WITHDRAW", callback_data="withdraw", style="danger"), make_button("🔙 BACK", callback_data="back_to_main", style="primary")]])

def admin_panel_markup():
    return build_inline_keyboard([
        [make_button("🌍 Add Country", callback_data="adm_add_country", style="success"), make_button("🗑️ Del Country", callback_data="adm_del_country", style="danger")],
        [make_button("📨 User Message", callback_data="adm_user_message", style="primary"), make_button("💰 Add Money", callback_data="adm_add_money", style="success")],
        [make_button("🗑️ Money Clear", callback_data="adm_money_clear", style="danger"), make_button("💰 Change Price", callback_data="admin_change_price", style="success")],
        [make_button("👥 User Count", callback_data="adm_user_count", style="primary"), make_button("📊 All User Money", callback_data="adm_all_money", style="primary")],
        [make_button("❌ Close", callback_data="adm_close", style="danger")]
    ])

def admin_cancel_markup():
    return build_inline_keyboard([[make_button("❌ Cancel", callback_data="adm_cancel", style="danger")]])

# ===================== CHANNEL/MESSAGE HANDLERS =====================
@bot.message_handler(func=lambda m: m.chat.id == OTP_GROUP_ID, content_types=['text'])
def handle_otp_group_message(message):
    try:
        msg_text = message.text or ""
        flag, country = extract_country_from_otp_message(msg_text)
        if not flag or not country: return
        
        service_name = "Others"
        for svc in ["facebook", "whatsapp", "instagram", "telegram"]:
            if svc in msg_text.lower():
                service_name = svc.capitalize()
                break
        update_traffic(service_name, country, flag)
    except Exception as e: logging.error(f"Traffic parsing fail: {e}")

@bot.message_handler(commands=['start'])
@safe_execute
def start(message):
    uid = str(message.from_user.id)
    uname = message.from_user.username or "User"
    register_user(uid, uname)
    user_names[uid] = uname
    
    if not is_joined(message.from_user.id):
        bot.send_message(message.chat.id, "🔗 𝐂𝐡𝐚𝐧𝐧𝐞𝐥 𝐕𝐞𝐫𝐢fic𝐚𝐭𝐢𝐨𝐧 𝐑𝐞𝐪𝐮𝐢𝐫𝐞 Required\n\n📢 আপনাকে আমাদের চ্যানেলে Join করতে হবে।", reply_markup=join_markup())
        return
        
    welcome_text = "👋𓆩𓆩WELCOME TO OTP SERViCE𓆪𓆪\n ̅ ̅ ̅ ̅ ̅ ̅ ̅ ̅ ̅ ̅ ̅ ̅ ̅ ̅ ̅\n\n🤖 WELCOME TO TEAM WITH 3.0 \n\n ̅ ̅ ̅ ̅ ̅ ̅ ̅ ̅ ̅ ̅ ̅ ̅ ̅ ̅ ̅\n\n♾️ POWERED BY Shuvoᯓᡣ𐭩"
    bot.send_message(message.chat.id, welcome_text, reply_markup=main_markup(uid))

# ===================== ENGINE PROCESSING (OTP SEARCH) =====================
def auto_check_otp(chat_id, phone_numbers, number_msg_id=None):
    if otp_running.get(chat_id): return
    otp_running[chat_id] = True
    used_otps.setdefault(chat_id, [])
    global_used_otps.setdefault(chat_id, set())
    start_time = time.time()

    while True:
        if time.time() - start_time > 1800:
            otp_running[chat_id] = False
            if number_msg_id:
                try: bot.delete_message(chat_id, number_msg_id)
                except Exception: pass
            bot.send_message(chat_id, "⏰ Time Expired!", reply_markup=build_inline_keyboard([[make_button("📱 GET NUMBER", callback_data="get_number_menu")]]))
            return
            
        current_nums = user_numbers.get(chat_id, [])
        if not current_nums or not any(n in current_nums for n in phone_numbers):
            otp_running[chat_id] = False
            return

        try:
            api_id = user_ranges.get(chat_id)
            if not api_id:
                time.sleep(5); continue
                
            r = requests.get(f"{OTP_API}/numbers/{api_id}", headers={"Authorization": f"Bearer {OTP_KEY}"}, timeout=12)
            for item in _normalize_inbox_items(r.json()):
                api_num = "".join(filter(str.isdigit, str(item.get("number", ""))))
                matched_num, matched_idx = None, None
                for idx, num in enumerate(phone_numbers):
                    cur = "".join(filter(str.isdigit, str(num)))
                    if api_num and cur and (api_num in cur or cur in api_num):
                        matched_num, matched_idx = num, idx
                        break
                if not matched_num: continue
                
                msg_id = item.get("otp_id") or item.get("id")
                if not msg_id or msg_id in global_used_otps[chat_id] or msg_id in used_otps[chat_id]: continue
                
                used_otps[chat_id].append(msg_id)
                global_used_otps[chat_id].add(msg_id)
                otp = extract_otp(item.get("message", ""), matched_num)
                if not otp: continue
                
                price = get_otp_price_from_firebase()
                update_firebase_balance(chat_id, price)
                
                countries_list = user_countries.get(chat_id, [])
                det_country = countries_list[matched_idx] if matched_idx < len(countries_list) else "Unknown"
                flag = get_flag(det_country)
                
                service = user_service.get(chat_id, "Others")
                update_traffic(service, det_country, flag)
                
                text = f"╭──────────────╮\n📩 {service} OTP  ✅\n╰──────────────╯\n{flag or '🌍'}  : {matched_num}\n💸 𝐄𝐚𝐫𝐧𝐞𝐝 : {price:.2f} ৳\n✅ 𝐒𝐭𝐚𝐭𝐮𝐬 : 𝐒𝐮𝐜𝐜𝐞𝐬𝐬"
                bot.send_message(chat_id, text, reply_markup=otp_result_markup(otp))
        except Exception: pass
        time.sleep(3)

def process_number(message, edit_msg=None, service_name="Unknown"):
    chat_id = message.chat.id
    load_countries_from_firebase()
    ranges_list = [item.get("rid") for item in service_countries.get(service_name, []) if item.get("rid")]
    rid = random.choice(ranges_list) if ranges_list else "8801"

    status_id = edit_msg.message_id if edit_msg else bot.send_message(chat_id, "⏳ PLEASE WAIT...\n🔄 NUMBER GENERATING...").message_id
    nums, countries = [], []

    for attempt in range(4):
        try:
            r = requests.post(f"{NUMBER_API}/numbers", json={"range": rid, "sid": "wa", "no_plus": False, "national": False}, timeout=12)
            d = r.json()
            if d.get("ok"):
                nums.append(str(d.get("number")).replace("+", ""))
                countries.append(d.get("country", "Unknown"))
                user_ranges[chat_id] = d.get("id")
                break
            time.sleep(2)
        except Exception: time.sleep(2)

    if not nums:
        bot.edit_message_text("⚠️ এখন নাম্বার পাওয়া যাচ্ছে না, একটু পরে আবার চেষ্টা করুন।", chat_id, status_id, reply_markup=build_inline_keyboard([[make_button("🔄 আবার চেষ্টা করুন", callback_data=f"sv_{service_name}", style="danger")]]))
        return

    otp_running[chat_id] = False
    time.sleep(0.2)
    user_numbers[chat_id] = nums
    user_countries[chat_id] = countries
    user_service[chat_id] = service_name
    
    back_cb = f"back_to_services"
    kb = build_inline_keyboard(
        [[make_button(f"{get_flag(countries[i])}  +{num}", style="primary", copy_text_val=f"+{num}")] for i, num in enumerate(nums)] +
        [[make_button(f"{get_flag(countries[0])} {countries[0]}", callback_data="noop", style="success"), make_button(f"📲 {service_name.upper()}", callback_data="noop", style="success")]] +
        [[make_button("🔄 Change Number", callback_data=f"sv_{service_name}", style="primary"), make_button("🔐 OTP GROUP", url=GROUP_URL, style="primary")], [make_button("🔙 BACK", callback_data=back_cb, style="danger")]]
    )
    bot.edit_message_text("⏳ WAITING FOR OTP...", chat_id, status_id, reply_markup=kb)
    Thread(target=auto_check_otp, args=(chat_id, list(nums), status_id), daemon=True).start()

# ===================== TEXT CORE COMMANDS =====================
@bot.message_handler(func=lambda m: True)
@safe_execute
def handle_text(message):
    uid = str(message.from_user.id)
    txt = message.text
    register_user(uid, message.from_user.username or "User")

    if uid in admin_state and admin_state[uid].get("step"):
        handle_admin_state(message, uid, txt)
        return

    if txt == "GET NUMBER":
        bot.send_message(message.chat.id, "📱 SELECT A SERVICE", reply_markup=service_menu_markup())
    elif txt == "LIVE TRAFFIC":
        bot.send_message(message.chat.id, "📡 𝐋𝐢𝐯𝐞 𝐓𝐫𝐚𝐟𝐟𝐢𝐂 𝐂𝐡𝐚𝐧𝐧𝐞𝐥 👇", reply_markup=build_inline_keyboard([[make_button("📊 LIVE TRAFFIC", url=GROUP_URL), make_button("❌ CANCEL", callback_data="back_to_main", style="danger")]]))
    elif txt == "GET 2FA CODE":
        msg = bot.send_message(message.chat.id, "🔐 𝐄𝐧𝐭𝐞𝐫 𝐲𝐨𝐮𝐫 𝟐𝐅𝐀 𝐜𝐨𝐝𝐞.\n🔑 𝐄𝐱𝐚𝐦𝐩𝐥𝐞: 𝐉𝐁𝐒𝐖𝐘𝟑𝐃𝐏𝐄𝐇𝐏𝐊𝟑𝐏𝐗𝐏")
        bot.register_next_step_handler(msg, process_2fa)
    elif txt == "PROFILE":
        bal = get_firebase_balance(uid)
        t_earn = today_earn.get(uid, 0.0) if today_date.get(uid) == str(date.today()) else 0.0
        t_count = today_otp_count.get(uid, 0) if today_date.get(uid) == str(date.today()) else 0
        bot.send_message(message.chat.id, f"👤 𝐘𝐎𝐔𝐑 𝐏𝐑𝐎𝐅𝐈𝐋𝐄\n\n💸 𝐓𝐨𝐝𝐚𝐲 𝐄𝐚𝐫𝐧 : {t_earn:.2f} 𝐓𝐊\n📩 𝐓𝐨𝐝𝐚𝐲 𝐎𝐓𝐏 : {t_count}\n🆔 𝐈𝐃 : {uid}\n💰 𝐁𝐚𝐥𝐚𝐧𝐜𝐞 : {bal:.2f} 𝐓𝐊\n✅ 𝐒𝐭𝐚𝐭𝐮𝐬 : 𝐀𝐂𝐓𝐈𝐕𝐄", reply_markup=profile_markup())
    elif txt == "BALANCE":
        bot.send_message(message.chat.id, f"💳 𝐘𝐎𝐔𝐑 𝐁𝐀𝐋𝐀𝐍𝐂𝐄\n\n💰 𝐁𝐀𝐋𝐀𝐍𝐂𝐄 {get_firebase_balance(uid):.2f} 𝐓𝐊", reply_markup=balance_markup(get_firebase_balance(uid)))
    elif txt == "ADMIN PANEL" and is_admin(uid):
        bot.send_message(message.chat.id, "🏠 ADMIN PANEL", reply_markup=admin_panel_markup())

# ===================== ADMIN FINITE STATES =====================
def handle_admin_state(message, uid, txt):
    state = admin_state.get(uid, {})
    step = state.get("step")
    cid = message.chat.id

    if step == "add_country_name":
        admin_state[uid]["country"] = txt
        admin_state[uid]["step"] = "add_country_rid"
        msg = bot.send_message(cid, f"✅ দেশের নাম: {txt}\n\nএখন রেন্জ (RID) দিন:", reply_markup=admin_cancel_markup())
        bot.register_next_step_handler(msg, lambda m: handle_admin_state(m, uid, m.text))
    elif step == "add_country_rid":
        svc, cname = state.get("service"), state.get("country")
        service_countries[svc].append({"name": cname, "rid": txt})
        save_countries_to_firebase(svc)
        admin_state.pop(uid, None)
        bot.send_message(cid, "✅ সফলভাবে এড হয়েছে!", reply_markup=admin_panel_markup())
    elif step == "change_price":
        try:
            set_otp_price_to_firebase(float(txt))
            admin_state.pop(uid, None)
            bot.send_message(cid, f"✅ OTP মূল্য আপডেট হয়েছে: {float(txt):.2f} TK", reply_markup=admin_panel_markup())
        except Exception: bot.send_message(cid, "❌ সঠিক সংখ্যা দিন।")

def process_2fa(message):
    secret = message.text.strip().replace(" ", "")
    user_2fa_keys[message.chat.id] = secret
    code = _totp_generate(secret)
    if code:
        bot.send_message(message.chat.id, f"🔐 YOUR 2FA CODE ✅\n\n🔑 Code : {code}", reply_markup=build_inline_keyboard([[make_button(code, style="success", copy_text_val=code)]]))
    else:
        bot.send_message(message.chat.id, "❌ Invalid Secret Key!")

# ===================== CALLBACK CORE QUERY =====================
@bot.callback_query_handler(func=lambda call: True)
@safe_execute
def handle_query(call):
    cid = call.message.chat.id
    uid_str = str(call.from_user.id)
    
    if call.data == "verify_join":
        if is_joined(call.from_user.id):
            bot.answer_callback_query(call.id, "✅ Verified Success!", show_alert=True)
            try: bot.delete_message(cid, call.message.message_id)
            except Exception: pass
            bot.send_message(cid, "🤖 WELCOME BACK TO ENGINE", reply_markup=main_markup(uid_str))
        else:
            bot.answer_callback_query(call.id, "❌ চ্যানেলে Join করুন তারপর Verified করুন!", show_alert=True)
            
    elif call.data.startswith("sv_"):
        svc = call.data.replace("sv_", "")
        process_number(call.message, edit_msg=call.message, service_name=svc)
        
    elif call.data == "adm_close" and is_admin(uid_str):
        admin_state.pop(uid_str, None)
        bot.edit_message_text("✅ Admin Panel বন্ধ।", cid, call.message.message_id)
        
    elif call.data == "adm_add_country" and is_admin(uid_str):
        kb = build_inline_keyboard([[make_button(s, callback_data=f"adm_svc_add_{s}")] for s in FIXED_SERVICES] + [[make_button("❌ Cancel", callback_data="adm_cancel", style="danger")]])
        bot.edit_message_text("🌍 কোন সার্ভিসে দেশ এড করবেন?", cid, call.message.message_id, reply_markup=kb)
        
    elif call.data.startswith("adm_svc_add_") and is_admin(uid_str):
        svc = call.data.replace("adm_svc_add_", "")
        admin_state[uid_str] = {"step": "add_country_name", "service": svc}
        msg = bot.send_message(cid, f"📝 {svc} — দেশের নাম লিখুন:")
        bot.register_next_step_handler(msg, lambda m: handle_admin_state(m, uid_str, m.text))
        
    elif call.data == "admin_change_price" and is_admin(uid_str):
        admin_state[uid_str] = {"step": "change_price"}
        bot.send_message(cid, "💰 নতুন OTP মূল্য কত হবে? (যেমন: 0.60)")
        
    elif call.data == "adm_cancel":
        admin_state.pop(uid_str, None)
        bot.edit_message_text("⚙️ ADMIN PANEL", cid, call.message.message_id, reply_markup=admin_panel_markup())
        
    elif call.data == "back_to_main":
        bot.edit_message_text("🤖 Main Menu", cid, call.message.message_id)
        
    else: bot.answer_callback_query(call.id)

# ===================== INIT ENGINE =====================
if __name__ == '__main__':
    keep_alive()
    print("Engine Core Connected Successfully.")
    while True:
        try: bot.polling(none_stop=True, timeout=60, long_polling_timeout=30)
        except Exception: time.sleep(3)
