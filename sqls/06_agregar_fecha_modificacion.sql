-- ============================================================================
-- AGREGAR COLUMNA fecha_modificacion A LA TABLA ventas
-- Ejecutar solo si la columna no existe
-- ============================================================================

-- Verificar si la columna existe:
SELECT COLUMN_NAME 
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_SCHEMA = 'inventario_cannon' 
  AND TABLE_NAME = 'ventas' 
  AND COLUMN_NAME = 'fecha_modificacion';

-- Si no existe, ejecutar:
ALTER TABLE ventas 
ADD COLUMN fecha_modificacion TIMESTAMP NULL 
AFTER estado_pago;

-- Verificar:
DESCRIBE ventas;
