# -*- coding: utf-8 -*-

import requests
import time
import telebot
import pickle
import os
import re
import random
import threading
import pycountry
import phonenumbers
from phonenumbers import geocoder
from telebot import types
from flask import Flask
from threading import Thread
from datetime import datetime, timezone, timedelta

# ===================== FLASK KEEP-ALIVE =====================
app = Flask('')

@app.route('/')
def home():
    return "Bot is Running!"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run_flask, daemon=True)
    t.start()

# ===================== CONFIG =====================
BOT_TOKEN         = "8764978166:AAH5tQLO71RCoCN1qtAr6xebGxFYiRT9z4A"
CHANNEL_ID        = "-1004361188862"
API_KEY           = "MUYZ1SXYKG8"
CONSOLE_URL       = "https://api.2oo9.cloud/MXS47FLFX0U/tness/@public/api/console"
HEADERS           = {"mauthapi": API_KEY}
DB_FILE           = "otp_history.pkl"
AUTO_DELETE_SEC   = 90  # ৯০ সেকেন্ড পর অটো ডিলিট

BD_TZ = timezone(timedelta(hours=6))

def bd_time():
    return datetime.now(BD_TZ).strftime("%H:%M")

bot = telebot.TeleBot(BOT_TOKEN)
bot.remove_webhook()

# ===================== দেশ ম্যাপ =====================
COUNTRY_NAME_MAP = {
    "ivory coast": "CI", "ivory coast 2": "CI",
    "côte d'ivoire": "CI", "cote d'ivoire": "CI", "cote divoire": "CI",
    "guinea bissau": "GW", "guinea-bissau": "GW",
    "south korea": "KR", "north korea": "KP",
    "russia": "RU", "tanzania": "TZ",
    "syria": "SY", "iran": "IR",
    "vietnam": "VN", "laos": "LA",
    "moldova": "MD", "congo": "CG",
    "dr congo": "CD", "palestine": "PS",
    "taiwan": "TW", "cape verde": "CV",
    "myanmar": "MM", "eswatini": "SZ",
    "swaziland": "SZ", "east timor": "TL",
    "micronesia": "FM", "curacao": "CW",
    "kosovo": "XK", "lesotho": "LS",
    "benin": "BJ", "armenia": "AM",
    "kazakhstan": "KZ", "tajikistan": "TJ",
    "central african republic": "CF",
    "venezuela": "VE", "bolivia": "BO",
    "trinidad": "TT", "haiti": "HT",
    "cameroon": "CM", "senegal": "SN",
    "mali": "ML", "niger": "NE",
    "burkina faso": "BF", "togo": "TG",
    "ghana": "GH", "sierra leone": "SL",
    "liberia": "LR", "gambia": "GM",
    "guinea": "GN", "mauritania": "MR",
    "ethiopia": "ET", "kenya": "KE",
    "uganda": "UG", "rwanda": "RW",
    "zambia": "ZM", "zimbabwe": "ZW",
    "mozambique": "MZ", "angola": "AO",
    "malawi": "MW", "madagascar": "MG",
    "somalia": "SO", "sudan": "SD",
    "chad": "TD", "nigeria": "NG",
    "egypt": "EG", "morocco": "MA",
    "algeria": "DZ", "tunisia": "TN",
    "libya": "LY", "south africa": "ZA",
    "iraq": "IQ", "jordan": "JO",
    "saudi arabia": "SA", "yemen": "YE",
    "oman": "OM", "uae": "AE",
    "kuwait": "KW", "bahrain": "BH",
    "qatar": "QA", "lebanon": "LB",
    "pakistan": "PK", "bangladesh": "BD",
    "india": "IN", "sri lanka": "LK",
    "nepal": "NP", "indonesia": "ID",
    "philippines": "PH", "thailand": "TH",
    "malaysia": "MY", "cambodia": "KH",
    "china": "CN", "japan": "JP",
    "ukraine": "UA", "poland": "PL",
    "romania": "RO", "hungary": "HU",
    "czech": "CZ", "slovakia": "SK",
    "bulgaria": "BG", "serbia": "RS",
    "croatia": "HR", "georgia": "GE",
    "azerbaijan": "AZ", "uzbekistan": "UZ",
    "kyrgyzstan": "KG", "turkmenistan": "TM",
    "mongolia": "MN", "belarus": "BY",
    "estonia": "EE", "latvia": "LV",
    "lithuania": "LT", "mexico": "MX",
    "colombia": "CO", "peru": "PE",
    "chile": "CL", "ecuador": "EC",
    "paraguay": "PY", "uruguay": "UY",
    "cuba": "CU", "jamaica": "JM",
    "dominican": "DO", "guatemala": "GT",
    "honduras": "HN", "nicaragua": "NI",
    "costa rica": "CR", "panama": "PA",
    "el salvador": "SV", "belize": "BZ",
}

COUNTRY_LANGUAGE_MAP = {
    "VE": "Spanish", "CO": "Spanish", "MX": "Spanish", "AR": "Spanish",
    "PE": "Spanish", "CL": "Spanish", "EC": "Spanish", "BO": "Spanish",
    "PY": "Spanish", "UY": "Spanish", "CU": "Spanish", "DO": "Spanish",
    "GT": "Spanish", "HN": "Spanish", "NI": "Spanish", "CR": "Spanish",
    "PA": "Spanish", "SV": "Spanish", "BZ": "English",
    "BR": "Portuguese", "PT": "Portuguese", "AO": "Portuguese",
    "MZ": "Portuguese", "CV": "Portuguese", "GW": "Portuguese",
    "FR": "French", "BE": "French", "SN": "French", "ML": "French",
    "BF": "French", "NE": "French", "TG": "French", "BJ": "French",
    "CI": "French", "CM": "French", "CF": "French", "CD": "French",
    "CG": "French", "GA": "French", "GN": "French", "MG": "French",
    "RW": "French", "HT": "French", "DJ": "French",
    "DE": "German", "AT": "German", "CH": "German",
    "RU": "Russian", "BY": "Russian", "KZ": "Russian",
    "UA": "Ukrainian", "PL": "Polish", "RO": "Romanian",
    "CN": "Chinese", "TW": "Chinese", "HK": "Chinese",
    "JP": "Japanese", "KR": "Korean", "KP": "Korean",
    "SA": "Arabic", "EG": "Arabic", "IQ": "Arabic", "SY": "Arabic",
    "JO": "Arabic", "LB": "Arabic", "YE": "Arabic", "OM": "Arabic",
    "AE": "Arabic", "KW": "Arabic", "BH": "Arabic", "QA": "Arabic",
    "MA": "Arabic", "DZ": "Arabic", "TN": "Arabic", "LY": "Arabic",
    "SD": "Arabic", "SO": "Arabic", "MR": "Arabic",
    "IN": "Hindi", "NP": "Nepali", "BD": "Bengali",
    "PK": "Urdu", "LK": "Sinhala", "MM": "Burmese",
    "TH": "Thai", "VN": "Vietnamese", "KH": "Khmer",
    "ID": "Indonesian", "MY": "Malay", "PH": "Filipino",
    "TR": "Turkish", "AZ": "Azerbaijani", "UZ": "Uzbek",
    "TM": "Turkmen", "KG": "Kyrgyz", "TJ": "Tajik",
    "AM": "Armenian", "GE": "Georgian", "MN": "Mongolian",
    "IR": "Persian", "AF": "Dari", "IL": "Hebrew",
    "ET": "Amharic", "NG": "English", "GH": "English",
    "KE": "English", "UG": "English", "TZ": "English",
    "ZM": "English", "ZW": "English", "MW": "English",
    "ZA": "English", "NA": "English", "BW": "English",
    "LS": "English", "SL": "English", "LR": "English",
    "GM": "English", "US": "English", "GB": "English",
    "CA": "English", "AU": "English", "NZ": "English",
    "JM": "English", "TT": "English",
}

def get_alpha2(country_name):
    if not country_name:
        return None
    name_lower = country_name.lower().strip()
    if name_lower in COUNTRY_NAME_MAP:
        return COUNTRY_NAME_MAP[name_lower]
    try:
        c = pycountry.countries.lookup(country_name)
        return c.alpha_2
    except Exception:
        pass
    try:
        results = pycountry.countries.search_fuzzy(country_name)
        if results:
            return results[0].alpha_2
    except Exception:
        pass
    return None

def get_flag(country_name):
    alpha2 = get_alpha2(country_name)
    if alpha2:
        return "".join(chr(ord(x) + 127397) for x in alpha2.upper())
    return "🌐"

def get_short_code(country_name):
    alpha2 = get_alpha2(country_name)
    if alpha2:
        return f"#{alpha2.upper()}"
    return "#??"

def get_language(alpha2):
    if not alpha2:
        return "English"
    return COUNTRY_LANGUAGE_MAP.get(alpha2.upper(), "English")

def get_country_from_number(number):
    try:
        clean = re.sub(r'\D', '', str(number))
        parsed = phonenumbers.parse("+" + clean, None)
        name = geocoder.country_name_for_number(parsed, "en")
        return name if name else "Unknown"
    except Exception:
        return "Unknown"

# ===================== SERVICE DETECT =====================
def detect_service(msg):
    msg_upper = msg.upper()
    if any(k in msg_upper for k in ["FACEBOOK", "FB"]):
        return "FACEBOOK"
    if any(k in msg_upper for k in ["INSTAGRAM", "IG", "INSTA"]):
        return "INSTAGRAM"
    if any(k in msg_upper for k in ["WHATSAPP", "WA"]):
        return "WHATSAPP"
    if "TELEGRAM" in msg_upper:
        return "TELEGRAM"
    return "OTP"

# ===================== OTP EXTRACT =====================
def extract_otp(message_text, phone_number=None):
    if not message_text:
        return None
    phone_digits = re.sub(r'\D', '', str(phone_number)) if phone_number else ""
    spaced = re.findall(r'\b(\d[\d ]{2,12}\d)\b', message_text)
    for match in spaced:
        joined = match.replace(" ", "")
        if not joined.isdigit():
            continue
        if phone_digits and (joined in phone_digits or phone_digits in joined):
            continue
        if 4 <= len(joined) <= 8:
            return joined
    candidates = re.findall(r'\b(\d{4,8})\b', message_text)
    for candidate in candidates:
        if phone_digits:
            if candidate in phone_digits:
                continue
            if phone_digits.endswith(candidate):
                continue
            if phone_digits[-8:] == candidate:
                continue
        if 4 <= len(candidate) <= 8:
            return candidate
    return None

# ===================== AUTO DELETE =====================
def auto_delete(chat_id, message_id, delay=AUTO_DELETE_SEC):
    """delay সেকেন্ড পর মেসেজ ডিলিট করবে"""
    def _delete():
        time.sleep(delay)
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage"
            requests.post(url, json={
                "chat_id": chat_id,
                "message_id": message_id
            }, timeout=10)
        except Exception as e:
            print(f"[Delete Error] {e}")
    threading.Thread(target=_delete, daemon=True).start()

# ===================== Console API =====================
def get_country_info(number):
    try:
        clean_number = re.sub(r'\D', '', str(number))
        parsed_number = phonenumbers.parse("+" + clean_number, None)
        country_name = geocoder.country_name_for_number(parsed_number, "en")
        alpha2 = get_alpha2(country_name)
        flag   = get_flag(country_name)
        short  = get_short_code(country_name)
        lang   = get_language(alpha2)
        return flag, short, lang, country_name if country_name else "Unknown"
    except Exception:
        return "🌐", "#??", "English", "Unknown"

def build_message(masked_number, flag, short_code, service, lang):
    current_time = bd_time()
    return (
        f"╭────────────╮\n"
        f"│✦{masked_number}✦\n"
        f"├────────────┤\n"
        f"│{flag} {short_code} 👉{service}\n"
        f"├────────────┤\n"
        f"│⏰{current_time} #{lang}\n"
        f"╰────────────╯"
    )

RANGE_CHANNEL_URL = "https://t.me/onlineskillshub1"
PANEL_BOT_URL     = "https://t.me/forhad_number_bot"

# ===================== SEND WITH STYLED BUTTONS =====================
def send_with_styled_buttons(text, otp_code, range_clean):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHANNEL_ID,
        "text": text,
        "reply_markup": {
            "inline_keyboard": [
                [
                    {
                        "text": f"{otp_code}",
                        "copy_text": {"text": otp_code},
                        "style": "success"
                    }
                ],

                [
                    {
                        "text": "𝙽𝚄𝙼𝙱𝙴𝚁 𝙱𝙾𝚃",
                        "url": PANEL_BOT_URL,
                        "style": "primary"
                    },
                    {
                        "text": "𝙼𝙴𝚃𝙷𝙾𝙳",
                        "url": RANGE_CHANNEL_URL,
                        "style": "primary"
                    }
                ]
            ]
        }
    }
    try:
        res = requests.post(url, json=payload, timeout=10)
        result = res.json()

        if result.get("ok"):
            # ✅ সফল — message_id নিয়ে ৬০ সেকেন্ড পর ডিলিট করো
            message_id = result["result"]["message_id"]
            auto_delete(CHANNEL_ID, message_id, AUTO_DELETE_SEC)
        else:
            # Fallback — pyTelegramBotAPI দিয়ে পাঠাও
            fallback_markup = types.InlineKeyboardMarkup()
            fallback_markup.add(types.InlineKeyboardButton(
                text=f"🟢 {otp_code} 🟢",
                copy_text=types.CopyTextButton(text=otp_code)
            ))

            fallback_markup.row(
                types.InlineKeyboardButton("🔵 𝙽𝚄𝙼𝙱𝙴𝚁 𝙱𝙾𝚃", url=PANEL_BOT_URL),
                types.InlineKeyboardButton("🔵 𝙼𝙴𝚃𝙷𝙾𝙳", url=RANGE_CHANNEL_URL)
            )
            sent = bot.send_message(CHANNEL_ID, text, reply_markup=fallback_markup)
            auto_delete(CHANNEL_ID, sent.message_id, AUTO_DELETE_SEC)

    except Exception as e:
        print(f"[Send Error] {e}")

def fill_xxx(number_str):
    def replace_x(match):
        return ''.join([str(random.randint(0, 9)) for _ in match.group()])
    filled = re.sub(r'[Xx]+', replace_x, number_str)
    return re.sub(r'\D', '', filled)

def send_styled_otp(hit):
    otp_full    = hit.get("message", "")
    full_number = str(hit.get("range", ""))

    flag, short_code, lang, country = get_country_info(full_number)

    real_num       = re.sub(r'[Xx]', '', full_number)
    real_digits    = re.sub(r'\D', '', real_num)
    filled_num     = fill_xxx(full_number)
    display_masked = filled_num[:4] + "★★" + filled_num[-4:]

    otp_code = extract_otp(otp_full, full_number)
    if not otp_code:
        m = re.search(r'\b\d{5,8}\b', otp_full)
        otp_code = m.group() if m else re.sub(r'\D', '', otp_full)[:8] or "------"

    service = detect_service(otp_full)
    text    = build_message(display_masked, flag, short_code, service, lang)

    send_with_styled_buttons(text, otp_code, real_digits)

def run_bot():
    print("🚀 OTP Bot (Console API) started...")
    while True:
        try:
            res = requests.get(CONSOLE_URL, headers=HEADERS, timeout=10).json()
            if res.get("meta", {}).get("status") == "ok":
                history = pickle.load(open(DB_FILE, "rb")) if os.path.exists(DB_FILE) else {}
                for hit in res.get("data", {}).get("hits", []):
                    msg_time = str(hit.get("time", ""))
                    if msg_time not in history:
                        send_styled_otp(hit)
                        history[msg_time] = True
                        pickle.dump(history, open(DB_FILE, "wb"))
                        time.sleep(1.5)
        except Exception as e:
            print(f"[Error] {e}")
        time.sleep(10)

# ===================== MAIN =====================
if __name__ == "__main__":
    keep_alive()
    threading.Thread(target=run_bot, daemon=True).start()
    print("✅ OTP Bot running!")
    while True:
        time.sleep(60)
