import cv2
import face_recognition
import numpy as np
import logging

logger = logging.getLogger(__name__)

def extract_face_encoding(image, upsample=1):
    """
    استخراج بصمة الوجه من الصورة
    
    Args:
        image: الصورة المدخلة (OpenCV format)
        upsample: عدد مرات رفع دقة الصورة
    
    Returns:
        numpy.ndarray: بصمة الوجه أو None
    """
    try:
        if image is None:
            logger.warning("الصورة المدخلة None")
            return None
        
        # تحويل الصورة من BGR إلى RGB
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # تحديد موقع الوجوه
        face_locations = face_recognition.face_locations(
            rgb_image, 
            upsample_num_times=upsample,
            model='hog'  # استخدام HOG بدلاً من CNN للسرعة
        )
        
        if len(face_locations) == 0:
            logger.warning("لم يتم العثور على وجه في الصورة")
            return None
        
        if len(face_locations) > 1:
            logger.warning(f"تم العثور على {len(face_locations)} وجوه، استخدام الأول فقط")
        
        # استخراج بصمات الوجوه
        face_encodings = face_recognition.face_encodings(
            rgb_image, 
            face_locations,
            num_jitters=1  # استخدام 1 للسرعة، 5 للدقة
        )
        
        if not face_encodings:
            logger.warning("فشل في استخراج بصمة الوجه")
            return None
        
        logger.info("تم استخراج بصمة الوجه بنجاح")
        return face_encodings[0]
    
    except Exception as e:
        logger.error(f"خطأ في استخراج بصمة الوجه: {str(e)}")
        return None

def detect_faces(image):
    """
    تحديد موقع جميع الوجوه في الصورة
    
    Args:
        image: الصورة المدخلة
    
    Returns:
        list: قائمة بمواقع الوجوه
    """
    try:
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(rgb_image)
        return face_locations
    except Exception as e:
        logger.error(f"خطأ في تحديد الوجوه: {str(e)}")
        return []

def compare_faces(known_encodings, test_encoding, tolerance=0.6):
    """
    مقارنة بصمة الوجه مع قاعدة البيانات
    
    Args:
        known_encodings: قائمة البصمات المخزنة
        test_encoding: بصمة الاختبار
        tolerance: حد التسامح (0.6 افتراضي)
    
    Returns:
        tuple: (matches, distances)
    """
    try:
        if not known_encodings or test_encoding is None:
            return [], []
        
        matches = face_recognition.compare_faces(
            known_encodings, 
            test_encoding, 
            tolerance=tolerance
        )
        
        distances = face_recognition.face_distance(
            known_encodings, 
            test_encoding
        )
        
        return matches, distances
    
    except Exception as e:
        logger.error(f"خطأ في المقارنة: {str(e)}")
        return [], []

def find_best_match(known_encodings, test_encoding, tolerance=0.6):
    """
    إيجاد أفضل مطابقة
    
    Args:
        known_encodings: قائمة البصمات المخزنة
        test_encoding: بصمة الاختبار
        tolerance: حد التسامح
    
    Returns:
        tuple: (best_match_index, best_distance) أو (-1, 1.0)
    """
    try:
        if not known_encodings or test_encoding is None:
            return -1, 1.0
        
        distances = face_recognition.face_distance(
            known_encodings, 
            test_encoding
        )
        
        best_match_index = np.argmin(distances)
        best_distance = distances[best_match_index]
        
        if best_distance < tolerance:
            return best_match_index, best_distance
        
        return -1, best_distance
    
    except Exception as e:
        logger.error(f"خطأ في البحث عن أفضل مطابقة: {str(e)}")
        return -1, 1.0