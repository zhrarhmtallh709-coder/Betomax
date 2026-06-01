import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """إعدادات التطبيق"""
    
    # قاعدة البيانات
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_NAME = os.getenv('DB_NAME', 'attendance_db')
    DB_USER = os.getenv('DB_USER', 'postgres')
    DB_PASSWORD = os.getenv('DB_PASSWORD', 'password')
    DB_PORT = os.getenv('DB_PORT', 5432)
    
    # Flask
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = os.getenv('DEBUG', 'False') == 'True'
    
    # التحقق من الوجه
    FACE_RECOGNITION_TOLERANCE = 0.6
    MIN_CONFIDENCE = 0.5
    EYE_ASPECT_RATIO_THRESHOLD = 0.2
    
    # معالجة الصور
    TARGET_IMAGE_SIZE = (640, 480)
    BLUR_THRESHOLD = 100
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    
    # المسارات
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
    ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif'}