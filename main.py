import logging
import nest_asyncio
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
from telegram import Bot, Update
from telegram.error import TelegramError
import asyncio
import os

# Apply nest_asyncio to allow nested event loops on Render or Jupyter
nest_asyncio.apply()

# Configure logging - detailed and clear
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load tokens from environment variables
TOKEN = os.getenv('BOT_TOKEN')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')
if not TOKEN or not WEBHOOK_URL:
    logger.error("BOT_TOKEN or WEBHOOK_URL environment variable missing!")
    raise RuntimeError("BOT_TOKEN or WEBHOOK_URL environment variable missing!")

bot = Bot(token=TOKEN)
app = FastAPI()

class TelegramUpdate(BaseModel):
    update_id: int

@app.on_event("startup")
async def startup_event():
    try:
        # Set webhook, ignore if already set
        result = await bot.set_webhook(WEBHOOK_URL)
        logger.info(f"Webhook set response: {result}")
    except TelegramError as e:
        logger.error(f"Error setting webhook: {e}")

@app.post("/webhook")
async def telegram_webhook(update: TelegramUpdate, request: Request):
    try:
        json_update = await request.json()
        update_obj = Update.de_json(json_update, bot)
        logger.info(f"Received update: {update_obj.update_id}")
        # Add your update handling logic here
        # For example, reply to /start command:
        if update_obj.message and update_obj.message.text == '/start':
            chat_id = update_obj.message.chat.id
            await bot.send_message(chat_id=chat_id, text="👋 Hello! I'm alive and ready!")
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Exception handling update: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Root path can show simple health check
@app.get("/")
def read_root():
    return {"status": "bot is running"}

# Run with: uvicorn main:app --host 0.0.0.0 --port $PORT
