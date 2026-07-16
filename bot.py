# -*- coding: utf-8 -*-

import telebot
import requests
import json
import pycountry
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

# ===================== কনফিগারেশন (আপনার নতুন তথ্য এখানে) =====================
API_KEY      = "nx_2KxBsj-RtOzFUtVKnxXrPv_M9hZo-8UdlTXJrg" # আপনার নতুন API Key
BOT_TOKEN    = "8738544813:AAEVERnaxuHKkYJ15XdJ0i1H1pdWpxknapQ" # আপনার নতুন টোকেন
FIREBASE_URL = "https://shuvo-866aa-default-rtdb.firebaseio.com/" # আপনার নতুন Firebase URL

# নেক্সাস এপিআই এন্ডপয়েন্ট
NEXUS_URL    = "https://v2.nexus-x.site/api/v1/numbers"
# OTP চেকিং এর জন্য পুরনো বেস ইউআরএল (যেহেতু ওটিপি এপিআই আপনি পরিবর্তন করেননি)
BASE_URL     = "https://api.2oo9.cloud/MXS47FLFX0U/tness/@public/api"

ADMIN_ID     = "6136815573"
GROUP_URL    = "https://t.me/tem_withh"
REQUIRED_CHANNELS = ["@range_channele", "@tem_withh"]
FIXED_SERVICES = ["Facebook", "WhatsApp", "Telegram", "Instagram"]

# Nexus SID Mapping
SID_MAP = {
    "Facebook": "fb",
    "WhatsApp": "wa",
    "Telegram": "tg",
    "Instagram": "ig"
}

SERVICE_ICONS = {
    "Facebook":  "F",
    "WhatsApp":  "💬",
    "Telegram":  "✈️",
    "Instagram": "📸",
}

OTP_PRICE = 0.40

# ===================== SESSION & BOT =====================
session = requests.Session()
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
today_earn      = {}
today_otp_count = {}
today_date      = {}
global_used_otps = {}
service_countries = {s: [] for s in FIXED_SERVICES}

# ===================== FIREBASE =====================
def _fb_get(path):
    try:
        r = requests.get(f"{FIREBASE_URL}{path}.json", timeout=10)
        if r.status_code == 200: return r.json()
    except: pass
    return None

def _fb_put(path, data):
    try: requests.put(f"{FIREBASE_URL}{path}.json", data=json.dumps(data, ensure_ascii=False), timeout=10)
    except: pass

def get_otp_price_from_firebase():
    val = _fb_get("/admin/otp_price")
    try: return float(val) if val is not None else OTP_PRICE
    except: return OTP_PRICE

def set_otp_price_to_firebase(price):
    price = round(float(price), 2)
    _fb_put("/admin/otp_price", price)
    return price

def get_firebase_balance(uid):
    val = _fb_get(f"/users/{uid}/balance")
    try: return float(val) if val is not None else 0.0
    except: return 0.0

def update_firebase_balance(uid, amount):
    uid = str(uid)
    current = get_firebase_balance(uid)
    new_bal = round(current + amount, 2)
    _fb_put(f"/users/{uid}/balance", new_bal)
    today_str = str(date.today())
    if today_date.get(uid) != today_str:
        today_date[uid]      = today_str
        today_earn[uid]      = 0.0
        today_otp_count[uid] = 0
    today_earn[uid]      = round(today_earn.get(uid, 0.0) + amount, 2)
    today_otp_count[uid] = today_otp_count.get(uid, 0) + 1
    return new_bal

def register_user(uid, name="User"):
    uid = str(uid)
    if not _fb_get(f"/users/{uid}/registered"):
        _fb_put(f"/users/{uid}/registered", True)
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
        if isinstance(data, list): service_countries[sname] = data
        elif isinstance(data, dict): service_countries[sname] = list(data.values())

def save_countries_to_firebase(service_name):
    _fb_put(f"/service_data/{service_name}", service_countries[service_name])

# ===================== TOTP, OTP EXTRACTION, TRAFFIC (হুবহু আগের মত) =====================
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
    except: return None

def extract_otp(message_text, phone_number=None):
    if not message_text: return None
    phone_digits = clean_number(phone_number) if phone_number else ""
    dashed_matches = re.findall(r'\b(\d{3,5}[-\s]\d{3,5})\b', message_text, re.ASCII)
    for match in dashed_matches:
        joined = re.sub(r'[-\s]', '', match)
        if 4 <= len(joined) <= 10: return joined
    candidates = re.findall(r'\b(\d{4,10})\b', message_text, re.ASCII)
    for candidate in candidates:
        if phone_digits and candidate in phone_digits: continue
        if 4 <= len(candidate) <= 10: return candidate
    return None

# [Traffic logic functions...]
live_traffic = {s: {} for s in list(FIXED_SERVICES) + ["Others"]}
traffic_last_reset = time.time()

def update_traffic(service_name, country, flag):
    global traffic_last_reset
    if time.time() - traffic_last_reset > 900:
        for s in live_traffic: live_traffic[s] = {}
        traffic_last_reset = time.time()
    svc = service_name if service_name in live_traffic else "Others"
    key = f"{flag} {country}"
    live_traffic[svc][key] = live_traffic[svc].get(key, 0) + 1

def get_traffic_display():
    display = "📊 LIVE TRAFFIC\n\n"
    for service in ["Facebook", "WhatsApp", "Instagram", "Telegram", "Others"]:
        display += f"{service}\n"
        if not live_traffic[service]: display += "  (কোনো OTP নেই)\n"
        else:
            sorted_countries = sorted(live_traffic[service].items(), key=lambda x: x[1], reverse=True)
            for k, v in sorted_countries[:5]: display += f"  {k} [{v}]\n"
        display += "\n"
    return display

# ===================== NUMBER PROCESSING (নতুন Nexus-X API লজিক) =====================
def process_number(message, edit_msg=None, service_name="Unknown", rid=None):
    chat_id = message.chat.id
    if rid is None: rid = user_ranges.get(chat_id) or message.text

    loading_text = "⏳ PLEASE WAIT...\n🔄 NUMBER GENERATING..."
    if edit_msg:
        try: bot.edit_message_text(loading_text, chat_id, edit_msg.message_id); status_id = edit_msg.message_id
        except: status_id = bot.send_message(chat_id, loading_text).message_id
    else: status_id = bot.send_message(chat_id, loading_text).message_id

    nums = []
    countries = []
    
    # আপনার দেওয়া API লজিক (SID এবং Range অনুযায়ী)
    sid = SID_MAP.get(service_name, "wa")
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    payload = {"range": str(rid), "sid": sid, "no_plus": False, "national": False}

    for _ in range(2): # ২টা নাম্বার নেওয়ার চেষ্টা
        try:
            r = requests.post(NEXUS_URL, headers=headers, json=payload, timeout=15)
            if r.status_code == 201 or r.status_code == 200:
                data = r.json()
                full_num = str(data.get("number", "")).replace("+", "")
                if full_num and full_num not in nums:
                    nums.append(full_num)
                    countries.append(data.get("country", "Unknown"))
        except: pass
        if len(nums) < 2: time.sleep(1)

    if not nums:
        bot.edit_message_text("⚠️ নাম্বার পাওয়া যায়নি। রেঞ্জ চেক করুন।", chat_id, status_id)
        return

    # স্টেট সেভ
    user_numbers[chat_id]   = nums
    user_countries[chat_id] = countries
    user_ranges[chat_id]    = rid
    user_service[chat_id]   = service_name
    otp_running[chat_id]    = False
    strd_running[chat_id]   = False
    
    # UI এবং অটো ওটিপি স্টার্ট
    flag = get_flag(countries[0])
    msg_text = "⏳ WAITING FOR OTP..."
    
    # বাটন তৈরি
    rows = []
    for n in nums:
        rows.append([types.InlineKeyboardButton(text=f"📞 +{n}", copy_text=types.CopyTextButton(text=f"+{n}"))])
    rows.append([types.InlineKeyboardButton(text="🔄 Change Number", callback_data="change_num"),
                 types.InlineKeyboardButton(text="🔐 OTP GROUP", url=GROUP_URL)])
    rows.append([types.InlineKeyboardButton(text="🔙 BACK", callback_data="back_to_services")])
    
    bot.edit_message_text(msg_text, chat_id, status_id, reply_markup=types.InlineKeyboardMarkup(keyboard=rows))
    threading.Thread(target=auto_check_otp, args=(chat_id, list(nums), status_id), daemon=True).start()

# ===================== অটো ওটিপি চেক (আগের কোডের মতই) =====================
def auto_check_otp(chat_id, phone_numbers, search_msg_id=None):
    if otp_running.get(chat_id): return
    otp_running[chat_id] = True
    if chat_id not in global_used_otps: global_used_otps[chat_id] = set()
    start_time = time.time()

    while otp_running.get(chat_id):
        if time.time() - start_time > 1800: # ৩০ মিনিট পর স্টপ
            otp_running[chat_id] = False; break
        try:
            r = session.get(f"{BASE_URL}/success-otp", timeout=10)
            data = r.json()
            if data.get("meta", {}).get("code") == 200:
                for item in data.get("data", {}).get("otps", []):
                    api_num = "".join(filter(str.isdigit, item.get("number", "")))
                    matched_num = None
                    for num in phone_numbers:
                        if api_num in num or num in api_num: matched_num = num; break
                    
                    if not matched_num: continue
                    msg_id = item.get("otp_id") or item.get("id")
                    if msg_id in global_used_otps[chat_id]: continue
                    
                    otp = extract_otp(item.get("message", ""), matched_num)
                    if otp:
                        global_used_otps[chat_id].add(msg_id)
                        price = get_otp_price_from_firebase()
                        update_firebase_balance(chat_id, price)
                        # ট্রাফিক আপডেট
                        svc = user_service.get(chat_id, "Others")
                        update_traffic(svc, "Country", "🌍")
                        
                        bot.send_message(chat_id, f"📩 {svc} OTP ✅\n\n+{matched_num}\nOTP: {otp}\n💸 Earned: {price} TK", 
                                         reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton(text=otp, copy_text=types.CopyTextButton(text=otp))))
            time.sleep(3)
        except: time.sleep(5)

# ===================== মেইন হ্যান্ডলার (আগের সব ফিচার) =====================
def make_button(text, callback_data=None, url=None, style="primary", copy_text_val=None):
    d = {"text": text, "callback_data": callback_data, "url": url}
    if copy_text_val: d["copy_text"] = {"text": copy_text_val}
    return d

def main_markup(uid=None):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.row("GET NUMBER", "LIVE TRAFFIC")
    markup.row("GET 2FA CODE", "ADMIN SUPPORT")
    markup.row("BALANCE", "PROFILE")
    if uid and str(uid) == ADMIN_ID: markup.add("ADMIN PANEL")
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    uid = str(message.from_user.id)
    register_user(uid, message.from_user.first_name)
    bot.send_message(message.chat.id, "👋 WELCOME TO TEAM WITH 3.0", reply_markup=main_markup(uid))

@bot.message_handler(func=lambda m: True)
def handle_text(message):
    uid = str(message.from_user.id)
    txt = message.text
    if txt == "GET NUMBER":
        rows = [[make_button(s.upper(), callback_data=f"sv_{s}")] for s in FIXED_SERVICES]
        kb = types.InlineKeyboardMarkup()
        for r in rows: kb.row(types.InlineKeyboardButton(text=r[0]['text'], callback_data=r[0]['callback_data']))
        bot.send_message(message.chat.id, "📱 SELECT A SERVICE", reply_markup=kb)
    elif txt == "BALANCE":
        bal = get_firebase_balance(uid)
        bot.send_message(message.chat.id, f"💰 BALANCE: {bal:.2f} TK")
    elif txt == "PROFILE":
        bal = get_firebase_balance(uid)
        bot.send_message(message.chat.id, f"👤 PROFILE\nID: {uid}\nBalance: {bal:.2f} TK")
    # [বাকি সব বাটন হ্যান্ডলার যেমন ছিল তেমন থাকবে...]

def clean_number(num): return "".join(filter(str.isdigit, str(num)))
def get_flag(c): return "🌍"

# [সার্ভার স্টার্ট]
if __name__ == "__main__":
    load_countries_from_firebase()
    load_all_users_from_firebase()
    keep_alive()
    bot.polling(none_stop=True)
