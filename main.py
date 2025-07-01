import os
import logging
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, ContextTypes
)
from dotenv import load_dotenv
import requests
from telegram.error import NetworkError, TimedOut

# Load environment variables
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

# Initialize Flask app
app = Flask(__name__)

# Telegram Application instance (async)
application = Application.builder().token(TOKEN).build()

# Example /start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Handling /start command from user: {update.effective_user.id}")
    try:
        await update.message.reply_text("👋 Hello! I'm alive and ready!")
    except NetworkError as ne:
        logger.error(f"NetworkError replying to /start: {ne}")
    except TimedOut as to:
        logger.error(f"TimedOut error replying to /start: {to}")
    except Exception as e:
        logger.exception(f"Unexpected error replying to /start: {e}")

# Register handlers
application.add_handler(CommandHandler("start", start))

# Sync webhook handler for Render compatibility
@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        json_data = request.get_json(force=True)
        update = Update.de_json(json_data, application.bot)
        logger.info("Webhook update received")

        async def process_update():
            await application.initialize()
            await application.process_update(update)

        asyncio.run(process_update())
        logger.info("Webhook update processed successfully")
        return "OK", 200

    except NetworkError as ne:
        logger.error(f"NetworkError during webhook processing: {ne}")
        return "NetworkError", 500
    except TimedOut as to:
        logger.error(f"TimedOut during webhook processing: {to}")
        return "TimedOut", 500
    except Exception as e:
        logger.exception(f"Error processing webhook update: {e}")
        return "Webhook error", 500

# Main entry point
if __name__ == "__main__":
    logger.info("🚀 Starting bot server...")
    logger.info(f"TOKEN: {'✔️' if TOKEN else '❌'}")
    logger.info(f"OPENAI_KEY: {'✔️' if OPENAI_KEY else '❌'}")
    logger.info(f"WEBHOOK_URL: {'✔️' if WEBHOOK_URL else '❌'}")

    # Set Telegram webhook
    try:
        response = requests.get(f"https://api.telegram.org/bot{TOKEN}/setWebhook?url={WEBHOOK_URL}/webhook")
        logger.info("📡 Webhook set response: %s", response.json())
    except Exception as e:
        logger.exception(f"Failed to set webhook: {e}")

    # Run Flask app
    app.run(host="0.0.0.0", port=5000)
