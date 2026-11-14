import json, os
from telegram import KeyboardButton, ReplyKeyboardMarkup, Update, WebAppInfo
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

def summary(data: dict) -> str:
    lines = [f"• {i['name']} × {i['qty']}" for i in data["items"]]
    return "✅ Замовлення прийнято!\n" + "\n".join(lines) + f"\nРазом: {data['total']} ₴"

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    # web_app_data приходить боту тільки з кнопки-клавіатури, не з menu button
    kb = ReplyKeyboardMarkup([[KeyboardButton("☕ Меню", web_app=WebAppInfo(os.environ["WEBAPP_URL"]))]], resize_keyboard=True)
    await update.message.reply_text("Привіт! Натисни «Меню», щоб замовити каву.", reply_markup=kb)

async def order(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(summary(json.loads(update.message.web_app_data.data)))

if __name__ == "__main__":
    assert "Разом: 160 ₴" in summary({"items": [{"name": "Лате", "qty": 2}], "total": 160})
    app = Application.builder().token(os.environ["BOT_TOKEN"]).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, order))
    app.run_polling()
