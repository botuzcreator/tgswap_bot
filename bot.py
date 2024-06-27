import http.client
import json
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler, CallbackContext
import base64

# API kalitlari va boshqa sozlamalar
API_HOST = "face-swapper.p.rapidapi.com"
API_KEY = "cf37032608msh34b120d1f62e828p102f79jsn41e8b9aa5437"
HEADERS = {
    'x-rapidapi-key': API_KEY,
    'x-rapidapi-host': API_HOST,
    'Content-Type': "application/json"
}

# Holatlar
SOURCE, TARGET = range(2)

async def start(update: Update, context: CallbackContext) -> int:
    """ Botni ishga tushirish va birinchi rasmni so'rash """
    await update.message.reply_text('Salom! Iltimos, birinchi rasmni (manba) yuboring.')
    return SOURCE

async def get_source_image(update: Update, context: CallbackContext) -> int:
    """ Birinchi rasmni qabul qilish va saqlash """
    source_image_file = await update.message.photo[-1].get_file()
    source_image_path = await source_image_file.download()
    with open(source_image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
    context.user_data['source_image_url'] = encoded_string
    await update.message.reply_text('Endi ikkinchi rasmni (maqsad) yuboring.')
    return TARGET

async def get_target_image_and_swap(update: Update, context: CallbackContext) -> int:
    """ Ikkinchi rasmni qabul qilish va yuzlarni almashinuvi uchun APIga so'rov yuborish """
    target_image_file = await update.message.photo[-1].get_file()
    target_image_path = await target_image_file.download()
    with open(target_image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
    
    conn = http.client.HTTPSConnection(API_HOST)
    payload = json.dumps({
        "source": context.user_data['source_image_url'],
        "target": encoded_string
    })
    conn.request("POST", "/swap", payload, HEADERS)
    response = conn.getresponse()
    data = json.loads(response.read().decode("utf-8"))

    if data['status'] == 'success':
        result_image = data['result']
        # Rasmlarni ko'rish uchun base64 formatini foydalanuvchiga ko'rsatish
        await update.message.reply_photo(photo=base64.b64decode(result_image))
    else:
        await update.message.reply_text('Yuz almashinuvi muvaffaqiyatsiz bo\'ldi: ' + data.get('errorMessage', 'Noma\'lum xato'))
    
    return ConversationHandler.END

async def cancel(update: Update, context: CallbackContext) -> int:
    """ Bekor qilish holati """
    await update.message.reply_text('Bekor qilindi.')
    return ConversationHandler.END

def main():
    """ Asosiy funksiya botni ishga tushirish uchun """
    application = Application.builder().token("7422914822:AAGODk20kl-OrEVpR47O4eTbU5BJDUxzZ80").build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            SOURCE: [MessageHandler(filters.PHOTO, get_source_image)],
            TARGET: [MessageHandler(filters.PHOTO, get_target_image_and_swap)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    application.add_handler(conv_handler)
    application.run_polling()

if __name__ == '__main__':
    main()
