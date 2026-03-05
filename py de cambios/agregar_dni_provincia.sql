-- ============================================================================
-- AGREGAR CAMPOS DNI Y PROVINCIA A TABLA VENTAS
-- Ejecutar en MySQL Workbench
-- ============================================================================

USE inventario_cannon;

ALTER TABLE ventas 
ADD COLUMN dni_cliente VARCHAR(20) NULL AFTER telefono_cliente,
ADD COLUMN provincia_cliente VARCHAR(100) NULL DEFAULT 'Capital Federal' AFTER dni_cliente;

-- Verificar que se agregaron correctamente
DESCRIBE ventas;
