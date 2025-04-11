import logging
from keys import TOKEN
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes, ApplicationBuilder, MessageHandler, filters
import re
import aiohttp
import json

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def help_fn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Welcome to the link parser bot! Send me any URL to shorten it."
    )

async def msg_handler_fn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user = update.message.from_user

    try:
        pattern = re.compile(
            r'''(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'".,<>?«»""'']))''',
            re.VERBOSE
        )
        matches = re.findall(pattern, text)
        
        if matches:
            for match in matches:
                link = match[0]  # The first group contains the URL
                
                payload = {
                    'link': link,
                    'user_id': str(user.id),
                    'user_name': user.username or "",
                    'first_name': user.first_name or "User",
                }

                logger.info(f"Processing link: {link} for user {user.id}")
                
                async with aiohttp.ClientSession() as session:
                    try:
                        async with session.get(
                            'http://127.0.0.1:8000/short/',
                            params=payload,
                            timeout=5
                        ) as response:
                            
                            response_data = await response.json()
                            logger.info(f"Response from server: {response_data}")
                            
                            if response.status == 200:
                                if response_data.get('status') == "success":
                                    await context.bot.send_message(
                                        chat_id=update.effective_chat.id,
                                        text=f"Here is your shortened link:\n{response_data.get('short_url')}"
                                    )
                                else:
                                    await context.bot.send_message(
                                        chat_id=update.effective_chat.id,
                                        text=response_data.get('message', "Sorry, something went wrong.")
                                    )
                            else:
                                logger.error(f"Server error: {response.status}")
                                await context.bot.send_message(
                                    chat_id=update.effective_chat.id,
                                    text="Sorry, the server encountered an error."
                                )
                    except aiohttp.ClientError as e:
                        logger.error(f"Connection error: {str(e)}")
                        await context.bot.send_message(
                            chat_id=update.effective_chat.id,
                            text="Sorry, we couldn't connect to the server. Please try again later."
                        )
                    except json.JSONDecodeError:
                        logger.error("Invalid JSON response from server")
                        await context.bot.send_message(
                            chat_id=update.effective_chat.id,
                            text="Sorry, we received an invalid response from the server."
                        )
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Sorry, there was an unexpected error processing your request."
        )

if __name__ == "__main__":
    application = ApplicationBuilder().token(TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler('help', help_fn))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), msg_handler_fn))
    
    # Start the bot
    application.run_polling()