import http.client
import json
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler, CallbackContext
import base64

# API kalitlari va boshqa sozlamalar
API_HOST = "face-swapper.p.rapidapi.com"
API_KEY = "c2ac18c217mshb99fc250b02f25cp16a34bjsn25403434e931"
HEADERS = {
    'x-rapidapi-key': API_KEY,
    'x-rapidapi-host': API_HOST,
    'Content-Type': "application/json"
}

# Holatlar
SOURCE, TARGET, ORTGA = range(3)
GROUP_ID = -1001887825461  # O'z guruhingiz yoki kanal ID'sini kiriting

async def is_user_in_group(user_id: int, bot) -> bool:
    """Foydalanuvchining guruh yoki kanal a'zosi ekanligini tekshirish"""
    try:
        member = await bot.get_chat_member(GROUP_ID, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        print(f"Xatolik yuz berdi: {e}")
        return False

def get_back_button() -> ReplyKeyboardMarkup:
    """Ortga tugmasini olish"""
    keyboard = [[KeyboardButton("Ortga")]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

async def start(update: Update, context: CallbackContext) -> int:
    """ Botni ishga tushirish va birinchi rasmni so'rash """
    user_id = update.message.from_user.id
    if not await is_user_in_group(user_id, context.bot):
        await update.message.reply_text('Botdan foydalanish uchun ushbu guruhga yoki kanalga qo\'shiling: https://t.me/unutilmas_ishq',
                                        disable_web_page_preview=True)
        return ConversationHandler.END

    await update.message.reply_text('Salom! Iltimos, birinchi rasmni (manba) yuboring.',
                                    reply_markup=get_back_button())
    return SOURCE

async def get_source_image(update: Update, context: CallbackContext) -> int:
    """ Birinchi rasmni qabul qilish va saqlash """
    if update.message.text == "Ortga":
        return await start(update, context)

    if not update.message.photo:
        await update.message.reply_text('Iltimos, rasm yuboring.')
        return SOURCE

    try:
        source_image_file = await update.message.photo[-1].get_file()
        source_image_path = await source_image_file.download()
        with open(source_image_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
        context.user_data['source_image_url'] = encoded_string
        await update.message.reply_text('Endi ikkinchi rasmni (maqsad) yuboring.', reply_markup=get_back_button())
        return TARGET
    except Exception as e:
        await update.message.reply_text(f'Xatolik yuz berdi: {str(e)}')
        return SOURCE

async def get_target_image_and_swap(update: Update, context: CallbackContext) -> int:
    """ Ikkinchi rasmni qabul qilish va yuzlarni almashinuvi uchun APIga so'rov yuborish """
    if update.message.text == "Ortga":
        return await start(update, context)

    if not update.message.photo:
        await update.message.reply_text('Iltimos, rasm yuboring.')
        return TARGET

    try:
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
            await update.message.reply_photo(photo=base64.b64decode(result_image), reply_markup=get_back_button())
        else:
            await update.message.reply_text('Yuz almashinuvi muvaffaqiyatsiz bo\'ldi: ' + data.get('errorMessage', 'Noma\'lum xato'))

        return ORTGA
    except Exception as e:
        await update.message.reply_text(f'Xatolik yuz berdi: {str(e)}')
        return TARGET

async def cancel(update: Update, context: CallbackContext) -> int:
    """ Bekor qilish holati """
    return await start(update, context)

async def handle_unexpected_message(update: Update, context: CallbackContext) -> None:
    """Noto'g'ri formatdagi xabarni qabul qilish"""
    await update.message.reply_text('Noto\'g\'ri formatdagi xabar. Iltimos, rasm yuboring.')

def main():
    """ Asosiy funksiya botni ishga tushirish uchun """
    application = Application.builder().token("6722967814:AAGKO-0xQ2roeYB_maPf1ZumPUE1UNABo4c").build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            SOURCE: [
                MessageHandler(filters.PHOTO, get_source_image),
                MessageHandler(filters.TEXT & filters.Regex("Ortga"), start),
                MessageHandler(~filters.PHOTO, handle_unexpected_message),
            ],
            TARGET: [
                MessageHandler(filters.PHOTO, get_target_image_and_swap),
                MessageHandler(filters.TEXT & filters.Regex("Ortga"), start),
                MessageHandler(~filters.PHOTO, handle_unexpected_message),
            ],
            ORTGA: [
                MessageHandler(filters.TEXT & filters.Regex("Ortga"), start),
                MessageHandler(~filters.PHOTO, handle_unexpected_message),
            ]
        },
        fallbacks=[MessageHandler(filters.Regex("Ortga"), start)]
    )

    application.add_handler(conv_handler)
    application.run_polling()

if __name__ == '__main__':
    main()
