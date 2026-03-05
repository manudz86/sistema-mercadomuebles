-- ============================================================================
-- SCRIPT DE VERIFICACIÓN - Sistema Cannon
-- Ejecuta este script para verificar que todo está correctamente instalado
-- ============================================================================

USE inventario_cannon;

SELECT '========== VERIFICACIÓN DEL SISTEMA ==========' AS '';

-- 1. Contar productos base por tipo
SELECT 
    '1. PRODUCTOS BASE' AS Verificación,
    tipo AS Tipo,
    COUNT(*) AS Cantidad,
    CASE 
        WHEN tipo = 'colchon' AND COUNT(*) = 59 THEN '✅'
        WHEN tipo = 'base' AND COUNT(*) = 24 THEN '✅'
        WHEN tipo = 'almohada' AND COUNT(*) = 8 THEN '✅'
        ELSE '❌'
    END AS Estado
FROM productos_base
GROUP BY tipo;

-- 2. Verificar productos compuestos
SELECT 
    '2. PRODUCTOS COMPUESTOS' AS Verificación,
    COUNT(*) AS Cantidad,
    CASE WHEN COUNT(*) = 17 THEN '✅' ELSE '❌' END AS Estado
FROM productos_compuestos;

-- 3. Verificar componentes configurados
SELECT 
    '3. COMPONENTES' AS Verificación,
    COUNT(*) AS 'Total Relaciones',
    CASE WHEN COUNT(*) > 0 THEN '✅' ELSE '❌' END AS Estado
FROM componentes;

-- 4. Verificar vistas
SELECT 
    '4. VISTAS SQL' AS Verificación,
    TABLE_NAME AS Vista,
    '✅' AS Estado
FROM information_schema.VIEWS
WHERE TABLE_SCHEMA = 'inventario_cannon'
    AND TABLE_NAME IN ('stock_compuestos', 'stock_disponible_ml', 'alertas_pendientes', 'ventas_activas');

-- 5. Verificar almohadas
SELECT 
    '5. ALMOHADAS ESPECÍFICAS' AS Verificación,
    sku AS SKU,
    nombre AS Nombre,
    '✅' AS Estado
FROM productos_base
WHERE tipo = 'almohada'
ORDER BY sku;

-- 6. Muestra de productos compuestos
SELECT 
    '6. MUESTRA COMBOS' AS Verificación,
    pc.sku AS SKU,
    pc.nombre AS Nombre,
    COUNT(c.id) AS 'Num Componentes',
    '✅' AS Estado
FROM productos_compuestos pc
LEFT JOIN componentes c ON pc.id = c.producto_compuesto_id
GROUP BY pc.id, pc.sku, pc.nombre
ORDER BY pc.sku
LIMIT 5;

-- 7. Verificar stock de combos (debe mostrar datos)
SELECT 
    '7. STOCK COMBOS (vista)' AS Verificación,
    COUNT(*) AS 'Combos Calculados',
    CASE WHEN COUNT(*) > 0 THEN '✅' ELSE '❌ Ejecutar 03_ACTUALIZAR_VISTAS_COMBOS.sql' END AS Estado
FROM stock_compuestos;

-- 8. Ejemplo: Stock de un combo específico
SELECT 
    '8. EJEMPLO COMBO' AS Verificación,
    sku AS SKU,
    nombre AS Nombre,
    stock_disponible AS 'Stock Disponible',
    componentes_detalle AS 'Componentes'
FROM stock_compuestos
WHERE sku = 'SEXP140+2'
LIMIT 1;

SELECT '=============================================' AS '';
SELECT 'VERIFICACIÓN COMPLETADA' AS '';
SELECT 'Si todos los checks muestran ✅, el sistema está correctamente instalado' AS '';
SELECT '=============================================' AS '';

-- DIAGNÓSTICO ADICIONAL
-- Si algo falla, ejecuta estas consultas:

-- Ver productos base que podrían estar faltando
-- SELECT * FROM productos_base WHERE tipo = 'colchon' ORDER BY sku;

-- Ver componentes de un combo específico
-- SELECT 
--     pc.sku as combo_sku,
--     pb.sku as componente_sku,
--     pb.nombre as componente_nombre,
--     c.cantidad_necesaria
-- FROM productos_compuestos pc
-- INNER JOIN componentes c ON pc.id = c.producto_compuesto_id
-- INNER JOIN productos_base pb ON c.producto_base_id = pb.id
-- WHERE pc.sku = 'SEXP140+2';
