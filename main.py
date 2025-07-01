import os
import logging
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, ContextTypes
)
from dotenv import load_dotenv

# Load .env.production vars
load_dotenv(".env.production")
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or "7788071056:AAECYEfIuxQYcCyS_DgAYaif1JHc_v9A5U8"
OPENAI_KEY = os.getenv("OPENAI_API_KEY") or "sk-your-openai-key-here"
WEBHOOK_URL = os.getenv("WEBHOOK_URL") or "https://mansoursaibotlearn.onrender.com/webhook"

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask app
app = Flask(__name__)

# Telegram app (async, lazy load)
application = Application.builder().token(TOKEN).build()

# Command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("Start command received from user %s", update.effective_user.id)
    await update.message.reply_text("👋 Hello! I'm alive and ready!")

# Register handlers
application.add_handler(CommandHandler("start", start))

# Sync webhook handler for Render compatibility
@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        json_data = request.get_json(force=True)
        update = Update.de_json(json_data, application.bot)

        async def process():
            await application.initialize()
            await application.process_update(update)

        asyncio.run(process())
        return "OK", 200
