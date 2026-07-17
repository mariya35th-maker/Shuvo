#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import telebot
import requests
import json
import threading
import time
import logging
import re
import random
from flask import Flask
from threading import Thread
from telebot import types
from datetime import datetime

# ===================== FLASK KEEP-ALIVE =====================
app = Flask('')

@app.route('/')
def home():
    return "Bot Running!"

def keep_alive():
    Thread(target=lambda: app.run(host='0.0.0.0', port=8080), daemon=True).start()

# ===================== কনফিগারেশন =====================
API_KEY      = "nx_2KxBsj-RtOzFUtVKnxXrPv_M9hZo-8UdlTXJrg"
BOT_TOKEN    = "8738544813:AAEVERnaxuHKkYJ15XdJ0i1H1pdWpxknapQ"
NUMBER_API   = "https://v2.nexus-x.site/api/v1"
NUMBER_KEY   = API_KEY
OTP_API      = "https://v2.nexus-x.site/api/v1"
OTP_KEY      = API_KEY
ADMIN_ID     = "6136815573"
FIREBASE_URL = "https://shuvo-866aa-default-rtdb.firebaseio.com/"

FIXED_SERVICES = ["Facebook", "WhatsApp", "Telegram", "Instagram"]

logging.basicConfig(level=logging.ERROR)
bot = telebot.TeleBot(BOT_TOKEN, threaded=True, num_threads=20)

# ===================== STATE =====================
# প্রতিটা service এর জন্য ranges
service_ranges = {
    "Facebook": [],
    "WhatsApp": [],
    "Telegram": [],
    "Instagram": []
}

user_numbers = {}
user_ranges_data = {}
user_service = {}
admin_state = {}

# ===================== FIREBASE FUNCTIONS =====================
def load_ranges_from_firebase():
    """Firebase থেকে সব ranges load করুন"""
    try:
        r = requests.get(f"{FIREBASE_URL}/admin_ranges.json", timeout=10)
        data = r.json()
        if data:
            return data
    except:
        pass
    return {}

def save_ranges_to_firebase(service_name, ranges):
    """Firebase এ ranges save করুন"""
    try:
        payload = {
            "ranges": ranges,
            "updated_at": datetime.now().isoformat()
        }
        requests.put(
            f"{FIREBASE_URL}/admin_ranges/{service_name}.json",
            json=payload,
            timeout=10
        )
        return True
    except Exception as e:
        logging.error(f"Firebase save error: {e}")
        return False

def load_all_ranges():
    """সব service এর ranges load করুন"""
    global service_ranges
    data = load_ranges_from_firebase()
    
    for service in FIXED_SERVICES:
        if service in data and data[service].get("ranges"):
            service_ranges[service] = data[service]["ranges"]
        else:
            service_ranges[service] = []

# ===================== MAIN MENU =====================
def main_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(types.KeyboardButton("📱 GET NUMBER"))
    kb.add(types.KeyboardButton("💰 BALANCE"))
    kb.add(types.KeyboardButton("👤 PROFILE"))
    kb.add(types.KeyboardButton("🔧 ADMIN PANEL"))
    return kb

# ===================== /START & /STRD =====================
@bot.message_handler(commands=['start', 'strd'])
def welcome(message):
    welcome_text = (
        "👋𓆩𓆩WELCOME TO OTP SERViCE𓆪𓆪\n"
        " ̅ ̅ ̅ ̅ ̅ ̅ ̅ ̅ ̅ ̅ ̅ ̅ ̅ ̅ ̅\n\n"
        "🤖 WELCOME TO TEAM WITH 3.0 \n\n"
        " ̅ ̅ ̅ ̅ ̅ ̅ ̅ ̅ ̅ ̅ ̅ ̅ ̅ ̅ ̅\n\n"
        "♾️ POWERED BY Shuvoᯓᡣ𐭩"
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=main_menu())

# ===================== GET NUMBER =====================
@bot.message_handler(func=lambda msg: msg.text == "📱 GET NUMBER")
def get_number(message):
    chat_id = message.chat.id
    
    kb = types.InlineKeyboardMarkup()
    for service in FIXED_SERVICES:
        kb.add(types.InlineKeyboardButton(service, callback_data=f"svc:{service}"))
    
    bot.send_message(chat_id, "🎯 সেবা বেছে নিন:", reply_markup=kb)

# ===================== SERVICE CALLBACK =====================
@bot.callback_query_handler(func=lambda call: call.data.startswith("svc:"))
def service_callback(call):
    service = call.data.split(":")[1]
    chat_id = call.message.chat.id
    
    user_service[chat_id] = service
    
    # ✅ এই service এর ranges আছে কিনা check করুন
    if not service_ranges[service]:
        bot.edit_message_text(
            f"❌ {service} এর জন্য এখনো ranges add করা হয়নি।",
            chat_id,
            call.message.message_id
        )
        return
    
    # নাম্বার পান
    get_number_from_service(chat_id, service, call.message.message_id)

# ===================== GET NUMBER FROM SERVICE =====================
def get_number_from_service(chat_id, service, msg_id):
    """Service এর ranges থেকে নাম্বার পান"""
    
    # ✅ Service এর ranges থেকে random একটা বেছে নিন
    ranges_list = service_ranges.get(service, [])
    
    if not ranges_list:
        bot.edit_message_text(
            f"❌ কোনো ranges পাওয়া যায়নি",
            chat_id,
            msg_id
        )
        return
    
    rid = random.choice(ranges_list)
    
    bot.edit_message_text(
        f"⏳ {service} নাম্বার পাচ্ছি...\n📍 Range: {rid}",
        chat_id,
        msg_id
    )
    
    try:
        # ✅ নাম্বার allocate করুন
        response = requests.post(
            f"{NUMBER_API}/numbers",
            headers={"Authorization": f"Bearer {NUMBER_KEY}"},
            json={"range": rid, "sid": service.lower(), "no_plus": False, "national": False},
            timeout=10
        )
        
        if response.status_code == 201:
            data = response.json()
            num = data.get("number", "N/A")
            api_id = data.get("id", "")
            
            user_numbers[chat_id] = num
            user_ranges_data[chat_id] = api_id
            
            bot.edit_message_text(
                f"✅ নাম্বার: {num}\n\n⏳ OTP অপেক্ষা করছি...",
                chat_id,
                msg_id
            )
            
            # OTP চেক করুন
            check_otp_thread(chat_id, api_id, num, service, msg_id)
        else:
            bot.edit_message_text(
                f"❌ Error: {response.status_code}",
                chat_id,
                msg_id
            )
    
    except Exception as e:
        logging.error(f"Error: {e}")
        bot.edit_message_text(
            f"❌ Error: {str(e)}",
            chat_id,
            msg_id
        )

# ===================== OTP EXTRACTION =====================
def extract_otp(message_text):
    """OTP extract করুন"""
    if not message_text:
        return None
    
    # Facebook special
    if "Facebook:" in message_text and "<#>" in message_text:
        match = re.search(r'<#>\s*(\d+)', message_text)
        if match:
            return match.group(1)
    
    # General patterns
    patterns = [r'\b(\d{6})\b', r'(\d{3})\s*-?\s*(\d{3})', r'\b(\d{4,8})\b']
    
    for pattern in patterns:
        match = re.search(pattern, message_text)
        if match:
            if len(match.groups()) > 1:
                return match.group(1) + match.group(2)
            return match.group(1)
    
    return None

# ===================== OTP CHECK THREAD =====================
def check_otp_thread(chat_id, api_id, number, service, msg_id, timeout=120):
    """OTP চেক করুন"""
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            r = requests.get(
                f"{OTP_API}/numbers/{api_id}",
                headers={"Authorization": f"Bearer {OTP_KEY}"},
                timeout=10
            )
            data = r.json()
            
            if data.get("ok") and data.get("otps") and len(data["otps"]) > 0:
                otp_obj = data["otps"][0]
                otp_text = otp_obj.get("body") or otp_obj.get("text") or otp_obj.get("full_text") or otp_obj.get("console")
                otp = extract_otp(otp_text)
                
                if otp:
                    msg = (
                        f"╭──────────────╮\n"
                        f"📩 {service} OTP ✅\n"
                        f"╰──────────────╯\n"
                        f"🌍 {number}\n"
                        f"💸 𝐄𝐚𝐫𝐧𝐞𝐝 : 0.40 ৳\n"
                        f"✅ 𝐒𝐭𝐚𝐭𝐮𝐬 : 𝐒𝐮𝐜𝐜𝐞𝐬𝐬"
                    )
                    
                    try:
                        bot.edit_message_text(msg, chat_id, msg_id)
                    except:
                        bot.send_message(chat_id, msg)
                    
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

# ===================== ADMIN PANEL =====================
@bot.message_handler(func=lambda msg: msg.text == "🔧 ADMIN PANEL")
def admin_panel(message):
    uid_str = str(message.from_user.id)
    
    if uid_str != ADMIN_ID:
        bot.reply_to(message, "❌ আপনি admin নন!")
        return
    
    # Ranges load করুন
    load_all_ranges()
    
    text = "📊 ADMIN PANEL\n\n"
    text += "কোন service এ ranges add করবেন?\n\n"
    
    kb = types.InlineKeyboardMarkup()
    for service in FIXED_SERVICES:
        count = len(service_ranges.get(service, []))
        kb.add(types.InlineKeyboardButton(f"{service} ({count})", callback_data=f"adm_service:{service}"))
    
    bot.send_message(message.chat.id, text, reply_markup=kb)

# ===================== ADMIN SERVICE SELECT =====================
@bot.callback_query_handler(func=lambda call: call.data.startswith("adm_service:"))
def admin_service_select(call):
    service = call.data.split(":")[1]
    chat_id = call.message.chat.id
    uid_str = str(call.from_user.id)
    
    if uid_str != ADMIN_ID:
        return
    
    admin_state[uid_str] = {"service": service, "step": "add_range"}
    
    ranges_text = "\n".join(service_ranges.get(service, []))
    
    text = (
        f"📝 {service}\n\n"
        f"বর্তমান ranges:\n"
        f"{ranges_text if ranges_text else 'কোনো ranges নেই'}\n\n"
        f"নতুন range দিন (যেমন: 8801)"
    )
    
    bot.edit_message_text(text, chat_id, call.message.message_id)

# ===================== ADMIN INPUT HANDLER =====================
@bot.message_handler(func=lambda msg: True)
def handle_admin_input(message):
    uid_str = str(message.from_user.id)
    
    if uid_str != ADMIN_ID:
        return
    
    state = admin_state.get(uid_str)
    
    if not state or state.get("step") != "add_range":
        return
    
    service = state.get("service")
    range_val = message.text.strip()
    
    if not range_val or not range_val.isdigit():
        bot.reply_to(message, "❌ সঠিক range দিন (শুধু সংখ্যা)")
        return
    
    # ✅ Range add করুন
    if range_val not in service_ranges[service]:
        service_ranges[service].append(range_val)
        
        # Firebase এ save করুন
        save_ranges_to_firebase(service, service_ranges[service])
        
        bot.reply_to(
            message,
            f"✅ Range added: {range_val}\n\n"
            f"{service} এ এখন {len(service_ranges[service])}টা ranges আছে"
        )
    else:
        bot.reply_to(message, "⚠️ এই range ইতিমধ্যে আছে!")
    
    admin_state.pop(uid_str, None)

# ===================== RUN =====================
if __name__ == "__main__":
    keep_alive()
    load_all_ranges()
    
    print("=" * 50)
    print("✅ BOT STARTED")
    print("=" * 50)
    print("Services with separate ranges:")
    for service in FIXED_SERVICES:
        print(f"  {service}: {len(service_ranges[service])} ranges")
    print("=" * 50)
    print("🚀 Ready!\n")
    
    bot.infinity_polling()
