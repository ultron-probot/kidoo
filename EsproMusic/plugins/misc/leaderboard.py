# ── leaderboard.py ──
import datetime
from pyrogram import filters
from pyrogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
)
from EsproMusic import app
from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGO_DB_URI  # ← tumhare config.py me Mongo URI hai na

# ==============================
# 📌 MongoDB Setup
# ==============================
mongo_client = AsyncIOMotorClient(MONGO_DB_URI)
db = mongo_client["LeaderboardDB"]
messages_collection = db["messages"]

# ==============================
# 📨 हर Group Message Count करना
# ==============================
@app.on_message(filters.group & ~filters.service)
async def count_messages(_, message):
    if not message.from_user:
        return
    chat_id = message.chat.id
    user_id = message.from_user.id
    today = datetime.datetime.utcnow().date().isoformat()

    await messages_collection.update_one(
        {"chat_id": chat_id, "user_id": user_id},
        {
            "$inc": {f"daily.{today}": 1, "total": 1}
        },
        upsert=True
    )
  # ==============================
# 🧠 Leaderboard Text Generator
# ==============================
async def get_leaderboard_text(chat_id: int, mode: str):
    now = datetime.datetime.utcnow()
    pipeline = [{"$match": {"chat_id": chat_id}}]

    # 🟡 Different modes
    if mode == "today":
        today = now.date().isoformat()
        pipeline.append({"$project": {"user_id": 1, "count": {"$ifNull": [f"$daily.{today}", 0]}}})
    elif mode == "week":
        today = now.date()
        dates = [(today - datetime.timedelta(days=i)).isoformat() for i in range(7)]
        pipeline.append({"$project": {"user_id": 1, "count": {"$sum": [f"$daily.{d}" for d in dates]}}})
    elif mode == "month":
        today = now.date()
        dates = [(today - datetime.timedelta(days=i)).isoformat() for i in range(30)]
        pipeline.append({"$project": {"user_id": 1, "count": {"$sum": [f"$daily.{d}" for d in dates]}}})
    else:
        pipeline.append({"$project": {"user_id": 1, "count": "$total"}})

    pipeline.append({"$sort": {"count": -1}})
    pipeline.append({"$limit": 10})

    top_users = await messages_collection.aggregate(pipeline).to_list(None)

    # 📨 Total Messages Count (for Overall / All)
    total_pipeline = [{"$match": {"chat_id": chat_id}}]
    if mode == "today":
        today = now.date().isoformat()
        total_pipeline.append({
            "$project": {"_id": 0, "count": {"$ifNull": [f"$daily.{today}", 0]}}
        })
    elif mode == "week":
        today = now.date()
        dates = [(today - datetime.timedelta(days=i)).isoformat() for i in range(7)]
        total_pipeline.append({
            "$project": {"_id": 0, "count": {"$sum": [f"$daily.{d}" for d in dates]}}
        })
    elif mode == "month":
        today = now.date()
        dates = [(today - datetime.timedelta(days=i)).isoformat() for i in range(30)]
        total_pipeline.append({
            "$project": {"_id": 0, "count": {"$sum": [f"$daily.{d}" for d in dates]}}
        })
    else:
        total_pipeline.append({
            "$project": {"_id": 0, "count": "$total"}
        })

    total_pipeline.append({"$group": {"_id": None, "total": {"$sum": "$count"}}})
    total_result = await messages_collection.aggregate(total_pipeline).to_list(None)
    total_messages = total_result[0]["total"] if total_result else 0

    # 🧾 Final Text
    text = f"📈 <b>LEADERBOARD ({mode.capitalize()})</b>\n"
    if not top_users:
        text += "\n⚠️ अभी कोई Data नहीं है!"
        return text

    for i, user_data in enumerate(top_users, start=1):
        try:
            user = await app.get_users(user_data["user_id"])
            name = user.first_name
        except:
            name = "Deleted Account"
        count = user_data["count"]
        text += f"{i}. 👤 {name} • {count}\n"

    text += f"\n✉️ Total messages: {total_messages}"
    return text

# ==============================
# 🟦 Inline Buttons
# ==============================
def leaderboard_buttons():
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("📅 Today", callback_data="rank_today"),
                InlineKeyboardButton("📆 Week", callback_data="rank_week"),
            ],
            [
                InlineKeyboardButton("🗓️ Month", callback_data="rank_month"),
                InlineKeyboardButton("🌐 Overall", callback_data="rank_overall"),
            ]
        ]
  )
  # ==============================
# 💬 /ranking Command
# ==============================
@app.on_message(filters.command("ranking") & filters.group)
async def show_ranking(_, message):
    text = await get_leaderboard_text(message.chat.id, "today")
    await message.reply_text(
        text,
        reply_markup=leaderboard_buttons(),
        disable_web_page_preview=True
    )

# ==============================
# 🔘 Inline Callback Handler
# ==============================
@app.on_callback_query(filters.regex(r"^rank_"))
async def on_rank_callback(_, cq: CallbackQuery):
    mode = cq.data.replace("rank_", "")
    text = await get_leaderboard_text(cq.message.chat.id, mode)
    await cq.message.edit_text(
        text,
        reply_markup=leaderboard_buttons(),
        disable_web_page_preview=True
    )
    await cq.answer()
