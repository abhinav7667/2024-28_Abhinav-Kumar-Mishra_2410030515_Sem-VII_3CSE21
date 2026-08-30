"""
config.py — Application configuration for NetSage AI
"""
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Flask
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "netsage-ai-dev-key-2024")
    DEBUG = os.getenv("FLASK_DEBUG", "true").lower() == "true"

    # Database
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'netsage.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # AI Provider
    DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() == "true"
    AI_PROVIDER = os.getenv("AI_PROVIDER", "openai")
    AI_API_KEY = os.getenv("AI_API_KEY", "")
    AI_MODEL = os.getenv("AI_MODEL", "gpt-4o")

    # Paths
    DATA_DIR = os.path.join(BASE_DIR, "data")
    PROMPTS_DIR = os.path.join(BASE_DIR, "prompts")
    CASES_CSV = os.path.join(DATA_DIR, "cases.csv")
    DIAGNOSE_PROMPT = os.path.join(PROMPTS_DIR, "diagnose_prompt.md")
