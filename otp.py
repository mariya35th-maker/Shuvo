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
BOT_TOKEN       = "8780904554:AAFkAvFElloccFi6TSGFE6OKbNMvVY2_SOM"
CHANNEL_ID      = "-1004361188862"
API_KEY         = "MUYZ1SXYKG8"
SUCCESS_OTP_URL = "https://api.2oo9.cloud/MXS47FLFX0U/tness/@public/api/success-otp"
HEADERS         = {"mauthapi": API_KEY}

BD_TZ = timezone(timedelta(hours=6))

def bd_time():
    return datetime.now(BD_TZ).strftime("%H:%M")

bot = telebot.TeleBot(BOT_TOKEN)
bot.remove_webhook()

SENT_OTP_FILE = "sent_otp_ids.pkl"
sent_lock = threading.Lock()

def load_sent_ids():
    if os.path.exists(SENT_OTP_FILE):
        try:
            return pickle.load(open(SENT_OTP_FILE, "rb"))
        except Exception:
            pass
    return set()

def save_sent_id(msg_id):
    with sent_lock:
        ids = load_sent_ids()
        ids.add(msg_id)
        pickle.dump(ids, open(SENT_OTP_FILE, "wb"))

sent_otp_ids = load_sent_ids()

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

    hash_match = re.search(r'[<\[#>\]]+\s*((?:\d+\s*){2,4})', message_text)
    if hash_match:
        joined = re.sub(r'\s', '', hash_match.group(1))
        if joined.isdigit() and 4 <= len(joined) <= 8:
            return joined

    keyword_match = re.search(
        r'(?:code|otp|pin|token|verification)[^\d]{0,10}(\d[\d\s]{1,10}\d)',
        message_text, re.IGNORECASE
    )
    if keyword_match:
        joined = re.sub(r'\s', '', keyword_match.group(1))
        if joined.isdigit() and 4 <= len(joined) <= 8:
            if not phone_digits or joined not in phone_digits:
                return joined

    spaced = re.findall(r'\b(\d{2,4})\s+(\d{2,4})\b', message_text)
    for g1, g2 in spaced:
        joined = g1 + g2
        if joined.isdigit() and 4 <= len(joined) <= 8:
            if not phone_digits or joined not in phone_digits:
                return joined

    candidates = re.findall(r'\b(\d{4,8})\b', message_text)
    for candidate in candidates:
        if phone_digits:
            if candidate in phone_digits:
                continue
            if phone_digits.endswith(candidate):
                continue
        if 4 <= len(candidate) <= 8:
            return candidate

    return None

# ===================== HELPERS =====================
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

RANGE_CHANNEL_URL = "https://t.me/otpgurup1"
PANEL_BOT_URL     = "https://t.me/forhad_number_bot"

def fill_xxx(number_str):
    def replace_x(match):
        return ''.join([str(random.randint(0, 9)) for _ in match.group()])
    filled = re.sub(r'[Xx]+', replace_x, number_str)
    return re.sub(r'\D', '', filled)

# ===================== BUILD MARKUP (color style সহ) =====================
def build_markup(otp_code, range_value):
    markup = types.InlineKeyboardMarkup()

    # ✅ OTP বাটন — সবুজ (success) + copy
    otp_btn = types.InlineKeyboardButton(
        text=f"{otp_code}",
        copy_text=types.CopyTextButton(text=otp_code)
    )
    otp_btn.__dict__["style"] = "success"
    markup.add(otp_btn)

    # ✅ NUMBER BOT + METHOD বাটন — নীল (primary)
    num_btn = types.InlineKeyboardButton(
        text="𝙽𝚄𝙼𝙱𝙴𝚁 𝙱𝙾𝚃",
        url=PANEL_BOT_URL
    )
    num_btn.__dict__["style"] = "primary"

    method_btn = types.InlineKeyboardButton(
        text="𝙼𝙴𝚃𝙷𝙾𝙳",
        url=RANGE_CHANNEL_URL
    )
    method_btn.__dict__["style"] = "primary"

    markup.row(num_btn, method_btn)
    return markup

# ===================== SEND TO CHANNEL (retry সহ) =====================
def send_to_channel(item):
    try:
        otp_msg     = item.get("message", "")
        full_number = str(item.get("number", ""))
        clean_num   = re.sub(r'\D', '', full_number)

        country_name = get_country_from_number(full_number)
        alpha2       = get_alpha2(country_name)
        flag         = get_flag(country_name)
        short_code   = get_short_code(country_name)
        lang         = get_language(alpha2)

        filled_num     = fill_xxx(full_number)
        display_masked = filled_num[:4] + "★★" + filled_num[-4:]

        filled_range = filled_num[:4] + filled_num[-4:]
        range_value  = filled_range

        otp_code = extract_otp(otp_msg, full_number)
        if not otp_code:
            m = re.search(r'\b\d{4,8}\b', otp_msg)
            if m:
                otp_code = m.group()
            else:
                digits = re.sub(r'\D', '', otp_msg)
                digits = digits.replace(clean_num, "")
                otp_code = digits[:8] if digits else "------"

        print(f"[OTP] num={clean_num} | otp={otp_code} | range={range_value} | msg={otp_msg}")

        service = detect_service(otp_msg)
        text    = build_message(display_masked, flag, short_code, service, lang)
        markup  = build_markup(otp_code, range_value)

        for attempt in range(3):
            try:
                sent_msg = bot.send_message(CHANNEL_ID, text, reply_markup=markup)
                return True
            except Exception as e:
                print(f"[Send Attempt {attempt+1} Failed] {e}")
                time.sleep(2)
        print("[Send Failed] সব attempt শেষ")
        return False

    except Exception as e:
        print(f"[send_to_channel Error] {e}")
        return False

# ===================== BOT LOOP =====================
def run_bot():
    print("🚀 BOT (success-otp) started...")
    session = requests.Session()
    session.headers.update(HEADERS)
    consecutive_errors = 0

    while True:
        try:
            r = session.get(SUCCESS_OTP_URL, timeout=15)
            data = r.json()
            consecutive_errors = 0

            if data.get("meta", {}).get("code") == 200:
                otps = data.get("data", {}).get("otps", [])
                for item in otps:
                    msg_id = str(item.get("otp_id") or item.get("id") or "")
                    if not msg_id:
                        continue
                    with sent_lock:
                        already_sent = msg_id in sent_otp_ids
                        if not already_sent:
                            sent_otp_ids.add(msg_id)
                    if not already_sent:
                        save_sent_id(msg_id)
                        send_to_channel(item)
                        time.sleep(0.5)
            else:
                print(f"[API] unexpected response: {data.get('meta')}")

        except requests.exceptions.Timeout:
            print("[BOT] Request timeout, retrying...")
            consecutive_errors += 1
        except requests.exceptions.ConnectionError:
            print("[BOT] Connection error, retrying...")
            consecutive_errors += 1
        except Exception as e:
            print(f"[BOT Error] {e}")
            consecutive_errors += 1

        if consecutive_errors >= 5:
            print("[BOT] Too many errors, resetting session...")
            session = requests.Session()
            session.headers.update(HEADERS)
            consecutive_errors = 0
            time.sleep(10)
        else:
            time.sleep(2)

# ===================== WATCHDOG =====================
def watchdog():
    while True:
        time.sleep(60)
        for t in threading.enumerate():
            if t.name == "bot_thread" and not t.is_alive():
                print("[WATCHDOG] Bot thread died! Restarting...")
                new_thread = threading.Thread(target=run_bot, name="bot_thread", daemon=True)
                new_thread.start()

# ===================== MAIN =====================
if __name__ == "__main__":
    keep_alive()

    bot_thread = threading.Thread(target=run_bot, name="bot_thread", daemon=True)
    bot_thread.start()

    wd_thread = threading.Thread(target=watchdog, name="watchdog", daemon=True)
    wd_thread.start()

    print("✅ Bot running!")
    while True:
        time.sleep(60)