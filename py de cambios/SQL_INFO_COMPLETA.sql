-- ============================================================================
-- SQL COMPLETO PARA OBTENER ESTRUCTURA DE LA BD
-- Copiá y pegá todo esto en MySQL Workbench
-- ============================================================================

-- Seleccionar la base de datos
USE inventario_cannon;

-- 1. VER TODAS LAS TABLAS
SELECT '=== LISTA DE TABLAS ===' AS info;
SHOW TABLES;

-- 2. BUSCAR TABLA DE PRODUCTOS/STOCK
-- (Muestra información de tablas que podrían ser de productos)
SELECT 
    '=== TABLAS QUE PODRÍAN SER DE PRODUCTOS/STOCK ===' AS info;
    
SELECT 
    TABLE_NAME,
    TABLE_ROWS as 'Filas Aprox',
    ROUND(DATA_LENGTH / 1024, 2) as 'Tamaño KB'
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = 'inventario_cannon'
AND (
    TABLE_NAME LIKE '%producto%' OR
    TABLE_NAME LIKE '%stock%' OR
    TABLE_NAME LIKE '%inventario%' OR
    TABLE_NAME LIKE '%item%' OR
    TABLE_NAME LIKE '%articulo%'
)
ORDER BY TABLE_NAME;

-- 3. ESTRUCTURA DE TABLA VENTAS_ITEMS (ya sabemos que existe)
SELECT '=== ESTRUCTURA: ventas_items ===' AS info;
DESCRIBE ventas_items;

SELECT '=== EJEMPLO DATOS: ventas_items (primeras 3 filas) ===' AS info;
SELECT * FROM ventas_items LIMIT 3;

-- 4. ESTRUCTURA DE TABLA VENTAS
SELECT '=== ESTRUCTURA: ventas ===' AS info;
DESCRIBE ventas;

SELECT '=== EJEMPLO DATOS: ventas (primeras 3 filas) ===' AS info;
SELECT * FROM ventas LIMIT 3;

-- 5. ESTRUCTURA DE TABLA SKU_MLA_MAPEO
SELECT '=== ESTRUCTURA: sku_mla_mapeo ===' AS info;
DESCRIBE sku_mla_mapeo;

SELECT '=== EJEMPLO DATOS: sku_mla_mapeo (primeras 3 filas) ===' AS info;
SELECT * FROM sku_mla_mapeo LIMIT 3;

-- 6. BUSCAR TODAS LAS TABLAS Y SUS COLUMNAS
SELECT '=== TODAS LAS TABLAS Y SUS COLUMNAS ===' AS info;

SELECT 
    TABLE_NAME,
    COLUMN_NAME,
    DATA_TYPE,
    IS_NULLABLE,
    COLUMN_KEY
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = 'inventario_cannon'
ORDER BY TABLE_NAME, ORDINAL_POSITION;

-- 7. BUSCAR COLUMNAS CON NOMBRE 'stock' EN CUALQUIER TABLA
SELECT '=== COLUMNAS QUE CONTIENEN "stock" ===' AS info;

SELECT 
    TABLE_NAME,
    COLUMN_NAME,
    DATA_TYPE
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = 'inventario_cannon'
AND COLUMN_NAME LIKE '%stock%'
ORDER BY TABLE_NAME;

-- 8. BUSCAR COLUMNAS CON NOMBRE 'sku' EN CUALQUIER TABLA
SELECT '=== COLUMNAS QUE CONTIENEN "sku" ===' AS info;

SELECT 
    TABLE_NAME,
    COLUMN_NAME,
    DATA_TYPE
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = 'inventario_cannon'
AND COLUMN_NAME LIKE '%sku%'
ORDER BY TABLE_NAME;

-- FIN DEL SCRIPT
SELECT '=== SCRIPT COMPLETADO ===' AS info;
