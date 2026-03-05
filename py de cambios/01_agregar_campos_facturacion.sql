-- ============================================================================
-- AGREGAR CAMPOS DE FACTURACIÓN A LA TABLA VENTAS
-- Ejecutar en MySQL Workbench o línea de comandos
-- ============================================================================

USE inventario_cannon;

-- Agregar campos de facturación del comprador
ALTER TABLE ventas
ADD COLUMN factura_business_name VARCHAR(200) DEFAULT NULL COMMENT 'Razón social del comprador',
ADD COLUMN factura_doc_type VARCHAR(20) DEFAULT NULL COMMENT 'CUIT/DNI/CUIL',
ADD COLUMN factura_doc_number VARCHAR(30) DEFAULT NULL COMMENT 'Número de documento',
ADD COLUMN factura_taxpayer_type VARCHAR(50) DEFAULT NULL COMMENT 'IVA Responsable Inscripto/Consumidor Final/Monotributo',
ADD COLUMN factura_city VARCHAR(100) DEFAULT NULL COMMENT 'Ciudad',
ADD COLUMN factura_street VARCHAR(200) DEFAULT NULL COMMENT 'Calle y número',
ADD COLUMN factura_state VARCHAR(50) DEFAULT NULL COMMENT 'Provincia',
ADD COLUMN factura_zip_code VARCHAR(20) DEFAULT NULL COMMENT 'Código postal',
ADD COLUMN factura_generada BOOLEAN DEFAULT FALSE COMMENT 'Si ya se generó archivo de facturación',
ADD COLUMN factura_fecha_generacion DATETIME DEFAULT NULL COMMENT 'Fecha generación archivo factura';

-- Verificar que se agregaron correctamente
DESCRIBE ventas;

SELECT 'Campos de facturación agregados correctamente' AS resultado;
