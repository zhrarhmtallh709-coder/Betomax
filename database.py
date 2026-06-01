import psycopg2
from psycopg2.extras import RealDictCursor
import numpy as np
from config import Config
import logging

logger = logging.getLogger(__name__)

class Database:
    """فئة للتعامل مع قاعدة البيانات"""
    
    def __init__(self):
        self.host = Config.DB_HOST
        self.database = Config.DB_NAME
        self.user = Config.DB_USER
        self.password = Config.DB_PASSWORD
        self.port = Config.DB_PORT
    
    def get_connection(self):
        """الاتصال بقاعدة البيانات"""
        try:
            conn = psycopg2.connect(
                host=self.host,
                database=self.database,
                user=self.user,
                password=self.password,
                port=self.port
            )
            return conn
        except psycopg2.Error as e:
            logger.error(f"خطأ في الاتصال بقاعدة البيانات: {str(e)}")
            return None
    
    def close_connection(self, conn, cursor=None):
        """إغلاق الاتصال والـ cursor"""
        try:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
        except psycopg2.Error as e:
            logger.error(f"خطأ في إغلاق الاتصال: {str(e)}")

# دوال العمليات على قاعدة البيانات

def save_student_data(student_id, name, email, face_encoding, photo_filename):
    """
    حفظ بيانات الطالب وبصمة الوجه
    
    Args:
        student_id: معرف الطالب
        name: اسم الطالب
        email: البريد الإلكتروني
        face_encoding: بصمة الوجه (numpy array)
        photo_filename: اسم الصورة
    
    Returns:
        bool: True إذا نجح، False إذا فشل
    """
    db = Database()
    conn = db.get_connection()
    
    if not conn:
        logger.error("فشل الاتصال بقاعدة البيانات")
        return False
    
    try:
        cur = conn.cursor()
        
        # التحقق من وجود الطالب
        cur.execute(
            "SELECT id FROM students WHERE student_id = %s",
            (student_id,)
        )
        existing_student = cur.fetchone()
        
        if existing_student:
            student_db_id = existing_student[0]
            # تحديث بيانات الطالب
            cur.execute("""
                UPDATE students 
                SET name = %s, email = %s, updated_at = CURRENT_TIMESTAMP
                WHERE student_id = %s
            """, (name, email, student_id))
        else:
            # إدراج طالب جديد
            cur.execute("""
                INSERT INTO students (student_id, name, email)
                VALUES (%s, %s, %s)
                RETURNING id
            """, (student_id, name, email))
            student_record = cur.fetchone()
            student_db_id = student_record[0]
        
        # تحويل numpy array إلى bytes
        encoding_bytes = face_encoding.tobytes()
        
        # حفظ بصمة الوجه
        cur.execute("""
            INSERT INTO face_encodings (student_id, encoding, photo_filename)
            VALUES (%s, %s, %s)
        """, (student_db_id, encoding_bytes, photo_filename))
        
        conn.commit()
        logger.info(f"تم حفظ بيانات الطالب: {student_id}")
        
        db.close_connection(conn, cur)
        return True
    
    except psycopg2.Error as e:
        logger.error(f"خطأ في حفظ البيانات: {str(e)}")
        if conn:
            conn.rollback()
        db.close_connection(conn, cur)
        return False

def save_attendance(attendance_record):
    """
    حفظ تسجيل الحضور
    
    Args:
        attendance_record: قاموس يحتوي على بيانات الحضور
    
    Returns:
        bool: True إذا نجح، False إذا فشل
    """
    db = Database()
    conn = db.get_connection()
    
    if not conn:
        logger.error("فشل الاتصال بقاعدة البيانات")
        return False
    
    try:
        cur = conn.cursor()
        
        # التحقق من عدم التسجيل مسبقاً في نفس المحاضرة
        cur.execute("""
            SELECT id FROM attendance 
            WHERE student_id = %s AND lecture_id = %s 
            AND DATE(check_in_time) = CURRENT_DATE
        """, (attendance_record['student_id'], attendance_record['lecture_id']))
        
        if cur.fetchone():
            logger.warning(f"الطالب {attendance_record['student_id']} مسجل مسبقاً")
            db.close_connection(conn, cur)
            return False
        
        # إدراج تسجيل الحضور
        cur.execute("""
            INSERT INTO attendance 
            (student_id, lecture_id, confidence_score, photo_path)
            VALUES (%s, %s, %s, %s)
        """, (
            attendance_record['student_id'],
            attendance_record['lecture_id'],
            attendance_record.get('confidence', 0.0),
            attendance_record.get('photo_path', None)
        ))
        
        conn.commit()
        logger.info(f"تم تسجيل حضور الطالب: {attendance_record['student_id']}")
        
        db.close_connection(conn, cur)
        return True
    
    except psycopg2.Error as e:
        logger.error(f"خطأ في حفظ الحضور: {str(e)}")
        if conn:
            conn.rollback()
        db.close_connection(conn, cur)
        return False

def load_all_face_encodings():
    """
    تحميل جميع بصمات الوجه من قاعدة البيانات
    
    Returns:
        tuple: (encodings, names, student_ids)
    """
    db = Database()
    conn = db.get_connection()
    
    if not conn:
        logger.error("فشل الاتصال بقاعدة البيانات")
        return [], [], []
    
    try:
        cur = conn.cursor()
        
        cur.execute("""
            SELECT s.id, s.name, s.student_id, fe.encoding
            FROM face_encodings fe
            JOIN students s ON fe.student_id = s.id
            WHERE s.is_active = TRUE AND fe.is_active = TRUE
            ORDER BY s.name
        """)
        
        records = cur.fetchall()
        
        encodings = []
        names = []
        student_ids = []
        
        for student_db_id, name, student_id, encoding_bytes in records:
            try:
                # تحويل bytes إلى numpy array
                encoding = np.frombuffer(encoding_bytes, dtype=np.float64)
                encodings.append(encoding)
                names.append(name)
                student_ids.append((student_db_id, student_id))
            except Exception as e:
                logger.warning(f"خطأ في تحويل بصمة الطالب {student_id}: {str(e)}")
                continue
        
        logger.info(f"تم تحميل {len(encodings)} بصمة وجه")
        db.close_connection(conn, cur)
        
        return encodings, names, student_ids
    
    except psycopg2.Error as e:
        logger.error(f"خطأ في تحميل البصمات: {str(e)}")
        db.close_connection(conn, cur)
        return [], [], []

def get_attendance_report(lecture_id):
    """
    الحصول على تقرير الحضور لمحاضرة معينة
    
    Args:
        lecture_id: معرف المحاضرة
    
    Returns:
        list: قائمة بتسجيلات الحضور
    """
    db = Database()
    conn = db.get_connection()
    
    if not conn:
        logger.error("فشل الاتصال بقاعدة البيانات")
        return []
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT 
                s.student_id, 
                s.name, 
                s.email,
                a.check_in_time, 
                a.confidence_score
            FROM attendance a
            JOIN students s ON a.student_id = s.id
            WHERE a.lecture_id = %s
            ORDER BY a.check_in_time DESC
        """, (lecture_id,))
        
        records = cur.fetchall()
        db.close_connection(conn, cur)
        
        return records
    
    except psycopg2.Error as e:
        logger.error(f"خطأ في جلب التقرير: {str(e)}")
        db.close_connection(conn, cur)
        return []

def get_student_by_id(student_id):
    """
    الحصول على بيانات الطالب
    
    Args:
        student_id: معرف الطالب
    
    Returns:
        dict: بيانات الطالب أو None
    """
    db = Database()
    conn = db.get_connection()
    
    if not conn:
        return None
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute(
            "SELECT * FROM students WHERE student_id = %s",
            (student_id,)
        )
        
        record = cur.fetchone()
        db.close_connection(conn, cur)
        
        return record
    
    except psycopg2.Error as e:
        logger.error(f"خطأ في جلب بيانات الطالب: {str(e)}")
        db.close_connection(conn, cur)
        return None

def get_all_lectures():
    """الحصول على جميع المحاضرات"""
    db = Database()
    conn = db.get_connection()
    
    if not conn:
        return []
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT * FROM lectures 
            WHERE lecture_date >= CURRENT_DATE
            ORDER BY lecture_date DESC, start_time DESC
        """)
        
        records = cur.fetchall()
        db.close_connection(conn, cur)
        
        return records
    
    except psycopg2.Error as e:
        logger.error(f"خطأ في جلب المحاضرات: {str(e)}")
        db.close_connection(conn, cur)
        return []

def add_attendance_log(student_id, action, details, ip_address=None):
    """
    إضافة سجل للعمليات
    
    Args:
        student_id: معرف الطالب
        action: نوع العملية
        details: تفاصيل العملية
        ip_address: عنوان IP
    
    Returns:
        bool: True إذا نجح
    """
    db = Database()
    conn = db.get_connection()
    
    if not conn:
        return False
    
    try:
        cur = conn.cursor()
        
        cur.execute("""
            INSERT INTO attendance_log 
            (student_id, action, details, ip_address)
            VALUES (%s, %s, %s, %s)
        """, (student_id, action, details, ip_address))
        
        conn.commit()
        db.close_connection(conn, cur)
        
        return True
    
    except psycopg2.Error as e:
        logger.error(f"خطأ في إضافة السجل: {str(e)}")
        if conn:
            conn.rollback()
        db.close_connection(conn, cur)
        return False