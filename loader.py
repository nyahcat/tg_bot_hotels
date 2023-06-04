import os
from dotenv import load_dotenv
from telebot import TeleBot
from telebot.types import Update
from flask import Flask, request
import time
from models import UserHistory
from ngrok_loader import run_ngrok
from loguru import logger
from typing import List, Optional, Tuple

__all__ = ['Optional', 'List', 'bot', 'headers', 'city_finder_url',
           'hotels_finder_url', 'photos_finder_url', 'app', 'logger']

app = Flask(__name__)


@app.route('/', methods=['POST'])
def web_hook() -> Tuple[str, int]:
    """
    Установка веб-хука для бота.
    :return: Tuple[str, int] - статус код.
    """
    bot.process_new_updates([Update.de_json(request.stream.read().decode('utf-8'))])
    return 'OK', 200


city_finder_url = "https://hotels4.p.rapidapi.com/locations/v2/search"
hotels_finder_url = "https://hotels4.p.rapidapi.com/properties/list"
photos_finder_url = "https://hotels4.p.rapidapi.com/properties/get-hotel-photos"

load_dotenv()
bot_token = os.getenv('BOT_TOKEN')
bot = TeleBot(bot_token)
bot_url = run_ngrok()
bot.remove_webhook()
time.sleep(1)
bot.set_webhook(url=bot_url)


api_token = os.getenv('API_KEY')
headers = {
        'x-rapidapi-host': "hotels4.p.rapidapi.com",
        'x-rapidapi-key': api_token
    }

if 'history.db' not in os.listdir():
    UserHistory.create_table()
    logger.info('database file created')
logger.success(f'ngrok started at {bot_url}')
