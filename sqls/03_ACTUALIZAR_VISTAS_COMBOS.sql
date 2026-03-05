-- ============================================================================
-- VISTAS ACTUALIZADAS PARA INCLUIR PRODUCTOS COMPUESTOS
-- ============================================================================

USE inventario_cannon;

-- Primero eliminamos las vistas anteriores si existen
DROP VIEW IF EXISTS stock_disponible_ml;
DROP VIEW IF EXISTS alertas_pendientes;
DROP VIEW IF EXISTS ventas_activas;

-- ============================================================================
-- VISTA: Stock disponible de productos COMPUESTOS
-- Calcula cuántas unidades de un combo se pueden hacer
-- ============================================================================

CREATE VIEW stock_compuestos AS
SELECT 
    pc.id as producto_compuesto_id,
    pc.sku,
    pc.nombre,
    pc.precio_base,
    -- Stock disponible = mínimo de (stock_componente / cantidad_necesaria)
    MIN(FLOOR(pb.stock_actual / c.cantidad_necesaria)) as stock_disponible,
    -- Lista de componentes para debug
    GROUP_CONCAT(
        CONCAT(pb.sku, ':', pb.stock_actual, '/', c.cantidad_necesaria)
        ORDER BY pb.sku
        SEPARATOR ' | '
    ) as componentes_detalle
FROM productos_compuestos pc
INNER JOIN componentes c ON pc.id = c.producto_compuesto_id
INNER JOIN productos_base pb ON c.producto_base_id = pb.id
WHERE pc.activo = TRUE AND pb.activo = TRUE
GROUP BY pc.id, pc.sku, pc.nombre, pc.precio_base;

-- ============================================================================
-- VISTA: Stock disponible para ML (productos base Y compuestos)
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
WHERE pb.activo = TRUE

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
INNER JOIN stock_compuestos sc ON pc.id = sc.producto_compuesto_id
WHERE pc.activo = TRUE;

-- ============================================================================
-- VISTA: Alertas pendientes
-- ============================================================================

CREATE VIEW alertas_pendientes AS
SELECT 
    a.id,
    a.sku,
    a.tipo_alerta,
    a.estado,
    a.fecha_creacion,
    a.fecha_procesada,
    a.mlas_afectados,
    sd.nombre,
    sd.stock_disponible,
    sd.tipo_producto
FROM alertas_stock a
LEFT JOIN stock_disponible_ml sd ON a.sku = sd.sku
WHERE a.estado = 'pendiente'
ORDER BY a.fecha_creacion DESC;

-- ============================================================================
-- VISTA: Ventas activas
-- ============================================================================

CREATE VIEW ventas_activas AS
SELECT 
    v.id,
    v.numero_venta,
    v.canal,
    v.nombre_cliente,
    v.telefono_cliente,
    v.importe_total,
    v.importe_abonado,
    v.metodo_pago,
    v.tipo_entrega,
    v.estado_pago,
    v.estado_entrega,
    v.fecha_venta,
    v.fecha_entrega_estimada,
    -- Items de la venta
    (SELECT COUNT(*) FROM items_venta iv WHERE iv.venta_id = v.id) as cantidad_items,
    -- Detalle de productos
    (SELECT GROUP_CONCAT(CONCAT(iv.cantidad, 'x ', iv.sku) SEPARATOR ', ')
     FROM items_venta iv 
     WHERE iv.venta_id = v.id) as productos
FROM ventas v
WHERE v.estado_entrega = 'pendiente'
ORDER BY v.fecha_venta DESC;

SELECT '✅ Vistas actualizadas con soporte para productos compuestos' AS Resultado;
