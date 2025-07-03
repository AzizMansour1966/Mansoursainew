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
load_dotenv(".env.production") # This will load from .env.production if it exists locally

# Get environment variables without hardcoded defaults
# If these are not set, os.getenv will return None
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# --- IMPORTANT: Add checks to ensure keys are set ---
# This prevents your application from running if the environment variables are missing
if not TOKEN:
    logging.error("TELEGRAM_BOT_TOKEN environment variable is not set. Exiting.")
    exit(1) # Or raise an error as appropriate for your application startup
if not OPENAI_KEY:
    logging.error("OPENAI_API_KEY environment variable is not set. Exiting.")
    exit(1)
if not WEBHOOK_URL:
    logging.error("WEBHOOK_URL environment variable is not set. Exiting.")
    exit(1)
# ----------------------------------------------------

openai.api_key = OPENAI_KEY
nest_asyncio.apply()

# ... rest of your code ...
