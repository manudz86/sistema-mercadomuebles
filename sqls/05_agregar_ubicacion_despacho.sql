-- ============================================
-- AGREGAR UBICACIÓN DE DESPACHO A VENTAS
-- ============================================

-- PASO 1: Verificar estructura actual de ventas
DESCRIBE ventas;

-- PASO 2: Agregar campo ubicacion_despacho
ALTER TABLE ventas 
ADD COLUMN ubicacion_despacho ENUM('DEP', 'FULL') DEFAULT 'DEP'
COMMENT 'Ubicación desde donde se despachará (DEP=Depósito propio, FULL=Full ML)'
AFTER tipo_envio;

-- PASO 3: Actualizar ventas existentes según tipo_envio
-- Las ventas con tipo_envio='FULL' van a FULL, el resto a DEP
UPDATE ventas 
SET ubicacion_despacho = 'FULL' 
WHERE tipo_envio = 'FULL';

UPDATE ventas 
SET ubicacion_despacho = 'DEP' 
WHERE tipo_envio != 'FULL' OR tipo_envio IS NULL;

-- PASO 4: Verificar resultado
SELECT id, numero_venta, tipo_envio, ubicacion_despacho, estado_entrega 
FROM ventas 
ORDER BY id DESC 
LIMIT 10;

-- PASO 5: Verificar que se agregó correctamente
DESCRIBE ventas;

-- Debe mostrar:
-- ubicacion_despacho | enum('DEP','FULL') | YES | | DEP |

-- ============================================
-- LÓGICA DE UBICACIÓN
-- ============================================

/*
Cuando se crea una venta:

1. Si tipo_envio = 'FULL':
   - ubicacion_despacho = 'FULL'
   - Stock disponible: stock_full (para Compac/Almohadas)
   
2. Si tipo_envio = 'Retiro' / 'Delega' / 'Flex' / 'Mercadoenvios' / 'Flete':
   - ubicacion_despacho = 'DEP'
   - Stock disponible: stock_actual (todos los productos)

Productos sin ubicaciones (Exclusive, Princess, etc):
- SIEMPRE usan stock_actual
- No importa si la venta es FULL o DEP
*/

-- ============================================
-- EJEMPLO DE USO
-- ============================================

-- Ver ventas FULL (deben descontar de Full ML)
SELECT id, numero_venta, tipo_envio, ubicacion_despacho 
FROM ventas 
WHERE ubicacion_despacho = 'FULL';

-- Ver ventas DEP (deben descontar de Depósito propio)
SELECT id, numero_venta, tipo_envio, ubicacion_despacho 
FROM ventas 
WHERE ubicacion_despacho = 'DEP';

-- ============================================
-- ROLLBACK (si algo sale mal)
-- ============================================

-- Para eliminar la columna:
-- ALTER TABLE ventas DROP COLUMN ubicacion_despacho;
