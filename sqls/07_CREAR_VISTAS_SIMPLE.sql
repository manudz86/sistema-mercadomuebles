-- ============================================================================
-- CREAR VISTAS ESENCIALES (SIMPLIFICADO)
-- Solo las vistas necesarias para que funcione la web
-- ============================================================================

USE inventario_cannon;

-- Eliminar vistas si existen
DROP VIEW IF EXISTS ventas_activas;
DROP VIEW IF EXISTS stock_disponible_ml;
DROP VIEW IF EXISTS stock_compuestos;

-- ============================================================================
-- 1. Vista: Stock de productos compuestos
-- ============================================================================
CREATE VIEW stock_compuestos AS
SELECT 
    pc.id as producto_compuesto_id,
    pc.sku,
    pc.nombre,
    pc.precio_base,
    MIN(FLOOR(pb.stock_actual / c.cantidad_necesaria)) as stock_disponible,
    GROUP_CONCAT(
        CONCAT(pb.sku, ':', pb.stock_actual, '/', c.cantidad_necesaria)
        ORDER BY pb.sku
        SEPARATOR ' | '
    ) as componentes_detalle
FROM productos_compuestos pc
INNER JOIN componentes c ON pc.id = c.producto_compuesto_id
INNER JOIN productos_base pb ON c.producto_base_id = pb.id
GROUP BY pc.id, pc.sku, pc.nombre, pc.precio_base;

SELECT '✓ Vista stock_compuestos creada' AS Estado;

-- ============================================================================
-- 2. Vista: Stock disponible ML (productos base + compuestos)
-- ============================================================================
CREATE VIEW stock_disponible_ml AS
-- Productos BASE
SELECT 
    pb.id,
    pb.sku,
    pb.nombre,
    pb.tipo,
    pb.stock_actual as stock_fisico,
    0 as stock_comprometido,
    pb.stock_actual as stock_disponible,
    pb.stock_minimo_pausar,
    pb.stock_minimo_reactivar,
    'BASE' as tipo_producto,
    CASE 
        WHEN pb.stock_actual <= pb.stock_minimo_pausar THEN 'SIN_STOCK'
        WHEN pb.stock_actual < pb.stock_minimo_reactivar THEN 'STOCK_BAJO'
        ELSE 'DISPONIBLE'
    END as estado_stock
FROM productos_base pb

UNION ALL

-- Productos COMPUESTOS
SELECT 
    pc.id,
    pc.sku,
    pc.nombre,
    'combo' as tipo,
    NULL as stock_fisico,
    0 as stock_comprometido,
    sc.stock_disponible,
    0 as stock_minimo_pausar,
    1 as stock_minimo_reactivar,
    'COMPUESTO' as tipo_producto,
    CASE 
        WHEN sc.stock_disponible <= 0 THEN 'SIN_STOCK'
        WHEN sc.stock_disponible < 3 THEN 'STOCK_BAJO'
        ELSE 'DISPONIBLE'
    END as estado_stock
FROM productos_compuestos pc
INNER JOIN stock_compuestos sc ON pc.id = sc.producto_compuesto_id;

SELECT '✓ Vista stock_disponible_ml creada' AS Estado;

-- ============================================================================
-- 3. Vista: Ventas activas (SIMPLIFICADA)
-- ============================================================================
CREATE VIEW ventas_activas AS
SELECT 
    v.*,
    (SELECT COUNT(*) FROM items_venta iv WHERE iv.venta_id = v.id) as cantidad_items
FROM ventas v
WHERE v.estado_entrega = 'pendiente'
ORDER BY v.fecha_venta DESC;

SELECT '✓ Vista ventas_activas creada' AS Estado;

-- ============================================================================
-- Verificación final
-- ============================================================================

SELECT '==================== VERIFICACIÓN ====================' AS '';

-- Ver cuántos productos hay en cada vista
SELECT 'Productos base' as Vista, COUNT(*) as Cantidad
FROM productos_base
UNION ALL
SELECT 'Productos compuestos', COUNT(*)
FROM productos_compuestos
UNION ALL
SELECT 'Stock compuestos (calculado)', COUNT(*)
FROM stock_compuestos
UNION ALL
SELECT 'Stock disponible ML', COUNT(*)
FROM stock_disponible_ml;

SELECT '=======================================================' AS '';
SELECT '✅ SISTEMA COMPLETO - Probá refrescar localhost:5000' AS Resultado;
