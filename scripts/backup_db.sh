#!/bin/sh

# Load environment variables
source .env

# Get the current date in the format dd_mm_yyyy
current_date=$(date +'%d_%m_%Y')

# Ensure the backup directory exists
mkdir -p ./db_backups

# Define the destination file name
destination_file="./db_backups/${current_date}.db"

# Use scp to copy the file from the remote server docker volume to the local machine
scp "$HOST:/var/lib/docker/volumes/chatgpt_telegram_bot_sqlite-volume/_data/sqlite.db" "$destination_file"
