import json
import os
import threading
import datetime
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

# === Bot Configuration ===
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
CHANNEL_LINKS = {
    "Join Channel 1": "https://t.me/proof_sharex",
    "Join Channel 2": "https://t.me/daily_earning_trick_users",
    "Join Channel 3": "https://t.me/real_earning_apps_here",
    "Join Channel 4": "https://t.me/+eFmLFIfSlmc1ZjY9"
}
DATA_FILE = "users.json"
MIN_WITHDRAW = 50
data_lock = threading.Lock()

# === Flask Keep-Alive ===
app = Flask('')
@app.route('/')
def home():
    return "Bot is running!"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

# === Data Handling ===
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump({}, f)

def load_data():
    with data_lock:
        with open(DATA_FILE, "r") as f:
            return json.load(f)

def save_data(data):
    with data_lock:
        with open(DATA_FILE, "w") as f:
            json.dump(data, f, indent=2)

# === Membership Check ===
async def check_membership(user_id, context):
    for title, url in CHANNEL_LINKS.items():
        try:
            username = url.split("t.me/")[1]
            if "+" in username:
                continue  # Skip private channels
            member = await context.bot.get_chat_member(chat_id=f"@{username}", user_id=user_id)
            if member.status not in ["member", "administrator", "creator"]:
                return False
        except Exception as e:
            print(f"Membership check error: {e}")
            return False
    return True

# === Reaction Handler ===
async def send_reaction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.react("👍")
    except:
        pass

# === Bot Commands ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = str(user.id)
    data = load_data()
    ref = context.args[0] if context.args else None

    if user_id not in data:
        data[user_id] = {"balance": 0, "referrals": [], "joined": False, "referrer": None}

    if ref and ref != user_id and ref in data:
        data[user_id]["referrer"] = ref
        save_data(data)

    if data[user_id]["joined"]:
        await update.message.reply_text("आप पहले से जुड़ चुके हैं! /balance से बैलेंस चेक करें")
        return

    buttons = [[InlineKeyboardButton(text=title, url=url)] for title, url in CHANNEL_LINKS.items()]
    buttons.append([InlineKeyboardButton("✅ सभी चैनल ज्वाइन कर लिए", callback_data="check_join")])

    await update.message.reply_text(
        "🎉 ₹5 प्रति रेफरल बोनस!

"
        "👉 बोनस पाने के लिए नीचे दिए सभी चैनल्स ज्वाइन करें:",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="Markdown"
    )

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    data = load_data()

    if query.data == "check_join":
        if await check_membership(user_id, context):
            if not data[user_id]["joined"]:
                data[user_id]["joined"] = True
                data[user_id]["balance"] += 5  # Signup bonus

                if data[user_id]["referrer"] and data[user_id]["referrer"] in data:
                    referrer_id = data[user_id]["referrer"]
                    data[referrer_id]["balance"] += 5
                    if user_id not in data[referrer_id]["referrals"]:
                        data[referrer_id]["referrals"].append(user_id)

                save_data(data)
                await query.edit_message_text("✅ सफलता! ₹5 बोनस क्रेडिट हुआ!

/invite से रेफर करके और कमाएं")
            else:
                await query.edit_message_text("⚠️ आप पहले ही ज्वाइन कर चुके हैं")
        else:
            await query.answer("❌ सभी चैनल्स ज्वाइन करें!", show_alert=True)

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    data = load_data()
    bal = data.get(user_id, {}).get("balance", 0)
    await update.message.reply_text(f"💰 आपका बैलेंस: ₹{bal}

Minimum withdrawal: ₹{MIN_WITHDRAW}")

async def invite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    await update.message.reply_text(
        f"📢 प्रति रेफरल ₹5 कमाएं!

"
        f"आपका रेफरल लिंक:
https://t.me/{context.bot.username}?start={uid}

"
        "👉 जितने ज्यादा लोग आपके लिंक से ज्वाइन करेंगे, उतने ₹5 आपको मिलेंगे!"
    )

async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    data = load_data()
    today = datetime.datetime.now().weekday()  # Monday=0, Sunday=6

    if today in [0, 5, 6]:
        await update.message.reply_text(
            "⚠️ निकासी रविवार, सोमवार और शनिवार को बंद रहेगी!
"
            "🕒 निकासी समय: मंगलवार से शुक्रवार (सुबह 10 AM से शाम 6 PM)"
        )
        return

    balance = data.get(user_id, {}).get("balance", 0)
    if balance < MIN_WITHDRAW:
        await update.message.reply_text(f"❌ न्यूनतम निकासी राशि ₹{MIN_WITHDRAW} है")
    else:
        await update.message.reply_text(
            "📩 अपना UPI ID यहाँ भेजें:
"
            "उदाहरण: 1234567890@ybl

"
            "⚠️ ध्यान दें: पेमेंट 24-48 घंटे में प्रोसेस होगी"
        )

if __name__ == "__main__":
    threading.Thread(target=run_flask).start()

    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(CommandHandler("balance", balance))
    application.add_handler(CommandHandler("invite", invite))
    application.add_handler(CommandHandler("withdraw", withdraw))
    application.add_handler(MessageHandler(filters.ALL, send_reaction))

    print("🤖 बॉट सक्रिय है...")
    application.run_polling()
