import telebot
import requests
import time
from threading import Thread
from telebot import types

# কনফিগারেশন
BOT_TOKEN = "8519014711:AAHtQCf4GX5016NF82YkIZdFT57D90GtWKU"
API_KEY = "nx_2KxBsj-RtOzFUtVKnxXrPv_M9hZo-8UdlTXJrg"

bot = telebot.TeleBot(BOT_TOKEN)

# ইউজার ডেটা স্টোর
user_orders = {}

# ওটিপি মনিটরিং ফাংশন
def monitor_otp(message, order_id):
    url = f"https://v2.nexus-x.site/api/v1/numbers/{order_id}"
    headers = {"Authorization": f"Bearer {API_KEY}"}
    
    for _ in range(240):
        try:
            res = requests.get(url, headers=headers)
            if res.status_code == 200:
                data = res.json()
                if data.get("status") == "success" and data.get("otps"):
                    otp_text = data["otps"][0].get("text")
                    # নাম্বার/ওটিপি মাস্কিং সহ আউটপুট
                    bot.reply_to(message, f"✅ ওটিপি পাওয়া গেছে:\n`{otp_text}`", parse_mode="Markdown")
                    return
        except:
            pass
        time.sleep(5)
    
    bot.reply_to(message, "⚠️ ওটিপি আসেনি (টাইম আউট)।")

# ইনলাইন বাটন ফাংশন
def get_number_markup():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔄 Change Number", callback_data="change_number"))
    return markup

# স্টার্ট কমান্ড
@bot.message_handler(commands=['start', 'sard'])
def send_welcome(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("GET NUMBER", "LIVE TRAFFIC")
    bot.send_message(message.chat.id, "👋 WELCOME TO NUMBER BOT", reply_markup=markup)

# লাইভ ট্রাফিক হ্যান্ডলার
@bot.message_handler(func=lambda message: message.text == "LIVE TRAFFIC")
def live_traffic(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔗 চ্যানেলে যান", url="https://t.me/sbvip674"))
    bot.send_message(message.chat.id, "Live traffic দেখুন 👇", reply_markup=markup)

# নাম্বার জেনারেশন হ্যান্ডলার
@bot.message_handler(func=lambda message: message.text == "GET NUMBER")
def ask_range(message):
    bot.send_message(message.chat.id, "আপনার রেন্জটি প্রদান করুন:")
    bot.register_next_step_handler(message, process_number_request)

def process_number_request(message):
    range_val = message.text
    user_orders[message.chat.id] = {"range": range_val}
    
    fetch_and_send_number(message, range_val)

def fetch_and_send_number(message, range_val):
    url = "https://v2.nexus-x.site/api/v1/numbers"
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    payload = {"range": range_val, "sid": "wa", "no_plus": False, "national": False}
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 201:
            data = response.json()
            num = data.get("number")
            order_id = data.get("id")
            user_orders[message.chat.id]["order_id"] = order_id
            
            # নাম্বারে চাপ দিলেই যেন কপি হয়, তাই ব্যাকটিক ব্যবহার
            msg = f"সফল! নাম্বার:\n`{num}`\n\nওটিপি চেক করছি..."
            bot.send_message(message.chat.id, msg, parse_mode="Markdown", reply_markup=get_number_markup())
            Thread(target=monitor_otp, args=(message, order_id)).start()
        else:
            bot.send_message(message.chat.id, "নাম্বার নিতে সমস্যা হয়েছে।")
    except Exception as e:
        bot.send_message(message.chat.id, f"এরর: {e}")

# নাম্বার পরিবর্তন হ্যান্ডলার (ডিলিট ও নতুন রিকোয়েস্ট)
@bot.callback_query_handler(func=lambda call: call.data == "change_number")
def change_number(call):
    chat_id = call.message.chat.id
    try:
        bot.delete_message(chat_id, call.message.message_id)
    except:
        pass
    
    if chat_id in user_orders:
        range_val = user_orders[chat_id]["range"]
        fetch_and_send_number(call.message, range_val)
    else:
        bot.answer_callback_query(call.id, "আগে একটি রেন্জ সেট করুন!")

bot.polling(none_stop=True)
