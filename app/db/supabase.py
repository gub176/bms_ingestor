from supabase import create_client, Client
from app.core.config import settings
from app.core.exceptions import SupabaseNotInitializedException
from loguru import logger


_client: Client = None


def get_supabase() -> Client:
    """Get or create Supabase client (lazy initialization)"""
    global _client
    if _client is None:
        try:
            logger.info(f"Creating Supabase client for URL: {settings.supabase_url}")
            _client = create_client(
                settings.supabase_url,
                settings.supabase_service_key
            )
            logger.info("Supabase client created successfully")
        except Exception as e:
            logger.error(f"Failed to create Supabase client: {e}")
            raise SupabaseNotInitializedException(f"Supabase client initialization failed: {e}")
    return _client


# For backward compatibility - lazy initialization only when accessed
def __getattr__(name):
    if name == "supabase":
        return get_supabase()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
