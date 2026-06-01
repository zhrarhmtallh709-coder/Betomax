import cv2
import numpy as np
from scipy.spatial import distance as dist
import logging

logger = logging.getLogger(__name__)

# محاولة استيراد dlib
try:
    import dlib
    DLIB_AVAILABLE = True
    detector = dlib.get_frontal_face_detector()
    
    # تحميل نموذج العلامات
    try:
        predictor = dlib.shape_predictor("shape_predictor_68_face_landmarks.dat")
    except:
        logger.warning("لم يتم العثور على shape_predictor_68_face_landmarks.dat")
        predictor = None
except ImportError:
    DLIB_AVAILABLE = False
    logger.warning("dlib غير مثبت - سيتم استخدام طريقة بديلة")
    detector = None
    predictor = None

# مؤشرات العيون في نموذج dlib
LEFT_EYE_START = 36
LEFT_EYE_END = 42
RIGHT_EYE_START = 42
RIGHT_EYE_END = 48

def eye_aspect_ratio(eye):
    """
    حساب نسبة العين (Eye Aspect Ratio - EAR)
    EAR منخفضة = العين مغلقة
    EAR عالية = العين مفتوحة
    
    Args:
        eye: مصفوفة نقاط العين
    
    Returns:
        float: نسبة العين
    """
    try:
        # حساب المسافات بين نقاط العين
        A = dist.euclidean(eye[1], eye[5])
        B = dist.euclidean(eye[2], eye[4])
        C = dist.euclidean(eye[0], eye[3])
        
        # حساب EAR
        ear = (A + B) / (2.0 * C)
        return ear
    except Exception as e:
        logger.error(f"خطأ في حساب EAR: {str(e)}")
        return 0.0

def check_eye_openness(image, ear_threshold=0.2):
    """
    التحقق من فتح العينين (اختبار الحيوية)
    
    Args:
        image: الصورة المدخلة
        ear_threshold: حد تسامح نسبة العين
    
    Returns:
        bool: True إذا كانت العينان مفتوحتان
    """
    try:
        if not DLIB_AVAILABLE or detector is None or predictor is None:
            logger.warning("dlib غير متاح - تخطي فحص العينين")
            return True
        
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # تحديد الوجوه
        faces = detector(gray, 0)
        
        if len(faces) == 0:
            logger.warning("لم يتم العثور على وجه في الصورة")
            return False
        
        face = faces[0]
        
        # استخراج العلامات الـ 68 للوجه
        landmarks = predictor(gray, face)
        landmarks = np.array([(landmarks.part(i).x, landmarks.part(i).y) 
                             for i in range(68)])
        
        # استخراج نقاط العينين
        left_eye = landmarks[LEFT_EYE_START:LEFT_EYE_END]
        right_eye = landmarks[RIGHT_EYE_START:RIGHT_EYE_END]
        
        # حساب EAR للعينين
        left_ear = eye_aspect_ratio(left_eye)
        right_ear = eye_aspect_ratio(right_eye)
        avg_ear = (left_ear + right_ear) / 2.0
        
        logger.info(f"EAR: {avg_ear:.2f}")
        
        # التحقق من حالة العينين
        is_open = avg_ear > ear_threshold
        logger.info(f"حالة العينين: {'مفتوحة' if is_open else 'مغلقة'}")
        
        return is_open
    
    except Exception as e:
        logger.error(f"خطأ في فحص العينين: {str(e)}")
        return True

def detect_blinking(image_sequence, ear_threshold=0.2, consecutive_frames=3):
    """
    كشف حركة العينين (رمش العينين)
    للتحقق من حيوية الشخص
    
    Args:
        image_sequence: سلسلة من الصور
        ear_threshold: حد تسامح EAR
        consecutive_frames: عدد الإطارات المتتالية
    
    Returns:
        bool: True إذا تم كشف رمش
    """
    try:
        if not DLIB_AVAILABLE or detector is None or predictor is None:
            logger.warning("dlib غير متاح - تخطي كشف الرمش")
            return True
        
        if not image_sequence or len(image_sequence) == 0:
            return False
        
        ear_values = []
        
        for image in image_sequence:
            try:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                faces = detector(gray, 0)
                
                if len(faces) > 0:
                    landmarks = predictor(gray, faces[0])
                    landmarks = np.array([(landmarks.part(i).x, landmarks.part(i).y) 
                                         for i in range(68)])
                    
                    left_eye = landmarks[LEFT_EYE_START:LEFT_EYE_END]
                    right_eye = landmarks[RIGHT_EYE_START:RIGHT_EYE_END]
                    
                    left_ear = eye_aspect_ratio(left_eye)
                    right_ear = eye_aspect_ratio(right_eye)
                    avg_ear = (left_ear + right_ear) / 2.0
                    
                    ear_values.append(avg_ear)
            except Exception as e:
                logger.warning(f"خطأ في معالجة إطار: {str(e)}")
                continue
        
        if len(ear_values) < consecutive_frames:
            return False
        
        # البحث عن نمط فتح/إغلاق العينين
        blink_detected = False
        for i in range(len(ear_values) - consecutive_frames + 1):
            window = ear_values[i:i + consecutive_frames]
            if min(window) < ear_threshold and max(window) > ear_threshold:
                blink_detected = True
                logger.info("تم كشف رمش العينين")
                break
        
        return blink_detected
    
    except Exception as e:
        logger.error(f"خطأ في كشف الرمش: {str(e)}")
        return True