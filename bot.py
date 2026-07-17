#!/usr/bin/env python3
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

# ===================== কনফিগারেশন =====================
API_KEY      = "nx_2KxBsj-RtOzFUtVKnxXrPv_M9hZo-8UdlTXJrg"
BOT_TOKEN    = "8738544813:AAEVERnaxuHKkYJ15XdJ0i1H1pdWpxknapQ"
BASE_URL     = "https://v2.nexus-x.site/api/v1"
HEADERS      = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
ADMIN_ID     = "6136815573"
GROUP_URL    = "https://t.me/tem_withh"
FIREBASE_URL = "https://shuvo-866aa-default-rtdb.firebaseio.com/"

REQUIRED_CHANNELS = ["@range_channele", "@tem_withh"]

FIXED_SERVICES = ["Facebook", "WhatsApp", "Telegram", "Instagram"]

SERVICE_ICONS = {
    "Facebook":  "F",
    "WhatsApp":  "💬",
    "Telegram":  "✈️",
    "Instagram": "📸",
}

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

today_earn      = {}
today_otp_count = {}
today_date      = {}

global_used_otps = {}

service_countries = {s: [] for s in FIXED_SERVICES}

# ===================== IMPORTANT FUNCTIONS =====================
def extract_otp(message_text, phone_number=None):
    """OTP extract করুন মেসেজ থেকে"""
    if not message_text:
        return None
    
    # Facebook special handling
    if "Facebook:" in message_text and "<#>" in message_text:
        match = re.search(r'<#>\s*(\d+)', message_text)
        if match:
            otp = match.group(1)
            if 4 <= len(otp) <= 10:
                return otp
    
    # General pattern
    patterns = [
        r'\b(\d{6})\b',
        r'(\d{3})\s*-?\s*(\d{3})',
        r'\b(\d{4,8})\b',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, message_text)
        if match:
            if len(match.groups()) > 1:
                return match.group(1) + match.group(2)
            return match.group(1)
    
    return None

def clean_number(num):
    """নাম্বার clean করুন"""
    if not num:
        return ""
    return re.sub(r'\D', '', str(num))

def main_markup(uid=None):
    """মেইন মেনু"""
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(types.KeyboardButton("📱 GET NUMBER"), types.KeyboardButton("🎯 LIVE TRAFFIC"))
    kb.add(types.KeyboardButton("🔐 GET 2FA CODE"), types.KeyboardButton("👨‍💼 ADMIN SUPPORT"))
    kb.add(types.KeyboardButton("💰 BALANCE"), types.KeyboardButton("👤 PROFILE"))
    kb.add(types.KeyboardButton("🔧 ADMIN PANEL"))
    return kb

# ===================== /START =====================
@bot.message_handler(commands=['start'])
def start(message):
    uid = str(message.from_user.id)
    user_name = message.from_user.username or f"{message.from_user.first_name or 'User'}"
    
    welcome_text = (
        "👋𓆩𓆩WELCOME TO OTP SERViCE𓆪𓆪\n"
        " ̅ ̅ ̅ ̅ ̅ ̅ ̅ ̅ ̅ ̅ ̅ ̅ ̅ ̅ ̅\n\n"
        "🤖 WELCOME TO TEAM WITH 3.0 \n\n"
        " ̅ ̅ ̅ ̅ ̅ ̅ ̅ ̅ ̅ ̅ ̅ ̅ ̅ ̅ ̅\n\n"
        "♾️ POWERED BY Shuvoᯓᡣ𐭩"
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=main_markup(uid))

# ===================== /STRD =====================
@bot.message_handler(commands=['strd'])
def strd_command(message):
    uid = str(message.from_user.id)
    chat_id = message.chat.id
    
    welcome_text = (
        "👋𓆩𓆩WELCOME TO OTP SERViCE𓆪𓆪\n"
        " ̅ ̅ ̅ ̅ ̅ ̅ ̅ ̅ ̅ ̅ ̅ ̅ ̅ ̅ ̅\n\n"
        "🤖 WELCOME TO TEAM WITH 3.0 \n\n"
        " ̅ ̅ ̅ ̅ ̅ ̅ ̅ ̅ ̅ ̅ ̅ ̅ ̅ ̅ ̅\n\n"
        "♾️ POWERED BY Shuvoᯓᡣ𐭩"
    )
    
    bot.send_message(chat_id, welcome_text, reply_markup=main_markup(uid))

# ===================== GET NUMBER =====================
@bot.message_handler(func=lambda msg: msg.text == "📱 GET NUMBER")
def get_number(message):
    chat_id = message.chat.id
    
    kb = types.InlineKeyboardMarkup()
    for service in FIXED_SERVICES:
        kb.add(types.InlineKeyboardButton(service, callback_data=f"service:{service}"))
    
    bot.send_message(chat_id, "🎯 সেবা বেছে নিন:", reply_markup=kb)

# ===================== SERVICE CALLBACK =====================
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
    
    # ✅ Nexus API - নাম্বার পান (এই ক্লিপটা কাজ করে)
    try:
        url = f"{BASE_URL}/numbers"
        payload = {
            "range": "8801",
            "sid": service.lower(),
            "no_plus": False,
            "national": False
        }
        
        response = requests.post(url, headers=HEADERS, json=payload)
        
        if response.status_code == 201:
            data = response.json()
            num = data.get("number", "N/A")
            api_id = data.get("id", "")
            country = data.get("country", "Unknown")
            
            user_numbers[chat_id] = [num]
            user_countries[chat_id] = [country]
            user_ranges[chat_id] = api_id
            
            bot.edit_message_text(
                f"✅ নাম্বার: {num}\n\n⏳ OTP অপেক্ষা করছি...",
                chat_id,
                call.message.message_id
            )
            
            # OTP চেক শুরু করুন
            check_otp_thread(chat_id, api_id, [num], service, call.message.message_id)
        else:
            bot.edit_message_text(
                f"❌ Error: {response.status_code}",
                chat_id,
                call.message.message_id
            )
    
    except Exception as e:
        logging.error(f"Error: {e}")
        bot.edit_message_text(
            f"❌ Error: {str(e)}",
            chat_id,
            call.message.message_id
        )

# ===================== OTP CHECK THREAD =====================
def check_otp_thread(chat_id, api_id, numbers, service, msg_id, timeout=120):
    """Nexus API থেকে OTP চেক করুন"""
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            r = requests.get(f"{BASE_URL}/numbers/{api_id}", headers=HEADERS, timeout=10)
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
                        f"🌍 {numbers[0]}\n"
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

# ===================== RUN =====================
if __name__ == "__main__":
    keep_alive()
    
    print("=" * 50)
    print("✅ BOT STARTED")
    print("=" * 50)
    print(f"✅ BOT_TOKEN: {BOT_TOKEN[:20]}...")
    print(f"✅ API_KEY: {API_KEY[:20]}...")
    print("=" * 50)
    print("🚀 Bot ready!\n")
    
    bot.infinity_polling()
