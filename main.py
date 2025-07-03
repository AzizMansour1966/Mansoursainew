import os
import logging
from fastapi import FastAPI, Request, HTTPException
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv
import openai
import asyncio
import nest_asyncio

# Load environment variables
load_dotenv(".env.production")
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "7788071056:AAECYEfIuxQYcCyS_DgAYaif1JHc_v9A5U8")
OPENAI_KEY = os.getenv("OPENAI_API_KEY", "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")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://mansoursainew.onrender.com/webhook")

openai.api_key = OPENAI_KEY
nest_asyncio.apply()

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI()

# Telegram Application
application = Application.builder().token(TOKEN).build()

# Telegram handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Hello! I’m alive and ready!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_msg = update.message.text
    reply = await ask_chatgpt(user_msg)
    await update.message.reply_text(reply)

# Register handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# OpenAI ChatGPT
async def ask_chatgpt(prompt: str) -> str:
    try:
        response = await openai.chat.completions.acreate(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"OpenAI error: {e}")
        return "⚠️ Error generating response from ChatGPT."

# Startup and shutdown
@app.on_event("startup")
async def on_startup():
    logger.info("🚀 Starting Telegram bot...")
    await application.initialize()
    webhook_url = f"{WEBHOOK_URL}/webhook"
    await application.bot.set_webhook(webhook_url)
    await application.start()

@app.on_event("shutdown")
async def on_shutdown():
    logger.info("🛑 Shutting down Telegram bot...")
    await application.stop()
    await application.shutdown()

# Webhook endpoint
@app.post("/webhook")
async def telegram_webhook(request: Request):
    try:
        data = await request.json()
        update = Update.de_json(data, application.bot)
        await application.process_update(update)
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        raise HTTPException(status_code=500, detail="Webhook processing failed")

# Health check
@app.get("/")
def health_check():
    return {"status": "✅ MansourAI is running"}
