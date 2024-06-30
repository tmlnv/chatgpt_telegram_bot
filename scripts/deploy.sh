#!/bin/sh

# Load environment variables
source .env

# Sync the entire directory excluding files listed in .gitignore
rsync -azP --exclude-from='.gitignore' . $HOST:/root/chatgpt_telegram_bot/
