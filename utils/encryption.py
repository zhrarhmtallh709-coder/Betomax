# -*- coding: utf-8 -*-
"""
وحدة التشفير - لتشفير وفك تشفير البيانات الحساسة
"""

from cryptography.fernet import Fernet
import os
import logging

logger = logging.getLogger(__name__)

class Encryption:
    """فئة لتشفير وفك تشفير البيانات الحساسة"""
    
    def __init__(self):
        """تهيئة Encryption"""
        # قراءة المفتاح من متغير البيئة
        key = os.getenv('ENCRYPTION_KEY')
        if not key:
            logger.warning("ENCRYPTION_KEY غير معرف - سيتم استخدام مفتاح افتراضي")
            key = Fernet.generate_key()
        
        try:
            self.cipher = Fernet(key.encode() if isinstance(key, str) else key)
        except Exception as e:
            logger.error(f"خطأ في تهيئة التشفير: {str(e)}")
            raise ValueError("مفتاح التشفير غير صحيح")
    
    def encrypt_encoding(self, encoding_bytes):
        """تشفير بصمة الوجه
        
        Args:
            encoding_bytes: البيانات المراد تشفيرها
        
        Returns:
            bytes: البيانات المشفرة
        """
        try:
            encrypted = self.cipher.encrypt(encoding_bytes)
            logger.info("تم تشفير بصمة الوجه بنجاح")
            return encrypted
        except Exception as e:
            logger.error(f"خطأ في تشفير البصمة: {str(e)}")
            raise
    
    def decrypt_encoding(self, encrypted_bytes):
        """فك تشفير بصمة الوجه
        
        Args:
            encrypted_bytes: البيانات المشفرة
        
        Returns:
            bytes: البيانات المفكوكة
        """
        try:
            decrypted = self.cipher.decrypt(encrypted_bytes)
            logger.info("تم فك تشفير بصمة الوجه بنجاح")
            return decrypted
        except Exception as e:
            logger.error(f"خطأ في فك التشفير: {str(e)}")
            raise

def generate_encryption_key():
    """توليد مفتاح تشفير جديد
    
    Returns:
        str: المفتاح المُشفر
    """
    key = Fernet.generate_key()
    return key.decode()
