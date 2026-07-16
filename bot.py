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

# ===================== কনফিগারেশন (আপনার দেওয়া নতুন তথ্য) =====================
API_KEY      = "nx_2KxBsj-RtOzFUtVKnxXrPv_M9hZo-8UdlTXJrg" # নতুন API KEY
BOT_TOKEN    = "8738544813:AAEVERnaxuHKkYJ15XdJ0i1H1pdWpxknapQ" # নতুন বট টোকেন
FIREBASE_URL = "https://shuvo-866aa-default-rtdb.firebaseio.com/" # নতুন Firebase URL

# Nexus-X API URL
GET_NUM_URL  = "https://v2.nexus-x.site/api/v1/numbers"
# OTP চেক করার জন্য পুরনো BASE_URL (যদি সাকসেস ওটিপি আগের এপিআই থেকে আসে)
BASE_URL     = "https://api.2oo9.cloud/MXS47FLFX0U/tness/@public/api" 

ADMIN_ID     = "6136815573"
GROUP_URL    = "https://t.me/tem_withh"
REQUIRED_CHANNELS = ["@range_channele", "@tem_withh"]
FIXED_SERVICES = ["Facebook", "WhatsApp", "Telegram", "Instagram"]

# সার্ভিস অনুযায়ী SID ম্যাপিং (Nexus-X এর জন্য)
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
# নতুন API এর জন্য হেডার লজিক
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

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

def register_user(uid, name="User"):
    uid = str(uid)
    if not _fb_get(f"/users/{uid}/registered"):
        _fb_put(f"/users/{uid}/registered", True)
    _fb_put(f"/users/{uid}/name", name)

def load_countries_from_firebase():
    for sname in FIXED_SERVICES:
        data = _fb_get(f"/service_data/{sname}")
        if isinstance(data, list): service_countries[sname] = data
        elif isinstance(data, dict): service_countries[sname] = list(data.values())

# [বাকি সব হেল্পার ফাংশন এবং মার্কআপ আগের মতোই থাকবে...]

# ===================== NUMBER PROCESSING (নতুন API লজিক) =====================
def process_number(message, edit_msg=None, service_name="WhatsApp", rid=None):
    chat_id = message.chat.id
    if rid is None:
        rid = user_ranges.get(chat_id) or message.text

    loading_text = "⏳ PLEASE WAIT...\n🔄 NUMBER GENERATING..."
    status_id = bot.edit_message_text(loading_text, chat_id, edit_msg.message_id).message_id if edit_msg else bot.send_message(chat_id, loading_text).message_id

    nums = []
    countries = []
    
    # SID নির্বাচন (ডিফল্ট WhatsApp বা 'wa')
    sid = SID_MAP.get(service_name, "wa")
    
    # Nexus-X API লজিক অনুযায়ী ২ বার রিকোয়েস্ট (আপনার ২ নাম্বারের লজিক রাখতে)
    for _ in range(2):
        try:
            payload = {
                "range": str(rid),
                "sid": sid,
                "no_plus": False,
                "national": False
            }
            # হেডার সরাসরি এখানেই ব্যবহার করা হলো আপনার দেওয়া লজিক অনুযায়ী
            r = requests.post(GET_NUM_URL, headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}, json=payload, timeout=15)
            if r.status_code == 201 or r.status_code == 200:
                data = r.json()
                full_num = str(data.get("number")).replace("+", "")
                if full_num and full_num not in nums:
                    nums.append(full_num)
                    countries.append(data.get("country", "Unknown"))
        except:
            pass
        time.sleep(1)

    if not nums:
        bot.edit_message_text("⚠️ নাম্বার পাওয়া যায়নি। রেঞ্জ চেক করুন বা আবার চেষ্টা করুন।", chat_id, status_id)
        return

    # স্টেট সেভ
    user_numbers[chat_id] = nums
    user_countries[chat_id] = countries
    user_ranges[chat_id] = rid
    user_service[chat_id] = service_name
    
    # UI আপডেট
    flag = "".join(chr(ord(x) + 127397) for x in "BD") # ডিফল্ট ফ্ল্যাগ বা ডাইনামিক লজিক
    msg_text = "⏳ WAITING FOR OTP..."
    
    # বাটন তৈরি
    rows = []
    for n in nums:
        rows.append([types.InlineKeyboardButton(text=f"📞 +{n}", copy_text=types.CopyTextButton(text=f"+{n}"))])
    rows.append([types.InlineKeyboardButton(text="🔄 Change Number", callback_data="change_num")])
    kb = types.InlineKeyboardMarkup(keyboard=rows)

    bot.edit_message_text(msg_text, chat_id, status_id, reply_markup=kb)
    
    # OTP চেক থ্রেড স্টার্ট (পুরনো সিস্টেম অনুযায়ী)
    threading.Thread(target=auto_check_otp, args=(chat_id, list(nums), status_id), daemon=True).start()

# [বাকি সব ফাংশন যেমন: auto_check_otp, handle_text, callback_query_handler আগের মতোই থাকবে...]

# নোট: আমি শুধুমাত্র আপনার দেওয়া API লজিক এবং ক্রেডেনশিয়ালগুলো ইন্টিগ্রেট করে দিয়েছি। 
# বাকি ফাংশনগুলো আগের কোড থেকে কপি করে এখানে যুক্ত করে নিলে আপনার বট পুরোপুরি রান হবে।

def run_bot():
    load_countries_from_firebase()
    keep_alive()
    while True:
        try:
            bot.polling(none_stop=True, interval=0, timeout=60)
        except Exception:
            time.sleep(2)

if __name__ == "__main__":
    run_bot()
