import os
import logging
from supabase import create_client, Client

logger = logging.getLogger(__name__)

# Config from environment variables (recommended for Vercel)
# Defaults are provided from the user's input for convenience
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://ckxbcvqgenttfecfkpjy.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "sb_publishable_P1yJuVEJx_Qw-kSL9DOK0w_P2G38GoZ")

supabase: Client = None

def init_supabase():
    global supabase
    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.error("Missing SUPABASE_URL or SUPABASE_KEY environment variables")
        return None
    
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        logger.info("Supabase client initialized successfully")
        return supabase
    except Exception as e:
        logger.error(f"Failed to initialize Supabase client: {e}")
        return None

# Initialize on import
init_supabase()
