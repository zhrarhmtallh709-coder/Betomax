# -*- coding: utf-8 -*-
"""
إعدادات التطبيق
"""

import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """إعدادات التطبيق الرئيسية"""
    
    # ============== قاعدة البيانات ==============
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_NAME = os.getenv('DB_NAME', 'attendance_db')
    DB_USER = os.getenv('DB_USER', 'postgres')
    DB_PASSWORD = os.getenv('DB_PASSWORD', 'password')
    DB_PORT = os.getenv('DB_PORT', 5432)
    
    # ============== Flask ==============
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = os.getenv('DEBUG', 'False') == 'True'
    TESTING = os.getenv('TESTING', 'False') == 'True'
    
    # ============== JWT ==============
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'dev-jwt-secret-change-in-production')
    JWT_ACCESS_TOKEN_EXPIRES = 86400  # 24 ساعة
    
    # ============== التشفير ==============
    ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY')
    
    # ============== التحقق من الوجه ==============
    FACE_RECOGNITION_TOLERANCE = float(os.getenv('FACE_RECOGNITION_TOLERANCE', 0.6))
    MIN_CONFIDENCE = float(os.getenv('MIN_CONFIDENCE', 0.5))
    EYE_ASPECT_RATIO_THRESHOLD = float(os.getenv('EYE_ASPECT_RATIO_THRESHOLD', 0.2))
    
    # ============== معالجة الصور ==============
    TARGET_IMAGE_SIZE = (640, 480)
    BLUR_THRESHOLD = 100
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5MB
    
    # ============== المسارات ==============
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
    ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png'}
    
    # ============== الأمان ==============
    SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'True') == 'True'
    SESSION_COOKIE_HTTPONLY = os.getenv('SESSION_COOKIE_HTTPONLY', 'True') == 'True'
    SESSION_COOKIE_SAMESITE = os.getenv('SESSION_COOKIE_SAMESITE', 'Lax')
    PERMANENT_SESSION_LIFETIME = 86400  # 24 ساعة
    
    # ============== التسجيل ==============
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_MAX_SIZE = 10 * 1024 * 1024  # 10MB
    LOG_BACKUP_COUNT = 10

class DevelopmentConfig(Config):
    """إعدادات التطوير"""
    DEBUG = True
    TESTING = False

class ProductionConfig(Config):
    """إعدادات الإنتاج"""
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True

class TestingConfig(Config):
    """إعدادات الاختبارات"""
    DEBUG = True
    TESTING = True
    DB_NAME = 'attendance_test_db'

# اختيار الإعدادات بناءً على البيئة
config_name = os.getenv('FLASK_ENV', 'development')
if config_name == 'production':
    Config = ProductionConfig
elif config_name == 'testing':
    Config = TestingConfig
else:
    Config = DevelopmentConfig
