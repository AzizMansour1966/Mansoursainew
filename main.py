import os
import logging
from fastapi import FastAPI, Request, HTTPException
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv
from openai import AsyncOpenAI # Import the async client for OpenAI v1.x
import asyncio
import nest_asyncio

# Load environment variables from .env.production for local development
load_dotenv(".env.production")

# --- IMPORTANT: Fetch environment variables WITHOUT hardcoded defaults ---
# These values MUST be set in your Render.com environment variables
# and in your local .env.production file.
# If they are not set, the bot will exit with an error, preventing accidental exposure.
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL") # This should be your base URL, e.g., https://mansoursainew.onrender.com

# --- Validate environment variables are set ---
if not TOKEN:
    logging.error("TELEGRAM_BOT_TOKEN environment variable is not set. Exiting.")
    exit(1)
if not OPENAI_KEY:
    logging.error("OPENAI_API_KEY environment variable is not set. Exiting.")
    exit(1)
if not WEBHOOK_URL:
    logging.error("WEBHOOK_URL environment variable is not set. Exiting.")
    exit(1)

# Initialize the async OpenAI client for v1.x
client = AsyncOpenAI(api_key=OPENAI_KEY)

nest_asyncio.apply() # Apply nest_asyncio for compatibility in certain environments

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI()

# Telegram Application setup
application = Application.builder().token(TOKEN).build()

# --- Telegram Handlers ---

# Custom /start command handler with a friendly welcome message
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_message = (
        "👋 Welcome to the Mansour's Family Smart Bot! 🎉\n\n"
        "I'm here to help with anything you need, tell jokes, answer questions, and more!\n\n"
        "Try asking me anything, or type /joke for a quick laugh! ✨"
    )
    await update.message.reply_text(welcome_message)

# Handler for general text messages, sending them to ChatGPT
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_msg = update.message.text
    reply = await ask_chatgpt(user_msg)
    await update.message.reply_text(reply)

# Register handlers with the Telegram Application
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# --- OpenAI ChatGPT Integration ---

# Async function to send prompt to ChatGPT with a defined personality and custom prefix
async def ask_chatgpt(prompt: str) -> str:
    try:
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                # System message to define the bot's personality
                {"role": "system", "content": "You are a friendly, enthusiastic, and slightly mischievous AI assistant named 'Botty McBotface' from the Mansour family. You love to use emojis in your responses, especially when you're excited or telling a joke. You're great at explaining things in a fun way, helping with ideas, and sharing positive vibes. Keep responses concise and engaging for kids and teens."},
                {"role": "user", "content": prompt}
            ]
        )
        chatgpt_reply = response.choices[0].message.content.strip()

        # Prepend the custom phrase to ChatGPT's reply
        final_reply = "Mansour's Family say: " + chatgpt_reply

        return final_reply
    except Exception as e:
        logger.error(f"OpenAI error: {e}")
        return "⚠️ Error generating response from ChatGPT."

# --- FastAPI Event Handlers (Startup/Shutdown) ---

@app.on_event("startup")
async def on_startup():
    logger.info("🚀 Starting Telegram bot...")
    await application.initialize()
    # Construct webhook URL. Ensure WEBHOOK_URL env var does NOT end with /webhook
    webhook_url = f"{WEBHOOK_URL}/webhook"
    logger.info(f"Setting webhook to: {webhook_url}")
    await application.bot.set_webhook(webhook_url)
    await application.start()

@app.on_event("shutdown")
async def on_shutdown():
    logger.info("🛑 Shutting down Telegram bot...")
    await application.stop()
    await application.shutdown()

# --- Webhook Endpoint for Telegram ---

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

# --- Health Check Endpoint ---

@app.get("/")
def health_check():
    return {"status": "✅ MansourAI is running"}
