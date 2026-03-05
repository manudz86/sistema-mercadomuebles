-- ============================================================================
-- AGREGAR COLUMNA fecha_entrega A LA TABLA ventas
-- ============================================================================

-- Verificar si la columna existe
SELECT COLUMN_NAME 
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_SCHEMA = 'inventario_cannon' 
  AND TABLE_NAME = 'ventas' 
  AND COLUMN_NAME = 'fecha_entrega';

-- Si no existe, ejecutar:
ALTER TABLE ventas 
ADD COLUMN fecha_entrega DATETIME NULL 
AFTER fecha_modificacion;

-- Verificar estructura actualizada:
DESCRIBE ventas;

-- ============================================================================
-- NOTAS:
-- ============================================================================
-- fecha_entrega se llena cuando:
-- 1. Se marca como entregada desde Ventas Activas
-- 2. Se marca como entregada desde Proceso de Envío
--
-- Se usa para:
-- - Ordenar ventas históricas por fecha real de entrega
-- - Calcular tiempos de entrega
-- - Reportes y estadísticas
-- ============================================================================
