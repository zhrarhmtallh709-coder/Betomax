# -*- coding: utf-8 -*-
"""
وحدة الأخطاء المخصصة - لمعالجة الأخطاء الخاصة بالنظام
"""

import logging

logger = logging.getLogger(__name__)

class AttendanceSystemException(Exception):
    """الفئة الأساسية لأخطاء النظام"""
    
    def __init__(self, message, error_code=500, log_details=None):
        """تهيئة الخطأ
        
        Args:
            message: الرسالة المعروضة للمستخدم
            error_code: كود HTTP
            log_details: التفاصيل المسجلة في السجل
        """
        self.message = message
        self.error_code = error_code
        self.log_details = log_details or message
        super().__init__(self.message)

class InvalidImageError(AttendanceSystemException):
    """خطأ في الصورة"""
    def __init__(self, message, log_details=None):
        super().__init__(message, 400, log_details)

class FaceNotDetectedError(AttendanceSystemException):
    """لم يتم كشف الوجه"""
    def __init__(self, message, log_details=None):
        super().__init__(message, 400, log_details)

class FaceLivenessError(AttendanceSystemException):
    """فشل اختبار الحيوية"""
    def __init__(self, message, log_details=None):
        super().__init__(message, 400, log_details)

class DatabaseError(AttendanceSystemException):
    """خطأ في قاعدة البيانات"""
    def __init__(self, message, log_details=None):
        super().__init__(
            "خطأ في قاعدة البيانات",
            500,
            log_details or message
        )

class AuthenticationError(AttendanceSystemException):
    """فشل المصادقة"""
    def __init__(self, message, log_details=None):
        super().__init__(
            "فشل المصادقة",
            401,
            log_details or message
        )

class AuthorizationError(AttendanceSystemException):
    """لا توجد صلاحيات"""
    def __init__(self, message, log_details=None):
        super().__init__(
            "لا توجد صلاحيات كافية",
            403,
            log_details or message
        )

class ValidationError(AttendanceSystemException):
    """خطأ في التحقق من البيانات"""
    def __init__(self, message, log_details=None):
        super().__init__(message, 400, log_details)
