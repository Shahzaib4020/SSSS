from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, CallbackQueryHandler
import requests
import sqlite3
import logging

# ====================== CONFIGURATION ======================
TELEGRAM_BOT_TOKEN = "7932690591:AAFbAE8Rq3Usr01AQGQ3K8MTZsJl9pM-hWw"
DEEPSEEK_API_KEY = "sk-b0d6387bbb6944d2b06c848b2572a637"

# Mandatory channels to join
MANDATORY_CHANNELS = [
    {"name": "EarningDeepSeek", "link": "https://t.me/EarningDeepSeek"},
    {"name": "DeepSeekEarnings", "link": "https://t.me/DeepSeekEarnings"}
]

# Sample airdrops (آپ یہاں 20 تک ایئرڈراپس شامل کر سکتے ہیں)
AIRDROPS = [
    {"name": "Airdrop 1", "link": "https://t.me/airdrop1"},
    {"name": "Airdrop 2", "link": "https://t.me/airdrop2"},
    {"name": "Airdrop 3", "link": "https://t.me/airdrop3"},
    {"name": "Airdrop 4", "link": "https://t.me/airdrop4"},
    {"name": "Airdrop 5", "link": "https://t.me/airdrop5"}
]

# ====================== DATABASE SETUP ======================
conn = sqlite3.connect('earnings.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    message_count INTEGER DEFAULT 0,
    tasks_completed INTEGER DEFAULT 0,
    balance REAL DEFAULT 0,
    joined_channels BOOLEAN DEFAULT 0
)''')
conn.commit()

def update_schema():
    cursor.execute("PRAGMA table_info(users)")
    columns = [info[1] for info in cursor.fetchall()]
    if "username" not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN username TEXT")
        conn.commit()

update_schema()

# ====================== LOGGER ======================
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

# ====================== FUNCTIONS ======================

async def force_channel_join(update: Update, context: CallbackContext):
    message = update.effective_message
    user = update.effective_user
    user_id = user.id
    username = user.username if user.username else "User"
    logging.info(f"/start triggered by user {user_id} - {username}")
    
    # Insert user if not exists
    cursor.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)", (user_id, username))
    conn.commit()
    
    # اگر یوزر پہلے سے چینلز join کر چکا ہے تو مین مینو دکھائیں
    cursor.execute("SELECT joined_channels FROM users WHERE user_id=?", (user_id,))
    result = cursor.fetchone()
    if result and result[0]:
        await show_main_menu(message, username)
        return
    
    keyboard = [
        [InlineKeyboardButton(channel["name"], url=channel["link"]) for channel in MANDATORY_CHANNELS],
        [InlineKeyboardButton("✅ Verify Join", callback_data="verify_join")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await message.reply_text(
        f"👋 Welcome {username}!\n🚨 You must join these channels to use the bot:",
        reply_markup=reply_markup
    )

async def verify_join(update: Update, context: CallbackContext):
    query = update.callback_query
    user = query.from_user
    user_id = user.id
    username = user.username if user.username else "User"
    cursor.execute("UPDATE users SET joined_channels = 1, username = ? WHERE user_id=?", (username, user_id))
    conn.commit()
    await query.answer()
    await query.edit_message_text("✅ Verification successful! You can now use the bot.")
    await show_main_menu(query.message, username)

async def show_main_menu(message, username):
    keyboard = [
        [InlineKeyboardButton("💬 Start Chat", callback_data="start_chat")],
        [InlineKeyboardButton("🎁 Earn", callback_data="earn")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await message.reply_text(f"Hi {username}, choose an option:", reply_markup=reply_markup)

async def start_chat(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("You are now in chat mode.\nSend any message to get a response from DeepSeek.")

async def back_to_chat(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("🔙 Back to Chat mode.\nSend your message:")

async def show_airdrops(update: Update, context: CallbackContext):
    message = update.effective_message
    keyboard = []
    for airdrop in AIRDROPS:
        keyboard.append([InlineKeyboardButton(airdrop["name"], url=airdrop["link"])])
    keyboard.append([InlineKeyboardButton("⏭️ Next Airdrop", callback_data="next_airdrop_0")])
    keyboard.append([InlineKeyboardButton("🔙 Back to Chat", callback_data="back_to_chat")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await message.reply_text("🎁 Available Airdrops:", reply_markup=reply_markup)

async def earn_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    keyboard = []
    for airdrop in AIRDROPS:
        keyboard.append([InlineKeyboardButton(airdrop["name"], url=airdrop["link"])])
    keyboard.append([InlineKeyboardButton("⏭️ Next Airdrop", callback_data="next_airdrop_0")])
    keyboard.append([InlineKeyboardButton("🔙 Back to Chat", callback_data="back_to_chat")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("🎁 Verified Airdrops:\nClick to participate:", reply_markup=reply_markup)

async def handle_next_airdrop(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data
    parts = data.split("_")
    current_index = int(parts[-1]) if parts[-1].isdigit() else 0
    next_index = current_index + 1
    if next_index < len(AIRDROPS):
        airdrop = AIRDROPS[next_index]
        keyboard = [
            [InlineKeyboardButton(airdrop["name"], url=airdrop["link"])],
            [InlineKeyboardButton("⏭️ Next Airdrop", callback_data=f"next_airdrop_{next_index}")],
            [InlineKeyboardButton("🔙 Back to Chat", callback_data="back_to_chat")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(f"🎁 Airdrop {next_index + 1}:\nClick below to participate:", reply_markup=reply_markup)
    else:
        await query.answer("No more airdrops available!")

async def handle_deepseek_chat(update: Update, context: CallbackContext):
    message = update.effective_message
    user = update.effective_user
    user_id = user.id
    cursor.execute("SELECT joined_channels FROM users WHERE user_id=?", (user_id,))
    result = cursor.fetchone()
    if not result or not result[0]:
        await force_channel_join(update, context)
        return

    user_text = message.text
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": user_text}]
    }
    try:
        response = requests.post("https://api.deepseek.com/v1/chat/completions", headers=headers, json=payload)
        if response.status_code == 200:
            response_data = response.json()
            reply = response_data["choices"][0]["message"]["content"]
        else:
            reply = f"⚠️ DeepSeek API returned status code {response.status_code}"
    except Exception as e:
        reply = f"⚠️ Error generating response from DeepSeek API: {str(e)}"
    
    cursor.execute("UPDATE users SET message_count = message_count + 1 WHERE user_id=?", (user_id,))
    conn.commit()
    
    cursor.execute("SELECT message_count FROM users WHERE user_id=?", (user_id,))
    count = cursor.fetchone()[0]
    if count % 5 == 0:
        reply += "\n\n🔒 Complete a task to continue chatting! Use /earn"
    
    await message.reply_text(reply)

def main():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Core commands
    application.add_handler(CommandHandler("start", force_channel_join))
    application.add_handler(CommandHandler("earn", show_airdrops))
    
    # Callback handlers
    application.add_handler(CallbackQueryHandler(verify_join, pattern="^verify_join$"))
    application.add_handler(CallbackQueryHandler(start_chat, pattern="^start_chat$"))
    application.add_handler(CallbackQueryHandler(earn_callback, pattern="^earn$"))
    application.add_handler(CallbackQueryHandler(handle_next_airdrop, pattern="^next_airdrop"))
    application.add_handler(CallbackQueryHandler(back_to_chat, pattern="^back_to_chat$"))
    
    # Chat handling
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_deepseek_chat))
    
    # Increased poll_interval for stable connection
    application.run_polling(poll_interval=3.0)

if __name__ == "__main__":
    main()
