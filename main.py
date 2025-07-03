import os
import logging
import re
from contextlib import asynccontextmanager # For FastAPI lifespan events
from fastapi import FastAPI, Request, HTTPException
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv
from openai import AsyncOpenAI
import asyncio
import nest_asyncio

# Load environment variables from .env.production
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
    # For a production deployment with webhooks, this is critical.
    exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Apply nest_asyncio for compatibility with FastAPI and other async libraries
# This is often needed when running nested event loops, but with FastAPI's
# built-in async handling and proper ptb setup, it might not always be strictly necessary,
# but it doesn't hurt to keep it if you encounter issues.
nest_asyncio.apply()

# Initialize OpenAI client
openai_client = AsyncOpenAI(api_key=OPENAI_KEY)

# Declare application globally but initialize it within the lifespan context
application: Application = None

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
    await update.message.reply_text("You can ask me anything! Just type your question or use commands like /start.")

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
                {"role": "system", "content": "You are a helpful AI assistant. Respond concisely."},
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

# --- Placeholder for the problematic handler ---
async def send_keyword_joke(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a joke when the 'joke' keyword is detected."""
    logger.info(f"User {update.effective_user.id} requested a joke.")
    await update.message.reply_text("Why don't scientists trust atoms? Because they make up everything!")

# --- FastAPI Lifespan Events ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles startup and shutdown events for the FastAPI application,
    including initializing and starting/stopping the Telegram bot Application.
    """
    global application # Access the global application variable
    logger.info("FastAPI app starting up...")

    # Initialize the Telegram Application
    application = Application.builder().token(TOKEN).build()

    # Register Telegram Handlers here (important to do it AFTER application is built)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    # Corrected Regex filter usage:
    # filters.Regex takes the pattern as the first argument, and optionally flags as the second.
    # The handler function is the second argument to MessageHandler.
    application.add_handler(MessageHandler(filters.Regex('^joke$', re.IGNORECASE), send_keyword_joke))


    # Set the webhook for the Telegram bot
    try:
        current_webhook_info = await application.bot.get_webhook_info()
        expected_webhook_url = f"{WEBHOOK_URL}/webhook"
        if current_webhook_info.url != expected_webhook_url:
            logger.info(f"Setting webhook to: {expected_webhook_url}")
            await application.bot.set_webhook(url=expected_webhook_url)
            logger.info("Webhook set successfully.")
        else:
            logger.info("Webhook is already set to the correct URL.")
    except Exception as e:
        logger.error(f"Failed to set webhook on startup: {e}")
        # Depending on your deployment, you might want to exit here if webhook setup is critical.

    # Start the Telegram bot's update processing (in webhook mode, this just prepares it)
    await application.initialize()
    await application.start()
    logger.info("Telegram Bot Application initialized and started.")

    yield # FastAPI application is running

    # --- Shutdown events ---
    logger.info("FastAPI app shutting down...")
    if application:
        logger.info("🛑 Shutting down Telegram bot application...")
        try:
            await application.stop()
            await application.shutdown() # Ensures clean shutdown of internal PTB resources
            logger.info("Telegram Bot Application stopped and shut down cleanly.")
        except Exception as e:
            logger.error(f"Error during Telegram bot shutdown: {e}")

# Initialize FastAPI app with lifespan events
app = FastAPI(lifespan=lifespan)

# --- FastAPI Endpoints ---

@app.post("/webhook")
async def telegram_webhook(request: Request):
    """Endpoint for Telegram to send updates."""
    if not application:
        logger.error("Telegram Application not initialized during webhook request.")
        raise HTTPException(status_code=503, detail="Telegram Bot Application not ready.")

    try:
        json_data = await request.json()
        update = Update.de_json(json_data, application.bot)
        # Process the update using the initialized application
        await application.process_update(update)
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        # Log the full traceback for debugging in production
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error processing update: {e}")

@app.get("/")
async def root():
    """Basic root endpoint to check if the FastAPI app is running."""
    return {"message": "Telegram Bot FastAPI backend is running!", "status": "active"}

# The `if __name__ == "__main__":` block for running Uvicorn directly is usually
# removed when deploying with a WSGI server like Uvicorn that calls `uvicorn main:app`.
# However, if you want to run it locally without a separate uvicorn command:
if __name__ == "__main__":
    import uvicorn
    # This will run FastAPI using uvicorn, and the lifespan event will handle
    # the Telegram bot initialization and webhook setup.
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))

