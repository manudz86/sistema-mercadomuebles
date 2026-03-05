-- ============================================
-- VERIFICAR ESTRUCTURA DE TABLAS - items_venta
-- ============================================

-- 1. Ver todas las tablas relacionadas con ventas
SHOW TABLES LIKE '%venta%';

-- 2. Ver estructura de la tabla items_venta
DESCRIBE items_venta;

-- 3. Ver estructura de la tabla ventas
DESCRIBE ventas;

-- 4. Ver si hay ventas pendientes
SELECT COUNT(*) as total_pendientes 
FROM ventas 
WHERE estado_entrega = 'pendiente';

-- 5. Ver ventas activas con productos
SELECT 
    v.id,
    v.numero_venta,
    v.estado_entrega,
    iv.sku,
    iv.cantidad
FROM ventas v
JOIN items_venta iv ON v.id = iv.venta_id
WHERE v.estado_entrega = 'pendiente';

-- 6. Ver resumen de stock comprometido por producto
SELECT 
    iv.sku,
    SUM(iv.cantidad) as cantidad_comprometida,
    COUNT(DISTINCT v.id) as num_ventas
FROM items_venta iv
JOIN ventas v ON iv.venta_id = v.id
WHERE v.estado_entrega = 'pendiente'
GROUP BY iv.sku
ORDER BY cantidad_comprometida DESC;

-- ============================================
-- CREAR VENTA DE PRUEBA (solo si necesitás probar)
-- ============================================

-- IMPORTANTE: Reemplazar los valores de ejemplo con tus datos reales

-- Insertar venta de prueba
INSERT INTO ventas (
    numero_venta, 
    canal, 
    nombre_cliente, 
    telefono_cliente, 
    tipo_entrega,
    estado_entrega,
    fecha_venta
) VALUES (
    'VENTA-TEST-001',
    'Mercado Libre',
    'Cliente Prueba',
    '1234567890',
    'envio',
    'pendiente',  -- IMPORTANTE: estado pendiente
    NOW()
);

-- Obtener el ID de la venta recién creada
SET @venta_id = LAST_INSERT_ID();

-- Insertar items de la venta (ejemplo con CEX80)
INSERT INTO items_venta (venta_id, sku, cantidad, precio_unitario)
VALUES (@venta_id, 'CEX80', 1, 50000);

-- Verificar que se creó correctamente
SELECT 
    v.*,
    iv.sku,
    iv.cantidad
FROM ventas v
JOIN items_venta iv ON v.id = iv.venta_id
WHERE v.id = @venta_id;

-- ============================================
-- LIMPIAR VENTA DE PRUEBA (ejecutar cuando termines de probar)
-- ============================================

-- Borrar items de la venta de prueba
DELETE FROM items_venta 
WHERE venta_id IN (SELECT id FROM ventas WHERE numero_venta = 'VENTA-TEST-001');

-- Borrar la venta de prueba
DELETE FROM ventas WHERE numero_venta = 'VENTA-TEST-001';

-- Verificar que se borró
SELECT * FROM ventas WHERE numero_venta = 'VENTA-TEST-001';
