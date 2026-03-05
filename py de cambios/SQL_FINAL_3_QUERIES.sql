-- ============================================================================
-- QUERIES FINALES - Copiá y ejecutá estas 3
-- ============================================================================

USE inventario_cannon;

-- 1. ESTRUCTURA DE productos_base
SELECT '=== ESTRUCTURA: productos_base ===' AS info;
DESCRIBE productos_base;

SELECT '=== DATOS EJEMPLO: productos_base (3 filas) ===' AS info;
SELECT * FROM productos_base LIMIT 3;

-- 2. ESTRUCTURA DE items_venta
SELECT '=== ESTRUCTURA: items_venta ===' AS info;
DESCRIBE items_venta;

SELECT '=== DATOS EJEMPLO: items_venta (3 filas) ===' AS info;
SELECT * FROM items_venta LIMIT 3;

-- 3. ESTRUCTURA DE ventas
SELECT '=== ESTRUCTURA: ventas ===' AS info;
DESCRIBE ventas;

SELECT '=== DATOS EJEMPLO: ventas (3 filas) ===' AS info;
SELECT * FROM ventas WHERE estado_entrega = 'pendiente' LIMIT 3;

-- FIN
