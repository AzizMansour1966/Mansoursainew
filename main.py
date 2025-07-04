import os
from fastapi import FastAPI, Request, HTTPException
from telegram import Bot, Update, Message
from telegram.ext import Dispatcher, MessageHandler, Filters
import openai
import asyncio

# --- Configuration ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "YOUR_OPENAI_API_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "YOUR_WEBHOOK_URL") # e.g., "https://your-domain.com/webhook"
AI_PREFIX = "Mansours Family says " # Changed to the new prefix

# Initialize FastAPI app
app = FastAPI()

# Initialize Telegram Bot
bot = Bot(token=TELEGRAM_BOT_TOKEN)

# Initialize OpenAI
openai.api_key = OPENAI_API_KEY

# Simple in-memory storage for conversation history
# In a real application, use a database (e.g., PostgreSQL, Redis)
conversation_history = {} # {chat_id: [{"role": "user", "content": "..."}]}

# --- Telegram Update Handler ---
async def handle_telegram_update(update: Update):
    if update.message and update.message.text:
        chat_id = update.message.chat_id
        user_message = update.message.text

        # Get or initialize conversation history for this chat
        if chat_id not in conversation_history:
            conversation_history[chat_id] = []

        # Add user message to history
        conversation_history[chat_id].append({"role": "user", "content": user_message})

        try:
            # Prepare messages for OpenAI (last few turns for context)
            # You might want to limit the number of messages sent to keep costs down
            messages_for_openai = conversation_history[chat_id][-5:] # Last 5 messages for context

            # Get AI response from OpenAI
            response = openai.chat.completions.create(
                model="gpt-3.5-turbo", # Or "gpt-4", "gpt-4o" etc.
                messages=messages_for_openai
            )
            ai_reply_content = response.choices[0].message.content.strip()

            # Add AI prefix to the reply
            final_ai_reply = AI_PREFIX + ai_reply_content

            # Add AI reply to history
            conversation_history[chat_id].append({"role": "assistant", "content": ai_reply_content}) # Store original content without prefix

            # Send the reply back to Telegram
            await bot.send_message(chat_id=chat_id, text=final_ai_reply)

        except Exception as e:
            print(f"Error processing message for chat_id {chat_id}: {e}")
            await bot.send_message(chat_id=chat_id, text=f"{AI_PREFIX}I encountered an error trying to process your request. Please try again later.")

# --- FastAPI Endpoints ---

@app.on_event("startup")
async def startup_event():
    # Set the webhook when the app starts
    print(f"Setting webhook to: {WEBHOOK_URL}")
    try:
        await bot.set_webhook(url=WEBHOOK_URL)
        print("Webhook set successfully!")
    except Exception as e:
        print(f"Failed to set webhook: {e}")
        # In a production environment, you might want to retry or log this more robustly

@app.post("/webhook")
async def telegram_webhook(request: Request):
    try:
        update_json = await request.json()
        update = Update.de_json(update_json, bot)
        await handle_telegram_update(update)
        return {"status": "ok"}
    except Exception as e:
        print(f"Error processing webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    return {"message": "Telegram Bot is running! Send updates to /webhook"}

# To run this file:
# 1. Save it as main.py
# 2. Set your environment variables:
#    export TELEGRAM_BOT_TOKEN="YOUR_TELEGRAM_BOT_TOKEN"
#    export OPENAI_API_KEY="YOUR_OPENAI_API_KEY"
#    export WEBHOOK_URL="https://your-domain.com/webhook"
# 3. Run with uvicorn:
#    uvicorn main:app --host 0.0.0.0 --port 8000
