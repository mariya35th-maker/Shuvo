#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ✅ COMPLETE NUMBER BOT - সম্পূর্ণভাবে Nexus API integrate করা

import telebot
import requests
import json
import re
import threading
import time
import logging
from flask import Flask
from threading import Thread
from telebot import types
from datetime import datetime

# ===================== FLASK KEEP-ALIVE =====================
app = Flask('')

@app.route('/')
def home():
    return "Bot Running - Nexus API"

def keep_alive():
    Thread(target=lambda: app.run(host='0.0.0.0', port=8080), daemon=True).start()

# ===================== ✅ NEXUS API CONFIG =====================
API_KEY      = "nx_2KxBsj-RtOzFUtVKnxXrPv_M9hZo-8UdlTXJrg"
BOT_TOKEN    = "8738544813:AAEVERnaxuHKkYJ15XdJ0i1H1pdWpxknapQ"
BASE_URL     = "https://v2.nexus-x.site/api/v1/numbers"
HEADERS      = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
ADMIN_ID     = "6136815573"
FIREBASE_URL = "https://shuvo-866aa-default-rtdb.firebaseio.com/"

REQUIRED_CHANNELS = ["@range_channele", "@tem_withh"]
FIXED_SERVICES = ["Facebook", "WhatsApp", "Telegram", "Instagram"]
OTP_PRICE = 0.40

# ===================== SESSION & BOT =====================
session = requests.Session()
session.headers.update(HEADERS)

logging.basicConfig(level=logging.ERROR)
bot = telebot.TeleBot(BOT_TOKEN, threaded=True, num_threads=20)

# ===================== STATE =====================
users = {}
user_numbers = {}
user_service = {}
received_otps = {}
otp_running = {}
user_state = {}
api_ids = {}  # Nexus API IDs store করতে

# ===================== ✅ COUNTRY FLAG FUNCTION =====================
def get_country_flag(phone_number):
    """দেশ detect করে পতাকা রিটার্ন করুন"""
    country_codes = {
        "880": "🇧🇩", "88": "🇧🇩",
        "92": "🇵🇰", "91": "🇮🇳", "60": "🇲🇾",
        "66": "🇹🇭", "84": "🇻🇳", "81": "🇯🇵",
        "86": "🇨🇳", "33": "🇫🇷", "44": "🇬🇧",
        "1": "🇺🇸", "90": "🇹🇷",
    }
    
    clean = re.sub(r'\D', '', str(phone_number))
    for code, flag in country_codes.items():
        if clean.startswith(code):
            return flag
    return "🌍"

# ===================== ✅ OTP EXTRACTION =====================
def extract_otp_from_nexus(otp_body):
    """Nexus API response থেকে OTP বের করুন"""
    if not otp_body:
        return None
    
    # Facebook special handling
    if "Facebook:" in otp_body and "<#>" in otp_body:
        match = re.search(r'<#>\s*(\d+)', otp_body)
        if match:
            return match.group(1)
    
    # সাধারণ pattern
    patterns = [
        r'\b(\d{6})\b',      # 6 digit
        r'(\d{3})\s*-?\s*(\d{3})',  # 123-456
        r'\b(\d{4,8})\b',    # 4-8 digit
    ]
    
    for pattern in patterns:
        match = re.search(pattern, otp_body)
        if match:
            if len(match.groups()) > 1:
                return match.group(1) + match.group(2)
            return match.group(1)
    
    return None

# ===================== ✅ OTP MESSAGE FORMAT =====================
def format_otp_message(phone_number, service, otp, earned=0.40):
    """সঠিক ফরম্যাটে OTP মেসেজ পতাকা সহ"""
    flag = get_country_flag(phone_number)
    
    return (
        f"╭──────────────╮\n"
        f"📩 {service} OTP ✅\n"
        f"╰──────────────╯\n"
        f"{flag}  {phone_number}\n"
        f"💸 𝐄𝐚𝐫𝐧𝐞𝐝 : {earned} ৳\n"
        f"✅ 𝐒𝐭𝐚𝐭𝐮𝐬 : 𝐒𝐮𝐜𝐜𝐞𝐬𝐬"
    )

# ===================== /START =====================
@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id
    
    verify_text = "🔐 এই চ্যানেলগুলোতে join করুন:\n\n"
    verify_text += "1️⃣ https://t.me/range_channele\n"
    verify_text += "2️⃣ https://t.me/tem_withh\n\n"
    verify_text += "Join করার পর /strd দিন"
    
    bot.send_message(chat_id, verify_text)

# ===================== /STRD =====================
@bot.message_handler(commands=['strd'])
def strd_command(message):
    chat_id = message.chat.id
    
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(types.KeyboardButton("📱 GET NUMBER"))
    kb.add(types.KeyboardButton("💸 WITHDRAWAL"))
    kb.add(types.KeyboardButton("📊 PROFILE"))
    
    bot.send_message(chat_id, "✅ চ্যানেল যাচাই সফল!\n\n📋 মেনু:", reply_markup=kb)

# ===================== GET NUMBER =====================
@bot.message_handler(func=lambda msg: msg.text == "📱 GET NUMBER")
def get_number(message):
    chat_id = message.chat.id
    
    kb = types.InlineKeyboardMarkup()
    for service in FIXED_SERVICES:
        kb.add(types.InlineKeyboardButton(service, callback_data=f"service:{service}"))
    
    bot.send_message(chat_id, "🎯 সেবা বেছে নিন:", reply_markup=kb)

# ===================== ✅ CALLBACK - SERVICE SELECT =====================
@bot.callback_query_handler(func=lambda call: call.data.startswith("service:"))
def service_callback(call):
    service = call.data.split(":")[1]
    chat_id = call.message.chat.id
    
    user_service[chat_id] = service
    
    status_msg = bot.edit_message_text(
        f"⏳ {service} নাম্বার পাচ্ছি...",
        chat_id,
        call.message.message_id
    )
    
    # ✅ Nexus API থেকে নাম্বার পান
    try:
        params = {
            "range": "bd",
            "sid": service.lower(),
            "no_plus": False,
            "national": False
        }
        
        r = session.get(BASE_URL, params=params, timeout=10)
        data = r.json()
        
        if data.get("ok") and data.get("number"):
            phone_number = data.get("number")
            api_id = data.get("id")
            
            user_numbers[chat_id] = phone_number
            api_ids[chat_id] = api_id
            
            bot.edit_message_text(
                f"✅ নাম্বার: {phone_number}\n\n⏳ OTP অপেক্ষা করছি...",
                chat_id,
                call.message.message_id
            )
            
            # OTP চেক শুরু করুন
            check_otp_loop(chat_id, api_id, phone_number, service, call.message.message_id)
        else:
            bot.edit_message_text(
                "❌ নাম্বার পাওয়া যাচ্ছে না!",
                chat_id,
                call.message.message_id
            )
    
    except Exception as e:
        bot.edit_message_text(
            f"❌ Error: {str(e)}",
            chat_id,
            call.message.message_id
        )

# ===================== ✅ OTP CHECK LOOP =====================
def check_otp_loop(chat_id, api_id, phone_number, service, msg_id, timeout=120):
    """Nexus API থেকে OTP চেক করা"""
    
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            # ✅ Nexus API থেকে OTP পান
            r = session.get(f"{BASE_URL}/{api_id}", timeout=10)
            data = r.json()
            
            if data.get("ok") and data.get("otps") and len(data["otps"]) > 0:
                otp_obj = data["otps"][0]
                
                # body, text, full_text, console যেকোনো একটি থেকে OTP বের করুন
                otp_text = otp_obj.get("body") or otp_obj.get("text") or otp_obj.get("full_text") or otp_obj.get("console")
                otp = extract_otp_from_nexus(otp_text)
                
                if otp:
                    # ✅ সঠিক ফরম্যাটে OTP মেসেজ পাঠান
                    otp_msg = format_otp_message(phone_number, service, otp, OTP_PRICE)
                    
                    try:
                        bot.edit_message_text(otp_msg, chat_id, msg_id)
                    except:
                        bot.send_message(chat_id, otp_msg)
                    
                    return
            
            time.sleep(5)
        
        except Exception as e:
            logging.error(f"OTP Error: {e}")
            time.sleep(5)
    
    # Timeout
    try:
        bot.edit_message_text(
            "❌ OTP পাওয়া যাচ্ছে না (Timeout)",
            chat_id,
            msg_id
        )
    except:
        bot.send_message(chat_id, "❌ OTP পাওয়া যাচ্ছে না (Timeout)")

# ===================== RUN =====================
if __name__ == "__main__":
    keep_alive()
    
    print("=" * 50)
    print("✅ FINAL COMPLETE BOT - NEXUS API")
    print("=" * 50)
    print(f"✅ BOT_TOKEN: {BOT_TOKEN[:20]}...")
    print(f"✅ API_KEY: {API_KEY[:20]}...")
    print(f"✅ BASE_URL: {BASE_URL}")
    print(f"✅ FIREBASE: {FIREBASE_URL}")
    print("=" * 50)
    print("🚀 Bot প্রস্তুত এবং চলছে...\n")
    
    bot.infinity_polling()
