-- ============================================================================
-- VERIFICAR MONTOS DE PAGO - Comparar BD vs lo que muestra el template
-- ============================================================================

USE inventario_cannon;

-- Ver ventas con sus montos reales
SELECT 
    numero_venta,
    nombre_cliente,
    
    -- Montos en BD
    importe_total as 'Total BD',
    costo_flete as 'Flete',
    importe_total - COALESCE(costo_flete, 0) as 'Solo Productos',
    
    -- Pagos
    importe_abonado as 'Abonado Total',
    pago_mercadopago as 'MP en BD',
    pago_efectivo as 'Efectivo en BD',
    
    -- Verificación
    CASE 
        WHEN importe_abonado = (pago_mercadopago + pago_efectivo) 
        THEN '✅ Coincide'
        ELSE '❌ NO Coincide'
    END as 'Check',
    
    -- Diferencia
    (pago_mercadopago + pago_efectivo) - importe_abonado as 'Diferencia',
    
    metodo_envio,
    estado_entrega
    
FROM ventas
WHERE estado_entrega = 'en_proceso'
  AND metodo_envio IN ('Flete Propio', 'Zippin')
ORDER BY id DESC
LIMIT 10;


-- ============================================================================
-- VER VENTAS ESPECÍFICAS DE LA IMAGEN
-- ============================================================================

-- Primera venta (FIOREROBERTO...)
SELECT 
    'VENTA 1 - FIOREROBERTO' as venta,
    numero_venta,
    importe_total,
    costo_flete,
    importe_abonado,
    pago_mercadopago,
    pago_efectivo
FROM ventas
WHERE numero_venta LIKE '%2000015220106792%'
   OR mla_code = 'FIOREROBERTO20210307010402';

-- Segunda venta (MADA4361716)
SELECT 
    'VENTA 2 - MADA4361716' as venta,
    numero_venta,
    importe_total,
    costo_flete,
    importe_abonado,
    pago_mercadopago,
    pago_efectivo
FROM ventas
WHERE numero_venta LIKE '%2000015207976532%'
   OR mla_code = 'MADA4361716';

-- Tercera venta (ANDRESGIGANTE)
SELECT 
    'VENTA 3 - ANDRESGIGANTE' as venta,
    numero_venta,
    importe_total,
    costo_flete,
    importe_abonado,
    pago_mercadopago,
    pago_efectivo
FROM ventas
WHERE numero_venta LIKE '%2000015202950412%'
   OR mla_code = 'ANDRESGIGANTE';


-- ============================================================================
-- ANÁLISIS: ¿El problema está en la BD o en el template?
-- ============================================================================

-- Si pago_mercadopago incluye el flete:
SELECT 
    numero_venta,
    
    -- Escenario A: pago_mercadopago ya incluye flete
    pago_mercadopago as 'MP en BD',
    importe_total as 'Total con Flete',
    importe_total - COALESCE(costo_flete, 0) as 'Total sin Flete',
    
    -- Verificar si MP = Total con Flete
    CASE 
        WHEN pago_mercadopago = importe_total 
        THEN '✅ MP incluye flete'
        WHEN pago_mercadopago = (importe_total - COALESCE(costo_flete, 0))
        THEN '✅ MP sin flete'
        ELSE '❌ Otra cosa'
    END as 'Análisis MP',
    
    metodo_envio,
    costo_flete
    
FROM ventas
WHERE estado_entrega = 'en_proceso'
  AND pago_mercadopago > 0
ORDER BY id DESC
LIMIT 10;
