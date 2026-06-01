from flask import Flask, render_template, request, jsonify
from datetime import datetime
import cv2
import numpy as np
import os
import logging
from functools import wraps

from config import Config
from error_handler import register_error_handlers
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

# إعداد السجلات
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('attendance_system.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# إنشاء التطبيق
app = Flask(__name__)
app.config.from_object(Config)

# تسجيل معالجات الأخطاء
register_error_handlers(app)

# إنشاء مجلد الرفع إذا لم يكن موجوداً
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# تحميل بصمات الوجه عند بدء التطبيق
logger.info("جاري تحميل بصمات الوجه...")
known_face_encodings, known_face_names, student_ids = load_all_face_encodings()
logger.info(f"تم تحميل {len(known_face_encodings)} بصمة وجه")

def require_post(f):
    """Decorator للتحقق من طريقة الطلب"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.method != 'POST':
            return jsonify({
                'status': 'error',
                'message': 'هذا الطلب يتطلب POST'
            }), 405
        return f(*args, **kwargs)
    return decorated_function

def log_request(f):
    """Decorator لتسجيل الطلبات"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        ip_address = request.remote_addr
        logger.info(f"طلب جديد من {ip_address} إلى {request.path}")
        return f(*args, **kwargs)
    return decorated_function

# ============== المسارات ==============

@app.route('/')
def index():
    """الصفحة الرئيسية"""
    try:
        lectures = get_all_lectures()
        return render_template('index.html', lectures=lectures)
    except Exception as e:
        logger.error(f"خطأ في الصفحة الرئيسية: {str(e)}")
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
                logger.warning("محاولة تسجيل ببيانات ناقصة")
                return jsonify({
                    'status': 'error',
                    'message': 'جميع الحقول مطلوبة'
                }), 400
            
            # التحقق من صيغة البريد الإلكتروني
            if '@' not in email:
                return jsonify({
                    'status': 'error',
                    'message': 'صيغة البريد الإلكتروني غير صحيحة'
                }), 400
            
            file = request.files.get('photo')
            if not file:
                return jsonify({
                    'status': 'error',
                    'message': 'يرجى رفع صورة'
                }), 400
            
            # قراءة الصورة
            file_content = file.read()
            nparr = np.frombuffer(file_content, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if image is None:
                logger.error("فشل في قراءة الصورة المرفوعة")
                return jsonify({
                    'status': 'error',
                    'message': 'فشل في قراءة الصورة'
                }), 400
            
            # التحقق من جودة الصورة
            validation = validate_image(image)
            if not validation['is_valid']:
                logger.warning(f"الصورة غير صالحة: {validation['reason']}")
                return jsonify({
                    'status': 'error',
                    'message': f"الصورة غير صالحة: {validation['reason']}"
                }), 400
            
            # معالجة الصورة
            processed_image = preprocess_image(image)
            
            # استخراج بصمة الوجه
            face_encoding = extract_face_encoding(processed_image)
            
            if face_encoding is None:
                logger.warning(f"لم يتم التعرف على وجه للطالب {student_id}")
                return jsonify({
                    'status': 'error',
                    'message': 'لم يتمكن النظام من التعرف على الوجه. تأكد من أن وجهك واضح في الصورة'
                }), 400
            
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
                filename
            )
            
            if success:
                # تحديث قائمة البصمات المحملة
                global known_face_encodings, known_face_names, student_ids
                known_face_encodings, known_face_names, student_ids = load_all_face_encodings()
                
                logger.info(f"تم تسجيل طالب جديد: {student_id}")
                add_attendance_log(None, 'registration', f'تسجيل طالب جديد: {student_id}')
                
                return jsonify({
                    'status': 'success',
                    'message': 'تم التسجيل بنجاح! يمكنك الآن تسجيل الحضور'
                })
            else:
                logger.error(f"فشل حفظ البيانات للطالب {student_id}")
                return jsonify({
                    'status': 'error',
                    'message': 'حدث خطأ في حفظ البيانات. يرجى المحاولة لاحقاً'
                }), 500
        
        except Exception as e:
            logger.error(f"خطأ في تسجيل الطالب: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': f'خطأ: {str(e)}'
            }), 500
    
    return render_template('register.html')

@app.route('/attendance', methods=['POST'])
@require_post
@log_request
def attendance():
    """تسجيل الحضور"""
    try:
        lecture_id = request.form.get('lecture_id', '').strip()
        file = request.files.get('photo')
        
        if not lecture_id or not file:
            return jsonify({
                'status': 'error',
                'message': 'المحاضرة والصورة مطلوبة'
            }), 400
        
        # قراءة الصورة
        file_content = file.read()
        nparr = np.frombuffer(file_content, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if image is None:
            logger.error("فشل في قراءة الصورة")
            return jsonify({
                'status': 'error',
                'message': 'فشل في قراءة الصورة'
            }), 400
        
        # التحقق من جودة الصورة
        validation = validate_image(image)
        if not validation['is_valid']:
            logger.warning(f"صورة الحضور غير صالحة: {validation['reason']}")
            return jsonify({
                'status': 'error',
                'message': f"صورة غير صالحة: {validation['reason']}"
            }), 400
        
        # معالجة الصورة
        processed_image = preprocess_image(image)
        
        # استخراج بصمة الوجه
        face_encoding = extract_face_encoding(processed_image)
        
        if face_encoding is None:
            logger.warning("لم يتم العثور على وجه في صورة الحضور")
            return jsonify({
                'status': 'error',
                'message': 'لم يتم العثور على وجه في الصورة'
            }), 400
        
        # التحقق من حيوية الوجه (فتح العينين)
        is_alive = check_eye_openness(processed_image)
        
        if not is_alive:
            logger.warning("فشل اختبار الحيوية")
            return jsonify({
                'status': 'error',
                'message': 'فشل اختبار الحيوية - تأكد من فتح عينيك'
            }), 400
        
        # البحث عن الطالب المطابق
        if not known_face_encodings:
            logger.error("لا توجد بصمات مخزنة")
            return jsonify({
                'status': 'error',
                'message': 'النظام لم يتم تسجيل أي طلاب بعد'
            }), 400
        
        best_match_index, best_distance = find_best_match(
            known_face_encodings,
            face_encoding,
            tolerance=Config.FACE_RECOGNITION_TOLERANCE
        )
        
        if best_match_index == -1:
            logger.warning("لم يتم العثور على طالب مطابق")
            add_attendance_log(None, 'unrecognized', 'محاولة تسجيل حضور لشخص غير معروف')
            
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
            logger.info(f"تم تسجيل حضور الطالب: {student_name} ({student_id})")
            add_attendance_log(student_db_id, 'attendance', f'تسجيل حضور في المحاضرة {lecture_id}')
            
            return jsonify({
                'status': 'success',
                'message': f'مرحباً {student_name}، تم تسجيل حضورك ✓',
                'student_name': student_name,
                'student_id': student_id,
                'confidence': round(confidence * 100, 2)
            })
        else:
            logger.error("فشل حفظ تسجيل الحضور")
            return jsonify({
                'status': 'error',
                'message': 'حدث خطأ في حفظ تسجيل الحضور'
            }), 500
    
    except Exception as e:
        logger.error(f"خطأ في تسجيل الحضور: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'خطأ: {str(e)}'
        }), 500

@app.route('/reports')
@log_request
def reports():
    """عرض تقارير الحضور"""
    try:
        lecture_id = request.args.get('lecture_id', '').strip()
        
        if not lecture_id:
            return jsonify({
                'status': 'error',
                'message': 'معرف المحاضرة مطلوب'
            }), 400
        
        attendance_data = get_attendance_report(lecture_id)
        
        # تحويل التاريخ والساعة إلى نص
        data_serializable = []
        for record in attendance_data:
            data_serializable.append({
                'student_id': record['student_id'],
                'name': record['name'],
                'email': record['email'],
                'check_in_time': record['check_in_time'].isoformat() if record['check_in_time'] else None,
                'confidence_score': float(record['confidence_score']) if record['confidence_score'] else 0
            })
        
        logger.info(f"تم جلب تقرير الحضور للمحاضرة {lecture_id}")
        
        return jsonify({
            'status': 'success',
            'data': data_serializable,
            'count': len(data_serializable)
        })
    
    except Exception as e:
        logger.error(f"خطأ في جلب التقارير: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'خطأ: {str(e)}'
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
        })
    
    except Exception as e:
        logger.error(f"خطأ في جلب المحاضرات: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'خطأ: {str(e)}'
        }), 500

@app.route('/health')
def health_check():
    """فحص صحة النظام"""
    return jsonify({
        'status': 'healthy',
        'loaded_encodings': len(known_face_encodings),
        'timestamp': datetime.now().isoformat()
    })

# ============== معالجات الأخطاء ==============

@app.before_request
def before_request():
    """معالج قبل كل طلب"""
    request.start_time = datetime.now()

@app.after_request
def after_request(response):
    """معالج بعد كل طلب"""
    if hasattr(request, 'start_time'):
        duration = (datetime.now() - request.start_time).total_seconds()
        logger.debug(f"الطلب استغرق {duration:.2f} ثانية")
    
    response.headers['Content-Type'] = 'application/json; charset=utf-8'
    return response

if __name__ == '__main__':
    logger.info("جاري بدء التطبيق...")
    logger.info(f"عدد البصمات المحملة: {len(known_face_encodings)}")
    
    app.run(
        debug=Config.DEBUG,
        host='0.0.0.0',
        port=5000,
        threaded=True
    )