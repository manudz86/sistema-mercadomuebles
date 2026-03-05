-- ============================================================================
-- VISTA MEJORADA: Con medida separada (ORDEN CORREGIDO)
-- ============================================================================

USE inventario_cannon;

DROP VIEW IF EXISTS stock_disponible_ml;

CREATE VIEW stock_disponible_ml AS
-- Productos BASE
SELECT 
    pb.id,
    pb.sku,
    -- Extraer nombre del producto sin la medida (orden correcto: primero las más largas)
    CASE 
        WHEN pb.nombre LIKE '%200x200%' THEN TRIM(REPLACE(pb.nombre, '200x200', ''))
        WHEN pb.nombre LIKE '%180x200%' THEN TRIM(REPLACE(pb.nombre, '180x200', ''))
        WHEN pb.nombre LIKE '%160x200%' THEN TRIM(REPLACE(pb.nombre, '160x200', ''))
        WHEN pb.nombre LIKE '%100x200%' THEN TRIM(REPLACE(pb.nombre, '100x200', ''))
        WHEN pb.nombre LIKE '%90x200%' THEN TRIM(REPLACE(pb.nombre, '90x200', ''))
        WHEN pb.nombre LIKE '%80x200%' THEN TRIM(REPLACE(pb.nombre, '80x200', ''))
        WHEN pb.nombre LIKE '%150x190%' THEN TRIM(REPLACE(pb.nombre, '150x190', ''))
        WHEN pb.nombre LIKE '%140x190%' THEN TRIM(REPLACE(pb.nombre, '140x190', ''))
        WHEN pb.nombre LIKE '%100x190%' THEN TRIM(REPLACE(pb.nombre, '100x190', ''))
        WHEN pb.nombre LIKE '%90x190%' THEN TRIM(REPLACE(pb.nombre, '90x190', ''))
        WHEN pb.nombre LIKE '%80x190%' THEN TRIM(REPLACE(pb.nombre, '80x190', ''))
        ELSE pb.nombre
    END as nombre,
    -- Extraer medida (orden correcto: primero las más largas)
    CASE 
        WHEN pb.nombre LIKE '%200x200%' THEN '200x200'
        WHEN pb.nombre LIKE '%180x200%' THEN '180x200'
        WHEN pb.nombre LIKE '%160x200%' THEN '160x200'
        WHEN pb.nombre LIKE '%100x200%' THEN '100x200'
        WHEN pb.nombre LIKE '%90x200%' THEN '90x200'
        WHEN pb.nombre LIKE '%80x200%' THEN '80x200'
        WHEN pb.nombre LIKE '%150x190%' THEN '150x190'
        WHEN pb.nombre LIKE '%140x190%' THEN '140x190'
        WHEN pb.nombre LIKE '%100x190%' THEN '100x190'
        WHEN pb.nombre LIKE '%90x190%' THEN '90x190'
        WHEN pb.nombre LIKE '%80x190%' THEN '80x190'
        ELSE NULL
    END as medida,
    pb.tipo,
    pb.stock_actual as stock_fisico,
    0 as stock_comprometido,
    pb.stock_actual as stock_disponible,
    pb.stock_minimo_pausar,
    pb.stock_minimo_reactivar,
    'BASE' as tipo_producto,
    pb.modelo,
    -- Solo DISPONIBLE o SIN_STOCK (sin STOCK_BAJO)
    CASE 
        WHEN pb.stock_actual <= 0 THEN 'SIN_STOCK'
        ELSE 'DISPONIBLE'
    END as estado_stock
FROM productos_base pb

UNION ALL

-- Productos COMPUESTOS
SELECT 
    pc.id,
    pc.sku,
    -- Extraer nombre del producto sin la medida (orden correcto: primero las más largas)
    CASE 
        WHEN pc.nombre LIKE '%200x200%' THEN TRIM(REPLACE(pc.nombre, '200x200', ''))
        WHEN pc.nombre LIKE '%180x200%' THEN TRIM(REPLACE(pc.nombre, '180x200', ''))
        WHEN pc.nombre LIKE '%160x200%' THEN TRIM(REPLACE(pc.nombre, '160x200', ''))
        WHEN pc.nombre LIKE '%100x200%' THEN TRIM(REPLACE(pc.nombre, '100x200', ''))
        WHEN pc.nombre LIKE '%90x200%' THEN TRIM(REPLACE(pc.nombre, '90x200', ''))
        WHEN pc.nombre LIKE '%80x200%' THEN TRIM(REPLACE(pc.nombre, '80x200', ''))
        WHEN pc.nombre LIKE '%150x190%' THEN TRIM(REPLACE(pc.nombre, '150x190', ''))
        WHEN pc.nombre LIKE '%140x190%' THEN TRIM(REPLACE(pc.nombre, '140x190', ''))
        WHEN pc.nombre LIKE '%100x190%' THEN TRIM(REPLACE(pc.nombre, '100x190', ''))
        WHEN pc.nombre LIKE '%90x190%' THEN TRIM(REPLACE(pc.nombre, '90x190', ''))
        WHEN pc.nombre LIKE '%80x190%' THEN TRIM(REPLACE(pc.nombre, '80x190', ''))
        ELSE pc.nombre
    END as nombre,
    -- Extraer medida (orden correcto: primero las más largas)
    CASE 
        WHEN pc.nombre LIKE '%200x200%' THEN '200x200'
        WHEN pc.nombre LIKE '%180x200%' THEN '180x200'
        WHEN pc.nombre LIKE '%160x200%' THEN '160x200'
        WHEN pc.nombre LIKE '%100x200%' THEN '100x200'
        WHEN pc.nombre LIKE '%90x200%' THEN '90x200'
        WHEN pc.nombre LIKE '%80x200%' THEN '80x200'
        WHEN pc.nombre LIKE '%150x190%' THEN '150x190'
        WHEN pc.nombre LIKE '%140x190%' THEN '140x190'
        WHEN pc.nombre LIKE '%100x190%' THEN '100x190'
        WHEN pc.nombre LIKE '%90x190%' THEN '90x190'
        WHEN pc.nombre LIKE '%80x190%' THEN '80x190'
        ELSE NULL
    END as medida,
    -- Tipo según SKU
    CASE 
        WHEN pc.sku LIKE 'S%' THEN 'sommier'
        WHEN pc.sku LIKE 'C%' THEN 'colchon'
        ELSE 'almohada'
    END as tipo,
    NULL as stock_fisico,
    0 as stock_comprometido,
    sc.stock_disponible,
    0 as stock_minimo_pausar,
    1 as stock_minimo_reactivar,
    'COMPUESTO' as tipo_producto,
    NULL as modelo,
    -- Solo DISPONIBLE o SIN_STOCK (sin STOCK_BAJO)
    CASE 
        WHEN sc.stock_disponible <= 0 THEN 'SIN_STOCK'
        ELSE 'DISPONIBLE'
    END as estado_stock
FROM productos_compuestos pc
INNER JOIN stock_compuestos sc ON pc.id = sc.producto_compuesto_id;

SELECT '✅ Vista corregida - Medidas 180x200 arregladas, sin Stock Bajo' AS Resultado;
