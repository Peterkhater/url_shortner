import logging

import requests
from keys import TOKEN, PAYMENT_TOKEN
from telegram import LabeledPrice, Update
from telegram.ext import CommandHandler, ContextTypes, ApplicationBuilder, MessageHandler, filters
import re
import aiohttp
import json

Base_url = 'https://127.0.0.1:8000'

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

# async def subscribe_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     chat_id = update.message.chat_id
#     print(f'#########################{type(chat_id)}#########################(int)')
#     r = requests.get(Base_url+"/check_user", params={'chat_id':chat_id})
#     title = 'Unlimited Use'
#     description = 'Subscribe To Use Our Service Unlimited'
#     payload = 'SuperSecret'
#     currency = 'USD'
#     price = 2
#     prices = [LabeledPrice("unlimited",price*100)]
#     await context.bot.send_invoice(
#         chat_id=chat_id,
#         title=title,
#         description=description,
#         payload=payload,
#         provider_token= PAYMENT_TOKEN,
#         currency=currency,
#         prices=prices,
#         need_name=True
#     )

async def subscribe_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        chat_id = update.effective_chat.id
        user = update.effective_user
        logger.info(f"Subscription request from {user.id} ({user.username})")

        # 1. Check user's current status
        try:
            response = requests.get(
                f"{Base_url}/check_user/",
                params={'chat_id': chat_id},
                timeout=5
            )
            response.raise_for_status()
            user_data = response.json()
            
            if user_data.get('status') == 'premium':
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="🎉 You're already a premium user! Enjoy unlimited access."
                )
                return

        except requests.exceptions.RequestException as e:
            logger.error(f"API Error: {str(e)}")
            await context.bot.send_message(
                chat_id=chat_id,
                text="⚠️ Service temporarily unavailable. Please try again later."
            )
            return

        
        title = "Premium Subscription"
        description = (
            "Unlock unlimited URL shortening and premium features\n"
            "• No link limits\n"
            "• Priority support\n"
            "• Advanced analytics"
        )
        payload = f"subscription_{chat_id}"
        currency = "USD"
        
        
        price = 199  # $1.99
        prices = [LabeledPrice("Premium Subscription", price)]

        await context.bot.send_invoice(
            chat_id=chat_id,
            title=title,
            description=description,
            payload=payload,
            provider_token=PAYMENT_TOKEN,
            currency=currency,
            prices=prices,
            need_name=True,
            need_email=True,
            photo_url="https://yourdomain.com/premium-banner.jpg",
            photo_size=512,
            photo_width=800,
            photo_height=450,
            start_parameter="premium_subscription"
        )

        logger.info(f"Invoice sent to {chat_id}")

    except Exception as e:
        logger.critical(f"Subscribe handler crashed: {str(e)}", exc_info=True)
        await context.bot.send_message(
            chat_id=chat_id,
            text="❌ An unexpected error occurred. Our team has been notified."
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
                link = match[0] 
                
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
    application.add_handler(CommandHandler('subscribe', subscribe_handler))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), msg_handler_fn))
    
    # Start the bot
    application.run_polling()