-- ============================================================================
-- RESTAURACIÓN DEL BACKUP + CAMPOS NUEVOS
-- Ejecutar en MySQL Workbench
-- ============================================================================

-- PASO 1: Borrar BD actual (si existe)
DROP DATABASE IF EXISTS inventario_cannon;

-- PASO 2: Importar backup
-- IMPORTANTE: Desde MySQL Workbench:
-- 1. File → Run SQL Script
-- 2. Seleccionar: backup.sql
-- 3. Ejecutar
-- 4. Luego ejecutar este script

-- ============================================================================
-- PASO 3: AGREGAR CAMPOS QUE FALTAN EN LA TABLA ventas
-- ============================================================================

USE inventario_cannon;

-- Agregar DNI y Provincia (campos manuales)
ALTER TABLE ventas 
ADD COLUMN dni_cliente VARCHAR(20) NULL COMMENT 'DNI/CUIT del cliente' AFTER telefono_cliente,
ADD COLUMN provincia_cliente VARCHAR(100) NULL DEFAULT 'Capital Federal' COMMENT 'Provincia del cliente' AFTER dni_cliente;

-- Agregar campos de facturación (billing info de ML)
ALTER TABLE ventas 
ADD COLUMN factura_business_name VARCHAR(255) NULL COMMENT 'Razón social de ML' AFTER pago_efectivo,
ADD COLUMN factura_doc_type VARCHAR(50) NULL COMMENT 'Tipo de documento' AFTER factura_business_name,
ADD COLUMN factura_doc_number VARCHAR(50) NULL COMMENT 'Número de documento/CUIT' AFTER factura_doc_type,
ADD COLUMN factura_taxpayer_type VARCHAR(100) NULL COMMENT 'Tipo de contribuyente IVA' AFTER factura_doc_number,
ADD COLUMN factura_city VARCHAR(100) NULL COMMENT 'Ciudad de facturación' AFTER factura_taxpayer_type,
ADD COLUMN factura_street VARCHAR(255) NULL COMMENT 'Dirección de facturación' AFTER factura_city,
ADD COLUMN factura_state VARCHAR(100) NULL COMMENT 'Provincia de facturación' AFTER factura_street,
ADD COLUMN factura_zip_code VARCHAR(20) NULL COMMENT 'Código postal' AFTER factura_state,
ADD COLUMN factura_generada BOOLEAN DEFAULT FALSE COMMENT 'Si ya se generó el Excel de facturación' AFTER factura_zip_code,
ADD COLUMN factura_fecha_generacion DATETIME NULL COMMENT 'Fecha de generación del Excel' AFTER factura_generada;


-- ============================================================================
-- VERIFICACIÓN: Mostrar estructura completa de ventas
-- ============================================================================

DESCRIBE ventas;

-- Debería mostrar 42 campos (32 anteriores + 10 nuevos)


-- ============================================================================
-- VERIFICACIÓN: Ver todas las tablas
-- ============================================================================

SHOW TABLES;

-- Deberías ver:
-- alertas_stock
-- componentes
-- items_venta
-- movimientos_stock
-- productos_base
-- productos_compuestos
-- sku_mla_mapeo
-- ventas
-- ventas_activas (vista)


-- ============================================================================
-- VERIFICACIÓN: Contar ventas restauradas
-- ============================================================================

SELECT COUNT(*) as total_ventas FROM ventas;

-- Debería mostrar alrededor de 64 ventas (según tu backup)


-- ============================================================================
-- VERIFICACIÓN: Ver productos base
-- ============================================================================

SELECT sku, nombre, tipo, stock_actual 
FROM productos_base 
ORDER BY tipo, nombre 
LIMIT 20;


-- ============================================================================
-- ✅ LISTO! Base de datos restaurada con todos los campos nuevos
-- ============================================================================

-- Ahora podés:
-- 1. Iniciar Flask: python app.py
-- 2. Probar crear nueva venta con DNI y Provincia
-- 3. Generar facturas Excel con los datos correctos
