import logging
from keys import TOKEN
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes, ApplicationBuilder, MessageHandler, filters
import re
import aiohttp

async def help_fn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Welcome to the link parser bot!")

async def msg_handler_fn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.message.from_user.id
    username = update.message.from_user.username
    first_name = update.message.from_user.first_name

    try:
        pattern = re.compile(r'''(?i)\b(?:https?://|www\.)[a-z0-9\-._~%]+(?:\.[a-z]{2,})+(?::\d{2,5})?(?:/[^\s]*)?''', re.VERBOSE)
        matches = re.findall(pattern, text)
        if matches:
            for link in matches:
                payload = {
                    'link': link,
                    'user_id': user_id,
                    'user_name': username,
                    'first_name': first_name,
                }

                async with aiohttp.ClientSession() as session:
                    async with session.get('http://127.0.0.1:8000/short/', params=payload) as r:
                        if r.status == 200:
                            result = await r.json()
                            if result.get('status') == "success":
                                await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Here is your shortened link:\n{result.get('short_url')}")
                            else:
                                await context.bot.send_message(chat_id=update.effective_chat.id, text="You have used all your free trial. Please click on /subscribe to continue.")
                        else:
                            await context.bot.send_message(chat_id=update.effective_chat.id, text="Sorry, Something Went Wrong")
    except Exception as e:
        logging.error(f"Error processing message from {user_id}: {e}")
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Sorry, there was an error processing your request.")

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    # app handlers
    msg_handler = MessageHandler(filters.ALL, msg_handler_fn)
    help_handler = CommandHandler('help', help_fn)

    # register handlers
    app.add_handler(help_handler)
    app.add_handler(msg_handler)

    app.run_polling()
