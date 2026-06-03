#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
بوت تحليل وتعديل الصور - Image Editor Bot
ملف واحد يحتوي على كل الكود
"""

import logging
import os
import base64
import json
import re
import asyncio
from typing import Dict, Any
from dotenv import load_dotenv

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

from PIL import Image, ImageEnhance
import google.generativeai as genai

# ──────────────────────────────────────────────
# الإعداد
# ──────────────────────────────────────────────
load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

genai.configure(api_key=GEMINI_API_KEY)
GEMINI_MODEL = "gemini-1.5-flash-latest"

# ──────────────────────────────────────────────
# الذاكرة المؤقتة
# ──────────────────────────────────────────────
user_settings: Dict[int, dict] = {}
user_states: Dict[int, str] = {}

# ──────────────────────────────────────────────
# رسالة الترحيب
# ──────────────────────────────────────────────
WELCOME_MESSAGE = """🖼️ *مرحباً بك في بوت تحليل وتعديل الصور\!*

✨ *آلية العمل:*

1️⃣ *أرسل صورة محررة* \- سأقوم بتحليل إعداداتها
2️⃣ *اعرض الإعدادات* \- ستظهر لك قيم التباين والسطوع وغيرها
3️⃣ *طبق على صورتك* \- أرسل صورة أخرى لتطبيق نفس الإعدادات عليها

📊 *الإعدادات التي يحللها البوت:*
• التباين \(Contrast\)
• السطوع \(Brightness\)
• التشبع \(Saturation\)
• الظلال \(Shadows\)
• الإضاءة \(Highlights\)
• درجة الحرارة اللونية \(Color Temperature\)
• الحدة \(Sharpness\)
• التلاشي \(Fade\)

👨‍💻 *المطور:* @choayeb

🚀 *ابدأ الآن:*
أرسل أي صورة محررة لتبدأ\!"""

# ──────────────────────────────────────────────
# Gemini - تحليل الصورة
# ──────────────────────────────────────────────
ANALYSIS_PROMPT = """أنت متخصص في تحليل إعدادات التحرير الفوتوغرافي.
قم بتحليل هذه الصورة واستخرج إعدادات التحرير التقريبية كأرقام دقيقة.
يجب أن يكون الرد بصيغة JSON فقط بدون أي نص إضافي:
{
    "contrast": <رقم -100 إلى 100>,
    "brightness": <رقم -100 إلى 100>,
    "saturation": <رقم -100 إلى 100>,
    "shadows": <رقم -100 إلى 100>,
    "highlights": <رقم -100 إلى 100>,
    "temperature": <رقم 2000 إلى 8000>,
    "sharpness": <رقم 0 إلى 100>,
    "fade": <رقم 0 إلى 100>,
    "analysis": "وصف موجز للمظهر العام"
}"""

async def analyze_image_settings(image_path: str) -> Dict[str, Any]:
    with open(image_path, 'rb') as f:
        image_data = base64.standard_b64encode(f.read()).decode('utf-8')

    model = genai.GenerativeModel(GEMINI_MODEL)
    response = model.generate_content([
        {"text": ANALYSIS_PROMPT},
        {"inline_data": {"mime_type": "image/jpeg", "data": image_data}}
    ])

    text = response.text
    logger.info(f"Gemini response: {text[:200]}")

    # استخراج JSON
    match = re.search(r'```json\s*(\{.*?\})\s*```', text, re.DOTALL)
    if match:
        text = match.group(1)
    else:
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            text = match.group(0)

    try:
        settings = json.loads(text)
    except json.JSONDecodeError:
        settings = {}

    defaults = {'contrast': 0, 'brightness': 0, 'saturation': 0,
                'shadows': 0, 'highlights': 0, 'temperature': 5500,
                'sharpness': 50, 'fade': 0}
    for k, v in defaults.items():
        if k not in settings:
            settings[k] = v

    return settings

# ──────────────────────────────────────────────
# Pillow - تطبيق التعديلات
# ──────────────────────────────────────────────
def normalize_value(value, min_in, max_in, min_out, max_out):
    normalized = (value - min_in) / (max_in - min_in)
    result = min_out + normalized * (max_out - min_out)
    return max(min_out, min(max_out, result))

def apply_edits(image: Image.Image, settings: dict) -> Image.Image:
    if 'contrast' in settings:
        v = normalize_value(settings['contrast'], -100, 100, 0.5, 3.0)
        image = ImageEnhance.Contrast(image).enhance(v)

    if 'brightness' in settings:
        v = normalize_value(settings['brightness'], -100, 100, 0.5, 2.5)
        image = ImageEnhance.Brightness(image).enhance(v)

    if 'saturation' in settings:
        v = normalize_value(settings['saturation'], -100, 100, 0.0, 2.5)
        image = ImageEnhance.Color(image).enhance(v)

    if 'sharpness' in settings:
        v = normalize_value(settings['sharpness'], 0, 100, 0.0, 3.0)
        image = ImageEnhance.Sharpness(image).enhance(v)

    if 'temperature' in settings:
        temp = settings['temperature']
        r, g, b = image.split()
        if temp < 5500:
            amount = min(0.3, ((5500 - temp) / 2500) * 0.3)
            b = ImageEnhance.Brightness(b).enhance(1 + amount)
        else:
            amount = min(0.3, ((temp - 5500) / 2500) * 0.3)
            r = ImageEnhance.Brightness(r).enhance(1 + amount)
        image = Image.merge('RGB', (r, g, b))

    if 'shadows' in settings and settings['shadows'] != 0:
        v = normalize_value(settings['shadows'], -100, 100, 0.3, 1.5)
        image = ImageEnhance.Brightness(image).enhance(v)

    if 'highlights' in settings and settings['highlights'] != 0:
        v = normalize_value(-settings['highlights'], -100, 100, 0.3, 1.5)
        image = ImageEnhance.Brightness(image).enhance(v)

    if 'fade' in settings and settings['fade'] > 0:
        fade = normalize_value(settings['fade'], 0, 100, 0.0, 0.8)
        white = Image.new('RGB', image.size, (255, 255, 255))
        image = Image.blend(image, white, fade)

    return image

async def apply_settings_to_image(image_path: str, settings: dict, user_id: int) -> str:
    image = Image.open(image_path).convert('RGB')
    loop = asyncio.get_event_loop()
    edited = await loop.run_in_executor(None, apply_edits, image, settings)
    output_path = f"output_photo_{user_id}.jpg"
    edited.save(output_path, quality=95, optimize=True)
    return output_path

# ──────────────────────────────────────────────
# تنسيق الإعدادات
# ──────────────────────────────────────────────
def format_settings(settings: dict) -> str:
    labels = {
        'contrast':    '🎚️ التباين \(Contrast\)',
        'brightness':  '☀️ السطوع \(Brightness\)',
        'saturation':  '🌈 التشبع \(Saturation\)',
        'shadows':     '🌑 الظلال \(Shadows\)',
        'highlights':  '💡 الإضاءة \(Highlights\)',
        'temperature': '🌡️ درجة الحرارة \(Temperature\)',
        'sharpness':   '✂️ الحدة \(Sharpness\)',
        'fade':        '👻 التلاشي \(Fade\)',
    }
    text = "📊 *إعدادات التحرير المستخرجة:*\n\n"
    for key, label in labels.items():
        if key in settings:
            text += f"{label}: `{settings[key]}`\n"
    if 'analysis' in settings:
        text += f"\n📝 *التحليل:* {settings['analysis']}"
    return text

def cleanup(user_id: int):
    for f in [f"temp_photo_{user_id}.jpg", f"input_photo_{user_id}.jpg", f"output_photo_{user_id}.jpg"]:
        if os.path.exists(f):
            os.remove(f)

# ──────────────────────────────────────────────
# معالجات البوت
# ──────────────────────────────────────────────
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("👨‍💻 المطور", url="https://t.me/choayeb")]]
    await update.message.reply_text(
        WELCOME_MESSAGE,
        parse_mode='MarkdownV2',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    message = update.effective_message

    # إذا كان المستخدم ينتظر صورة للتعديل، أرسلها للمعالج الثاني
    if user_states.get(user_id) == 'waiting_for_photo_to_edit':
        await apply_edits_photo_handler(update, context)
        return

    try:
        await update.effective_chat.send_action('upload_document')
        processing_msg = await message.reply_text("⏳ جاري تحليل الصورة واستخراج الإعدادات\.\.\.", parse_mode='MarkdownV2')

        photo_file = await context.bot.get_file(message.photo[-1].file_id)
        photo_path = f"temp_photo_{user_id}.jpg"
        await photo_file.download_to_drive(photo_path)

        settings = await analyze_image_settings(photo_path)
        user_settings[user_id] = {'settings': settings}
        user_states[user_id] = 'waiting_for_apply'

        keyboard = [[InlineKeyboardButton("📸 نسخ التعديل على صورتي", callback_data="apply_settings")]]
        await processing_msg.delete()
        await message.reply_text(
            f"✅ *تم تحليل الإعدادات بنجاح\!*\n\n{format_settings(settings)}",
            parse_mode='MarkdownV2',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    except Exception as e:
        logger.error(f"خطأ: {e}")
        await message.reply_text(f"❌ حدث خطأ: {str(e)}")

async def button_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if query.data == "apply_settings":
        user_states[user_id] = 'waiting_for_photo_to_edit'
        await query.edit_message_text("📤 أرسل الصورة التي تريد تطبيق الإعدادات عليها:")

async def apply_edits_photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    message = update.effective_message

    try:
        await update.effective_chat.send_action('upload_document')
        processing_msg = await message.reply_text("⏳ جاري تطبيق الإعدادات على صورتك\.\.\.", parse_mode='MarkdownV2')

        if user_id not in user_settings:
            await processing_msg.edit_text("❌ لم يتم العثور على إعدادات. يرجى تحليل صورة أولاً.")
            user_states[user_id] = None
            return

        settings = user_settings[user_id]['settings']
        photo_file = await context.bot.get_file(message.photo[-1].file_id)
        input_path = f"input_photo_{user_id}.jpg"
        await photo_file.download_to_drive(input_path)

        output_path = await apply_settings_to_image(input_path, settings, user_id)

        await processing_msg.delete()
        with open(output_path, 'rb') as photo:
            await message.reply_photo(
                photo=photo,
                caption="✅ تم تطبيق الإعدادات بنجاح\! 📸",
                parse_mode='MarkdownV2'
            )

        cleanup(user_id)
        user_states[user_id] = None

    except Exception as e:
        logger.error(f"خطأ: {e}")
        await message.reply_text(f"❌ حدث خطأ: {str(e)}")
        user_states[user_id] = None

# ──────────────────────────────────────────────
# تشغيل البوت
# ──────────────────────────────────────────────
def main():
    if not TELEGRAM_TOKEN:
        logger.error('TELEGRAM_TOKEN غير موجود')
        return
    if not GEMINI_API_KEY:
        logger.error('GEMINI_API_KEY غير موجود')
        return

    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler('start', start_handler))
    app.add_handler(CallbackQueryHandler(button_callback_handler))
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))

    logger.info('✅ البوت يعمل...')
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == '__main__':
    main()
