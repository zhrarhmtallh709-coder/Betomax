# -*- coding: utf-8 -*-
"""
وحدة تجمع الاتصالات - لإدارة اتصالات قاعدة البيانات بكفاءة
"""

from psycopg2 import pool
import logging

logger = logging.getLogger(__name__)

class DatabasePool:
    """فئة لتجمع الاتصالات بقاعدة البيانات"""
    
    _pool = None
    
    @classmethod
    def initialize(cls, config):
        """تهيئة التجمع
        
        Args:
            config: كائن الإعدادات
        """
        if cls._pool is not None:
            logger.warning("التجمع مُهيأ بالفعل")
            return
        
        try:
            cls._pool = pool.SimpleConnectionPool(
                minconn=2,
                maxconn=10,
                host=config.DB_HOST,
                database=config.DB_NAME,
                user=config.DB_USER,
                password=config.DB_PASSWORD,
                port=int(config.DB_PORT),
                connect_timeout=5
            )
            logger.info("✅ تم تهيئة تجمع الاتصالات بنجاح")
        except Exception as e:
            logger.error(f"❌ خطأ في تهيئة التجمع: {str(e)}")
            raise
    
    @classmethod
    def get_connection(cls):
        """الحصول على اتصال من التجمع
        
        Returns:
            connection: اتصال بقاعدة البيانات
        """
        if cls._pool is None:
            raise RuntimeError("يجب استدعاء initialize أولاً")
        
        try:
            conn = cls._pool.getconn()
            return conn
        except pool.PoolError as e:
            logger.error(f"❌ خطأ في الحصول على اتصال من التجمع: {str(e)}")
            raise
    
    @classmethod
    def return_connection(cls, conn):
        """إرجاع الاتصال للتجمع
        
        Args:
            conn: الاتصال المراد إرجاعه
        """
        if cls._pool is not None and conn is not None:
            try:
                cls._pool.putconn(conn)
            except Exception as e:
                logger.warning(f"خطأ في إرجاع الاتصال: {str(e)}")
    
    @classmethod
    def close_all(cls):
        """إغلاق جميع الاتصالات"""
        if cls._pool is not None:
            try:
                cls._pool.closeall()
                logger.info("✅ تم إغلاق تجمع الاتصالات")
                cls._pool = None
            except Exception as e:
                logger.error(f"❌ خطأ في إغلاق التجمع: {str(e)}")
