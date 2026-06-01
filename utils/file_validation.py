# -*- coding: utf-8 -*-
"""
وحدة التحقق من الملفات - للتحقق من صحة الملفات المرفوعة
"""

import os
import logging
from werkzeug.utils import secure_filename

logger = logging.getLogger(__name__)

class FileValidator:
    """فئة للتحقق من صحة الملفات"""
    
    ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png'}
    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
    
    # التوقيعات السحرية (Magic Bytes)
    MAGIC_BYTES = {
        b'\xff\xd8\xff': 'jpg',   # JPEG
        b'\x89PNG\r\n': 'png',   # PNG
    }
    
    @staticmethod
    def is_allowed_extension(filename):
        """التحقق من امتداد الملف
        
        Args:
            filename: اسم الملف
        
        Returns:
            bool: صحيح إذا كان الامتداد مسموح
        """
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in FileValidator.ALLOWED_EXTENSIONS
    
    @staticmethod
    def has_valid_magic_bytes(file_content):
        """التحقق من التوقيع السحري للملف
        
        Args:
            file_content: محتوى الملف
        
        Returns:
            bool: صحيح إذا كان التوقيع صحيح
        """
        for signature in FileValidator.MAGIC_BYTES.keys():
            if file_content.startswith(signature):
                return True
        return False
    
    @staticmethod
    def validate_file(file, max_size=None):
        """التحقق الشامل من الملف
        
        Args:
            file: كائن الملف من Flask
            max_size: الحد الأقصى لحجم الملف
        
        Returns:
            tuple: (is_valid, message)
        """
        if max_size is None:
            max_size = FileValidator.MAX_FILE_SIZE
        
        # التحقق من أن الملف موجود
        if not file or file.filename == '':
            return False, 'لم يتم اختيار ملف'
        
        # تأمين اسم الملف
        filename = secure_filename(file.filename)
        
        # التحقق من الامتداد
        if not FileValidator.is_allowed_extension(filename):
            logger.warning(f"امتداد ملف غير مسموح: {filename}")
            return False, 'نوع الملف غير مسموح (jpg, jpeg, png فقط)'
        
        # قراءة المحتوى
        file_content = file.read()
        file.seek(0)  # إعادة المؤشر للبداية
        
        # التحقق من الحجم
        if len(file_content) > max_size:
            logger.warning(f"ملف كبير جداً: {len(file_content)} بايت")
            return False, f'الملف كبير جداً (الحد الأقصى {max_size / 1024 / 1024:.0f} MB)'
        
        # التحقق من أن الملف ليس فارغاً
        if len(file_content) == 0:
            return False, 'الملف فارغ'
        
        # التحقق من التوقيع السحري
        if not FileValidator.has_valid_magic_bytes(file_content):
            logger.warning(f"توقيع سحري غير صحيح: {filename}")
            return False, 'الملف ليس صورة صالحة'
        
        logger.info(f"الملف صحيح: {filename}")
        return True, 'صحيح'
