-- 012_lista_precios_historial.sql
-- Historial de la lista de precios de Cannon.
--
-- cannon_lista_precios tiene UNIQUE por codigo_material: cada importación pisa
-- el precio anterior y no queda rastro de cuánto costaba antes. Eso hace que
-- recalcular rentabilidad de una venta vieja le aplique el costo de HOY.
-- Esta tabla guarda una fila por material y vigencia, así se puede reconstruir
-- el costo que regía en cualquier fecha.

CREATE TABLE IF NOT EXISTS cannon_lista_precios_hist (
    id               INT AUTO_INCREMENT PRIMARY KEY,
    codigo_material  BIGINT         NOT NULL,
    precio_lista     DECIMAL(12,2)  NOT NULL,
    vigencia         DATE           NOT NULL,
    tipo             VARCHAR(20)    DEFAULT 'lista',   -- lista | almohadas
    fecha_carga      TIMESTAMP      DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_material_vigencia (codigo_material, vigencia),
    INDEX idx_vigencia (vigencia),
    INDEX idx_material (codigo_material)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Semilla: lo que hay hoy en la lista vigente, para no arrancar vacío.
INSERT IGNORE INTO cannon_lista_precios_hist (codigo_material, precio_lista, vigencia, tipo)
SELECT codigo_material, precio_lista, vigencia,
       CASE WHEN codigo_material IN (
            SELECT codigo_material FROM cannon_productos
            WHERE descripcion LIKE 'ALM%'
               OR sku IN ('CLASICA','SUBLIME','CERVICAL','RENOVATION',
                          'PLATINO','DORAL','DUAL','EXCLUSIVE')
       ) THEN 'almohadas' ELSE 'lista' END
FROM cannon_lista_precios
WHERE vigencia IS NOT NULL;
