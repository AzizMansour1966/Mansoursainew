import os
import logging
import asyncio
from fastapi import FastAPI, Request, HTTPException
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from dotenv import load_dotenv

# === Load environment variables ===
load_dotenv(".env.production")
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "7788071056:AAECYEfIuxQYcCyS_DgAYaif1JHc_v9A5U8")
OPENAI_KEY = os.getenv("OPENAI_API_KEY", "sk-YOUR-OPENAI-KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://mansoursaibotlearn.onrender.com")

# === Logging setup ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === Create FastAPI app ===
app = FastAPI()

# === Create Telegram application ===
application = Application.builder().token(TOKEN).build()

# === Telegram command handler ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Hello! I'm alive and ready!")

application.add_handler(CommandHandler("start", start))

# === FastAPI startup event ===
@app.on_event("startup")
async def on_startup():
    logger.info("🚀 Starting Telegram bot...")
    await application.initialize()
    webhook_url = f"{WEBHOOK_URL}/webhook"
    response = await application.bot.set_webhook(webhook_url)
    if response:
        logger.info(f"✅ Webhook set to {webhook_url}")
    else:
        logger.error("❌ Failed to set webhook")
    await application.start()

# === FastAPI shutdown event ===
@app.on_event("shutdown")
async def on_shutdown():
    logger.info("🛑 Shutting down Telegram bot...")
    await application.stop()
    await application.shutdown()

# === Telegram webhook endpoint ===
@app.post("/webhook")
async def webhook(request: Request):
    try:
        data = await request.json()
        update = Update.de_json(data, application.bot)
        # ⚠️ Run this as a background task to immediately return 200 to Telegram
        asyncio.create_task(application.process_update(update))
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"❌ Webhook processing error: {e}")
        raise HTTPException(status_code=500, detail="Webhook processing error")

# === Health check ===
@app.get("/")
def health():
    return {"status": "✅ MansourAI is running"}
