"""
utils.py — Funciones utilitarias compartidas entre app.py y tienda_bp.py
"""

import pymysql
import os
from datetime import datetime, timezone, timedelta


def _get_db_connection():
    """Abre una conexión directa a la BD (para uso interno de utils)."""
    return pymysql.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        user=os.getenv('DB_USER', 'cannon'),
        password=os.getenv('DB_PASSWORD', ''),
        database=os.getenv('DB_NAME', 'inventario_cannon'),
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
    )


def crear_tabla_sistema_logs():
    """Crea la tabla sistema_logs si no existe. Llamar al iniciar la app."""
    conn = _get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sistema_logs (
                    id          INT AUTO_INCREMENT PRIMARY KEY,
                    timestamp   DATETIME DEFAULT CURRENT_TIMESTAMP,
                    nivel       ENUM('INFO','WARNING','ERROR') DEFAULT 'INFO',
                    modulo      VARCHAR(50),
                    accion      VARCHAR(100),
                    detalle     TEXT,
                    sku         VARCHAR(50),
                    venta_id    INT,
                    usuario     VARCHAR(100),
                    ip          VARCHAR(50),
                    INDEX idx_timestamp (timestamp),
                    INDEX idx_modulo (modulo),
                    INDEX idx_sku (sku),
                    INDEX idx_nivel (nivel)
                )
            """)
        conn.commit()
    except Exception as e:
        print(f"[utils] Error creando tabla sistema_logs: {e}")
    finally:
        conn.close()


def log_evento(nivel, modulo, accion, detalle,
               sku=None, venta_id=None, usuario=None, ip=None):
    """
    Registra un evento en sistema_logs.
    Silencioso — nunca rompe el flujo principal si falla.

    Parámetros:
        nivel   : 'INFO' | 'WARNING' | 'ERROR'
        modulo  : 'stock' | 'venta' | 'entrega' | 'tienda' | 'ml' | 'webhook'
        accion  : descripción corta ej: 'carga_stock', 'nueva_venta', 'descuento_stock'
        detalle : texto libre con toda la info relevante
        sku     : SKU del producto si aplica
        venta_id: ID de venta si aplica
        usuario : usuario del sistema
        ip      : IP del request si aplica
    """
    try:
        conn = _get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO sistema_logs
                        (nivel, modulo, accion, detalle, sku, venta_id, usuario, ip)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (nivel, modulo, accion, detalle, sku, venta_id, usuario, ip))
            conn.commit()
        finally:
            conn.close()
    except Exception:
        pass  # Nunca propagar errores de logging
