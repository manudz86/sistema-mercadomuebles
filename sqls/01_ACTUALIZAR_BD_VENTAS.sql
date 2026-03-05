-- ============================================================================
-- ACTUALIZACIÓN BASE DE DATOS - SISTEMA DE VENTAS COMPLETO
-- ============================================================================

-- Agregar columnas faltantes a tabla ventas

-- Canal de venta
ALTER TABLE ventas 
ADD COLUMN canal VARCHAR(50) DEFAULT 'Mercado Libre' 
COMMENT 'Canal: Mercado Libre / Fuera de ML';

-- Tipo de entrega
ALTER TABLE ventas 
ADD COLUMN tipo_entrega VARCHAR(50) 
COMMENT 'Retiro / Envío';

-- Tipo de flete (si es envío)
ALTER TABLE ventas 
ADD COLUMN tipo_flete VARCHAR(50) 
COMMENT 'Mercadoenvios / Flex / Delega / Zippin / Flete Propio';

-- Zona (si es flete propio)
ALTER TABLE ventas 
ADD COLUMN zona VARCHAR(50) 
COMMENT 'Sur / Norte / Capital / Oeste';

-- Fletero (si es flete propio)
ALTER TABLE ventas 
ADD COLUMN fletero VARCHAR(100) 
COMMENT 'Leo / Lean / Ezequiel / Antonio / Tucu';

-- Costo del flete
ALTER TABLE ventas 
ADD COLUMN costo_flete DECIMAL(10,2) DEFAULT 0;

-- Dirección de envío
ALTER TABLE ventas 
ADD COLUMN direccion_envio TEXT;

-- Pagos desagregados
ALTER TABLE ventas 
ADD COLUMN pago_mercadopago DECIMAL(10,2) DEFAULT 0 
COMMENT 'Pago por MercadoPago';

ALTER TABLE ventas 
ADD COLUMN pago_efectivo DECIMAL(10,2) DEFAULT 0 
COMMENT 'Pago en efectivo o transferencia';

-- Observaciones
ALTER TABLE ventas 
ADD COLUMN observaciones TEXT;

-- Fecha de entrega
ALTER TABLE ventas 
ADD COLUMN fecha_entrega DATE;

-- Actualizar estado para que acepte los 4 estados
-- (solo si la columna ya existe, si no existe se creará con los valores correctos)
ALTER TABLE ventas 
MODIFY COLUMN estado ENUM('ACTIVA', 'EN_PROCESO', 'ENTREGADA', 'CANCELADA') 
DEFAULT 'ACTIVA';

-- ============================================================================
-- VERIFICACIÓN
-- ============================================================================

-- Ver estructura de la tabla ventas
DESCRIBE ventas;

-- Verificar que no haya datos conflictivos
SELECT COUNT(*) as total_ventas, 
       SUM(CASE WHEN estado NOT IN ('ACTIVA', 'EN_PROCESO', 'ENTREGADA', 'CANCELADA') THEN 1 ELSE 0 END) as estados_invalidos
FROM ventas;

-- ============================================================================
-- NOTAS
-- ============================================================================

/*
ESTADOS VÁLIDOS:
- ACTIVA: Venta registrada, pendiente de preparar
- EN_PROCESO: En proceso de entrega
- ENTREGADA: Ya fue entregada al cliente
- CANCELADA: Venta cancelada

FLUJO NORMAL:
ACTIVA → EN_PROCESO → ENTREGADA

FLUJO CANCELACIÓN:
ACTIVA → CANCELADA
EN_PROCESO → CANCELADA

CAMPOS CONDICIONALES:
- Si tipo_entrega = 'Retiro' → direccion_envio, tipo_flete, zona, fletero quedan NULL
- Si tipo_entrega = 'Envío' y tipo_flete != 'Flete Propio' → zona, fletero quedan NULL
- Si tipo_flete = 'Flete Propio' → zona y fletero son obligatorios

PAGOS:
- pago_mercadopago + pago_efectivo debe ser <= importe_total
- El saldo se calcula automáticamente en el frontend
*/
