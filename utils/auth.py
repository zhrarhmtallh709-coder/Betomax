# -*- coding: utf-8 -*-
"""
وحدة المصادقة - لإدارة تسجيل الدخول والمصادقة
"""

from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from functools import wraps
import bcrypt
import logging
from datetime import timedelta

logger = logging.getLogger(__name__)

jwt = JWTManager()

def init_jwt(app):
    """تهيئة JWT في التطبيق
    
    Args:
        app: تطبيق Flask
    """
    import os
    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'dev-jwt-secret-change-in-production')
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=24)
    jwt.init_app(app)
    logger.info("✅ تم تهيئة JWT")

def hash_password(password):
    """تجزئة كلمة المرور
    
    Args:
        password: كلمة المرور
    
    Returns:
        str: كلمة المرور المجزأة
    """
    try:
        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    except Exception as e:
        logger.error(f"خطأ في تجزئة كلمة المرور: {str(e)}")
        raise

def verify_password(password, hashed):
    """التحقق من كلمة المرور
    
    Args:
        password: كلمة المرور المدخلة
        hashed: كلمة المرور المجزأة المخزنة
    
    Returns:
        bool: صحيح إذا كانت كلمة المرور صحيحة
    """
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except Exception as e:
        logger.error(f"خطأ في التحقق من كلمة المرور: {str(e)}")
        return False

def create_auth_token(identity, expires_delta=None):
    """إنشاء رمز المصادقة
    
    Args:
        identity: معرف المستخدم
        expires_delta: مدة انتهاء الرمز
    
    Returns:
        str: رمز JWT
    """
    try:
        access_token = create_access_token(
            identity=identity,
            expires_delta=expires_delta
        )
        logger.info(f"✅ تم إنشاء رمز مصادقة للمستخدم: {identity}")
        return access_token
    except Exception as e:
        logger.error(f"❌ خطأ في إنشاء الرمز: {str(e)}")
        raise

def require_auth(f):
    """Decorator للتحقق من المصادقة
    
    Args:
        f: الدالة المراد حمايتها
    
    Returns:
        function: الدالة المحمية
    """
    @wraps(f)
    @jwt_required()
    def decorated_function(*args, **kwargs):
        try:
            identity = get_jwt_identity()
            logger.debug(f"المستخدم المصرح: {identity}")
            return f(*args, **kwargs)
        except Exception as e:
            logger.error(f"خطأ في المصادقة: {str(e)}")
            raise
    
    return decorated_function
