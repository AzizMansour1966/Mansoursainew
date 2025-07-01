import os
import logging
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, ContextTypes
)
import requests

# ----- Configuration -----
TOKEN = "7788071056:AAECYEfIuxQYcCyS_DgAYaif1JHc_v9A5U8"  # Replace with your actual token
WEBHOOK_URL = "https://mansoursaibotlearn.onrender.com"  # Replace with your actual URL

# ----- Logging -----
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ----- Flask app -----
app = Flask(__name__)

# ----- Telegram Application -----
application = Application.builder().token(TOKEN).build()

# ----- Handlers -----
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("Received /start command")
    try:
        await update.message.reply_text("👋 Hello! I'm alive and ready!")
        logger.info("Replied to /start command")
    except Exception as e:
        logger.error(f"Failed to send reply in start handler: {e}")

application.add_handler(CommandHandler("start", start))

# ----- Initialize Application once before serving -----
asyncio.run(application.initialize())

# ----- Webhook route -----
@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        json_data = request.get_json(force=True)
        update = Update.de_json(json_data, application.bot)

        async def process():
            logger.info("Processing incoming update")
            await application.process_update(update)

        asyncio.run(process())
        return "OK", 200
    except Exception as e:
        logger.error(f"Error in webhook processing: {e}")
        return "Error", 500

# ----- Set webhook and start Flask -----
if __name__ == "__main__":
    logger.info("Starting bot server...")

    # Set webhook
    try:
        response = requests.get(f"https://api.telegram.org/bot{TOKEN}/setWebhook?url={WEBHOOK_URL}/webhook")
        logger.info(f"Set webhook response: {response.json()}")
    except Exception as e:
        logger.error(f"Failed to set webhook: {e}")

    app.run(host="0.0.0.0", port=5000)
