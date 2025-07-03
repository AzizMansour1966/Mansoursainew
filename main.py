import os
import logging
import re
from fastapi import FastAPI, Request, HTTPException
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv
from openai import AsyncOpenAI
import asyncio
import nest_asyncio

# Load environment variables from .env.production for local development
load_dotenv(".env.production")

# --- IMPORTANT: Fetch environment variables WITHOUT hardcoded defaults ---
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# --- Validate environment variables are set ---
if not TOKEN:
    logging.error("TELEGRAM_BOT_TOKEN environment variable is not set. Exiting.")
    exit(1)
if not OPENAI_KEY:
    logging.error("OPENAI_API_KEY environment variable is not set. Exiting.")
    exit(1)
if not WEBHOOK_URL:
    logging.error("WEBHOOK_URL environment variable is not set. Exiting.")
    # For local development without a public URL, you might want to allow this
    # if using polling instead of webhooks. If webhooks are mandatory, exit.
    # For this example, we'll assume webhooks are desired.
    exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Apply nest_asyncio for compatibility with FastAPI and other async libraries
nest_asyncio.apply()

# Initialize OpenAI client
openai_client = AsyncOpenAI(api_key=OPENAI_KEY)

# Initialize FastAPI app
app = FastAPI()

# Initialize Telegram Bot Application
application = Application.builder().token(TOKEN).build()

# --- Telegram Bot Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a welcome message when the /start command is issued."""
    user = update.effective_user
    logger.info(f"User {user.id} ({user.first_name}) started the bot.")
    await update.message.reply_html(
        rf"Hi {user.mention_html()}! I'm your AI assistant. How can I help you today?",
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a help message when the /help command is issued."""
    await update.message.reply_text("You can ask me anything! Just type your question.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles incoming text messages and responds using OpenAI."""
    user_message = update.message.text
    user_id = update.effective_user.id
    logger.info(f"User {user_id} sent message: '{user_message}'")

    if not user_message:
        return

    try:
        # Example of using OpenAI (you'll want to refine this for your specific needs)
        response = await openai_client.chat.completions.create(
            model="gpt-3.5-turbo",  # Or "gpt-4", etc.
            messages=[
                {"role": "system", "content": "You are a helpful AI assistant."},
                {"role": "user", "content": user_message},
            ],
            max_tokens=500,
            temperature=0.7,
        )
        ai_response = response.choices[0].message.content
        logger.info(f"OpenAI responded to user {user_id}: '{ai_response}'")
        await update.message.reply_text(ai_response)

    except Exception as e:
        logger.error(f"Error processing message from user {user_id}: {e}")
        await update.message.reply_text("Sorry, I encountered an error while processing your request. Please try again later.")

# --- Register Telegram Handlers ---
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("help", help_command))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# --- FastAPI Endpoints ---

@app.post("/webhook")
async def telegram_webhook(request: Request):
    """Endpoint for Telegram to send updates."""
    try:
        json_data = await request.json()
        update = Update.de_json(json_data, application.bot)
        await application.process_update(update)
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    """Basic root endpoint to check if the FastAPI app is running."""
    return {"message": "Telegram Bot FastAPI backend is running!"}

# --- Main execution block (for setting up webhook if run directly) ---
# Note: When deploying with services like Render, Heroku, or Vercel, they typically
# run your FastAPI app via a Uvicorn command, and you set the webhook once
# manually or via a separate script.
# This block is more for local testing or initial setup.

async def setup_webhook():
    """Sets the Telegram webhook."""
    if WEBHOOK_URL:
        try:
            current_webhook_info = await application.bot.get_webhook_info()
            if current_webhook_info.url != WEBHOOK_URL + "/webhook":
                logger.info(f"Setting webhook to: {WEBHOOK_URL}/webhook")
                await application.bot.set_webhook(url=f"{WEBHOOK_URL}/webhook")
                logger.info("Webhook set successfully.")
            else:
                logger.info("Webhook is already set to the correct URL.")
        except Exception as e:
            logger.error(f"Failed to set webhook: {e}")
    else:
        logger.warning("WEBHOOK_URL is not set. Webhook will not be configured automatically.")

# This block can be used for local testing with polling, or to set webhook on startup
if __name__ == "__main__":
    # If you intend to run this script directly for development/testing,
    # you might want to use polling instead of webhooks or set the webhook here.

    # Option 1: Run with polling (good for local dev without public URL)
    # logger.info("Starting bot in polling mode...")
    # application.run_polling(allowed_updates=Update.ALL_TYPES)

    # Option 2: Set up webhook and then rely on a WSGI server (e.g., uvicorn)
    # to run the FastAPI app.
    # To run with uvicorn: uvicorn main:app --host 0.0.0.0 --port 8000
    # Make sure to run setup_webhook() once after deployment or as part of your
    # deployment pipeline.
    asyncio.run(setup_webhook())
    logger.info("FastAPI app is ready to receive webhook requests.")

