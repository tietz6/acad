#!/bin/bash
# Start the SALESBOT Training System Telegram Bot

echo "🤖 Starting SALESBOT Training System Telegram Bot..."
echo ""

# Check if TELEGRAM_BOT_TOKEN is set
if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
    echo "❌ Error: TELEGRAM_BOT_TOKEN environment variable is not set!"
    echo ""
    echo "Please set your Telegram bot token:"
    echo "  export TELEGRAM_BOT_TOKEN='your-bot-token-here'"
    echo ""
    echo "To get a token:"
    echo "  1. Message @BotFather on Telegram"
    echo "  2. Use /newbot command"
    echo "  3. Follow the instructions"
    echo ""
    exit 1
fi

echo "Backend URL: ${BACKEND_URL:-http://127.0.0.1:8080}"
echo ""
echo "Bot is starting... Press Ctrl+C to stop"
echo ""

cd "$(dirname "$0")"
python simple_telegram_bot.py
