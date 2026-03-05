-- ============================================================================
-- COMPARACIÓN: Dos ventas con FLETE - una suma y otra no
-- Ejecutar en MySQL Workbench
-- ============================================================================

USE inventario_cannon;

-- ============================================================================
-- 1. COMPARAR DATOS PRINCIPALES DE AMBAS VENTAS
-- ============================================================================

SELECT 
    numero_venta,
    nombre_cliente,
    
    -- Importes
    importe_total as 'Total en BD',
    costo_flete as 'Costo Flete en BD',
    importe_total + COALESCE(costo_flete, 0) as 'Total + Flete',
    
    -- Métodos
    metodo_envio,
    tipo_entrega,
    ubicacion_despacho,
    
    -- Pagos
    pago_mercadopago as 'Pago MP',
    pago_efectivo as 'Pago Efec',
    importe_abonado as 'Total Abonado',
    
    -- Canal
    canal,
    mla_code,
    
    -- Fecha
    fecha_venta
    
FROM ventas
WHERE numero_venta IN (
    'ML-2000015202950412',
    'VENTA-2000015194466049'
)
ORDER BY numero_venta;


-- ============================================================================
-- 2. VER ITEMS DE CADA VENTA (incluyendo si FLETE está como item)
-- ============================================================================

-- VENTA 1 (que suma bien):
SELECT 
    'ML-2000015202950412' as venta,
    iv.sku,
    iv.cantidad,
    iv.precio_unitario,
    iv.cantidad * iv.precio_unitario as subtotal,
    COALESCE(pb.nombre, pc.nombre, 'NO ENCONTRADO') as nombre_producto
FROM items_venta iv
LEFT JOIN productos_base pb ON iv.sku = pb.sku
LEFT JOIN productos_compuestos pc ON iv.sku = pc.sku
WHERE iv.venta_id = (
    SELECT id FROM ventas WHERE numero_venta = 'ML-2000015202950412'
)

UNION ALL

-- VENTA 2 (que NO suma bien):
SELECT 
    'VENTA-2000015194466049' as venta,
    iv.sku,
    iv.cantidad,
    iv.precio_unitario,
    iv.cantidad * iv.precio_unitario as subtotal,
    COALESCE(pb.nombre, pc.nombre, 'NO ENCONTRADO') as nombre_producto
FROM items_venta iv
LEFT JOIN productos_base pb ON iv.sku = pb.sku
LEFT JOIN productos_compuestos pc ON iv.sku = pc.sku
WHERE iv.venta_id = (
    SELECT id FROM ventas WHERE numero_venta = 'VENTA-2000015194466049'
);


-- ============================================================================
-- 3. VERIFICAR SI EL FLETE ESTÁ GUARDADO COMO ITEM EN items_venta
-- ============================================================================

-- ¿Hay algún item con SKU "FLETE" en items_venta?
SELECT 
    v.numero_venta,
    iv.sku,
    iv.cantidad,
    iv.precio_unitario,
    'FLETE EN ITEMS_VENTA' as nota
FROM items_venta iv
JOIN ventas v ON iv.venta_id = v.id
WHERE v.numero_venta IN (
    'ML-2000015202950412',
    'VENTA-2000015194466049'
)
AND iv.sku = 'FLETE';


-- ============================================================================
-- 4. CALCULAR SUMA DE ITEMS vs IMPORTE_TOTAL
-- ============================================================================

SELECT 
    v.numero_venta,
    v.importe_total as 'Total en ventas',
    v.costo_flete as 'Flete en ventas',
    SUM(iv.cantidad * iv.precio_unitario) as 'Suma de items_venta',
    CASE 
        WHEN v.importe_total = SUM(iv.cantidad * iv.precio_unitario) THEN '✅ Coincide'
        ELSE '❌ NO Coincide'
    END as 'Verificación'
FROM ventas v
LEFT JOIN items_venta iv ON v.id = iv.venta_id
WHERE v.numero_venta IN (
    'ML-2000015202950412',
    'VENTA-2000015194466049'
)
GROUP BY v.numero_venta, v.importe_total, v.costo_flete;


-- ============================================================================
-- 5. ¿EL FLETE ESTÁ INCLUIDO EN importe_total?
-- ============================================================================

SELECT 
    numero_venta,
    
    -- Escenario A: importe_total SIN flete
    importe_total as 'Total BD',
    costo_flete as 'Flete BD',
    importe_total + COALESCE(costo_flete, 0) as 'A: Total + Flete',
    
    -- Escenario B: importe_total YA incluye flete
    importe_total as 'B: Total (con flete incluido)',
    
    -- ¿Cuál es correcto según el Excel?
    CASE numero_venta
        WHEN 'ML-2000015202950412' THEN 1325812
        WHEN 'VENTA-2000015194466049' THEN 1070000
    END as 'Total esperado en Excel'
    
FROM ventas
WHERE numero_venta IN (
    'ML-2000015202950412',
    'VENTA-2000015194466049'
);
