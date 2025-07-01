import os
import logging
from fastapi import FastAPI, Request, HTTPException
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
PORT = int(os.getenv("PORT", 8000))

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

app = FastAPI()

# Create Telegram application (async)
application = Application.builder().token(TOKEN).build()

# Command handler for /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Received /start from user {update.effective_user.id}")
    await update.message.reply_text("👋 Hello! Bot is alive and ready!")

application.add_handler(CommandHandler("start", start))

# Healthcheck endpoint
@app.get("/")
async def read_root():
    return {"status": "Bot server is running"}

# Telegram webhook endpoint
@app.post("/webhook")
async def telegram_webhook(request: Request):
    try:
        data = await request.json()
        update = Update.de_json(data, application.bot)
        logger.info(f"Webhook update received: {data}")

        await application.process_update(update)

        return {"ok": True}
    except Exception as e:
        logger.error(f"Error processing update: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")

# Startup event to set webhook on Telegram side
@app.on_event("startup")
async def on_startup():
    webhook_url = f"{WEBHOOK_URL}/webhook"
    logger.info(f"Setting webhook: {webhook_url}")
    success = await application.bot.set_webhook(webhook_url)
    if success:
        logger.info("Webhook set successfully")
    else:
        logger.error("Failed to set webhook")

if __name__ == "__main__":
    import uvicorn
    logger.info(f"Starting FastAPI app on port {PORT}")
    uvicorn.run(app, host="0.0.0.0", port=PORT)
