# -*- coding: utf-8 -*-
"""
تطبيق نظام تسجيل الحضور الذكي - النسخة المحسنة
"""

from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from datetime import datetime, timedelta
import cv2
import numpy as np
import os
import logging
from functools import wraps

# استيراد الوحدات المخصصة
from config import Config
from error_handler import register_error_handlers
from utils.auth import init_jwt, require_auth, create_auth_token, hash_password, verify_password
from utils.exceptions import (
    AttendanceSystemException,
    InvalidImageError,
    FaceNotDetectedError,
    FaceLivenessError,
    DatabaseError,
    AuthenticationError,
    ValidationError
)
from utils.file_validation import FileValidator
from utils.encryption import Encryption
from utils.database_pool import DatabasePool
from utils.face_recognition import extract_face_encoding, find_best_match
from utils.eye_detection import check_eye_openness
from utils.image_processing import preprocess_image, validate_image, detect_blur
from utils.database import (
    save_attendance,
    save_student_data,
    load_all_face_encodings,
    get_attendance_report,
    get_student_by_id,
    get_all_lectures,
    add_attendance_log
)

# ============== إعداد السجلات ==============

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/attendance_system.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ============== إنشاء التطبيق ==============

app = Flask(__name__)
app.config.from_object(Config)

# تفعيل CORS
CORS(app, resources={r"/api/*": {"origins": "*"}})

# تهيئة JWT
init_jwt(app)

# تهيئة تجمع الاتصالات
try:
    DatabasePool.initialize(Config)
except Exception as e:
    logger.error(f"❌ فشل تهيئة تجمع الاتصالات: {str(e)}")
    # سيكون هناك محاولة للاتصال المباشر كبديل

# تسجيل معالجات الأخطاء
register_error_handlers(app)

# إنشاء مجلدات مطلوبة
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('logs', exist_ok=True)

# تهيئة التشفير
try:
    encryption = Encryption()
except Exception as e:
    logger.warning(f"⚠️  تحذير في تهيئة التشفير: {str(e)}")
    encryption = None

# ============== تحميل البيانات ==============

logger.info("جاري تحميل بصمات الوجه...")
try:
    known_face_encodings, known_face_names, student_ids = load_all_face_encodings()
    logger.info(f"✅ تم تحميل {len(known_face_encodings)} بصمة وجه")
except Exception as e:
    logger.error(f"❌ خطأ في تحميل البصمات: {str(e)}")
    known_face_encodings, known_face_names, student_ids = [], [], []

# ============== Decorators ==============

def require_post(f):
    """Decorator للتحقق من طريقة الطلب (POST)"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.method != 'POST':
            raise ValidationError('هذا الطلب يتطلب POST')
        return f(*args, **kwargs)
    return decorated_function

def log_request(f):
    """Decorator لتسجيل الطلبات"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        ip_address = request.remote_addr
        logger.info(f"📍 طلب جديد من {ip_address} إلى {request.path}")
        return f(*args, **kwargs)
    return decorated_function

# ============== المسارات - المصادقة ==============

@app.route('/auth/login', methods=['POST'])
def login():
    """تسجيل دخول المستخدم"""
    try:
        data = request.get_json()
        if not data:
            raise ValidationError('يجب إرسال بيانات JSON')
        
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        
        if not username or not password:
            raise ValidationError('اسم المستخدم وكلمة المرور مطلوبة')
        
        # التحقق من بيانات الدخول (يمكن تحسينها بقاعدة بيانات)
        if username == 'admin' and password == 'admin':
            access_token = create_auth_token(identity=username)
            logger.info(f"✅ تسجيل دخول ناجح: {username}")
            return jsonify({
                'status': 'success',
                'message': 'تم تسجيل الدخول بنجاح',
                'access_token': access_token
            }), 200
        
        logger.warning(f"❌ محاولة تسجيل دخول فاشلة: {username}")
        raise AuthenticationError('بيانات دخول غير صحيحة')
    
    except AttendanceSystemException as e:
        logger.warning(f"⚠️  خطأ مصادقة: {e.log_details}")
        return jsonify({
            'status': 'error',
            'message': e.message
        }), e.error_code
    except Exception as e:
        logger.error(f"❌ خطأ في تسجيل الدخول: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'خطأ غير متوقع في المصادقة'
        }), 500

# ============== المسارات - الصفحات ==============

@app.route('/')
def index():
    """الصفحة الرئيسية"""
    try:
        lectures = get_all_lectures()
        return render_template('index.html', lectures=lectures)
    except Exception as e:
        logger.error(f"❌ خطأ في الصفحة الرئيسية: {str(e)}")
        return render_template('index.html', lectures=[])

@app.route('/register', methods=['GET', 'POST'])
@log_request
def register():
    """تسجيل طالب جديد"""
    if request.method == 'POST':
        try:
            student_id = request.form.get('student_id', '').strip()
            student_name = request.form.get('name', '').strip()
            email = request.form.get('email', '').strip()
            
            # التحقق من المدخلات
            if not all([student_id, student_name, email]):
                logger.warning("❌ محاولة تسجيل ببيانات ناقصة")
                raise ValidationError('جميع الحقول مطلوبة')
            
            # التحقق من صيغة البريد الإلكتروني
            if '@' not in email or '.' not in email:
                raise ValidationError('صيغة البريد الإلكتروني غير صحيحة')
            
            file = request.files.get('photo')
            if not file:
                raise ValidationError('يرجى رفع صورة')
            
            # التحقق من الملف
            is_valid, message = FileValidator.validate_file(file)
            if not is_valid:
                logger.warning(f"❌ ملف غير صالح: {message}")
                raise InvalidImageError(message)
            
            # قراءة الصورة
            file_content = file.read()
            file.seek(0)
            nparr = np.frombuffer(file_content, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if image is None:
                logger.error("❌ فشل في قراءة الصورة المرفوعة")
                raise InvalidImageError('فشل في قراءة الصورة')
            
            # التحقق من جودة الصورة
            validation = validate_image(image)
            if not validation['is_valid']:
                logger.warning(f"⚠️  الصورة غير صالحة: {validation['reason']}")
                raise InvalidImageError(validation['reason'])
            
            # معالجة الصورة
            processed_image = preprocess_image(image)
            if processed_image is None:
                raise InvalidImageError('فشل في معالجة الصورة')
            
            # استخراج بصمة الوجه
            face_encoding = extract_face_encoding(processed_image)
            if face_encoding is None:
                logger.warning(f"⚠️  لم يتم التعرف على وجه للطالب {student_id}")
                raise FaceNotDetectedError(
                    'لم يتمكن النظام من التعرف على الوجه. تأكد من أن وجهك واضح في الصورة'
                )
            
            # حفظ الصورة
            filename = f"{student_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            cv2.imwrite(filepath, image)
            
            # حفظ البيانات
            success = save_student_data(
                student_id,
                student_name,
                email,
                face_encoding,
                filename,
                encryption
            )
            
            if success:
                # تحديث قائمة البصمات المحملة
                global known_face_encodings, known_face_names, student_ids
                known_face_encodings, known_face_names, student_ids = load_all_face_encodings()
                
                logger.info(f"✅ تم تسجيل طالب جديد: {student_id}")
                add_attendance_log(None, 'registration', f'تسجيل طالب جديد: {student_id}', request.remote_addr)
                
                return jsonify({
                    'status': 'success',
                    'message': 'تم التسجيل بنجاح! يمكنك الآن تسجيل الحضور'
                }), 200
            else:
                raise DatabaseError('فشل حفظ البيانات')
        
        except AttendanceSystemException as e:
            logger.warning(f"⚠️  خطأ في التسجيل: {e.log_details}")
            return jsonify({
                'status': 'error',
                'message': e.message
            }), e.error_code
        except Exception as e:
            logger.error(f"❌ خطأ غير متوقع في التسجيل: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': 'حدث خطأ في التسجيل. يرجى المحاولة لاحقاً'
            }), 500
    
    return render_template('register.html')

@app.route('/attendance', methods=['GET', 'POST'])
@require_post
@log_request
def attendance():
    """تسجيل الحضور"""
    try:
        lecture_id = request.form.get('lecture_id', '').strip()
        file = request.files.get('photo')
        
        if not lecture_id:
            raise ValidationError('معرف المحاضرة مطلوب')
        
        if not file:
            raise ValidationError('الصورة مطلوبة')
        
        # التحقق من الملف
        is_valid, message = FileValidator.validate_file(file)
        if not is_valid:
            raise InvalidImageError(message)
        
        # قراءة الصورة
        file_content = file.read()
        file.seek(0)
        nparr = np.frombuffer(file_content, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if image is None:
            raise InvalidImageError('فشل في قراءة الصورة')
        
        # التحقق من جودة الصورة
        validation = validate_image(image)
        if not validation['is_valid']:
            logger.warning(f"⚠️  صورة الحضور غير صالحة: {validation['reason']}")
            raise InvalidImageError(validation['reason'])
        
        # معالجة الصورة
        processed_image = preprocess_image(image)
        if processed_image is None:
            raise InvalidImageError('فشل في معالجة الصورة')
        
        # استخراج بصمة الوجه
        face_encoding = extract_face_encoding(processed_image)
        if face_encoding is None:
            logger.warning("⚠️  لم يتم العثور على وجه في صورة الحضور")
            raise FaceNotDetectedError('لم يتم العثور على وجه في الصورة')
        
        # التحقق من حيوية الوجه (فتح العينين)
        is_alive = check_eye_openness(processed_image)
        if not is_alive:
            logger.warning("⚠️  فشل اختبار الحيوية")
            raise FaceLivenessError('فشل اختبار الحيوية - تأكد من فتح عينيك')
        
        # البحث عن الطالب المطابق
        if not known_face_encodings:
            logger.error("❌ لا توجد بصمات مخزنة")
            raise DatabaseError('النظام لم يتم تسجيل أي طلاب بعد')
        
        best_match_index, best_distance = find_best_match(
            known_face_encodings,
            face_encoding,
            tolerance=Config.FACE_RECOGNITION_TOLERANCE
        )
        
        if best_match_index == -1:
            logger.warning("⚠️  لم يتم العثور على طالب مطابق")
            add_attendance_log(None, 'unrecognized', 'محاولة تسجيل حضور لشخص غير معروف', request.remote_addr)
            return jsonify({
                'status': 'error',
                'message': 'لم يتم التعرف على هذا الطالب'
            }), 404
        
        # الحصول على معلومات الطالب
        student_db_id, student_id = student_ids[best_match_index]
        student_name = known_face_names[best_match_index]
        confidence = 1 - best_distance
        
        # حفظ صورة الحضور
        filename = f"{student_id}_attendance_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        cv2.imwrite(filepath, image)
        
        # حفظ تسجيل الحضور
        attendance_record = {
            'student_id': student_db_id,
            'student_name': student_name,
            'lecture_id': lecture_id,
            'timestamp': datetime.now(),
            'confidence': confidence,
            'photo_path': filepath
        }
        
        success = save_attendance(attendance_record)
        
        if success:
            logger.info(f"✅ تم تسجيل حضور: {student_name} ({student_id})")
            add_attendance_log(student_db_id, 'attendance', f'تسجيل حضور في المحاضرة {lecture_id}', request.remote_addr)
            
            return jsonify({
                'status': 'success',
                'message': f'مرحباً {student_name}، تم تسجيل حضورك ✓',
                'student_name': student_name,
                'student_id': student_id,
                'confidence': round(confidence * 100, 2)
            }), 200
        else:
            raise DatabaseError('فشل حفظ تسجيل الحضور')
    
    except AttendanceSystemException as e:
        logger.warning(f"⚠️  خطأ في تسجيل الحضور: {e.log_details}")
        return jsonify({
            'status': 'error',
            'message': e.message
        }), e.error_code
    except Exception as e:
        logger.error(f"❌ خطأ غير متوقع في تسجيل الحضور: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'حدث خطأ في تسجيل الحضور. يرجى المحاولة لاحقاً'
        }), 500

@app.route('/attendance/form')
def attendance_form():
    """نموذج تسجيل الحضور"""
    return render_template('attendance.html')

@app.route('/reports')
@require_auth
@log_request
def reports():
    """عرض تقارير الحضور"""
    try:
        lecture_id = request.args.get('lecture_id', '').strip()
        page = request.args.get('page', 1, type=int)
        
        if not lecture_id:
            raise ValidationError('معرف المحاضرة مطلوب')
        
        attendance_data = get_attendance_report(lecture_id, page=page)
        
        return jsonify({
            'status': 'success',
            'data': attendance_data
        }), 200
    
    except AttendanceSystemException as e:
        logger.warning(f"⚠️  خطأ في التقارير: {e.log_details}")
        return jsonify({
            'status': 'error',
            'message': e.message
        }), e.error_code
    except Exception as e:
        logger.error(f"❌ خطأ في جلب التقارير: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'خطأ في جلب التقارير'
        }), 500

@app.route('/lectures')
def get_lectures():
    """الحصول على قائمة المحاضرات"""
    try:
        lectures = get_all_lectures()
        
        lectures_data = []
        for lecture in lectures:
            lectures_data.append({
                'id': lecture['id'],
                'course_code': lecture['course_code'],
                'course_name': lecture['course_name'],
                'instructor_name': lecture['instructor_name'],
                'classroom': lecture['classroom'],
                'lecture_date': lecture['lecture_date'].isoformat() if lecture['lecture_date'] else None,
                'start_time': str(lecture['start_time']) if lecture['start_time'] else None,
                'end_time': str(lecture['end_time']) if lecture['end_time'] else None
            })
        
        return jsonify({
            'status': 'success',
            'data': lectures_data
        }), 200
    
    except Exception as e:
        logger.error(f"❌ خطأ في جلب المحاضرات: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'خطأ في جلب المحاضرات'
        }), 500

@app.route('/health')
def health_check():
    """فحص صحة النظام"""
    return jsonify({
        'status': 'healthy',
        'loaded_encodings': len(known_face_encodings),
        'timestamp': datetime.now().isoformat()
    }), 200

# ============== معالجات طلبات أخرى ==============

@app.before_request
def before_request():
    """معالج قبل كل طلب"""
    request.start_time = datetime.now()

@app.after_request
def after_request(response):
    """معالج بعد كل طلب"""
    if hasattr(request, 'start_time'):
        duration = (datetime.now() - request.start_time).total_seconds()
        logger.debug(f"⏱️  الطلب استغرق {duration:.2f} ثانية")
    
    response.headers['Content-Type'] = 'application/json; charset=utf-8'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    
    return response

@app.teardown_appcontext
def teardown_db(exception=None):
    """تنظيف الموارد عند إغلاق التطبيق"""
    DatabasePool.close_all()

# ============== نقطة الدخول الرئيسية ==============

if __name__ == '__main__':
    logger.info("="*50)
    logger.info("🚀 جاري بدء التطبيق...")
    logger.info(f"📊 عدد البصمات المحملة: {len(known_face_encodings)}")
    logger.info("="*50)
    
    app.run(
        debug=Config.DEBUG,
        host='0.0.0.0',
        port=5000,
        threaded=True
    )
