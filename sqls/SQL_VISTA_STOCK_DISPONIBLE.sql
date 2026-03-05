-- CREAR VISTA QUE CALCULA STOCK DISPONIBLE CORRECTAMENTE
-- Stock disponible = Stock físico - Cantidad en ventas activas

USE inventario_cannon;

DROP VIEW IF EXISTS stock_disponible_real;

CREATE VIEW stock_disponible_real AS
SELECT 
    pb.sku,
    pb.nombre,
    pb.tipo,
    pb.stock_actual as stock_fisico,
    COALESCE(SUM(CASE WHEN v.estado = 'ACTIVA' THEN iv.cantidad ELSE 0 END), 0) as cantidad_vendida,
    (pb.stock_actual - COALESCE(SUM(CASE WHEN v.estado = 'ACTIVA' THEN iv.cantidad ELSE 0 END), 0)) as stock_disponible
FROM productos_base pb
LEFT JOIN items_venta iv ON pb.sku = iv.sku
LEFT JOIN ventas v ON iv.venta_id = v.id
GROUP BY pb.sku, pb.nombre, pb.tipo, pb.stock_actual;
