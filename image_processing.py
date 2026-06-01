import cv2
import numpy as np
from config import Config
import logging

logger = logging.getLogger(__name__)

def preprocess_image(image, target_size=None):
    """
    معالجة الصورة قبل المعالجة
    
    Args:
        image: الصورة المدخلة
        target_size: حجم الصورة المستهدف
    
    Returns:
        numpy.ndarray: الصورة المعالجة أو None
    """
    try:
        if image is None:
            logger.error("الصورة المدخلة None")
            return None
        
        if target_size is None:
            target_size = Config.TARGET_IMAGE_SIZE
        
        # تغيير حجم الصورة
        resized = cv2.resize(image, target_size)
        
        # تصحيح الإضاءة (CLAHE)
        lab = cv2.cvtColor(resized, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        l = clahe.apply(l)
        
        processed = cv2.merge([l, a, b])
        processed = cv2.cvtColor(processed, cv2.COLOR_LAB2BGR)
        
        # تطبيق تصفية ثنائية لتنعيم الصورة
        processed = cv2.bilateralFilter(processed, 9, 75, 75)
        
        logger.info("تمت معالجة الصورة بنجاح")
        return processed
    
    except Exception as e:
        logger.error(f"خطأ في معالجة الصورة: {str(e)}")
        return None

def enhance_image(image):
    """
    تحسين جودة الصورة
    
    Args:
        image: الصورة المدخلة
    
    Returns:
        numpy.ndarray: الصورة المحسنة
    """
    try:
        if image is None:
            return None
        
        # زيادة التباين
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l = clahe.apply(l)
        
        enhanced = cv2.merge([l, a, b])
        enhanced = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
        
        logger.info("تم تحسين الصورة")
        return enhanced
    
    except Exception as e:
        logger.error(f"خطأ في تحسين الصورة: {str(e)}")
        return image

def detect_blur(image, threshold=None):
    """
    كشف تمويه الصورة
    
    Args:
        image: الصورة المدخلة
        threshold: حد كشف التمويه
    
    Returns:
        bool: True إذا كانت الصورة حادة، False إذا كانت مموهة
    """
    try:
        if image is None:
            return False
        
        if threshold is None:
            threshold = Config.BLUR_THRESHOLD
        
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        
        is_sharp = laplacian_var > threshold
        
        logger.info(f"جودة الصورة: {laplacian_var:.2f} {'حادة' if is_sharp else 'مموهة'}")
        
        return is_sharp
    
    except Exception as e:
        logger.error(f"خطأ في كشف التمويه: {str(e)}")
        return True

def crop_face(image, face_location):
    """
    قص منطقة الوجه من الصورة
    
    Args:
        image: الصورة المدخلة
        face_location: موقع الوجه (top, right, bottom, left)
    
    Returns:
        numpy.ndarray: صورة الوجه المقصوصة
    """
    try:
        top, right, bottom, left = face_location
        
        # إضافة حاشية حول الوجه
        margin = 20
        top = max(0, top - margin)
        right = min(image.shape[1], right + margin)
        bottom = min(image.shape[0], bottom + margin)
        left = max(0, left - margin)
        
        cropped = image[top:bottom, left:right]
        
        return cropped
    
    except Exception as e:
        logger.error(f"خطأ في قص الوجه: {str(e)}")
        return None

def validate_image(image, min_quality_score=None):
    """
    التحقق من جودة الصورة
    
    Args:
        image: الصورة المدخلة
        min_quality_score: الحد الأدنى لجودة الصورة
    
    Returns:
        dict: نتائج التحقق
    """
    try:
        if image is None:
            return {
                'is_valid': False,
                'reason': 'الصورة None'
            }
        
        # التحقق من الأبعاد
        h, w = image.shape[:2]
        if h < 100 or w < 100:
            return {
                'is_valid': False,
                'reason': 'حجم الصورة صغير جداً'
            }
        
        # كشف التمويه
        if not detect_blur(image):
            return {
                'is_valid': False,
                'reason': 'الصورة مموهة'
            }
        
        # التحقق من الإضاءة
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        brightness = np.mean(gray)
        
        if brightness < 30:
            return {
                'is_valid': False,
                'reason': 'الصورة مظلمة جداً'
            }
        
        if brightness > 220:
            return {
                'is_valid': False,
                'reason': 'الصورة مضاءة جداً'
            }
        
        return {
            'is_valid': True,
            'brightness': brightness
        }
    
    except Exception as e:
        logger.error(f"خطأ في التحقق من الصورة: {str(e)}")
        return {
            'is_valid': False,
            'reason': f'خطأ: {str(e)}'
        }