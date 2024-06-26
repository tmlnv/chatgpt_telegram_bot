import asyncio
import html
import json
import traceback
from datetime import datetime

from loguru import logger
from telegram import BotCommand, InlineKeyboardButton, InlineKeyboardMarkup, Update, User
from telegram.constants import ParseMode
from telegram.error import BadRequest
from telegram.ext import (
    AIORateLimiter,
    Application,
    ApplicationBuilder,
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters
)

import chatgpt
import conf as config
import database_sqlite

# setup
db = database_sqlite.SqliteDataBase(config.sqlite_database_uri)
user_semaphores = {}

HELP_MESSAGE = """Commands:
/new – 🆕 Start new conversation
/mode – ↕️ Select chat mode
/retry – 🔁 Regenerate last bot answer
/help – ℹ️ Show help
"""

# Dictionary to track if we're expecting a chat mode selection from a user
expecting_mode_selection: dict[int, dict[str, bool | int]] = {}


def split_text_into_chunks(text, chunk_size):
    for i in range(0, len(text), chunk_size):
        yield text[i:i + chunk_size]


async def register_user_if_not_exists(update: Update, context: CallbackContext, user: User):
    if not db.check_if_user_exists(user.id):
        db.add_new_user(
            user.id,
            update.message.chat_id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )
        db.start_new_dialog(user.id)

    if db.get_user_attribute(user.id, "current_dialog_id") is None:
        db.start_new_dialog(user.id)

    if user.id not in user_semaphores:
        user_semaphores[user.id] = asyncio.Semaphore(1)

    if db.get_user_attribute(user.id, "current_chat_mode") is None:
        db.set_user_attribute(user_id=user.id, key="current_chat_mode", value="assistant")


async def start_handle(update: Update, context: CallbackContext):
    await register_user_if_not_exists(update, context, update.message.from_user)
    user_id = update.message.from_user.id

    db.set_user_attribute(user_id, "last_interaction", datetime.now())
    db.start_new_dialog(user_id)

    reply_text = "This is the <b>ChatGPT</b> Telegram Bot, powered by advanced AI language processing.\n\n"
    reply_text += HELP_MESSAGE
    reply_text += "\nIt can provide personalized recommendations and real-time responses to a wide range of" \
                  " natural language queries. Enjoy!"

    await update.message.reply_text(reply_text, parse_mode=ParseMode.HTML)


async def help_handle(update: Update, context: CallbackContext):
    await register_user_if_not_exists(update, context, update.message.from_user)
    user_id = update.message.from_user.id
    db.set_user_attribute(user_id, "last_interaction", datetime.now())
    await update.message.reply_text(HELP_MESSAGE, parse_mode=ParseMode.HTML)


async def retry_handle(update: Update, context: CallbackContext):
    await register_user_if_not_exists(update, context, update.message.from_user)
    if await is_previous_message_not_answered_yet(update, context):
        return

    user_id = update.message.from_user.id
    db.set_user_attribute(user_id, "last_interaction", datetime.now())

    last_dialog_message = db.remove_dialog_last_message(user_id)
    if last_dialog_message is None:
        await update.message.reply_text("🤷‍♂️ No message to retry")
        return

    await message_handle(update, context, message=last_dialog_message["user"], use_new_dialog_timeout=False)


async def message_handle(update: Update, context: CallbackContext, message=None, use_new_dialog_timeout=True):
    # check if message is edited
    if update.edited_message is not None:
        await edited_message_handle(update, context)
        return

    await register_user_if_not_exists(update, context, update.message.from_user)
    if await is_previous_message_not_answered_yet(update, context):
        return

    user_id = update.message.from_user.id
    chat_mode = db.get_user_attribute(user_id, "current_chat_mode")

    # New check for chat mode selection
    if await is_chat_mode_selection_handle(update, context):
        return  # If the message was handled as a chat mode selection, exit early

    async with user_semaphores[user_id]:
        # new dialog timeout
        if use_new_dialog_timeout:
            if (
                    datetime.now() - db.get_user_attribute(user_id, "last_interaction")
            ).seconds > config.new_dialog_timeout and len(db.get_dialog_messages(user_id)) > 0:
                db.start_new_dialog(user_id)
                await update.message.reply_text(
                    f'💬 Starting new dialog due to timeout (<b>{chatgpt.CHAT_MODES[chat_mode]["name"]}'
                    f'</b> mode).',
                    parse_mode=ParseMode.HTML)
        db.set_user_attribute(user_id, "last_interaction", datetime.now())

        try:

            # send placeholder message to user
            placeholder_message = await update.message.reply_text("...")

            # send typing action
            await update.message.chat.send_action(action="typing")

            message = message or update.message.text

            dialog_messages = db.get_dialog_messages(user_id, dialog_id=None)
            parse_mode = {
                "html": ParseMode.HTML,
                "markdown": ParseMode.MARKDOWN
            }[chatgpt.CHAT_MODES[chat_mode]["parse_mode"]]

            chatgpt_instance = chatgpt.ChatGPT()
            if config.enable_message_streaming:
                gen = chatgpt_instance.send_message_stream(message, dialog_messages=dialog_messages,
                                                           chat_mode=chat_mode)
            else:
                answer, prompt, n_first_dialog_messages_removed = await chatgpt_instance.send_message(
                    message,
                    dialog_messages=dialog_messages,
                    chat_mode=chat_mode
                )

                async def fake_gen():
                    yield "finished", answer, prompt, n_first_dialog_messages_removed

                gen = fake_gen()

            prev_answer = ""
            answer = ""
            async for gen_item in gen:
                status, answer, prompt, n_first_dialog_messages_removed = gen_item

                answer = answer[:4096]  # telegram message limit

                # update only when 100 new symbols are ready
                if abs(len(answer) - len(prev_answer)) < 100 and status != "finished":
                    continue

                try:
                    await context.bot.edit_message_text(
                        text=answer,
                        chat_id=placeholder_message.chat_id,
                        message_id=placeholder_message.message_id,
                        parse_mode=parse_mode
                    )
                except BadRequest as e:
                    if str(e).startswith("Message is not modified"):
                        continue

                    await context.bot.edit_message_text(
                        text=answer,
                        chat_id=placeholder_message.chat_id,
                        message_id=placeholder_message.message_id
                    )

                await asyncio.sleep(0.01)  # wait a bit to avoid flooding

                prev_answer = answer

            # update user data
            new_dialog_message = {"user": message, "bot": answer, "date": datetime.now()}
            db.append_dialog_message(user_id, new_dialog_message, dialog_id=None)

        except Exception as e:
            error_text = f"Something went wrong during completion. Reason: {e}"
            logger.error(error_text)
            await update.message.reply_text(error_text)
            return

        # send message if some messages were removed from the context
        if n_first_dialog_messages_removed > 0:
            if n_first_dialog_messages_removed == 1:
                text = "✂️ <i>Note:</i> Your current dialog is too long, so your <b>first message</b> was removed" \
                       " from the context.\n Send /new command to start new dialog."
            else:
                text = f"✂️ <i>Note:</i> Your current dialog is too long, so" \
                       f" <b>{n_first_dialog_messages_removed} first messages</b> were removed from the context.\n " \
                       f"Send /new command to start new dialog."
            await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def is_previous_message_not_answered_yet(update: Update, context: CallbackContext):
    await register_user_if_not_exists(update, context, update.message.from_user)

    user_id = update.message.from_user.id
    if user_semaphores[user_id].locked():
        text = "⏳ Please <b>wait</b> for a reply to the previous message"
        await update.message.reply_text(text, reply_to_message_id=update.message.id, parse_mode=ParseMode.HTML)
        return True
    else:
        return False


async def new_dialog_handle(update: Update, context: CallbackContext):
    await register_user_if_not_exists(update, context, update.message.from_user)
    if await is_previous_message_not_answered_yet(update, context):
        return

    user_id = update.message.from_user.id
    db.set_user_attribute(user_id, "last_interaction", datetime.now())

    db.start_new_dialog(user_id)
    await update.message.reply_text("💬 Starting new dialog.")

    chat_mode = db.get_user_attribute(user_id, "current_chat_mode")
    await update.message.reply_text(f"{chatgpt.CHAT_MODES[chat_mode]['welcome_message']}", parse_mode=ParseMode.HTML)


async def show_chat_modes_handle(update: Update, context: CallbackContext):
    await register_user_if_not_exists(update, context, update.message.from_user)
    if await is_previous_message_not_answered_yet(update, context):
        return

    user_id = update.message.from_user.id
    db.set_user_attribute(user_id, "last_interaction", datetime.now())
    logger.info("User {} is setting chat mode", user_id)

    keyboard = []
    for i, (chat_mode, chat_mode_dict) in enumerate(chatgpt.CHAT_MODES.items(), start=1):
        keyboard.append([InlineKeyboardButton(
            text=f'{i}. {chat_mode_dict["name"]}',
            callback_data=f"set_chat_mode|{chat_mode}")]
        )
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Send the reply and capture the result
    sent_message = await update.message.reply_text("Select chat mode:", reply_markup=reply_markup)

    # Store the message ID of the bot's reply
    expecting_mode_selection[user_id] = {
        "expecting": True,
        "message_id": sent_message.message_id,  # This is the bot's message ID
        "chat_id": sent_message.chat_id
    }


async def is_chat_mode_selection_handle(update: Update, context: CallbackContext) -> bool:
    user_id = update.message.from_user.id
    if user_id in expecting_mode_selection and expecting_mode_selection[user_id]["expecting"]:
        text = update.message.text.strip()
        if text.isdigit():
            option_number = int(text)
            chat_modes = list(chatgpt.CHAT_MODES.keys())

            if 1 <= option_number <= len(chat_modes):
                chat_mode = chat_modes[option_number - 1]

                await context.bot.edit_message_text(
                    text=f"{chatgpt.CHAT_MODES[chat_mode]['welcome_message']}",
                    parse_mode=ParseMode.HTML,
                    chat_id=expecting_mode_selection[user_id]["chat_id"],
                    message_id=expecting_mode_selection[user_id]["message_id"]
                )

                del expecting_mode_selection[user_id]  # Clear the state after selection

                db.set_user_attribute(user_id, "current_chat_mode", chat_mode)
                db.start_new_dialog(user_id)
                logger.info(
                    "User {} set chat mode to {} via number sending",
                    user_id,
                    chat_mode
                )

                return True
    return False


async def set_chat_mode_handle(update: Update, context: CallbackContext):
    await register_user_if_not_exists(update.callback_query, context, update.callback_query.from_user)
    user_id = update.callback_query.from_user.id

    query = update.callback_query
    await query.answer()

    chat_mode = query.data.split("|")[1]

    db.set_user_attribute(user_id, "current_chat_mode", chat_mode)
    db.start_new_dialog(user_id)
    logger.info("User {} set chat mode to {} via message selection options (tg keyboard)", user_id, chat_mode)

    del expecting_mode_selection[user_id]  # Clear the state after selection

    await query.edit_message_text(f"{chatgpt.CHAT_MODES[chat_mode]['welcome_message']}", parse_mode=ParseMode.HTML)


async def edited_message_handle(update: Update, context: CallbackContext):
    text = "🥲 Unfortunately, message <b>editing</b> is not supported"
    await update.edited_message.reply_text(text, parse_mode=ParseMode.HTML)


async def error_handle(update: Update, context: CallbackContext) -> None:
    logger.error(f"Exception while handling an update: {context.error}")

    try:
        # collect error message
        tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
        tb_string = "".join(tb_list)[:2000]
        update_str = update.to_dict() if isinstance(update, Update) else str(update)
        message = (
            f"An exception was raised while handling an update\n"
            f"<pre>update = {html.escape(json.dumps(update_str, indent=2, ensure_ascii=False))}"
            "</pre>\n\n"
            f"<pre>{html.escape(tb_string)}</pre>"
        )

        # split text into multiple messages due to 4096 character limit
        for message_chunk in split_text_into_chunks(message, 4096):
            try:
                await context.bot.send_message(update.effective_chat.id, message_chunk, parse_mode=ParseMode.HTML)
            except BadRequest:
                # answer has invalid characters, so we send it without parse_mode
                await context.bot.send_message(update.effective_chat.id, message_chunk)
    except:
        await context.bot.send_message(update.effective_chat.id, "Some error in error handler")


async def post_init(application: Application):
    await application.bot.set_my_commands([
        BotCommand("/new", "Start new conversation"),
        BotCommand("/mode", "Select chat mode"),
        BotCommand("/retry", "Regenerate response for previous query"),
        BotCommand("/help", "Show help message"),
    ])


def run_bot() -> None:
    application = (
        ApplicationBuilder()
        .token(config.telegram_token)
        .concurrent_updates(True)
        .rate_limiter(AIORateLimiter(max_retries=5))
        .post_init(post_init)
        .build()
    )

    # add handlers
    if len(config.allowed_telegram_usernames) == 0:
        user_filter = filters.ALL
    else:
        user_filter = filters.User(username=config.allowed_telegram_usernames)

    application.add_handler(CommandHandler("start", start_handle, filters=user_filter))
    application.add_handler(CommandHandler("help", help_handle, filters=user_filter))

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & user_filter, message_handle))
    application.add_handler(CommandHandler("retry", retry_handle, filters=user_filter))
    application.add_handler(CommandHandler("new", new_dialog_handle, filters=user_filter))

    application.add_handler(CommandHandler("mode", show_chat_modes_handle, filters=user_filter))
    application.add_handler(CallbackQueryHandler(set_chat_mode_handle, pattern="^set_chat_mode"))

    application.add_error_handler(error_handle)

    # start the bot
    application.run_polling()


if __name__ == "__main__":
    run_bot()
