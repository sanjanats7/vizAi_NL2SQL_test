"""
Configuration settings for the Finance Manager Analytics application.
"""
import os
from urllib.parse import quote_plus
from dotenv import load_dotenv

load_dotenv()

DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = quote_plus(os.getenv("DB_PASSWORD", "Viridian@7"))
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_NAME = os.getenv("DB_NAME", "classicmodels")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_TYPE = "postgres"

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
LLM_MODEL = os.getenv("LLM_MODEL", "gemini-1.5-pro")

# CONNECTION_STRING = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
CONNECTION_STRING = f"postgresql://neondb_owner:npg_zRarqn8j1BQu@ep-holy-surf-a5zvvzwg-pooler.us-east-2.aws.neon.tech/neondb?sslmode=require"

DEFAULT_NUM_QUERIES = int(os.getenv("DEFAULT_NUM_QUERIES", "3"))