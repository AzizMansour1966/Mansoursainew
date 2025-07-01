import os
import logging
from fastapi import FastAPI, Request, HTTPException
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from dotenv import load_dotenv
import asyncio

# Load environment variables
load_dotenv(".env.production")
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI()

# Create Telegram application (async)
application = Application.builder().token(TOKEN).build()

# Command handler example
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Hello! I'm alive and ready!")

# Register handlers
application.add_handler(CommandHandler("start", start))

@app.on_event("startup")
async def on_startup():
    logger.info("🚀 Starting Telegram bot...")
    # Set webhook for Telegram
    from telegram.constants import ParseMode
    url = f"{WEBHOOK_URL}/webhook"
    response = await application.bot.set_webhook(url)
    if response:
        logger.info(f"Webhook set successfully to {url}")
    else:
        logger.error("Failed to set webhook")
    await application.initialize()
    await application.start()
    await application.updater.start_polling()  # Optional if you want polling fallback

@app.on_event("shutdown")
async def on_shutdown():
    logger.info("🛑 Shutting down Telegram bot...")
    await application.updater.stop()
    await application.stop()
    await application.shutdown()

@app.post("/webhook")
async def webhook(request: Request):
    try:
        data = await request.json()
        update = Update.de_json(data, application.bot)
        await application.process_update(update)
        logger.info("Webhook update received and processed")
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Error processing webhook update: {e}")
        raise HTTPException(status_code=500, detail="Webhook processing error")

# Root endpoint for health check
