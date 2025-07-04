import os
import logging
import re
from contextlib import asynccontextmanager
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
    exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Apply nest_asyncio for compatibility with FastAPI and other async libraries
nest_asyncio.apply()

# Initialize OpenAI client
openai_client = AsyncOpenAI(api_key=OPENAI_KEY)

# Declare application globally but initialize it within the lifespan context
application: Application = None

# --- Conversation History Storage (In-memory for simplicity) ---
# In a real-world scenario, use a database (e.g., Redis, PostgreSQL)
# to persist conversation history across restarts and for scalability.
user_conversations = {} # Stores messages for each user: {user_id: [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}, ...]}

# --- Telegram Bot Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a welcome message and initial buttons when the /start command is issued."""
    user = update.effective_user
    user_id = user.id
    logger.info(f"User {user_id} ({user.first_name}) started the bot.")

    # Initialize conversation history for this user
    user_conversations[user_id] = [{"role": "system", "content": "You are a helpful AI assistant."}]

    # Define reply keyboard with buttons
    keyboard = [
        [KeyboardButton("Tell me a joke"), KeyboardButton("Tell me a story")],
        [KeyboardButton("What can you do?"), KeyboardButton("Clear chat")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

    await update.message.reply_html(
        rf"Hi {user.mention_html()}! I'm your AI assistant. How can I help you today?",
        reply_markup=reply_markup # Attach the keyboard
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a help message when the /help command is issued."""
    await update.message.reply_text("You can ask me anything! Try 'Tell me a joke', 'Tell me a story', or use /start to see quick options.")

async def clear_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Clears the conversation history for the current user."""
    user_id = update.effective_user.id
    if user_id in user_conversations:
        user_conversations[user_id] = [{"role": "system", "content": "You are a helpful AI assistant."}]
        await update.message.reply_text("Chat history cleared! You can start a new conversation.")
        logger.info(f"Chat history cleared for user {user_id}.")
    else:
        await update.message.reply_text("No chat history to clear.")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles incoming text messages and responds using OpenAI, maintaining conversation history."""
    user_message = update.message.text
    user_id = update.effective_user.id
    logger.info(f"User {user_id} sent message: '{user_message}'")

    if not user_message:
        return

    # Ensure conversation history exists for this user
    if user_id not in user_conversations:
        user_conversations[user_id] = [{"role": "system", "content": "You are a helpful AI assistant."}]

    # Add user message to history
    user_conversations[user_id].append({"role": "user", "content": user_message})

    # Optional: Truncate history to avoid exceeding token limits for long conversations
    # This is a simple truncation. For more advanced methods, consider libraries like langchain.
    # Keep last N messages, excluding the system prompt which is always first.
    max_history_messages = 10
    if len(user_conversations[user_id]) > max_history_messages + 1: # +1 for the system message
        user_conversations[user_id] = [user_conversations[user_id][0]] + user_conversations[user_id][-(max_history_messages):]


    try:
        # Use the full conversation history for context
        response = await openai_client.chat.completions.create(
            model="gpt-3.5-turbo", # Or "gpt-4", etc., if available and desired
            messages=user_conversations[user_id],
            max_tokens=500,
            temperature=0.7,
        )
        ai_response = response.choices[0].message.content
        logger.info(f"OpenAI responded to user {user_id}: '{ai_response}'")

        # Add AI response to history
        user_conversations[user_id].append({"role": "assistant", "content": ai_response})

        await update.message.reply_text(ai_response)

    except Exception as e:
        logger.error(f"Error processing message from user {user_id}: {e}")
        await update.message.reply_text("Sorry, I encountered an error while processing your request. Please try again later.")
        # Revert last user message from history if error occurred to avoid confusing the AI
        if user_conversations[user_id] and user_conversations[user_id][-1]["role"] == "user":
            user_conversations[user_id].pop()


async def send_keyword_joke(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a joke generated by OpenAI when 'joke' keyword is detected."""
    user_id = update.effective_user.id
    logger.info(f"User {user_id} requested a joke.")

    if user_id not in user_conversations:
        user_conversations[user_id] = [{"role": "system", "content": "You are a helpful AI assistant."}]

    # Temporarily add a specific user message to history for joke generation
    # Or keep it out if you want the joke to be a standalone, context-less response
    joke_prompt = "Tell me a short, funny, family-friendly joke."
    messages_for_joke = user_conversations[user_id] + [{"role": "user", "content": joke_prompt}]


    try:
        response = await openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": "You are a helpful comedian bot."},
                      {"role": "user", "content": joke_prompt}],
            max_tokens=150,
            temperature=0.9, # Higher temperature for more creative jokes
        )
        joke = response.choices[0].message.content
        await update.message.reply_text(joke)
        logger.info(f"OpenAI generated joke for user {user_id}: '{joke}'")
        # Add the joke to history for context
        user_conversations[user_id].append({"role": "assistant", "content": joke})

    except Exception as e:
        logger.error(f"Error generating joke for user {user_id}: {e}")
        await update.message.reply_text("Sorry, I couldn't come up with a joke right now. Please try again later.")

# --- FastAPI Lifespan Events ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles startup and shutdown events for the FastAPI application,
    including initializing and starting/stopping the Telegram bot Application.
    """
    global application
    logger.info("FastAPI app starting up...")

    # Initialize the Telegram Application
    application = Application.builder().token(TOKEN).build()

    # Register Telegram Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("clear_chat", clear_chat)) # New command for clearing history

    # Add handlers for buttons/keywords
    application.add_handler(MessageHandler(filters.Regex('(?i)^tell me a joke$'), send_keyword_joke))
    application.add_handler(MessageHandler(filters.Regex('(?i)^tell me a story$'), handle_message)) # Direct to general handler
    application.add_handler(MessageHandler(filters.Regex('(?i)^what can you do\\?$'), handle_message)) # Direct to general handler
    application.add_handler(MessageHandler(filters.Regex('(?i)^clear chat$'), clear_chat)) # Button for clearing chat

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)) # Fallback for all other text


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

    # Start the Telegram bot's update processing
    await application.initialize()
    await application.start()
    logger.info("Telegram Bot Application initialized and started.")

    yield

    # --- Shutdown events ---
    logger.info("FastAPI app shutting down...")
    if application:
        logger.info("🛑 Shutting down Telegram bot application...")
        try:
            await application.stop()
            await application.shutdown()
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
        await application.process_update(update)
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error processing update: {e}")

@app.get("/")
async def root():
    """Basic root endpoint to check if the FastAPI app is running."""
    return {"message": "Telegram Bot FastAPI backend is running!", "status": "active"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
