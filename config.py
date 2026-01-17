"""
Configuration module for the Book Generation System.
Loads environment variables and provides centralized config access.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from the project root
PROJECT_ROOT = Path(__file__).parent
load_dotenv(PROJECT_ROOT / ".env")


class Config:
    """Centralized configuration for the book generation system."""
    
    # ==========================================================================
    # PROJECT PATHS
    # ==========================================================================
    PROJECT_ROOT = PROJECT_ROOT
    INPUT_DIR = PROJECT_ROOT / "input"
    OUTPUT_DIR = PROJECT_ROOT / "output"
    
    # ==========================================================================
    # SUPABASE CONFIG
    # ==========================================================================
    SUPABASE_URL = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
    
    # ==========================================================================
    # GEMINI CONFIG
    # ==========================================================================
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")
    
    # ==========================================================================
    # EMAIL NOTIFICATIONS
    # ==========================================================================
    SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
    NOTIFICATION_EMAIL = os.getenv("NOTIFICATION_EMAIL", "")
    
    # ==========================================================================
    # OPTIONAL: MS TEAMS
    # ==========================================================================
    TEAMS_WEBHOOK_URL = os.getenv("TEAMS_WEBHOOK_URL", "")
    
    @classmethod
    def validate(cls) -> dict:
        """Validate that required config values are set."""
        issues = {}
        
        if not cls.SUPABASE_URL:
            issues["SUPABASE_URL"] = "Missing Supabase URL"
        if not cls.SUPABASE_KEY:
            issues["SUPABASE_KEY"] = "Missing Supabase Key"
        if not cls.GEMINI_API_KEY:
            issues["GEMINI_API_KEY"] = "Missing Gemini API Key"
            
        return issues
    
    @classmethod
    def print_status(cls):
        """Print configuration status for debugging."""
        print("=" * 60)
        print("BOOK GENERATION SYSTEM - CONFIGURATION STATUS")
        print("=" * 60)
        
        print(f"\n📁 Project Root: {cls.PROJECT_ROOT}")
        print(f"📁 Input Dir: {cls.INPUT_DIR}")
        print(f"📁 Output Dir: {cls.OUTPUT_DIR}")
        
        print(f"\n🗄️  Supabase URL: {'✓ Set' if cls.SUPABASE_URL else '✗ Missing'}")
        print(f"🗄️  Supabase Key: {'✓ Set' if cls.SUPABASE_KEY else '✗ Missing'}")
        
        print(f"\n🤖 Gemini Key: {'✓ Set' if cls.GEMINI_API_KEY else '✗ Missing'}")
        print(f"🤖 Gemini Model: {cls.GEMINI_MODEL}")
        
        print(f"\n📧 SMTP Host: {cls.SMTP_HOST}")
        print(f"📧 SMTP User: {'✓ Set' if cls.SMTP_USER else '✗ Missing'}")
        print(f"📧 Notification Email: {'✓ Set' if cls.NOTIFICATION_EMAIL else '✗ Missing'}")
        
        print(f"\n🔗 Teams Webhook: {'✓ Set' if cls.TEAMS_WEBHOOK_URL else 'Not configured'}")
        
        # Validate
        issues = cls.validate()
        if issues:
            print("\n⚠️  CONFIGURATION ISSUES:")
            for key, msg in issues.items():
                print(f"   - {key}: {msg}")
        else:
            print("\n✅ All required configuration is set!")
        
        print("=" * 60)


# Create directories if they don't exist
Config.INPUT_DIR.mkdir(exist_ok=True)
Config.OUTPUT_DIR.mkdir(exist_ok=True)


if __name__ == "__main__":
    # Test configuration when run directly
    Config.print_status()
