#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import telebot
import requests
import json
import threading
import time
import logging
import re
from flask import Flask
from threading import Thread
from telebot import types
from datetime import datetime

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

FIXED_SERVICES = ["Facebook", "WhatsApp", "Telegram", "Instagram"]

# ===================== SESSION & BOT =====================
session = requests.Session()
session.headers.update(HEADERS)

logging.basicConfig(level=logging.ERROR)
bot = telebot.TeleBot(BOT_TOKEN, threaded=True, num_threads=20)

# ===================== STATE =====================
user_state = {}  # chat_id → "waiting_range" or "got_number"
user_numbers = {}  # chat_id → number
user_ranges_data = {}  # chat_id → api_id
user_service = {}  # chat_id → service_name

# ===================== MAIN MENU =====================
def main_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(types.KeyboardButton("📱 GET NUMBER"))
    kb.add(types.KeyboardButton("💰 BALANCE"))
    kb.add(types.KeyboardButton("👤 PROFILE"))
    return kb

# ===================== /START =====================
@bot.message_handler(commands=['start'])
def start(message):
    welcome_text = (
        "👋𓆩𓆩WELCOME TO OTP SERViCE𓆪𓆪\n"
        " ̅ ̅ ̅ ̅ ̅ ̅ ̅ ̅ ̅ ̅ ̅ ̅ ̅ ̅ ̅\n\n"
        "🤖 WELCOME TO TEAM WITH 3.0 \n\n"
        " ̅ ̅ ̅ ̅ ̅ ̅ ̅ ̅ ̅ ̅ ̅ ̅ ̅ ̅ ̅\n\n"
        "♾️ POWERED BY Shuvoᯓᡣ𐭩"
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=main_menu())

# ===================== /STRD =====================
@bot.message_handler(commands=['strd'])
def strd_command(message):
    welcome_text = (
        "👋𓆩𓆩WELCOME TO OTP SERViCE𓆪𓆪\n"
        " ̅ ̅ ̅ ̅ ̅ ̅ ̅ ̅ ̅ ̅ ̅ ̅ ̅ ̅ ̅\n\n"
        "🤖 WELCOME TO TEAM WITH 3.0 \n\n"
        " ̅ ̅ ̅ ̅ ̅ ̅ ̅ ̅ ̅ ̅ ̅ ̅ ̅ ̅ ̅\n\n"
        "♾️ POWERED BY Shuvoᯓᡣ𐭩"
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=main_menu())

# ===================== GET NUMBER - SERVICE SELECT =====================
@bot.message_handler(func=lambda msg: msg.text == "📱 GET NUMBER")
def get_number(message):
    chat_id = message.chat.id
    user_state[chat_id] = "waiting_service"
    
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
    user_state[chat_id] = "waiting_range"
    
    # Range চাইবে
    bot.edit_message_text(
        f"✅ সেবা: {service}\n\n🌍 রেঞ্জ দিন (যেমন: 8801):",
        chat_id,
        call.message.message_id
    )

# ===================== RANGE INPUT =====================
@bot.message_handler(func=lambda msg: user_state.get(msg.chat.id) == "waiting_range")
def handle_range(message):
    chat_id = message.chat.id
    range_val = message.text.strip()
    service = user_service.get(chat_id, "WhatsApp")
    
    if not range_val:
        bot.reply_to(message, "❌ রেঞ্জ দিন!")
        return
    
    # নাম্বার request করুন
    status_msg = bot.send_message(chat_id, f"⏳ {service} নাম্বার পাচ্ছি...")
    
    try:
        url = f"{BASE_URL}/numbers"
        payload = {
            "range": range_val,
            "sid": service.lower(),
            "no_plus": False,
            "national": False
        }
        
        response = requests.post(url, headers=HEADERS, json=payload, timeout=10)
        
        if response.status_code == 201:
            data = response.json()
            num = data.get("number", "N/A")
            api_id = data.get("id", "")
            
            user_numbers[chat_id] = num
            user_ranges_data[chat_id] = api_id
            user_state[chat_id] = "got_number"
            
            # নাম্বার দেখান এবং OTP খোঁজা শুরু করুন
            bot.edit_message_text(
                f"✅ নাম্বার: {num}\n\n⏳ OTP অপেক্ষা করছি...",
                chat_id,
                status_msg.message_id
            )
            
            # OTP চেক শুরু করুন
            check_otp_thread(chat_id, api_id, num, service, status_msg.message_id)
        else:
            bot.edit_message_text(
                f"❌ Error: {response.status_code}\n\nফিরে আসুন এবং আবার চেষ্টা করুন।",
                chat_id,
                status_msg.message_id
            )
    
    except Exception as e:
        logging.error(f"Error: {e}")
        bot.edit_message_text(
            f"❌ Error: {str(e)}",
            chat_id,
            status_msg.message_id
        )

# ===================== OTP CHECK FUNCTION =====================
def extract_otp(message_text):
    """OTP extract করুন"""
    if not message_text:
        return None
    
    # Facebook special handling
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

# ===================== RUN =====================
if __name__ == "__main__":
    keep_alive()
    
    print("=" * 50)
    print("✅ BOT STARTED")
    print("=" * 50)
    print("Flow:")
    print("1. GET NUMBER → Service Select → Range Input → Number")
    print("2. OTP Checking...")
    print("=" * 50)
    print("🚀 Ready!\n")
    
    bot.infinity_polling()
