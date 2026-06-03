#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
معالج تطبيق التعديلات على الصور باستخدام Pillow
"""

import logging
import os
from typing import Dict, Any
from PIL import Image, ImageEnhance
import asyncio

logger = logging.getLogger(__name__)

async def apply_settings_to_image(
    image_path: str,
    settings: Dict[str, Any]
) -> str:
    """
    تطبيق إعدادات التحرير على الصورة
    
    Args:
        image_path: مسار صورة الإدخال
        settings: قاموس الإعدادات
        
    Returns:
        مسار صورة الإخراج
    """
    try:
        logger.info(f"🖼️ بدء تطبيق الإعدادات على الصورة: {image_path}")
        logger.info(f"الإعدادات: {settings}")
        
        # فتح الصورة
        image = Image.open(image_path).convert('RGB')
        logger.info(f"✅ تم فتح الصورة بحجم: {image.size}")
        
        # تطبيق التعديلات بشكل متزامن
        loop = asyncio.get_event_loop()
        edited_image = await loop.run_in_executor(
            None,
            apply_edits,
            image,
            settings
        )
        
        # حفظ الصورة المعدلة
        # استخراج user_id من مسار الملف
        user_id = image_path.split('_')[2].split('.')[0]
        output_path = f"output_photo_{user_id}.jpg"
        
        edited_image.save(output_path, quality=95, optimize=True)
        logger.info(f"✅ تم حفظ الصورة المعدلة: {output_path}")
        
        return output_path
        
    except Exception as e:
        logger.error(f"❌ خطأ في تطبيق الإعدادات: {str(e)}")
        raise Exception(f"فشل تطبيق الإعدادات: {str(e)}")

def apply_edits(image: Image.Image, settings: Dict[str, Any]) -> Image.Image:
    """
    تطبيق التعديلات على الصورة (دالة متزامنة)
    
    Args:
        image: كائن الصورة
        settings: قاموس الإعدادات
        
    Returns:
        الصورة المعدلة
    """
    try:
        # 1. تطبيق التباين (Contrast)
        if 'contrast' in settings:
            contrast_value = normalize_value(settings['contrast'], -100, 100, 0.5, 3.0)
            logger.info(f"🎚️ تطبيق التباين: {contrast_value}")
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(contrast_value)
        
        # 2. تطبيق السطوع (Brightness)
        if 'brightness' in settings:
            brightness_value = normalize_value(settings['brightness'], -100, 100, 0.5, 2.5)
            logger.info(f"☀️ تطبيق السطوع: {brightness_value}")
            enhancer = ImageEnhance.Brightness(image)
            image = enhancer.enhance(brightness_value)
        
        # 3. تطبيق التشبع (Saturation)
        if 'saturation' in settings:
            saturation_value = normalize_value(settings['saturation'], -100, 100, 0.0, 2.5)
            logger.info(f"🌈 تطبيق التشبع: {saturation_value}")
            enhancer = ImageEnhance.Color(image)
            image = enhancer.enhance(saturation_value)
        
        # 4. تطبيق الحدة (Sharpness)
        if 'sharpness' in settings:
            sharpness_value = normalize_value(settings['sharpness'], 0, 100, 0.0, 3.0)
            logger.info(f"✂️ تطبيق الحدة: {sharpness_value}")
            enhancer = ImageEnhance.Sharpness(image)
            image = enhancer.enhance(sharpness_value)
        
        # 5. تطبيق درجة الحرارة اللونية (Color Temperature)
        if 'temperature' in settings:
            temp = settings['temperature']
            logger.info(f"🌡️ تطبيق درجة الحرارة: {temp}K")
            image = apply_color_temperature(image, temp)
        
        # 6. تطبيق الظلال (Shadows) - زيادة السطوع للمناطق المظلمة
        if 'shadows' in settings:
            shadows_value = settings['shadows']
            logger.info(f"🌑 تطبيق الظلال: {shadows_value}")
            image = apply_shadows(image, shadows_value)
        
        # 7. تطبيق الإضاءة (Highlights) - تقليل السطوع للمناطق الساطعة
        if 'highlights' in settings:
            highlights_value = settings['highlights']
            logger.info(f"💡 تطبيق الإضاءة: {highlights_value}")
            image = apply_highlights(image, highlights_value)
        
        # 8. تطبيق التلاشي (Fade)
        if 'fade' in settings:
            fade_value = normalize_value(settings['fade'], 0, 100, 0.0, 0.8)
            logger.info(f"👻 تطبيق التلاشي: {fade_value}")
            image = apply_fade(image, fade_value)
        
        logger.info("✅ تم تطبيق جميع التعديلات بنجاح")
        return image
        
    except Exception as e:
        logger.error(f"❌ خطأ في تطبيق التعديلات: {str(e)}")
        raise

def normalize_value(value: float, min_in: float, max_in: float, min_out: float, max_out: float) -> float:
    """
    تطبيع القيمة من نطاق إلى نطاق آخر
    
    Args:
        value: القيمة الأصلية
        min_in: الحد الأدنى للقيمة الأصلية
        max_in: الحد الأقصى للقيمة الأصلية
        min_out: الحد الأدنى للقيمة الجديدة
        max_out: الحد الأقصى للقيمة الجديدة
        
    Returns:
        القيمة المطبعة
    """
    # تطبيع من [min_in, max_in] إلى [0, 1]
    normalized = (value - min_in) / (max_in - min_in)
    # تطبيع إلى [min_out, max_out]
    result = min_out + normalized * (max_out - min_out)
    return max(min_out, min(max_out, result))

def apply_color_temperature(image: Image.Image, temperature: float) -> Image.Image:
    """
    تطبيق درجة الحرارة اللونية
    
    Args:
        image: الصورة
        temperature: درجة الحرارة بالكلفن (K)
        
    Returns:
        الصورة المعدلة
    """
    try:
        # إذا كانت درجة الحرارة أقل من 5500K، أضف أزرق (بارد)
        # إذا كانت أعلى من 5500K، أضف أحمر (دافئ)
        
        if temperature < 5500:
            # بارد - إضافة أزرق
            amount = (5500 - temperature) / 2500  # من 0 إلى 1
            amount = min(0.3, amount * 0.3)  # تحديد الحد الأقصى
            image_array = image.convert('RGB')
            r, g, b = image_array.split()
            b = ImageEnhance.Brightness(b).enhance(1 + amount)
            image = Image.merge('RGB', (r, g, b))
        else:
            # دافئ - إضافة أحمر
            amount = (temperature - 5500) / 2500  # من 0 إلى 1
            amount = min(0.3, amount * 0.3)  # تحديد الحد الأقصى
            image_array = image.convert('RGB')
            r, g, b = image_array.split()
            r = ImageEnhance.Brightness(r).enhance(1 + amount)
            image = Image.merge('RGB', (r, g, b))
        
        return image
    except Exception as e:
        logger.error(f"❌ خطأ في تطبيق درجة الحرارة: {str(e)}")
        return image

def apply_shadows(image: Image.Image, shadows_value: float) -> Image.Image:
    """
    تطبيق تأثير الظلال
    
    Args:
        image: الصورة
        shadows_value: قيمة الظلال (-100 إلى 100)
        
    Returns:
        الصورة المعدلة
    """
    try:
        if shadows_value == 0:
            return image
        
        # تطبيع القيمة
        normalized = normalize_value(shadows_value, -100, 100, 0.3, 1.5)
        enhancer = ImageEnhance.Brightness(image)
        return enhancer.enhance(normalized)
    except Exception as e:
        logger.error(f"❌ خطأ في تطبيق الظلال: {str(e)}")
        return image

def apply_highlights(image: Image.Image, highlights_value: float) -> Image.Image:
    """
    تطبيق تأثير الإضاءة
    
    Args:
        image: الصورة
        highlights_value: قيمة الإضاءة (-100 إلى 100)
        
    Returns:
        الصورة المعدلة
    """
    try:
        if highlights_value == 0:
            return image
        
        # تطبيع القيمة (معاكسة الظلال)
        normalized = normalize_value(-highlights_value, -100, 100, 0.3, 1.5)
        enhancer = ImageEnhance.Brightness(image)
        return enhancer.enhance(normalized)
    except Exception as e:
        logger.error(f"❌ خطأ في تطبيق الإضاءة: {str(e)}")
        return image

def apply_fade(image: Image.Image, fade_value: float) -> Image.Image:
    """
    تطبيق تأثير التلاشي (Fade)
    
    Args:
        image: الصورة
        fade_value: قيمة التلاشي (0 إلى 1)
        
    Returns:
        الصورة المعدلة
    """
    try:
        if fade_value == 0:
            return image
        
        # إنشاء صورة بيضاء نصف شفافة
        white_overlay = Image.new('RGB', image.size, (255, 255, 255))
        
        # دمج الصور
        image = Image.blend(image, white_overlay, fade_value)
        return image
    except Exception as e:
        logger.error(f"❌ خطأ في تطبيق التلاشي: {str(e)}")
        return image
