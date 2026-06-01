from flask import jsonify
import logging

logger = logging.getLogger(__name__)

def register_error_handlers(app):
    """تسجيل معالجات الأخطاء"""
    
    @app.errorhandler(400)
    def bad_request(error):
        logger.warning(f"طلب غير صحيح: {str(error)}")
        return jsonify({
            'status': 'error',
            'message': 'طلب غير صحيح',
            'error_code': 400
        }), 400
    
    @app.errorhandler(404)
    def not_found(error):
        logger.warning(f"الصفحة غير موجودة: {str(error)}")
        return jsonify({
            'status': 'error',
            'message': 'الصفحة غير موجودة',
            'error_code': 404
        }), 404
    
    @app.errorhandler(413)
    def request_entity_too_large(error):
        logger.warning("الملف كبير جداً")
        return jsonify({
            'status': 'error',
            'message': 'الملف كبير جداً (الحد الأقصى 16MB)',
            'error_code': 413
        }), 413
    
    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"خطأ داخلي: {str(error)}")
        return jsonify({
            'status': 'error',
            'message': 'خطأ داخلي في الخادم',
            'error_code': 500
        }), 500
    
    return app