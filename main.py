import sqlite3
import os
import shutil
import time
from datetime import date

from telegram import *
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_USERNAME = os.environ.get("CHANNEL_USERNAME")
ADMIN_ID = int(os.environ.get("ADMIN_ID"))

DB="empire.db"
BACKUP="backup.db"

if not os.path.exists(DB) and os.path.exists(BACKUP):
    shutil.copy(BACKUP,DB)

conn=sqlite3.connect(DB,check_same_thread=False)
cursor=conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users(
user_id INTEGER PRIMARY KEY,
points INTEGER DEFAULT 0
)
""")
conn.commit()

cooldown={}
def anti(uid):
    now=time.time()
    if uid in cooldown and now-cooldown[uid]<2:
        return False
    cooldown[uid]=now
    return True


def menu(uid):
    return ReplyKeyboardMarkup(
        [["💰 المهام","👤 حسابي"]],
        resize_keyboard=True
    )


async def start(update:Update,context:ContextTypes.DEFAULT_TYPE):
    uid=update.effective_user.id

    cursor.execute(
        "INSERT OR IGNORE INTO users(user_id,points) VALUES(?,0)",
        (uid,))
    conn.commit()

    await update.message.reply_text(
        "👑 البوت يعمل بنجاح",
        reply_markup=menu(uid)
    )


async def user(update:Update,context:ContextTypes.DEFAULT_TYPE):
    uid=update.effective_user.id

    if not anti(uid):
        return

    if update.message.text=="👤 حسابي":
        cursor.execute(
            "SELECT points FROM users WHERE user_id=?",(uid,))
        pts=cursor.fetchone()[0]

        await update.message.reply_text(
            f"💰 نقاطك: {pts}"
        )


async def buttons(update:Update,context:ContextTypes.DEFAULT_TYPE):
    q=update.callback_query
    await q.answer()
    await q.edit_message_text("✅ تم")


def main():
    app=Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start",start))
    app.add_handler(MessageHandler(filters.TEXT,user))
    app.add_handler(CallbackQueryHandler(buttons))

    print("BOT STARTED")

    app.run_polling()


if __name__=="__main__":
    main()
