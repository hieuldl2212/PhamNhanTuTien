import os
from dotenv import load_dotenv

load_dotenv()
GROQ_API_KEY = os.getenv('GROQ_API_KEY') 
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY') 
PREFIX = '!'
DB_NAME = 'bot_users.db'
