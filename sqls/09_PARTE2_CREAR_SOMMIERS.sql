-- ============================================================================
-- PARTE 2: CREAR TODOS LOS SOMMIERS AUTOMÁTICAMENTE
-- Generado por script Python
-- ============================================================================

USE inventario_cannon;
SET SQL_SAFE_UPDATES = 0;

-- Limpiar sommiers anteriores
DELETE FROM componentes;
DELETE FROM productos_compuestos;

-- ============================================================================
-- CREAR PRODUCTOS COMPUESTOS (SOMMIERS)
-- ============================================================================

INSERT INTO productos_compuestos (sku, nombre, precio_base, descripcion) VALUES
('SPR8020', 'Sommier Princess 20cm 80x190', 690000, 'Colchón + Base');
INSERT INTO productos_compuestos (sku, nombre, precio_base, descripcion) VALUES
('SPR9020', 'Sommier Princess 20cm 90x190', 720000, 'Colchón + Base');
INSERT INTO productos_compuestos (sku, nombre, precio_base, descripcion) VALUES
('SPR10020', 'Sommier Princess 20cm 100x190', 750000, 'Colchón + Base');
INSERT INTO productos_compuestos (sku, nombre, precio_base, descripcion) VALUES
('SPR14020', 'Sommier Princess 20cm 140x190', 870000, 'Colchón + Base');
INSERT INTO productos_compuestos (sku, nombre, precio_base, descripcion) VALUES
('SPR8023', 'Sommier Princess 23cm 80x190', 690000, 'Colchón + Base');
INSERT INTO productos_compuestos (sku, nombre, precio_base, descripcion) VALUES
('SPR9023', 'Sommier Princess 23cm 90x190', 720000, 'Colchón + Base');
INSERT INTO productos_compuestos (sku, nombre, precio_base, descripcion) VALUES
('SPR10023', 'Sommier Princess 23cm 100x190', 750000, 'Colchón + Base');
INSERT INTO productos_compuestos (sku, nombre, precio_base, descripcion) VALUES
('SPR14023', 'Sommier Princess 23cm 140x190', 870000, 'Colchón + Base');
INSERT INTO productos_compuestos (sku, nombre, precio_base, descripcion) VALUES
('SSO80', 'Sommier Soñar 80x190', 690000, 'Colchón + Base');
INSERT INTO productos_compuestos (sku, nombre, precio_base, descripcion) VALUES
('SSO90', 'Sommier Soñar 90x190', 720000, 'Colchón + Base');
INSERT INTO productos_compuestos (sku, nombre, precio_base, descripcion) VALUES
('SSO100', 'Sommier Soñar 100x190', 750000, 'Colchón + Base');
INSERT INTO productos_compuestos (sku, nombre, precio_base, descripcion) VALUES
('SSO140', 'Sommier Soñar 140x190', 870000, 'Colchón + Base');
INSERT INTO productos_compuestos (sku, nombre, precio_base, descripcion) VALUES
('SEX80', 'Sommier Exclusive 80x190', 690000, 'Colchón + Base');
INSERT INTO productos_compuestos (sku, nombre, precio_base, descripcion) VALUES
('SEX90', 'Sommier Exclusive 90x190', 720000, 'Colchón + Base');
INSERT INTO productos_compuestos (sku, nombre, precio_base, descripcion) VALUES
('SEX100', 'Sommier Exclusive 100x190', 750000, 'Colchón + Base');
INSERT INTO productos_compuestos (sku, nombre, precio_base, descripcion) VALUES
('SEX140', 'Sommier Exclusive 140x190', 870000, 'Colchón + Base');
INSERT INTO productos_compuestos (sku, nombre, precio_base, descripcion) VALUES
('SEX150', 'Sommier Exclusive 150x190', 900000, 'Colchón + Base');
INSERT INTO productos_compuestos (sku, nombre, precio_base, descripcion) VALUES
('SEX160', 'Sommier Exclusive 160x200', 930000, 'Colchón + Base');
INSERT INTO productos_compuestos (sku, nombre, precio_base, descripcion) VALUES
('SEX180', 'Sommier Exclusive 180x200', 990000, 'Colchón + Base');
INSERT INTO productos_compuestos (sku, nombre, precio_base, descripcion) VALUES
('SEX200', 'Sommier Exclusive 200x200', 1050000, 'Colchón + Base');
INSERT INTO productos_compuestos (sku, nombre, precio_base, descripcion) VALUES
('SEXP80', 'Sommier Exclusive Pillow 80x190', 690000, 'Colchón + Base');
INSERT INTO productos_compuestos (sku, nombre, precio_base, descripcion) VALUES
('SEXP90', 'Sommier Exclusive Pillow 90x190', 720000, 'Colchón + Base');
INSERT INTO productos_compuestos (sku, nombre, precio_base, descripcion) VALUES
('SEXP100', 'Sommier Exclusive Pillow 100x190', 750000, 'Colchón + Base');
INSERT INTO productos_compuestos (sku, nombre, precio_base, descripcion) VALUES
('SEXP140', 'Sommier Exclusive Pillow 140x190', 870000, 'Colchón + Base');
INSERT INTO productos_compuestos (sku, nombre, precio_base, descripcion) VALUES
('SEXP150', 'Sommier Exclusive Pillow 150x190', 900000, 'Colchón + Base');
INSERT INTO productos_compuestos (sku, nombre, precio_base, descripcion) VALUES
('SEXP160', 'Sommier Exclusive Pillow 160x200', 930000, 'Colchón + Base');
INSERT INTO productos_compuestos (sku, nombre, precio_base, descripcion) VALUES
('SEXP180', 'Sommier Exclusive Pillow 180x200', 990000, 'Colchón + Base');
INSERT INTO productos_compuestos (sku, nombre, precio_base, descripcion) VALUES
('SEXP200', 'Sommier Exclusive Pillow 200x200', 1050000, 'Colchón + Base');
INSERT INTO productos_compuestos (sku, nombre, precio_base, descripcion) VALUES
('SDO80', 'Sommier Doral 80x190', 690000, 'Colchón + Base');
INSERT INTO productos_compuestos (sku, nombre, precio_base, descripcion) VALUES
('SDO90', 'Sommier Doral 90x190', 720000, 'Colchón + Base');
INSERT INTO productos_compuestos (sku, nombre, precio_base, descripcion) VALUES
('SDO100', 'Sommier Doral 100x190', 750000, 'Colchón + Base');
INSERT INTO productos_compuestos (sku, nombre, precio_base, descripcion) VALUES
('SDO140', 'Sommier Doral 140x190', 870000, 'Colchón + Base');
INSERT INTO productos_compuestos (sku, nombre, precio_base, descripcion) VALUES
('SDO150', 'Sommier Doral 150x190', 900000, 'Colchón + Base');
INSERT INTO productos_compuestos (sku, nombre, precio_base, descripcion) VALUES
('SDO160', 'Sommier Doral 160x200', 930000, 'Colchón + Base');
INSERT INTO productos_compuestos (sku, nombre, precio_base, descripcion) VALUES
('SDO180', 'Sommier Doral 180x200', 990000, 'Colchón + Base');
INSERT INTO productos_compuestos (sku, nombre, precio_base, descripcion) VALUES
('SDO200', 'Sommier Doral 200x200', 1050000, 'Colchón + Base');
INSERT INTO productos_compuestos (sku, nombre, precio_base, descripcion) VALUES
('SDOP140', 'Sommier Doral Pillow 140x190', 870000, 'Colchón + Base');
INSERT INTO productos_compuestos (sku, nombre, precio_base, descripcion) VALUES
('SDOP150', 'Sommier Doral Pillow 150x190', 900000, 'Colchón + Base');
INSERT INTO productos_compuestos (sku, nombre, precio_base, descripcion) VALUES
('SDOP160', 'Sommier Doral Pillow 160x200', 930000, 'Colchón + Base');
INSERT INTO productos_compuestos (sku, nombre, precio_base, descripcion) VALUES
('SDOP180', 'Sommier Doral Pillow 180x200', 990000, 'Colchón + Base');
INSERT INTO productos_compuestos (sku, nombre, precio_base, descripcion) VALUES
('SDOP200', 'Sommier Doral Pillow 200x200', 1050000, 'Colchón + Base');
INSERT INTO productos_compuestos (sku, nombre, precio_base, descripcion) VALUES
('SRE80', 'Sommier Renovation 80x190', 690000, 'Colchón + Base');
INSERT INTO productos_compuestos (sku, nombre, precio_base, descripcion) VALUES
('SRE90', 'Sommier Renovation 90x190', 720000, 'Colchón + Base');
INSERT INTO productos_compuestos (sku, nombre, precio_base, descripcion) VALUES
('SRE100', 'Sommier Renovation 100x190', 750000, 'Colchón + Base');
INSERT INTO productos_compuestos (sku, nombre, precio_base, descripcion) VALUES
('SRE140', 'Sommier Renovation 140x190', 870000, 'Colchón + Base');
INSERT INTO productos_compuestos (sku, nombre, precio_base, descripcion) VALUES
('SRE150', 'Sommier Renovation 150x190', 900000, 'Colchón + Base');
INSERT INTO productos_compuestos (sku, nombre, precio_base, descripcion) VALUES
('SRE160', 'Sommier Renovation 160x200', 930000, 'Colchón + Base');
INSERT INTO productos_compuestos (sku, nombre, precio_base, descripcion) VALUES
('SRE180', 'Sommier Renovation 180x200', 990000, 'Colchón + Base');
INSERT INTO productos_compuestos (sku, nombre, precio_base, descripcion) VALUES
('SRE200', 'Sommier Renovation 200x200', 1050000, 'Colchón + Base');
INSERT INTO productos_compuestos (sku, nombre, precio_base, descripcion) VALUES
('SREP80', 'Sommier Renovation Europillow 80x190', 690000, 'Colchón + Base');
INSERT INTO productos_compuestos (sku, nombre, precio_base, descripcion) VALUES
('SREP90', 'Sommier Renovation Europillow 90x190', 720000, 'Colchón + Base');
INSERT INTO productos_compuestos (sku, nombre, precio_base, descripcion) VALUES
('SREP100', 'Sommier Renovation Europillow 100x190', 750000, 'Colchón + Base');
INSERT INTO productos_compuestos (sku, nombre, precio_base, descripcion) VALUES
('SREP140', 'Sommier Renovation Europillow 140x190', 870000, 'Colchón + Base');
INSERT INTO productos_compuestos (sku, nombre, precio_base, descripcion) VALUES
('SREP150', 'Sommier Renovation Europillow 150x190', 900000, 'Colchón + Base');
INSERT INTO productos_compuestos (sku, nombre, precio_base, descripcion) VALUES
('SREP160', 'Sommier Renovation Europillow 160x200', 930000, 'Colchón + Base');
INSERT INTO productos_compuestos (sku, nombre, precio_base, descripcion) VALUES
('SREP180', 'Sommier Renovation Europillow 180x200', 990000, 'Colchón + Base');
INSERT INTO productos_compuestos (sku, nombre, precio_base, descripcion) VALUES
('SREP200', 'Sommier Renovation Europillow 200x200', 1050000, 'Colchón + Base');
INSERT INTO productos_compuestos (sku, nombre, precio_base, descripcion) VALUES
('SSUP140', 'Sommier Sublime Europillow 140x190', 870000, 'Colchón + Base');
INSERT INTO productos_compuestos (sku, nombre, precio_base, descripcion) VALUES
('SSUP150', 'Sommier Sublime Europillow 150x190', 900000, 'Colchón + Base');
INSERT INTO productos_compuestos (sku, nombre, precio_base, descripcion) VALUES
('SSUP160', 'Sommier Sublime Europillow 160x200', 930000, 'Colchón + Base');
INSERT INTO productos_compuestos (sku, nombre, precio_base, descripcion) VALUES
('SSUP180', 'Sommier Sublime Europillow 180x200', 990000, 'Colchón + Base');
INSERT INTO productos_compuestos (sku, nombre, precio_base, descripcion) VALUES
('SSUP200', 'Sommier Sublime Europillow 200x200', 1050000, 'Colchón + Base');

-- ✓ 62 sommiers creados

-- ============================================================================
-- CONFIGURAR COMPONENTES
-- ============================================================================

-- SPR8020
INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 1 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'SPR8020' AND pb.sku IN ('CPR8020', 'BASE_SAB80');

-- SPR9020
INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 1 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'SPR9020' AND pb.sku IN ('CPR9020', 'BASE_SAB90');

-- SPR10020
INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 1 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'SPR10020' AND pb.sku IN ('CPR10020', 'BASE_SAB100');

-- SPR14020
INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 1 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'SPR14020' AND pb.sku IN ('CPR14020', 'BASE_SAB140');

-- SPR8023
INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 1 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'SPR8023' AND pb.sku IN ('CPR8023', 'BASE_GRIS80');

-- SPR9023
INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 1 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'SPR9023' AND pb.sku IN ('CPR9023', 'BASE_GRIS90');

-- SPR10023
INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 1 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'SPR10023' AND pb.sku IN ('CPR10023', 'BASE_GRIS100');

-- SPR14023
INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 1 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'SPR14023' AND pb.sku IN ('CPR14023', 'BASE_GRIS140');

-- SSO80
INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 1 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'SSO80' AND pb.sku IN ('CSO80', 'BASE_SAB80');

-- SSO90
INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 1 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'SSO90' AND pb.sku IN ('CSO90', 'BASE_SAB90');

-- SSO100
INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 1 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'SSO100' AND pb.sku IN ('CSO100', 'BASE_SAB100');

-- SSO140
INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 1 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'SSO140' AND pb.sku IN ('CSO140', 'BASE_SAB140');

-- SEX80
INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 1 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'SEX80' AND pb.sku IN ('CEX80', 'BASE_CHOC80');

-- SEX90
INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 1 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'SEX90' AND pb.sku IN ('CEX90', 'BASE_CHOC90');

-- SEX100
INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 1 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'SEX100' AND pb.sku IN ('CEX100', 'BASE_CHOC100');

-- SEX140
INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 1 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'SEX140' AND pb.sku IN ('CEX140', 'BASE_CHOC140');

-- SEX150
INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 1 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'SEX150' AND pb.sku IN ('CEX150', 'BASE_CHOC150');

-- SEX160 (2 bases)
INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 1 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'SEX160' AND pb.sku = 'CEX160';

INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 2 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'SEX160' AND pb.sku = 'BASE_CHOC80200';

-- SEX180 (2 bases)
INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 1 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'SEX180' AND pb.sku = 'CEX180';

INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 2 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'SEX180' AND pb.sku = 'BASE_CHOC90200';

-- SEX200 (2 bases)
INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 1 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'SEX200' AND pb.sku = 'CEX200';

INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 2 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'SEX200' AND pb.sku = 'BASE_CHOC100200';

-- SEXP80
INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 1 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'SEXP80' AND pb.sku IN ('CEXP80', 'BASE_CHOC80');

-- SEXP90
INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 1 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'SEXP90' AND pb.sku IN ('CEXP90', 'BASE_CHOC90');

-- SEXP100
INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 1 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'SEXP100' AND pb.sku IN ('CEXP100', 'BASE_CHOC100');

-- SEXP140
INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 1 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'SEXP140' AND pb.sku IN ('CEXP140', 'BASE_CHOC140');

-- SEXP150
INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 1 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'SEXP150' AND pb.sku IN ('CEXP150', 'BASE_CHOC150');

-- SEXP160 (2 bases)
INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 1 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'SEXP160' AND pb.sku = 'CEXP160';

INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 2 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'SEXP160' AND pb.sku = 'BASE_CHOC80200';

-- SEXP180 (2 bases)
INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 1 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'SEXP180' AND pb.sku = 'CEXP180';

INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 2 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'SEXP180' AND pb.sku = 'BASE_CHOC90200';

-- SEXP200 (2 bases)
INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 1 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'SEXP200' AND pb.sku = 'CEXP200';

INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 2 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'SEXP200' AND pb.sku = 'BASE_CHOC100200';

-- SDO80
INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 1 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'SDO80' AND pb.sku IN ('CDO80', 'BASE_GRIS80');

-- SDO90
INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 1 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'SDO90' AND pb.sku IN ('CDO90', 'BASE_GRIS90');

-- SDO100
INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 1 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'SDO100' AND pb.sku IN ('CDO100', 'BASE_GRIS100');

-- SDO140
INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 1 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'SDO140' AND pb.sku IN ('CDO140', 'BASE_GRIS140');

-- SDO150
INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 1 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'SDO150' AND pb.sku IN ('CDO150', 'BASE_GRIS150');

-- SDO160 (2 bases)
INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 1 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'SDO160' AND pb.sku = 'CDO160';

INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 2 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'SDO160' AND pb.sku = 'BASE_GRIS80200';

-- SDO180 (2 bases)
INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 1 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'SDO180' AND pb.sku = 'CDO180';

INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 2 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'SDO180' AND pb.sku = 'BASE_GRIS90200';

-- SDO200 (2 bases)
INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 1 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'SDO200' AND pb.sku = 'CDO200';

INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 2 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'SDO200' AND pb.sku = 'BASE_GRIS100200';

-- SDOP140
INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 1 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'SDOP140' AND pb.sku IN ('CDOP140', 'BASE_GRIS140');

-- SDOP150
INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 1 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'SDOP150' AND pb.sku IN ('CDOP150', 'BASE_GRIS150');

-- SDOP160 (2 bases)
INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 1 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'SDOP160' AND pb.sku = 'CDOP160';

INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 2 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'SDOP160' AND pb.sku = 'BASE_GRIS80200';

-- SDOP180 (2 bases)
INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 1 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'SDOP180' AND pb.sku = 'CDOP180';

INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 2 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'SDOP180' AND pb.sku = 'BASE_GRIS90200';

-- SDOP200 (2 bases)
INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 1 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'SDOP200' AND pb.sku = 'CDOP200';

INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 2 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'SDOP200' AND pb.sku = 'BASE_GRIS100200';

-- SRE80
INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 1 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'SRE80' AND pb.sku IN ('CRE80', 'BASE_GRIS80');

-- SRE90
INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 1 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'SRE90' AND pb.sku IN ('CRE90', 'BASE_GRIS90');

-- SRE100
INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 1 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'SRE100' AND pb.sku IN ('CRE100', 'BASE_GRIS100');

-- SRE140
INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 1 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'SRE140' AND pb.sku IN ('CRE140', 'BASE_GRIS140');

-- SRE150
INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 1 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'SRE150' AND pb.sku IN ('CRE150', 'BASE_GRIS150');

-- SRE160 (2 bases)
INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 1 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'SRE160' AND pb.sku = 'CRE160';

INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 2 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'SRE160' AND pb.sku = 'BASE_GRIS80200';

-- SRE180 (2 bases)
INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 1 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'SRE180' AND pb.sku = 'CRE180';

INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 2 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'SRE180' AND pb.sku = 'BASE_GRIS90200';

-- SRE200 (2 bases)
INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 1 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'SRE200' AND pb.sku = 'CRE200';

INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 2 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'SRE200' AND pb.sku = 'BASE_GRIS100200';

-- SREP80
INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 1 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'SREP80' AND pb.sku IN ('CREP80', 'BASE_GRIS80');

-- SREP90
INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 1 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'SREP90' AND pb.sku IN ('CREP90', 'BASE_GRIS90');

-- SREP100
INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 1 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'SREP100' AND pb.sku IN ('CREP100', 'BASE_GRIS100');

-- SREP140
INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 1 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'SREP140' AND pb.sku IN ('CREP140', 'BASE_GRIS140');

-- SREP150
INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 1 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'SREP150' AND pb.sku IN ('CREP150', 'BASE_GRIS150');

-- SREP160 (2 bases)
INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 1 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'SREP160' AND pb.sku = 'CREP160';

INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 2 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'SREP160' AND pb.sku = 'BASE_GRIS80200';

-- SREP180 (2 bases)
INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 1 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'SREP180' AND pb.sku = 'CREP180';

INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 2 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'SREP180' AND pb.sku = 'BASE_GRIS90200';

-- SREP200 (2 bases)
INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 1 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'SREP200' AND pb.sku = 'CREP200';

INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 2 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'SREP200' AND pb.sku = 'BASE_GRIS100200';

-- SSUP140
INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 1 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'SSUP140' AND pb.sku IN ('CSUP140', 'BASE_SUBL140');

-- SSUP150
INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 1 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'SSUP150' AND pb.sku IN ('CSUP150', 'BASE_SUBL150');

-- SSUP160 (2 bases)
INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 1 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'SSUP160' AND pb.sku = 'CSUP160';

INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 2 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'SSUP160' AND pb.sku = 'BASE_SUBL80200';

-- SSUP180 (2 bases)
INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 1 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'SSUP180' AND pb.sku = 'CSUP180';

INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 2 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'SSUP180' AND pb.sku = 'BASE_SUBL90200';

-- SSUP200 (2 bases)
INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 1 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'SSUP200' AND pb.sku = 'CSUP200';

INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 2 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'SSUP200' AND pb.sku = 'BASE_SUBL100200';

-- ============================================================================
-- COMBOS CON ALMOHADAS
-- ============================================================================

INSERT INTO productos_compuestos (sku, nombre, precio_base, descripcion) VALUES
('DUALX2', 'Combo 2 Almohadas Dual', 66000, '2 almohadas');

INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 2 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'DUALX2' AND pb.sku = 'DUAL';

INSERT INTO productos_compuestos (sku, nombre, precio_base, descripcion) VALUES
('PLATINOX2', 'Combo 2 Almohadas Platino', 60000, '2 almohadas');

INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 2 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'PLATINOX2' AND pb.sku = 'PLATINO';

INSERT INTO productos_compuestos (sku, nombre, precio_base, descripcion) VALUES
('PLATINOX4', 'Combo 4 Almohadas Platino', 120000, '4 almohadas');

INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 4 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'PLATINOX4' AND pb.sku = 'PLATINO';

INSERT INTO productos_compuestos (sku, nombre, precio_base, descripcion) VALUES
('EXCLUSIVEX2', 'Combo 2 Almohadas Exclusive', 64000, '2 almohadas');

INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 2 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'EXCLUSIVEX2' AND pb.sku = 'EXCLUSIVE';

INSERT INTO productos_compuestos (sku, nombre, precio_base, descripcion) VALUES
('DORALX2', 'Combo 2 Almohadas Doral', 56000, '2 almohadas');

INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 2 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'DORALX2' AND pb.sku = 'DORAL';

-- Sommiers con 1 almohada
INSERT INTO productos_compuestos (sku, nombre, precio_base, descripcion)
SELECT CONCAT(sku, '+1'), CONCAT(nombre, ' + 1 Almohada'), precio_base + 30000, 'Sommier + 1 Platino'
FROM productos_compuestos WHERE sku = 'SPR9023';

-- Componentes del sommier
INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pcc.id, c.producto_base_id, c.cantidad_necesaria
FROM productos_compuestos pcc
JOIN productos_compuestos pcs ON pcs.sku = 'SPR9023'
JOIN componentes c ON c.producto_compuesto_id = pcs.id
WHERE pcc.sku = 'SPR9023+1';

-- Agregar almohada
INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 1 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'SPR9023+1' AND pb.sku = 'PLATINO';

INSERT INTO productos_compuestos (sku, nombre, precio_base, descripcion)
SELECT CONCAT(sku, '+1'), CONCAT(nombre, ' + 1 Almohada'), precio_base + 30000, 'Sommier + 1 Platino'
FROM productos_compuestos WHERE sku = 'SPR10023';

-- Componentes del sommier
INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pcc.id, c.producto_base_id, c.cantidad_necesaria
FROM productos_compuestos pcc
JOIN productos_compuestos pcs ON pcs.sku = 'SPR10023'
JOIN componentes c ON c.producto_compuesto_id = pcs.id
WHERE pcc.sku = 'SPR10023+1';

-- Agregar almohada
INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 1 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'SPR10023+1' AND pb.sku = 'PLATINO';

INSERT INTO productos_compuestos (sku, nombre, precio_base, descripcion)
SELECT CONCAT(sku, '+1'), CONCAT(nombre, ' + 1 Almohada'), precio_base + 30000, 'Sommier + 1 Platino'
FROM productos_compuestos WHERE sku = 'SEX100';

-- Componentes del sommier
INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pcc.id, c.producto_base_id, c.cantidad_necesaria
FROM productos_compuestos pcc
JOIN productos_compuestos pcs ON pcs.sku = 'SEX100'
JOIN componentes c ON c.producto_compuesto_id = pcs.id
WHERE pcc.sku = 'SEX100+1';

-- Agregar almohada
INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 1 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'SEX100+1' AND pb.sku = 'PLATINO';

INSERT INTO productos_compuestos (sku, nombre, precio_base, descripcion)
SELECT CONCAT(sku, '+1'), CONCAT(nombre, ' + 1 Almohada'), precio_base + 30000, 'Sommier + 1 Platino'
FROM productos_compuestos WHERE sku = 'SEXP100';

-- Componentes del sommier
INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pcc.id, c.producto_base_id, c.cantidad_necesaria
FROM productos_compuestos pcc
JOIN productos_compuestos pcs ON pcs.sku = 'SEXP100'
JOIN componentes c ON c.producto_compuesto_id = pcs.id
WHERE pcc.sku = 'SEXP100+1';

-- Agregar almohada
INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 1 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'SEXP100+1' AND pb.sku = 'PLATINO';

-- Sommiers con 2 almohadas
INSERT INTO productos_compuestos (sku, nombre, precio_base, descripcion)
SELECT CONCAT(sku, '+2'), CONCAT(nombre, ' + 2 Almohadas'), precio_base + 60000, 'Sommier + 2 Platino'
FROM productos_compuestos WHERE sku = 'SDO140';

-- Componentes del sommier
INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pcc.id, c.producto_base_id, c.cantidad_necesaria
FROM productos_compuestos pcc
JOIN productos_compuestos pcs ON pcs.sku = 'SDO140'
JOIN componentes c ON c.producto_compuesto_id = pcs.id
WHERE pcc.sku = 'SDO140+2';

-- Agregar 2 almohadas
INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 2 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'SDO140+2' AND pb.sku = 'PLATINO';

INSERT INTO productos_compuestos (sku, nombre, precio_base, descripcion)
SELECT CONCAT(sku, '+2'), CONCAT(nombre, ' + 2 Almohadas'), precio_base + 60000, 'Sommier + 2 Platino'
FROM productos_compuestos WHERE sku = 'SDOP140';

-- Componentes del sommier
INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pcc.id, c.producto_base_id, c.cantidad_necesaria
FROM productos_compuestos pcc
JOIN productos_compuestos pcs ON pcs.sku = 'SDOP140'
JOIN componentes c ON c.producto_compuesto_id = pcs.id
WHERE pcc.sku = 'SDOP140+2';

-- Agregar 2 almohadas
INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 2 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'SDOP140+2' AND pb.sku = 'PLATINO';

INSERT INTO productos_compuestos (sku, nombre, precio_base, descripcion)
SELECT CONCAT(sku, '+2'), CONCAT(nombre, ' + 2 Almohadas'), precio_base + 60000, 'Sommier + 2 Platino'
FROM productos_compuestos WHERE sku = 'SREP140';

-- Componentes del sommier
INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pcc.id, c.producto_base_id, c.cantidad_necesaria
FROM productos_compuestos pcc
JOIN productos_compuestos pcs ON pcs.sku = 'SREP140'
JOIN componentes c ON c.producto_compuesto_id = pcs.id
WHERE pcc.sku = 'SREP140+2';

-- Agregar 2 almohadas
INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 2 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'SREP140+2' AND pb.sku = 'PLATINO';

INSERT INTO productos_compuestos (sku, nombre, precio_base, descripcion)
SELECT CONCAT(sku, '+2'), CONCAT(nombre, ' + 2 Almohadas'), precio_base + 60000, 'Sommier + 2 Platino'
FROM productos_compuestos WHERE sku = 'SRE140';

-- Componentes del sommier
INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pcc.id, c.producto_base_id, c.cantidad_necesaria
FROM productos_compuestos pcc
JOIN productos_compuestos pcs ON pcs.sku = 'SRE140'
JOIN componentes c ON c.producto_compuesto_id = pcs.id
WHERE pcc.sku = 'SRE140+2';

-- Agregar 2 almohadas
INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 2 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'SRE140+2' AND pb.sku = 'PLATINO';

INSERT INTO productos_compuestos (sku, nombre, precio_base, descripcion)
SELECT CONCAT(sku, '+2'), CONCAT(nombre, ' + 2 Almohadas'), precio_base + 60000, 'Sommier + 2 Platino'
FROM productos_compuestos WHERE sku = 'SEX140';

-- Componentes del sommier
INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pcc.id, c.producto_base_id, c.cantidad_necesaria
FROM productos_compuestos pcc
JOIN productos_compuestos pcs ON pcs.sku = 'SEX140'
JOIN componentes c ON c.producto_compuesto_id = pcs.id
WHERE pcc.sku = 'SEX140+2';

-- Agregar 2 almohadas
INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 2 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'SEX140+2' AND pb.sku = 'PLATINO';

INSERT INTO productos_compuestos (sku, nombre, precio_base, descripcion)
SELECT CONCAT(sku, '+2'), CONCAT(nombre, ' + 2 Almohadas'), precio_base + 60000, 'Sommier + 2 Platino'
FROM productos_compuestos WHERE sku = 'SEXP140';

-- Componentes del sommier
INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pcc.id, c.producto_base_id, c.cantidad_necesaria
FROM productos_compuestos pcc
JOIN productos_compuestos pcs ON pcs.sku = 'SEXP140'
JOIN componentes c ON c.producto_compuesto_id = pcs.id
WHERE pcc.sku = 'SEXP140+2';

-- Agregar 2 almohadas
INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 2 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'SEXP140+2' AND pb.sku = 'PLATINO';

-- Colchones solos con almohadas
INSERT INTO productos_compuestos (sku, nombre, precio_base, descripcion) VALUES
('CEX140+2', 'Colchón Exclusive 140x190 + 2 Almohadas', 570000, 'Colchón + 2 Platino'),
('CEXP140+2', 'Colchón Exclusive Pillow 140x190 + 2 Almohadas', 590000, 'Colchón + 2 Platino');

INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 1 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'CEX140+2' AND pb.sku = 'CEX140';

INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 2 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'CEX140+2' AND pb.sku = 'PLATINO';

INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 1 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'CEXP140+2' AND pb.sku = 'CEXP140';

INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 2 FROM productos_compuestos pc CROSS JOIN productos_base pb
WHERE pc.sku = 'CEXP140+2' AND pb.sku = 'PLATINO';

SET SQL_SAFE_UPDATES = 1;

-- ============================================================================
-- VERIFICACIÓN
-- ============================================================================

SELECT 'Productos compuestos creados:' AS Info, COUNT(*) AS Total FROM productos_compuestos;
SELECT 'Componentes configurados:' AS Info, COUNT(*) AS Total FROM componentes;

-- Ver algunos sommiers con sus componentes
SELECT pc.sku, pc.nombre, COUNT(c.id) as num_componentes
FROM productos_compuestos pc
LEFT JOIN componentes c ON pc.id = c.producto_compuesto_id
GROUP BY pc.id, pc.sku, pc.nombre
ORDER BY pc.sku
LIMIT 20;

SELECT '✅ Script completado' AS Resultado;
SELECT '⏭️  Ahora ejecutar: 07_CREAR_VISTAS_SIMPLE.sql' AS 'Siguiente Paso';
