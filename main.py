import os
import logging
from fastapi import FastAPI, Request, HTTPException
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv
import asyncio
import openai

# === Load environment ===
load_dotenv(".env.production")  # Optional, for local testing
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "7788071056:AAECYEfIuxQYcCyS_DgAYaif1JHc_v9A5U8")
OPENAI_KEY = os.getenv("OPENAI_API_KEY", "sk-YOUR-OPENAI-KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://mansoursaibotlearn.onrender.com")

# === Logging ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === FastAPI instance ===
app = FastAPI()

# === OpenAI setup ===
openai.api_key = OPENAI_KEY

async def ask_gpt(prompt):
    try:
        response = await openai.ChatCompletion.acreate(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"OpenAI error: {e}")
        return "❌ Failed to get a response from ChatGPT."

# === Telegram bot setup ===
application = Application.builder().token(BOT_TOKEN).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Hello! Send me any message and I’ll ask ChatGPT for you.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text
    reply = await ask_gpt(user_input)
    await update.message.reply_text(f"🤖 {reply}")

application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# === Startup & Shutdown hooks ===
@app.on_event("startup")
async def on
