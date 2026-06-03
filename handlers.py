#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
معا��جات أوامر البوت
"""

import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from gemini_handler import analyze_image_settings
from image_processor import apply_settings_to_image

logger = logging.getLogger(__name__)

# قاموس لتخزين الإعدادات المؤقتة (user_id -> settings)
user_settings = {}

# قاموس لتتبع حالة المستخدم (user_id -> state)
user_states = {}

# رسالة الترحيب
WELCOME_MESSAGE = """🖼️ **مرحباً بك في بوت تحليل وتعديل الصور!**

✨ **آلية العمل:**

1️⃣ **أرسل صورة محررة** - سأقوم بتحليل إعداداتها
2️⃣ **اعرض الإعدادات** - ستظهر لك قيم التباين والسطوع وغيرها
3️⃣ **طبق على صورتك** - أرسل صورة أخرى لتطبيق نفس الإعدادات عليها

📊 **الإعدادات التي يحللها البوت:**
• التباين (Contrast)
• السطوع (Brightness)
• التشبع (Saturation)
• الظلال (Shadows)
• الإضاءة (Highlights)
• درجة الحرارة اللونية (Color Temperature)
• الحدة (Sharpness)
• التلاشي (Fade)

👨‍💻 **المطور:** @choayeb

🚀 **ابدأ الآن:**
أرسل أي صورة محررة لتبدأ!"""

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    معالج أمر /start
    """
    user = update.effective_user
    user_id = user.id
    
    logger.info(f"👤 مستخدم جديد: {user.first_name} ({user_id})")
    
    # إنشاء الأزرار
    keyboard = [
        [
            InlineKeyboardButton(
                "👨‍💻 المطور",
                url="https://t.me/choayeb"
            )
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # إرسال رسالة الترحيب
    await update.message.reply_text(
        WELCOME_MESSAGE,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    معالج الصور - تحليل الإعدادات
    """
    user_id = update.effective_user.id
    message = update.effective_message
    
    try:
        # إظهار مؤشر الكتابة
        await update.effective_chat.send_action('upload_document')
        
        # إرسال رسالة معالجة
        processing_msg = await message.reply_text(
            "⏳ جاري تحليل الصورة وإستخراج الإعدادات..."
        )
        
        # الحصول على الصورة
        photo_file = await context.bot.get_file(message.photo[-1].file_id)
        photo_path = f"temp_photo_{user_id}.jpg"
        await photo_file.download_to_drive(photo_path)
        
        # تحليل الصورة باستخدام Gemini
        logger.info(f"🔍 تحليل صورة للمستخدم {user_id}")
        settings = await analyze_image_settings(photo_path)
        
        # حفظ الإعدادات مؤقتاً
        user_settings[user_id] = {
            'settings': settings,
            'original_photo_path': photo_path
        }
        
        # تنسيق الإعدادات للعرض
        settings_text = format_settings(settings)
        
        # إنشاء زر لتطبيق التعديلات
        keyboard = [
            [
                InlineKeyboardButton(
                    "📸 نسخ التعديل على صورتي",
                    callback_data="apply_settings"
                )
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # حذف رسالة المعالجة وإرسال الإعدادات
        await processing_msg.delete()
        await message.reply_text(
            f"✅ **تم تحليل الإعدادات بنجاح!**\n\n{settings_text}",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
        # وضع المستخدم في حالة الانتظار (اختياري)
        user_states[user_id] = 'waiting_for_apply'
        
    except Exception as e:
        logger.error(f"❌ خطأ في تحليل الصورة: {str(e)}")
        await message.reply_text(
            f"❌ حدث خطأ في تحليل الصورة:\n{str(e)}",
            parse_mode='Markdown'
        )

async def button_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    معالج أزرار inline
    """
    query = update.callback_query
    user_id = query.from_user.id
    
    try:
        # الإجابة على استدعاء الزر
        await query.answer()
        
        if query.data == "apply_settings":
            # طلب صورة من المستخدم
            user_states[user_id] = 'waiting_for_photo_to_edit'
            await query.edit_message_text(
                "📤 أرسل الصورة التي تريد تطبيق الإعدادات عليها:",
                parse_mode='Markdown'
            )
            
    except Exception as e:
        logger.error(f"❌ خطأ في معالج الزر: {str(e)}")
        await query.answer(text="حدث خطأ!", show_alert=True)

async def apply_edits_photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    معالج صور تطبيق التعديلات
    """
    user_id = update.effective_user.id
    message = update.effective_message
    
    # التحقق من أن المستخدم في حالة الانتظار
    if user_states.get(user_id) != 'waiting_for_photo_to_edit':
        return
    
    try:
        # إظهار مؤشر الكتابة
        await update.effective_chat.send_action('upload_document')
        
        # إرسال رسالة معالجة
        processing_msg = await message.reply_text(
            "⏳ جاري تطبيق الإعدادات على صورتك..."
        )
        
        # الحصول على الإعدادات المحفوظة
        if user_id not in user_settings:
            await processing_msg.edit_text(
                "❌ لم يتم العثور على إعدادات محفوظة. يرجى تحليل صورة أولاً."
            )
            user_states[user_id] = None
            return
        
        settings = user_settings[user_id]['settings']
        
        # الحصول على الصورة الجديدة
        photo_file = await context.bot.get_file(message.photo[-1].file_id)
        input_photo_path = f"input_photo_{user_id}.jpg"
        await photo_file.download_to_drive(input_photo_path)
        
        # تطبيق الإعدادات على الصورة
        logger.info(f"🎨 تطبيق الإعدادات على صورة المستخدم {user_id}")
        output_photo_path = await apply_settings_to_image(
            input_photo_path,
            settings
        )
        
        # إرسال الصورة المعدلة
        await processing_msg.delete()
        with open(output_photo_path, 'rb') as photo:
            await message.reply_photo(
                photo=photo,
                caption="✅ تم تطبيق الإعدادات بنجاح!\n📸 صورتك المعدلة جاهزة",
                parse_mode='Markdown'
            )
        
        # تنظيف الملفا�� المؤقتة
        cleanup_temp_files(user_id)
        user_states[user_id] = None
        
    except Exception as e:
        logger.error(f"❌ خطأ في تطبيق الإعدادات: {str(e)}")
        await message.reply_text(
            f"❌ حدث خطأ في تطبيق الإعدادات:\n{str(e)}",
            parse_mode='Markdown'
        )
        user_states[user_id] = None

def format_settings(settings: dict) -> str:
    """
    تنسيق الإعدادات للعرض
    """
    text = "📊 **إعدادات التحرير المستخرجة:**\n\n"
    
    settings_mapping = {
        'contrast': '🎚️ التباين (Contrast)',
        'brightness': '☀️ السطوع (Brightness)',
        'saturation': '🌈 التشبع (Saturation)',
        'shadows': '🌑 الظلال (Shadows)',
        'highlights': '💡 الإضاءة (Highlights)',
        'temperature': '🌡️ درجة الحرارة اللونية (Color Temperature)',
        'sharpness': '✂️ الحدة (Sharpness)',
        'fade': '👻 التلاشي (Fade)'
    }
    
    for key, label in settings_mapping.items():
        if key in settings:
            value = settings[key]
            # تحديد نطاق القي��ة المناسب
            if isinstance(value, (int, float)):
                text += f"{label}: **{value}**\n"
            else:
                text += f"{label}: **{value}**\n"
    
    return text

def cleanup_temp_files(user_id: int) -> None:
    """
    تنظيف الملفات المؤقتة
    """
    try:
        temp_files = [
            f"temp_photo_{user_id}.jpg",
            f"input_photo_{user_id}.jpg",
            f"output_photo_{user_id}.jpg"
        ]
        
        for file_path in temp_files:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"🗑️ تم حذف الملف المؤقت: {file_path}")
    except Exception as e:
        logger.error(f"❌ خطأ في تنظيف الملفات: {str(e)}")
