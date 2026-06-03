#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
بوت تحليل وتعديل الصور - Image Editor Bot
تحليل إعدادات التحرير من الصور وتطبيقها على صور أخرى
"""

import logging
import os
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from handlers import (
    start_handler,
    photo_handler,
    button_callback_handler,
    apply_edits_photo_handler
)

# تحميل متغيرات البيئة
load_dotenv()

# إعداد السجلات
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# الحصول على التوكنات من متغيرات البيئة
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

def main():
    """تشغيل البوت"""
    
    if not TELEGRAM_TOKEN:
        logger.error('❌ TELEGRAM_TOKEN غير موجود في ملف .env')
        return
    
    if not GEMINI_API_KEY:
        logger.error('❌ GEMINI_API_KEY غير موجود في ملف .env')
        return
    
    logger.info('🚀 بدء تشغيل البوت...')
    
    # إنشاء تطبيق البوت
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # إضافة معالجات الأوامر
    app.add_handler(CommandHandler('start', start_handler))
    
    # معالج الصور
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    
    # معالج الأزرار inline
    app.add_handler(CallbackQueryHandler(button_callback_handler))
    
    # معالج صور تطبيق التعديلات
    app.add_handler(MessageHandler(filters.PHOTO, apply_edits_photo_handler))
    
    logger.info('✅ البوت جاهز للعمل')
    
    # تشغيل البوت
    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True
    )

if __name__ == '__main__':
    main()
