-- إنشاء قاعدة البيانات
CREATE DATABASE attendance_db;

-- جدول الطلاب
CREATE TABLE students (
    id SERIAL PRIMARY KEY,
    student_id VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    phone VARCHAR(20),
    department VARCHAR(100),
    enrollment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- جدول بصمات الوجه
CREATE TABLE face_encodings (
    id SERIAL PRIMARY KEY,
    student_id INT NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    encoding BYTEA NOT NULL,
    photo_filename VARCHAR(255),
    uploaded_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    quality_score FLOAT DEFAULT 0.0,
    is_active BOOLEAN DEFAULT TRUE
);

-- جدول المحاضرات
CREATE TABLE lectures (
    id SERIAL PRIMARY KEY,
    course_code VARCHAR(50) NOT NULL,
    course_name VARCHAR(200) NOT NULL,
    instructor_name VARCHAR(100) NOT NULL,
    classroom VARCHAR(50),
    lecture_date DATE NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- جدول تسجيل الحضور
CREATE TABLE attendance (
    id SERIAL PRIMARY KEY,
    student_id INT NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    lecture_id INT NOT NULL REFERENCES lectures(id) ON DELETE CASCADE,
    check_in_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    confidence_score FLOAT DEFAULT 0.0,
    is_verified BOOLEAN DEFAULT FALSE,
    photo_path VARCHAR(255),
    notes TEXT
);

-- جدول السجل (Audit Log)
CREATE TABLE attendance_log (
    id SERIAL PRIMARY KEY,
    student_id INT REFERENCES students(id) ON DELETE SET NULL,
    action VARCHAR(50) NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    details TEXT,
    ip_address VARCHAR(50)
);

-- الفهارس لتحسين الأداء
CREATE INDEX idx_student_id ON students(student_id);
CREATE INDEX idx_face_encodings_student ON face_encodings(student_id);
CREATE INDEX idx_attendance_student ON attendance(student_id);
CREATE INDEX idx_attendance_lecture ON attendance(lecture_id);
CREATE INDEX idx_attendance_date ON attendance(check_in_time);
CREATE INDEX idx_lectures_date ON lectures(lecture_date);
CREATE INDEX idx_attendance_log_timestamp ON attendance_log(timestamp);

-- إنشاء عرض (View) للإحصائيات
CREATE VIEW attendance_summary AS
SELECT 
    l.id as lecture_id,
    l.course_name,
    l.lecture_date,
    COUNT(DISTINCT a.student_id) as attended_count,
    COUNT(DISTINCT s.id) as total_students,
    ROUND(100.0 * COUNT(DISTINCT a.student_id) / COUNT(DISTINCT s.id), 2) as attendance_percentage
FROM lectures l
LEFT JOIN attendance a ON l.id = a.lecture_id
CROSS JOIN students s
WHERE s.is_active = TRUE
GROUP BY l.id, l.course_name, l.lecture_date;