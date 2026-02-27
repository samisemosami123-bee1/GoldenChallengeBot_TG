import sqlite3
import os
import shutil
import time
from datetime import date
from telegram import *
from telegram.ext import *

# ================= CONFIG =================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_USERNAME = os.environ.get("CHANNEL_USERNAME")
ADMIN_ID = int(os.environ.get("ADMIN_ID"))

# ================= DATABASE FILES =================
DB = "empire.db"
BACKUP = "backup.db"

# ================= RECOVERY =================
if not os.path.exists(DB) and os.path.exists(BACKUP):
    shutil.copy(BACKUP, DB)

conn = sqlite3.connect(DB, check_same_thread=False)
cursor = conn.cursor()

# ================= DATABASE =================
cursor.execute("""
CREATE TABLE IF NOT EXISTS users(
user_id INTEGER PRIMARY KEY,
points INTEGER DEFAULT 0,
referrals INTEGER DEFAULT 0,
level TEXT DEFAULT 'Member',
vip INTEGER DEFAULT 0,
inviter INTEGER,
last_daily TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS tasks(
id INTEGER PRIMARY KEY AUTOINCREMENT,
title TEXT,
link TEXT,
reward INTEGER
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS completed(
user_id INTEGER,
task_id INTEGER
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS withdraws(
id INTEGER PRIMARY KEY AUTOINCREMENT,
user_id INTEGER,
amount INTEGER,
status TEXT DEFAULT 'pending'
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS banned(
user_id INTEGER PRIMARY KEY
)
""")

conn.commit()

# ================= AUTO BACKUP =================
def backup():
    conn.commit()
    shutil.copy(DB, BACKUP)

# ================= ANTI SPAM =================
cooldown = {}
def anti(uid):
    now = time.time()
    if uid in cooldown:
        if now - cooldown[uid] < 2:
            return False
    cooldown[uid] = now
    return True

# ================= LEVEL SYSTEM =================
def level(points):
    if points >= 5000:
        return "👑 Legend"
    elif points >= 2000:
        return "🔥 King"
    elif points >= 1000:
        return "⚡ Elite"
    elif points >= 500:
        return "💎 Pro"
    elif points >= 200:
        return "🥷 Soldier"
    return "Member"

# ================= MENU =================
def menu(uid):
    buttons = [
        ["💰 المهام","👤 حسابي"],
        ["👥 دعوة","💵 سحب"],
        ["🏆 مستواي","💎 VIP"]
    ]
    if uid == ADMIN_ID:
        buttons.append(["⚙️ لوحة التحكم","📊 الإحصائيات"])
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

# ================= CHECK SUB =================
def check_subscription(update, context):
    user = update.effective_user
    try:
        member = context.bot.get_chat_member(CHANNEL_USERNAME, user.id)
        if member.status in ['member', 'administrator', 'creator']:
            return True
        else:
            return False
    except:
        return False

# ================= START =================
def start(update, context):
    user = update.effective_user
    uid = user.id

    if not check_subscription(update, context):
        update.message.reply_text(
            f"🔒 يجب الانضمام أولًا إلى قناة {CHANNEL_USERNAME} لتتمكن من استخدام البوت",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("انضم الآن", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")]])
        )
        return

    cursor.execute("SELECT user_id FROM banned WHERE user_id=?", (uid,))
    if cursor.fetchone():
        return

    inviter = None
    if context.args:
        try:
            inviter = int(context.args[0])
        except:
            pass

    cursor.execute("SELECT user_id FROM users WHERE user_id=?", (uid,))
    if not cursor.fetchone():
        cursor.execute("""
        INSERT INTO users(user_id,points,referrals,level,vip,inviter,last_daily)
        VALUES(?,?,?,?,?,?,?)
        """, (uid,0,0,"Member",0,inviter,None))

        # نقاط الدعوة
        if inviter and inviter != uid:
            cursor.execute("SELECT vip FROM users WHERE user_id=?", (inviter,))
            vip_status = cursor.fetchone()[0] or 0
            bonus = 40 if vip_status == 1 else 20
            cursor.execute("""
            UPDATE users
            SET points=points+?,referrals=referrals+1
            WHERE user_id=?""", (bonus, inviter))

    backup()

    update.message.reply_text(
        "👑 EMPIRE PRO MAX ACTIVE",
        reply_markup=menu(uid)
    )

# ================= USER PANEL =================
def user(update, context):
    uid = update.effective_user.id
    text = update.message.text
    if not anti(uid):
        return

    # ---------- المهام ----------
    if text == "💰 المهام":
        cursor.execute("SELECT * FROM tasks")
        tasks = cursor.fetchall()
        if not tasks:
            update.message.reply_text("لا يوجد مهام حالياً")
            return
        for t in tasks:
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("🚀 تنفيذ", callback_data=f"task_{t[0]}")]])
            update.message.reply_text(f"{t[1]}\n{t[2]}\n💰 {t[3]} نقطة", reply_markup=kb)

    # ---------- الحساب ----------
    elif text == "👤 حسابي":
        cursor.execute("SELECT points,referrals,level,vip FROM users WHERE user_id=?", (uid,))
        p,r,l,vip = cursor.fetchone()
        vip_text = "💎 VIP" if vip == 1 else "Member"
        update.message.reply_text(f"👤 حسابك\n💰 نقاط: {p}\n👥 دعوات: {r}\n🏆 المستوى: {l}\n{vip_text}")

    # ---------- الدعوات ----------
    elif text == "👥 دعوة":
        link = f"https://t.me/{context.bot.username}?start={uid}"
        update.message.reply_text(f"رابطك:\n{link}\n🎁 20 نقطة لكل دعوة (VIP = 40)")

    # ---------- المستوى ----------
    elif text == "🏆 مستواي":
        cursor.execute("SELECT points FROM users WHERE user_id=?", (uid,))
        pts = cursor.fetchone()[0]
        lv = level(pts)
        cursor.execute("UPDATE users SET level=? WHERE user_id=?", (lv, uid))
        backup()
        update.message.reply_text(f"🏆 مستواك الحالي:\n{lv}")

    # ---------- سحب ----------
    elif text == "💵 سحب":
        cursor.execute("SELECT points FROM users WHERE user_id=?", (uid,))
        pts = cursor.fetchone()[0]
        if pts < 200:
            update.message.reply_text("❌ تحتاج 200 نقطة")
            return
        cursor.execute("INSERT INTO withdraws(user_id,amount) VALUES(?,200)", (uid,))
        cursor.execute("UPDATE users SET points=points-200 WHERE user_id=?", (uid,))
        backup()
        context.bot.send_message(ADMIN_ID, f"💵 طلب سحب من {uid}")
        update.message.reply_text("✅ تم إرسال الطلب")

    # ---------- VIP ----------
    elif text == "💎 VIP":
        cursor.execute("SELECT vip,points FROM users WHERE user_id=?", (uid,))
        vip, pts = cursor.fetchone()
        if vip == 1:
            update.message.reply_text("💎 أنت مشترك VIP بالفعل")
            return
        if pts < 1000:
            update.message.reply_text("❌ تحتاج 1000 نقطة للترقية إلى VIP")
            return
        cursor.execute("UPDATE users SET vip=1,points=points-1000 WHERE user_id=?", (uid,))
        backup()
        update.message.reply_text("🎉 تم ترقيتك إلى VIP بنجاح!")

    # ---------- الإحصائيات ----------
    elif text == "📊 الإحصائيات" and uid == ADMIN_ID:
        cursor.execute("SELECT COUNT(*),SUM(points),SUM(referrals) FROM users")
        total_users, total_points, total_refs = cursor.fetchone()
        cursor.execute("SELECT COUNT(*) FROM users WHERE vip=1")
        vip_count = cursor.fetchone()[0]
        cursor.execute("SELECT user_id,points FROM users ORDER BY points DESC LIMIT 5")
        top_users = cursor.fetchall()
        text = f"📊 إحصائيات البوت:\n\n👥 المستخدمين: {total_users}\n💰 إجمالي النقاط: {total_points}\n👥 إجمالي الدعوات: {total_refs}\n💎 VIP: {vip_count}\n\n🏆 أفضل 5 مستخدمين:\n"
        for i,u in enumerate(top_users,1):
            text += f"{i}. {u[0]} - {u[1]} نقطة\n"
        update.message.reply_text(text)

    # ---------- ADMIN PANEL ----------
    elif text == "⚙️ لوحة التحكم" and uid == ADMIN_ID:
        update.message.reply_text("""
👑 ADMIN PANEL

/addtask title|link|reward
/accept USERID
/ban USERID
/stats
/broadcast TEXT
""")

# ================= TASK COMPLETE =================
def buttons(update, context):
    q = update.callback_query
    uid = q.from_user.id
    q.answer()
    if q.data.startswith("task_"):
        tid = int(q.data.split("_")[1])
        cursor.execute("SELECT * FROM completed WHERE user_id=? AND task_id=?", (uid, tid))
        if cursor.fetchone():
            q.answer("منفذة مسبقاً", True)
            return
        cursor.execute("SELECT reward FROM tasks WHERE id=?", (tid,))
        reward = cursor.fetchone()[0]
        cursor.execute("SELECT vip FROM users WHERE user_id=?", (uid,))
        vip = cursor.fetchone()[0]
        if vip == 1:
            reward *= 2
        cursor.execute("INSERT INTO completed VALUES(?,?)", (uid, tid))
        cursor.execute("UPDATE users SET points=points+? WHERE user_id=?", (reward, uid))
        backup()
        q.edit_message_text("✅ تم احتساب المكافأة")

# ================= ADMIN COMMANDS =================
def addtask(update, context):
    if update.effective_user.id != ADMIN_ID:
        return
    data = " ".join(context.args).split("|")
    cursor.execute("INSERT INTO tasks(title,link,reward) VALUES(?,?,?)", (data[0], data[1], int(data[2])))
    backup()
    update.message.reply_text("✅ تمت إضافة المهمة")

def stats(update, context):
    if update.effective_user.id != ADMIN_ID:
        return
    cursor.execute("SELECT COUNT(*),SUM(points),SUM(referrals) FROM users")
    total_users, total_points, total_refs = cursor.fetchone()
    update.message.reply_text(f"👥 {total_users}\n💰 {total_points}\n👥 {total_refs}")

def ban(update, context):
    if update.effective_user.id != ADMIN_ID:
        return
    uid = int(context.args[0])
    cursor.execute("INSERT OR IGNORE INTO banned VALUES(?)", (uid,))
    backup()
    update.message.reply_text("🚫 تم الحظر")

# ================= MAIN =================
def main():
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("addtask", addtask))
    dp.add_handler(CommandHandler("stats", stats))
    dp.add_handler(CommandHandler("ban", ban))
    dp.add_handler(MessageHandler(Filters.text, user))
    dp.add_handler(CallbackQueryHandler(buttons))
    updater.start_polling()
    updater.idle()

main()
