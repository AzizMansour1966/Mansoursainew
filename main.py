import os
import logging
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, ContextTypes
)
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)

# Initialize Telegram Application (async)
application = Application.builder().token(TOKEN).build()

# Define command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Hello! I'm alive and ready!")

# Register command handlers
application.add_handler(CommandHandler("start", start))

# Flask route to handle Telegram webhook requests
@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        json_data = request.get_json(force=True)
        update = Update.de_json(json_data, application.bot)

        async def process_update():
            await application.initialize()
            await application.process_update(update)

        asyncio.run(process_update())
        logger.info("Webhook update processed successfully")
        return "OK", 200
    except Exception as e:
        logger.exception("Error processing webhook update")
        return "Error", 500

# Main entry point
if __name__ == "__main__":
    logger.info("🚀 Starting bot server...")
    logger.info(f"TOKEN: {'✔️' if TOKEN else '❌'}")
    logger.info(f"OPENAI_KEY: {'✔️' if OPENAI_KEY else '❌'}")
    logger.info(f"WEBHOOK_URL: {'✔️' if WEBHOOK_URL else '❌'}")

    # Set webhook with Telegram API
    import requests
    webhook_response = requests.get(
        f"https://api.telegram.org/bot{TOKEN}/setWebhook?url={WEBHOOK_URL}/webhook"
    )
    logger.info(f"📡 Webhook set response: {webhook_response.json()}")

    # Run Flask app
    app.run(host="0.0.0.0", port=5000)
