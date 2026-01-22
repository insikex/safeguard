#!/usr/bin/env python3
"""
Safeguard Bot Runner
====================
Main script to run the Safeguard Telegram Bot.

Usage:
    python run.py

Make sure to set up your .env file with the required configuration first.
"""

import os
import sys

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bot.main import run_bot


if __name__ == "__main__":
    print("""
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║   🛡️  SAFEGUARD BOT - Telegram Group Protection          ║
║                                                           ║
║   Version: 1.0.0                                          ║
║   Multi-language: Indonesian 🇮🇩 / English 🇺🇸            ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
    """)
    
    # Check for .env file
    if not os.path.exists('.env') and not os.getenv('BOT_TOKEN'):
        print("⚠️  Warning: No .env file found!")
        print("   Please create a .env file with your BOT_TOKEN")
        print("   You can copy .env.example to .env and fill in your values.")
        print()
    
    try:
        run_bot()
    except ValueError as e:
        print(f"\n❌ Configuration Error: {e}")
        print("   Please check your .env file and ensure BOT_TOKEN is set.")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n👋 Bot stopped by user. Goodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
