from supabase import create_client, Client
import os

# initialize Supabase client with service-role key so we can INSERT
SUPABASE_URL: str = os.getenv("SUPABASE_URL")  # e.g. "https://xyzcompany.supabase.co"
SUPABASE_SERVICE_ROLE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
