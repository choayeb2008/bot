#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
معالج تحليل الصور باستخدام Google Gemini API
"""

import logging
import os
import base64
import json
import re
from typing import Dict, Any
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# إعداد Gemini API
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
genai.configure(api_key=GEMINI_API_KEY)

MODEL = "gemini-1.5-flash-latest"

ANALYSIS_PROMPT = """أنت متخصص في تحليل إعدادات التحرير الفوتوغرافي.

قم بتحليل هذه الصورة واستخرج إعدادات التحرير التقريبية كأرقام دقيقة:

1. **التباين (Contrast)**: من -100 إلى +100 (0 = طبيعي)
2. **السطوع (Brightness)**: من -100 إلى +100 (0 = طبيعي)
3. **التشبع (Saturation)**: من -100 إلى +100 (0 = طبيعي)
4. **الظلال (Shadows)**: من -100 إلى +100 (0 = لا توجد ظلال)
5. **الإضاءة (Highlights)**: من -100 إلى +100 (0 = لا توجد إضاءة)
6. **درجة الحرارة اللونية (Color Temperature)**: من 2000K إلى 8000K (5500 = محايد)
7. **الحدة (Sharpness)**: من 0 إلى 100 (50 = طبيعي)
8. **التلاشي (Fade)**: من 0 إلى 100 (0 = بدون تلاشي)

**يجب أن يكون الرد بصيغة JSON فقط بدون أي نص إضافي:**
```json
{
    "contrast": <رقم>,
    "brightness": <رقم>,
    "saturation": <رقم>,
    "shadows": <رقم>,
    "highlights": <رقم>,
    "temperature": <رقم>,
    "sharpness": <رقم>,
    "fade": <رقم>,
    "analysis": "وصف موجز للمظهر العام للصورة"
}
```

تأكد من أن الأرقام دقيقة ومعقولة بناءً على ما تراه في الصورة."""

async def analyze_image_settings(image_path: str) -> Dict[str, Any]:
    """
    تحليل الصورة واستخراج إعدادات التحرير
    
    Args:
        image_path: مسار الصورة
        
    Returns:
        قاموس يحتوي على الإعدادات المستخرجة
    """
    try:
        logger.info(f"📸 بدء تحليل الصورة: {image_path}")
        
        # قراءة الصورة وتحويلها إلى base64
        with open(image_path, 'rb') as image_file:
            image_data = base64.standard_b64encode(image_file.read()).decode('utf-8')
        
        # إرسال الصورة إلى Gemini
        model = genai.GenerativeModel(MODEL)
        
        message = model.generate_content([
            {
                "text": ANALYSIS_PROMPT
            },
            {
                "inline_data": {
                    "mime_type": "image/jpeg",
                    "data": image_data,
                }
            }
        ])
        
        # استخراج النص من الرد
        response_text = message.text
        logger.info(f"📝 الرد من Gemini: {response_text[:200]}")
        
        # محاولة استخراج JSON من الرد
        settings = extract_json_from_response(response_text)
        
        logger.info(f"✅ تم تحليل الصورة بنجاح: {settings}")
        return settings
        
    except Exception as e:
        logger.error(f"❌ خطأ في تحليل الصورة: {str(e)}")
        raise Exception(f"فشل تحليل الصورة: {str(e)}")

def extract_json_from_response(response_text: str) -> Dict[str, Any]:
    """
    استخراج JSON من نص الرد
    
    Args:
        response_text: النص المرجع من الـ API
        
    Returns:
        قاموس بالإعدادات
    """
    try:
        # محاولة إيجاد JSON block في النص
        json_match = re.search(r'```json\s*({.*?})\s*```', response_text, re.DOTALL)
        
        if json_match:
            json_str = json_match.group(1)
            settings = json.loads(json_str)
        else:
            # محاولة مباشرة
            settings = json.loads(response_text)
        
        # التحقق من وجود جميع المفاتيح المطلوبة
        required_keys = [
            'contrast', 'brightness', 'saturation', 'shadows',
            'highlights', 'temperature', 'sharpness', 'fade'
        ]
        
        # إضافة قيم افتراضية للمفاتيح الناقصة
        for key in required_keys:
            if key not in settings:
                logger.warning(f"⚠️ مفتاح ناقص: {key}، استخدام قيمة افتراضية")
                settings[key] = 0
        
        return settings
        
    except json.JSONDecodeError as e:
        logger.error(f"❌ خطأ في فك تشفير JSON: {str(e)}")
        logger.error(f"النص: {response_text}")
        
        # إرجاع إعدادات افتراضية
        return {
            'contrast': 0,
            'brightness': 0,
            'saturation': 0,
            'shadows': 0,
            'highlights': 0,
            'temperature': 5500,
            'sharpness': 50,
            'fade': 0
        }
