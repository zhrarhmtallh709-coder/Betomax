# -*- coding: utf-8 -*-
"""
معالج الأخطاء - للتعامل مع الأخطاء بشكل آمن
"""

from flask import jsonify
import logging
from utils.exceptions import AttendanceSystemException

logger = logging.getLogger(__name__)

def register_error_handlers(app):
    """تسجيل معالجات الأخطاء في التطبيق
    
    Args:
        app: تطبيق Flask
    """
    
    @app.errorhandler(400)
    def bad_request(error):
        """معالج خطأ 400"""
        logger.warning(f"⚠️  طلب غير صحيح: {str(error)}")
        return jsonify({
            'status': 'error',
            'message': 'طلب غير صحيح',
            'error_code': 400
        }), 400
    
    @app.errorhandler(401)
    def unauthorized(error):
        """معالج خطأ 401"""
        logger.warning(f"⚠️  غير مصرح: {str(error)}")
        return jsonify({
            'status': 'error',
            'message': 'غير مصرح',
            'error_code': 401
        }), 401
    
    @app.errorhandler(403)
    def forbidden(error):
        """معالج خطأ 403"""
        logger.warning(f"⚠️  محظور: {str(error)}")
        return jsonify({
            'status': 'error',
            'message': 'محظور',
            'error_code': 403
        }), 403
    
    @app.errorhandler(404)
    def not_found(error):
        """معالج خطأ 404"""
        logger.warning(f"⚠️  الصفحة غير موجودة: {str(error)}")
        return jsonify({
            'status': 'error',
            'message': 'الصفحة غير موجودة',
            'error_code': 404
        }), 404
    
    @app.errorhandler(413)
    def request_entity_too_large(error):
        """معالج خطأ 413"""
        logger.warning("⚠️  الملف كبير جداً")
        return jsonify({
            'status': 'error',
            'message': 'الملف كبير جداً (الحد الأقصى 5MB)',
            'error_code': 413
        }), 413
    
    @app.errorhandler(500)
    def internal_error(error):
        """معالج خطأ 500"""
        logger.error(f"❌ خطأ داخلي: {str(error)}")
        return jsonify({
            'status': 'error',
            'message': 'خطأ داخلي في الخادم',
            'error_code': 500
        }), 500
    
    @app.errorhandler(AttendanceSystemException)
    def handle_custom_error(error):
        """معالج الأخطاء المخصصة"""
        logger.error(f"❌ Custom Error: {error.log_details}")
        return jsonify({
            'status': 'error',
            'message': error.message
        }), error.error_code
    
    @app.errorhandler(Exception)
    def handle_general_error(error):
        """معالج الأخطاء العامة"""
        logger.error(f"❌ Unexpected Error: {str(error)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': 'حدث خطأ غير متوقع. يرجى المحاولة لاحقاً'
        }), 500
    
    return app
