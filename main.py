import os
import logging
from fastapi import FastAPI, Request, HTTPException
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from dotenv import load_dotenv
import asyncio

# Load environment variables
load_dotenv(".env.production")
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "7788071056:AAECYEfIuxQYcCyS_DgAYaif1JHc_v9A5U8")
OPENAI_KEY = os.getenv("OPENAI_API_KEY", "sk-YOUR-OPENAI-KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://mansoursaibotlearn.onrender.com")

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
    await application.initialize()
    url = f"{WEBHOOK_URL}/webhook"
    response = await application.bot.set_webhook(url)
    if response:
        logger.info(f"Webhook set successfully to {url}")
    else:
        logger.error("Failed to set webhook")
    await application.start()

@app.on_event("shutdown")
async def on_shutdown():
    logger.info("🛑 Shutting down Telegram bot...")
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

@app.get("/")
def health():
    return {"status": "✅ MansourAI is running"}

# ✅ Required to expose port on Render
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=10000)
