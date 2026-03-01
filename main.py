import sqlite3
import os
import shutil
import time
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# ================= ENV =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

# ================= DATABASE =================
DB = "empire.db"
BACKUP = "backup.db"

if not os.path.exists(DB) and os.path.exists(BACKUP):
    shutil.copy(BACKUP, DB)

conn = sqlite3.connect(DB, check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users(
user_id INTEGER PRIMARY KEY,
points INTEGER DEFAULT 0
)
""")
conn.commit()

# ================= ANTI SPAM =================
cooldown = {}

def anti(uid):
    now = time.time()
    if uid in cooldown and now - cooldown[uid] < 2:
        return False
    cooldown[uid] = now
    return True

# ================= MENU =================
def menu():
    return ReplyKeyboardMarkup(
        [
            ["💰 المهام", "👤 حسابي"]
        ],
        resize_keyboard=True
    )

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    cursor.execute(
        "INSERT OR IGNORE INTO users(user_id,points) VALUES(?,0)",
        (uid,)
    )
    conn.commit()

    await update.message.reply_text(
        "👑 البوت يعمل بنجاح ✅",
        reply_markup=menu()
    )

# ================= USER =================
async def user(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.message:
        return

    uid = update.effective_user.id

    if not anti(uid):
        return

    text = update.message.text

    if text == "👤 حسابي":

        cursor.execute(
            "SELECT points FROM users WHERE user_id=?",
            (uid,)
        )

        row = cursor.fetchone()

        if not row:
            return

        pts = row[0]

        await update.message.reply_text(
            f"💰 نقاطك: {pts}"
        )

# ================= CALLBACK =================
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("✅ تم التنفيذ")

# ================= ERROR HANDLER =================
async def error_handler(update, context):
    print(f"ERROR: {context.error}")

# ================= MAIN =================
def main():

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            user
        )
    )

    app.add_handler(CallbackQueryHandler(buttons))

    app.add_error_handler(error_handler)

    print("✅ BOT STARTED SUCCESSFULLY")

    app.run_polling(
        drop_pending_updates=True
    )

if __name__ == "__main__":
    main()
