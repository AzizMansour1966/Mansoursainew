import os
import logging
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, ContextTypes, MessageHandler, filters
)
from dotenv import load_dotenv

# Load .env vars
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# Configure detailed logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG
)
logger = logging.getLogger(__name__)

# Flask app
app = Flask(__name__)

# Telegram application (async, lazy init)
application = Application.builder().token(TOKEN).build()

# Handler: /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Received /start from user_id={update.effective_user.id}")
    await update.message.reply_text("👋 Hello! I'm alive and ready!")

# Example message handler (echo)
async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Echo message from user_id={update.effective_user.id}: {update.message.text}")
    await update.message.reply_text(f"Echo: {update.message.text}")

# Register handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

# Sync webhook route for Render compatibility
@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        logger.debug("Webhook POST received")
        json_data = request.get_json(force=True)
        logger.debug(f"Update JSON: {json_data}")

        update = Update.de_json(json_data, application.bot)

        async def process_update():
            logger.debug("Initializing application for update processing")
            await application.initialize()
            logger.debug("Processing update now")
            await application.process_update(update)
            logger.debug("Finished processing update")

        asyncio.run(process_update())
        return "OK", 200

    except Exception as e:
        logger.exception("❌ Exception in webhook handler")
        return "Webhook error", 500

# Entry point
if __name__ == "__main__":
    logger.info("🚀 Starting bot server...")
    logger.info(f"TOKEN: {'✔️' if TOKEN else '❌'}")
    logger.info(f"OPENAI_KEY: {'✔️' if OPENAI_KEY else '❌'}")
    logger.info(f"WEBHOOK_URL: {'✔️' if WEBHOOK_URL else '❌'}")

    # Set webhook (log response fully)
    import requests
    try:
        response = requests.get(f"https://api.telegram.org/bot{TOKEN}/setWebhook?url={WEBHOOK_URL}/webhook")
        logger.info(f"📡 Webhook set response: {response.status_code} - {response.text}")
    except Exception as e:
        logger.error(f"Failed to set webhook: {e}")

    # Run Flask app
    app.run(host="0.0.0.0", port=5000)
