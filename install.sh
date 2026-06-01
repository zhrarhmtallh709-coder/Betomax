#!/bin/bash

echo "🚀 جاري تثبيت نظام تسجيل الحضور..."

# تحديث النظام
echo "📦 تحديث النظام..."
sudo apt-get update
sudo apt-get install -y python3-pip python3-dev libpq-dev

# تثبيت المتطلبات
echo "📚 تثبيت المكتبات المطلوبة..."
pip install -r requirements.txt

# تحميل نموذج dlib
echo "⬇️ تحميل نموذج العلامات..."
cd utils
wget http://dlib.net/files/shape_predictor_68_face_landmarks.dat.bz2
bzip2 -d shape_predictor_68_face_landmarks.dat.bz2
cd ..

# إنشاء قاعدة البيانات
echo "🗄️ إنشاء قاعدة البيانات..."
psql -U postgres -f database/schema.sql

# إنشاء مجلد الرفع
mkdir -p uploads

echo "✅ اكتمل التثبيت!"
echo "▶️  لتشغيل التطبيق: python app.py"