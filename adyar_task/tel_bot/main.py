import httpx
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters
)
from adyar_task.backend.groq_tool import enhance_prompt

BACKEND_URL = "http://localhost:8000/falai/sora"


CHOOSING, TEXT_PROMPT, IMAGE_PROMPT = range(3)


keyboard = [["تولید ویدیو با تصویر", "تولید ویدیو با متن"]]
markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "یک گزینه انتخاب کن:",
        reply_markup=markup
    )
    return CHOOSING


async def choose_option(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    context.user_data['option'] = text
    if text == "تولید ویدیو با متن":
        await update.message.reply_text(
            "لطفا پرامپت متنی خود را وارد کنید:",
            reply_markup=ReplyKeyboardRemove()
        )
        return TEXT_PROMPT
    elif text == "تولید ویدیو با تصویر":
        await update.message.reply_text(
            "لطفا تصویر خود را ارسال کنید:",
            reply_markup=ReplyKeyboardRemove()
        )
        return IMAGE_PROMPT
    else:
        await update.message.reply_text("گزینه نامعتبر است. دوباره تلاش کنید.")
        return CHOOSING



async def receive_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prompt = update.message.text
    enhanced_prompt = await enhance_prompt(prompt)
    telegram_user_id = str(update.message.from_user.id)

    payload = {
        "telegram_user_id": telegram_user_id,
        "type": "text",
        "prompt": enhanced_prompt
    }

    await update.message.reply_text(f"ویدیوی شما با متن '{enhanced_prompt}' تولید می‌شود!")

    async with httpx.AsyncClient() as client:
        response = await client.post(f"{BACKEND_URL}/request", json=payload)
        if response.status_code != 200:
            await update.message.reply_text(" خطا در ارسال درخواست به سرور.")
            return ConversationHandler.END

        data = response.json()

    await update.message.reply_text(data)

    return ConversationHandler.END


async def receive_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1]
    file_id = photo.file_id
    context.user_data['image_file_id'] = file_id
    await update.message.reply_text("تصویر دریافت شد. حالا لطفا پرامپت متنی خود را وارد کنید:")
    return TEXT_PROMPT


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("گفتگو لغو شد.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


app = ApplicationBuilder().token("").build()

conv_handler = ConversationHandler(
    entry_points=[CommandHandler('start', start)],
    states={
        CHOOSING: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_option)],
        TEXT_PROMPT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_text)],
        IMAGE_PROMPT: [MessageHandler(filters.PHOTO, receive_image)]
    },
    fallbacks=[CommandHandler('cancel', cancel)]
)

app.add_handler(conv_handler)
app.run_polling()
