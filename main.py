import os
import logging
from fastapi import FastAPI, Request, HTTPException
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

application = Application.builder().token(TOKEN).build()

# Telegram command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Hello! FastAPI bot is alive!")

application.add_handler(CommandHandler("start", start))

@app.on_event("startup")
async def startup():
    logger.info("Starting Telegram Application")
    await application.initialize()
    await application.bot.set_webhook(f"{WEBHOOK_URL}/webhook")
    logger.info(f"Webhook set to {WEBHOOK_URL}/webhook")

@app.post("/webhook")
async def telegram_webhook(request: Request):
    try:
        json_data = await request.json()
        update = Update.de_json(json_data, application.bot)
        await application.process_update(update)
        logger.info("Processed update successfully")
        return {"status": "ok"}
    except Exception as e:
        logger.exception(f"Error processing update: {e}")
        raise HTTPException(status_code=500, detail="Error processing update")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
