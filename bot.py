import telebot
import requests
import time
from threading import Thread
from telebot import types
from flask import Flask

# ১. সেশন ব্যবহার করে নেটওয়ার্ক কল ফাস্ট করা
session = requests.Session()
BOT_TOKEN = "8519014711:AAHtQCf4GX5016NF82YkIZdFT57D90GtWKU"
API_KEY = "nx_2KxBsj-RtOzFUtVKnxXrPv_M9hZo-8UdlTXJrg"

bot = telebot.TeleBot(BOT_TOKEN, threaded=True) # Threaded মোড অন
user_orders = {}

# ২. ওটিপি মনিটরিং ফাংশন ফাস্ট করা
def monitor_otp(message, order_id):
    url = f"https://v2.nexus-x.site/api/v1/numbers/{order_id}"
    headers = {"Authorization": f"Bearer {API_KEY}"}
    
    for _ in range(240):
        try:
            # সেশন ব্যবহার করে রিকোয়েস্ট
            res = session.get(url, headers=headers, timeout=5)
            if res.status_code == 200:
                data = res.json()
                if data.get("status") == "success" and data.get("otps"):
                    otp_text = data["otps"][0].get("text")
                    bot.reply_to(message, f"✅ ওটিপি পাওয়া গেছে:\n`{otp_text}`", parse_mode="Markdown")
                    return
        except:
            pass
        time.sleep(3) # টাইম কমিয়ে ৩ সেকেন্ড করা হয়েছে যেন দ্রুত কাজ করে
    bot.reply_to(message, "⚠️ ওটিপি আসেনি (টাইম আউট)।")

# ফাস্ট রেসপন্সের জন্য ইনলাইন বাটন
def get_number_markup():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔄 Change Number", callback_data="change_number"))
    return markup

# মেনু হ্যান্ডলার
@bot.message_handler(commands=['start', 'sard'])
def send_welcome(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("GET NUMBER", "LIVE TRAFFIC")
    bot.send_message(message.chat.id, "👋 WELCOME TO NUMBER BOT", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == "GET NUMBER")
def ask_range(message):
    bot.send_message(message.chat.id, "আপনার রেন্জটি প্রদান করুন:")
    bot.register_next_step_handler(message, process_number_request)

def process_number_request(message):
    range_val = message.text
    user_orders[message.chat.id] = {"range": range_val}
    # সরাসরি ফাস্ট ফেচিং শুরু
    fetch_and_send_number(message, range_val)

def fetch_and_send_number(message, range_val):
    url = "https://v2.nexus-x.site/api/v1/numbers"
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    payload = {"range": range_val, "sid": "wa", "no_plus": False, "national": False}
    try:
        # সেশন ব্যবহার করে পোস্ট রিকোয়েস্ট
        response = session.post(url, headers=headers, json=payload, timeout=10)
        if response.status_code == 201:
            data = response.json()
            num = data.get("number")
            order_id = data.get("id")
            user_orders[message.chat.id]["order_id"] = order_id
            bot.send_message(message.chat.id, f"সফল! নাম্বার:\n`{num}`\n\nওটিপি চেক করছি...", parse_mode="Markdown", reply_markup=get_number_markup())
            Thread(target=monitor_otp, args=(message, order_id)).start()
        else:
            bot.send_message(message.chat.id, "নাম্বার নিতে সমস্যা হয়েছে।")
    except Exception as e:
        bot.send_message(message.chat.id, f"এরর: {e}")

@bot.callback_query_handler(func=lambda call: call.data == "change_number")
def change_number(call):
    chat_id = call.message.chat.id
    # ডিলিট বাদে রিকুয়েস্ট ফাস্ট করা
    if chat_id in user_orders:
        fetch_and_send_number(call.message, user_orders[chat_id]["range"])
    else: bot.answer_callback_query(call.id, "আগে একটি রেন্জ সেট করুন!")

# ওয়েব সার্ভার অংশ
app = Flask(__name__)
@app.route('/')
def home(): return "Bot is running!"

if __name__ == "__main__":
    Thread(target=lambda: app.run(host='0.0.0.0', port=8080)).start()
    # লং পোলিং এনাবল করা হয়েছে ফাস্ট পারফরম্যান্সের জন্য
    bot.infinity_polling(timeout=60, long_polling_timeout=60)
