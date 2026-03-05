-- ============================================================================
-- SCRIPT COMPLETO: CREAR TABLAS + PRODUCTOS + COMBOS + VISTAS
-- Ejecutar TODO de una vez en MySQL Workbench
-- ============================================================================

USE inventario_cannon;

-- ============================================================================
-- PASO 1: CREAR TABLAS QUE FALTAN
-- ============================================================================

-- Tabla de productos compuestos (combos)
CREATE TABLE IF NOT EXISTS productos_compuestos (
    id INT PRIMARY KEY AUTO_INCREMENT,
    sku VARCHAR(50) UNIQUE NOT NULL,
    nombre VARCHAR(255) NOT NULL,
    descripcion TEXT,
    precio_base DECIMAL(10,2),
    activo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Tabla de componentes de productos compuestos
CREATE TABLE IF NOT EXISTS componentes (
    id INT PRIMARY KEY AUTO_INCREMENT,
    producto_compuesto_id INT NOT NULL,
    producto_base_id INT NOT NULL,
    cantidad_necesaria INT DEFAULT 1,
    FOREIGN KEY (producto_compuesto_id) REFERENCES productos_compuestos(id) ON DELETE CASCADE,
    FOREIGN KEY (producto_base_id) REFERENCES productos_base(id) ON DELETE CASCADE
);

SELECT '✓ Tablas productos_compuestos y componentes creadas' AS Paso;

-- ============================================================================
-- PASO 2: LIMPIAR Y CARGAR PRODUCTOS
-- ============================================================================

SET FOREIGN_KEY_CHECKS = 0;
DELETE FROM componentes;
DELETE FROM productos_compuestos;
DELETE FROM items_venta;
DELETE FROM ventas;
DELETE FROM productos_base;
SET FOREIGN_KEY_CHECKS = 1;

SELECT '✓ Base de datos limpiada' AS Paso;

-- ============================================================================
-- COLCHONES LÍNEA ESPUMA
-- ============================================================================

-- Tropical - solo chicos (80, 90, 100)
INSERT INTO productos_base (sku, nombre, tipo, linea, modelo, medida, stock_actual, stock_minimo_pausar, stock_minimo_reactivar, precio_base) VALUES
('CTR80', 'Colchón Tropical 80x190', 'colchon', 'espuma', 'Tropical', '80x190', 0, 0, 1, 250000),
('CTR90', 'Colchón Tropical 90x190', 'colchon', 'espuma', 'Tropical', '90x190', 0, 0, 1, 270000),
('CTR100', 'Colchón Tropical 100x190', 'colchon', 'espuma', 'Tropical', '100x190', 0, 0, 1, 290000);

-- Princess 20cm - hasta 140
INSERT INTO productos_base (sku, nombre, tipo, linea, modelo, medida, stock_actual, stock_minimo_pausar, stock_minimo_reactivar, precio_base) VALUES
('CPR8020', 'Colchón Princess 20cm 80x190', 'colchon', 'espuma', 'Princess 20cm', '80x190', 0, 0, 1, 300000),
('CPR9020', 'Colchón Princess 20cm 90x190', 'colchon', 'espuma', 'Princess 20cm', '90x190', 0, 0, 1, 320000),
('CPR10020', 'Colchón Princess 20cm 100x190', 'colchon', 'espuma', 'Princess 20cm', '100x190', 0, 0, 1, 340000),
('CPR14020', 'Colchón Princess 20cm 140x190', 'colchon', 'espuma', 'Princess 20cm', '140x190', 0, 0, 1, 450000);

-- Princess 23cm - hasta 140 (CORREGIDO)
INSERT INTO productos_base (sku, nombre, tipo, linea, modelo, medida, stock_actual, stock_minimo_pausar, stock_minimo_reactivar, precio_base) VALUES
('CPR8023', 'Colchón Princess 23cm 80x190', 'colchon', 'espuma', 'Princess 23cm', '80x190', 0, 0, 1, 320000),
('CPR9023', 'Colchón Princess 23cm 90x190', 'colchon', 'espuma', 'Princess 23cm', '90x190', 0, 0, 1, 340000),
('CPR10023', 'Colchón Princess 23cm 100x190', 'colchon', 'espuma', 'Princess 23cm', '100x190', 0, 0, 1, 360000),
('CPR14023', 'Colchón Princess 23cm 140x190', 'colchon', 'espuma', 'Princess 23cm', '140x190', 0, 0, 1, 480000);

-- Exclusive - todas las medidas
INSERT INTO productos_base (sku, nombre, tipo, linea, modelo, medida, stock_actual, stock_minimo_pausar, stock_minimo_reactivar, precio_base) VALUES
('CEX80', 'Colchón Exclusive 80x190', 'colchon', 'espuma', 'Exclusive', '80x190', 0, 0, 1, 350000),
('CEX90', 'Colchón Exclusive 90x190', 'colchon', 'espuma', 'Exclusive', '90x190', 0, 0, 1, 370000),
('CEX100', 'Colchón Exclusive 100x190', 'colchon', 'espuma', 'Exclusive', '100x190', 0, 0, 1, 390000),
('CEX140', 'Colchón Exclusive 140x190', 'colchon', 'espuma', 'Exclusive', '140x190', 0, 0, 1, 510000),
('CEX150', 'Colchón Exclusive 150x190', 'colchon', 'espuma', 'Exclusive', '150x190', 0, 0, 1, 550000),
('CEX160', 'Colchón Exclusive 160x200', 'colchon', 'espuma', 'Exclusive', '160x200', 0, 0, 1, 650000),
('CEX180', 'Colchón Exclusive 180x200', 'colchon', 'espuma', 'Exclusive', '180x200', 0, 0, 1, 750000),
('CEX200', 'Colchón Exclusive 200x200', 'colchon', 'espuma', 'Exclusive', '200x200', 0, 0, 1, 850000);

-- Exclusive Pillow - TODAS LAS MEDIDAS (CORREGIDO)
INSERT INTO productos_base (sku, nombre, tipo, linea, modelo, medida, stock_actual, stock_minimo_pausar, stock_minimo_reactivar, precio_base) VALUES
('CEXP80', 'Colchón Exclusive Pillow 80x190', 'colchon', 'espuma', 'Exclusive Pillow', '80x190', 0, 0, 1, 370000),
('CEXP90', 'Colchón Exclusive Pillow 90x190', 'colchon', 'espuma', 'Exclusive Pillow', '90x190', 0, 0, 1, 390000),
('CEXP100', 'Colchón Exclusive Pillow 100x190', 'colchon', 'espuma', 'Exclusive Pillow', '100x190', 0, 0, 1, 410000),
('CEXP140', 'Colchón Exclusive Pillow 140x190', 'colchon', 'espuma', 'Exclusive Pillow', '140x190', 0, 0, 1, 530000),
('CEXP150', 'Colchón Exclusive Pillow 150x190', 'colchon', 'espuma', 'Exclusive Pillow', '150x190', 0, 0, 1, 570000),
('CEXP160', 'Colchón Exclusive Pillow 160x200', 'colchon', 'espuma', 'Exclusive Pillow', '160x200', 0, 0, 1, 670000),
('CEXP180', 'Colchón Exclusive Pillow 180x200', 'colchon', 'espuma', 'Exclusive Pillow', '180x200', 0, 0, 1, 770000),
('CEXP200', 'Colchón Exclusive Pillow 200x200', 'colchon', 'espuma', 'Exclusive Pillow', '200x200', 0, 0, 1, 870000);

-- Renovation - todas las medidas
INSERT INTO productos_base (sku, nombre, tipo, linea, modelo, medida, stock_actual, stock_minimo_pausar, stock_minimo_reactivar, precio_base) VALUES
('CREN80', 'Colchón Renovation 80x190', 'colchon', 'espuma', 'Renovation', '80x190', 0, 0, 1, 380000),
('CREN90', 'Colchón Renovation 90x190', 'colchon', 'espuma', 'Renovation', '90x190', 0, 0, 1, 400000),
('CREN100', 'Colchón Renovation 100x190', 'colchon', 'espuma', 'Renovation', '100x190', 0, 0, 1, 420000),
('CREN140', 'Colchón Renovation 140x190', 'colchon', 'espuma', 'Renovation', '140x190', 0, 0, 1, 540000),
('CREN150', 'Colchón Renovation 150x190', 'colchon', 'espuma', 'Renovation', '150x190', 0, 0, 1, 580000),
('CREN160', 'Colchón Renovation 160x200', 'colchon', 'espuma', 'Renovation', '160x200', 0, 0, 1, 680000),
('CREN180', 'Colchón Renovation 180x200', 'colchon', 'espuma', 'Renovation', '180x200', 0, 0, 1, 780000),
('CREN200', 'Colchón Renovation 200x200', 'colchon', 'espuma', 'Renovation', '200x200', 0, 0, 1, 880000);

-- Renovation Europillow - todas las medidas
INSERT INTO productos_base (sku, nombre, tipo, linea, modelo, medida, stock_actual, stock_minimo_pausar, stock_minimo_reactivar, precio_base) VALUES
('CRENEP80', 'Colchón Renovation Europillow 80x190', 'colchon', 'espuma', 'Renovation Europillow', '80x190', 0, 0, 1, 400000),
('CRENEP90', 'Colchón Renovation Europillow 90x190', 'colchon', 'espuma', 'Renovation Europillow', '90x190', 0, 0, 1, 420000),
('CRENEP100', 'Colchón Renovation Europillow 100x190', 'colchon', 'espuma', 'Renovation Europillow', '100x190', 0, 0, 1, 440000),
('CRENEP140', 'Colchón Renovation Europillow 140x190', 'colchon', 'espuma', 'Renovation Europillow', '140x190', 0, 0, 1, 560000),
('CRENEP150', 'Colchón Renovation Europillow 150x190', 'colchon', 'espuma', 'Renovation Europillow', '150x190', 0, 0, 1, 600000),
('CRENEP160', 'Colchón Renovation Europillow 160x200', 'colchon', 'espuma', 'Renovation Europillow', '160x200', 0, 0, 1, 700000),
('CRENEP180', 'Colchón Renovation Europillow 180x200', 'colchon', 'espuma', 'Renovation Europillow', '180x200', 0, 0, 1, 800000),
('CRENEP200', 'Colchón Renovation Europillow 200x200', 'colchon', 'espuma', 'Renovation Europillow', '200x200', 0, 0, 1, 900000);

-- Compac - en caja
INSERT INTO productos_base (sku, nombre, tipo, linea, modelo, medida, stock_actual, stock_minimo_pausar, stock_minimo_reactivar, precio_base) VALUES
('CCOMP80', 'Colchón Compac 80x190', 'colchon', 'box', 'Compac', '80x190', 0, 0, 1, 180000),
('CCOMP100200', 'Colchón Compac 100x200', 'colchon', 'box', 'Compac', '100x200', 0, 0, 1, 220000),
('CCOMP140', 'Colchón Compac 140x190', 'colchon', 'box', 'Compac', '140x190', 0, 0, 1, 320000),
('CCOMP160', 'Colchón Compac 160x200', 'colchon', 'box', 'Compac', '160x200', 0, 0, 1, 420000);

-- Compac Plus Pocket - en caja
INSERT INTO productos_base (sku, nombre, tipo, linea, modelo, medida, stock_actual, stock_minimo_pausar, stock_minimo_reactivar, precio_base) VALUES
('CCOMPP80', 'Colchón Compac Plus Pocket 80x190', 'colchon', 'box', 'Compac Plus Pocket', '80x190', 0, 0, 1, 220000),
('CCOMPP100200', 'Colchón Compac Plus Pocket 100x200', 'colchon', 'box', 'Compac Plus Pocket', '100x200', 0, 0, 1, 260000),
('CCOMPP140', 'Colchón Compac Plus Pocket 140x190', 'colchon', 'box', 'Compac Plus Pocket', '140x190', 0, 0, 1, 360000),
('CCOMPP160', 'Colchón Compac Plus Pocket 160x200', 'colchon', 'box', 'Compac Plus Pocket', '160x200', 0, 0, 1, 460000);

-- ============================================================================
-- COLCHONES LÍNEA RESORTES
-- ============================================================================

INSERT INTO productos_base (sku, nombre, tipo, linea, modelo, medida, stock_actual, stock_minimo_pausar, stock_minimo_reactivar, precio_base) VALUES
('CSON80', 'Colchón Soñar 80x190', 'colchon', 'resortes', 'Soñar', '80x190', 0, 0, 1, 330000),
('CSON90', 'Colchón Soñar 90x190', 'colchon', 'resortes', 'Soñar', '90x190', 0, 0, 1, 350000),
('CSON100', 'Colchón Soñar 100x190', 'colchon', 'resortes', 'Soñar', '100x190', 0, 0, 1, 370000),
('CSON140', 'Colchón Soñar 140x190', 'colchon', 'resortes', 'Soñar', '140x190', 0, 0, 1, 490000),
('CDO80', 'Colchón Doral 80x190', 'colchon', 'resortes', 'Doral', '80x190', 0, 0, 1, 400000),
('CDO90', 'Colchón Doral 90x190', 'colchon', 'resortes', 'Doral', '90x190', 0, 0, 1, 420000),
('CDO100', 'Colchón Doral 100x190', 'colchon', 'resortes', 'Doral', '100x190', 0, 0, 1, 440000),
('CDO140', 'Colchón Doral 140x190', 'colchon', 'resortes', 'Doral', '140x190', 0, 0, 1, 560000),
('CDO150', 'Colchón Doral 150x190', 'colchon', 'resortes', 'Doral', '150x190', 0, 0, 1, 600000),
('CDO160', 'Colchón Doral 160x200', 'colchon', 'resortes', 'Doral', '160x200', 0, 0, 1, 700000),
('CDO180', 'Colchón Doral 180x200', 'colchon', 'resortes', 'Doral', '180x200', 0, 0, 1, 800000),
('CDO200', 'Colchón Doral 200x200', 'colchon', 'resortes', 'Doral', '200x200', 0, 0, 1, 900000),
('CDOP140', 'Colchón Doral Pillow 140x190', 'colchon', 'resortes', 'Doral Pillow', '140x190', 0, 0, 1, 580000),
('CDOP150', 'Colchón Doral Pillow 150x190', 'colchon', 'resortes', 'Doral Pillow', '150x190', 0, 0, 1, 620000),
('CDOP160', 'Colchón Doral Pillow 160x200', 'colchon', 'resortes', 'Doral Pillow', '160x200', 0, 0, 1, 720000),
('CDOP180', 'Colchón Doral Pillow 180x200', 'colchon', 'resortes', 'Doral Pillow', '180x200', 0, 0, 1, 820000),
('CDOP200', 'Colchón Doral Pillow 200x200', 'colchon', 'resortes', 'Doral Pillow', '200x200', 0, 0, 1, 920000),
('CSUB140', 'Colchón Sublime Europillow 140x190', 'colchon', 'resortes', 'Sublime Europillow', '140x190', 0, 0, 1, 650000),
('CSUB150', 'Colchón Sublime Europillow 150x190', 'colchon', 'resortes', 'Sublime Europillow', '150x190', 0, 0, 1, 690000),
('CSUB160', 'Colchón Sublime Europillow 160x200', 'colchon', 'resortes', 'Sublime Europillow', '160x200', 0, 0, 1, 790000),
('CSUB180', 'Colchón Sublime Europillow 180x200', 'colchon', 'resortes', 'Sublime Europillow', '180x200', 0, 0, 1, 890000),
('CSUB200', 'Colchón Sublime Europillow 200x200', 'colchon', 'resortes', 'Sublime Europillow', '200x200', 0, 0, 1, 990000);

-- ============================================================================
-- BASES
-- ============================================================================

INSERT INTO productos_base (sku, nombre, tipo, stock_actual, stock_minimo_pausar, stock_minimo_reactivar, precio_base, medida) VALUES
('BASE_SAB80', 'Base Sabana 80x190', 'base', 0, 0, 1, 150000, '80x190'),
('BASE_SAB90', 'Base Sabana 90x190', 'base', 0, 0, 1, 160000, '90x190'),
('BASE_SAB100', 'Base Sabana 100x190', 'base', 0, 0, 1, 170000, '100x190'),
('BASE_SAB140', 'Base Sabana 140x190', 'base', 0, 0, 1, 230000, '140x190'),
('BASE_CHOC80', 'Base Chocolate 80x190', 'base', 0, 0, 1, 180000, '80x190'),
('BASE_CHOC90', 'Base Chocolate 90x190', 'base', 0, 0, 1, 190000, '90x190'),
('BASE_CHOC100', 'Base Chocolate 100x190', 'base', 0, 0, 1, 200000, '100x190'),
('BASE_CHOC140', 'Base Chocolate 140x190', 'base', 0, 0, 1, 260000, '140x190'),
('BASE_CHOC150', 'Base Chocolate 150x190', 'base', 0, 0, 1, 280000, '150x190'),
('BASE_CHOC80200', 'Base Chocolate 80x200', 'base', 0, 0, 1, 190000, '80x200'),
('BASE_CHOC90200', 'Base Chocolate 90x200', 'base', 0, 0, 1, 200000, '90x200'),
('BASE_CHOC100200', 'Base Chocolate 100x200', 'base', 0, 0, 1, 210000, '100x200'),
('BASE_GRIS80', 'Base Gris 80x190', 'base', 0, 0, 1, 170000, '80x190'),
('BASE_GRIS90', 'Base Gris 90x190', 'base', 0, 0, 1, 180000, '90x190'),
('BASE_GRIS100', 'Base Gris 100x190', 'base', 0, 0, 1, 190000, '100x190'),
('BASE_GRIS140', 'Base Gris 140x190', 'base', 0, 0, 1, 250000, '140x190'),
('BASE_GRIS150', 'Base Gris 150x190', 'base', 0, 0, 1, 270000, '150x190'),
('BASE_GRIS80200', 'Base Gris 80x200', 'base', 0, 0, 1, 180000, '80x200'),
('BASE_GRIS90200', 'Base Gris 90x200', 'base', 0, 0, 1, 190000, '90x200'),
('BASE_GRIS100200', 'Base Gris 100x200', 'base', 0, 0, 1, 200000, '100x200'),
('BASE_SUBL140', 'Base Sublime 140x190', 'base', 0, 0, 1, 300000, '140x190'),
('BASE_SUBL150', 'Base Sublime 150x190', 'base', 0, 0, 1, 320000, '150x190'),
('BASE_SUBL80200', 'Base Sublime 80x200', 'base', 0, 0, 1, 220000, '80x200'),
('BASE_SUBL90200', 'Base Sublime 90x200', 'base', 0, 0, 1, 230000, '90x200'),
('BASE_SUBL100200', 'Base Sublime 100x200', 'base', 0, 0, 1, 240000, '100x200');

-- ============================================================================
-- ALMOHADAS (8 MODELOS)
-- ============================================================================

INSERT INTO productos_base (sku, nombre, tipo, stock_actual, stock_minimo_pausar, stock_minimo_reactivar, precio_base, modelo_almohada) VALUES
('PLATINO', 'Almohada Platino', 'almohada', 0, 20, 40, 30000, 'Platino'),
('DORAL', 'Almohada Doral', 'almohada', 0, 0, 1, 28000, 'Doral'),
('EXCLUSIVE', 'Almohada Exclusive', 'almohada', 0, 0, 1, 32000, 'Exclusive'),
('CLASICA', 'Almohada Visco Clásica', 'almohada', 0, 0, 1, 25000, 'Visco Clásica'),
('CERVICAL', 'Almohada Visco Cervical', 'almohada', 0, 0, 1, 27000, 'Visco Cervical'),
('SUBLIME', 'Almohada Sublime', 'almohada', 0, 0, 1, 35000, 'Sublime'),
('RENOVATION', 'Almohada Renovation', 'almohada', 0, 0, 1, 29000, 'Renovation'),
('DUAL', 'Almohada Dual Refreshing', 'almohada', 0, 0, 1, 33000, 'Dual Refreshing');

SELECT '✓ Productos base cargados: 91 productos' AS Paso;

-- ============================================================================
-- PRODUCTOS COMPUESTOS (COMBOS)
-- ============================================================================

-- Combos de Almohadas
INSERT INTO productos_compuestos (sku, nombre, precio_base, descripcion) VALUES
('DUALX2', 'Combo 2 Almohadas Dual Refreshing', 66000, '2 almohadas Dual'),
('PLATINOX2', 'Combo 2 Almohadas Platino', 60000, '2 almohadas Platino'),
('PLATINOX4', 'Combo 4 Almohadas Platino', 120000, '4 almohadas Platino'),
('EXCLUSIVEX2', 'Combo 2 Almohadas Exclusive', 64000, '2 almohadas Exclusive'),
('DORALX2', 'Combo 2 Almohadas Doral', 56000, '2 almohadas Doral');

-- Sommiers con 1 almohada
INSERT INTO productos_compuestos (sku, nombre, precio_base, descripcion) VALUES
('SPR9023+1', 'Sommier Princess 23cm 90x190 + 1 Almohada', 540000, 'Colchón + Base + 1 Platino'),
('SPR10023+1', 'Sommier Princess 23cm 100x190 + 1 Almohada', 560000, 'Colchón + Base + 1 Platino'),
('SEX100+1', 'Sommier Exclusive 100x190 + 1 Almohada', 620000, 'Colchón + Base + 1 Platino'),
('SEXP100+1', 'Sommier Exclusive Pillow 100x190 + 1 Almohada', 640000, 'Colchón + Base + 1 Platino');

-- Sommiers con 2 almohadas
INSERT INTO productos_compuestos (sku, nombre, precio_base, descripcion) VALUES
('SDO140+2', 'Sommier Doral 140x190 + 2 Almohadas', 870000, 'Colchón + Base + 2 Platino'),
('SDOP140+2', 'Sommier Doral Pillow 140x190 + 2 Almohadas', 890000, 'Colchón + Base + 2 Platino'),
('SREP140+2', 'Sommier Renovation Europillow 140x190 + 2 Almohadas', 870000, 'Colchón + Base + 2 Platino'),
('SRE140+2', 'Sommier Renovation 140x190 + 2 Almohadas', 850000, 'Colchón + Base + 2 Platino'),
('SEX140+2', 'Sommier Exclusive 140x190 + 2 Almohadas', 830000, 'Colchón + Base + 2 Platino'),
('SEXP140+2', 'Sommier Exclusive Pillow 140x190 + 2 Almohadas', 850000, 'Colchón + Base + 2 Platino');

-- Colchones solos con almohadas
INSERT INTO productos_compuestos (sku, nombre, precio_base, descripcion) VALUES
('CEX140+2', 'Colchón Exclusive 140x190 + 2 Almohadas', 570000, 'Colchón + 2 Platino'),
('CEXP140+2', 'Colchón Exclusive Pillow 140x190 + 2 Almohadas', 590000, 'Colchón + 2 Platino');

SELECT '✓ Productos compuestos creados: 17 combos' AS Paso;

-- ============================================================================
-- COMPONENTES (Relaciones)
-- ============================================================================

-- Combos de almohadas
INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 2 FROM productos_compuestos pc CROSS JOIN productos_base pb 
WHERE pc.sku = 'DUALX2' AND pb.sku = 'DUAL';

INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 2 FROM productos_compuestos pc CROSS JOIN productos_base pb 
WHERE pc.sku = 'PLATINOX2' AND pb.sku = 'PLATINO';

INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 4 FROM productos_compuestos pc CROSS JOIN productos_base pb 
WHERE pc.sku = 'PLATINOX4' AND pb.sku = 'PLATINO';

INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 2 FROM productos_compuestos pc CROSS JOIN productos_base pb 
WHERE pc.sku = 'EXCLUSIVEX2' AND pb.sku = 'EXCLUSIVE';

INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 2 FROM productos_compuestos pc CROSS JOIN productos_base pb 
WHERE pc.sku = 'DORALX2' AND pb.sku = 'DORAL';

-- SPR9023+1
INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 1 FROM productos_compuestos pc CROSS JOIN productos_base pb 
WHERE pc.sku = 'SPR9023+1' AND pb.sku IN ('CPR9023', 'BASE_SAB90', 'PLATINO');

-- SPR10023+1
INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 1 FROM productos_compuestos pc CROSS JOIN productos_base pb 
WHERE pc.sku = 'SPR10023+1' AND pb.sku IN ('CPR10023', 'BASE_SAB100', 'PLATINO');

-- SEX100+1
INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 1 FROM productos_compuestos pc CROSS JOIN productos_base pb 
WHERE pc.sku = 'SEX100+1' AND pb.sku IN ('CEX100', 'BASE_CHOC100', 'PLATINO');

-- SEXP100+1
INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 1 FROM productos_compuestos pc CROSS JOIN productos_base pb 
WHERE pc.sku = 'SEXP100+1' AND pb.sku IN ('CEXP100', 'BASE_CHOC100', 'PLATINO');

-- SDO140+2
INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 1 FROM productos_compuestos pc CROSS JOIN productos_base pb 
WHERE pc.sku = 'SDO140+2' AND pb.sku IN ('CDO140', 'BASE_GRIS140');

INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 2 FROM productos_compuestos pc CROSS JOIN productos_base pb 
WHERE pc.sku = 'SDO140+2' AND pb.sku = 'PLATINO';

-- SDOP140+2
INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 1 FROM productos_compuestos pc CROSS JOIN productos_base pb 
WHERE pc.sku = 'SDOP140+2' AND pb.sku IN ('CDOP140', 'BASE_GRIS140');

INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 2 FROM productos_compuestos pc CROSS JOIN productos_base pb 
WHERE pc.sku = 'SDOP140+2' AND pb.sku = 'PLATINO';

-- SREP140+2
INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 1 FROM productos_compuestos pc CROSS JOIN productos_base pb 
WHERE pc.sku = 'SREP140+2' AND pb.sku IN ('CRENEP140', 'BASE_GRIS140');

INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 2 FROM productos_compuestos pc CROSS JOIN productos_base pb 
WHERE pc.sku = 'SREP140+2' AND pb.sku = 'PLATINO';

-- SRE140+2
INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 1 FROM productos_compuestos pc CROSS JOIN productos_base pb 
WHERE pc.sku = 'SRE140+2' AND pb.sku IN ('CREN140', 'BASE_GRIS140');

INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 2 FROM productos_compuestos pc CROSS JOIN productos_base pb 
WHERE pc.sku = 'SRE140+2' AND pb.sku = 'PLATINO';

-- SEX140+2
INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 1 FROM productos_compuestos pc CROSS JOIN productos_base pb 
WHERE pc.sku = 'SEX140+2' AND pb.sku IN ('CEX140', 'BASE_CHOC140');

INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 2 FROM productos_compuestos pc CROSS JOIN productos_base pb 
WHERE pc.sku = 'SEX140+2' AND pb.sku = 'PLATINO';

-- SEXP140+2
INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 1 FROM productos_compuestos pc CROSS JOIN productos_base pb 
WHERE pc.sku = 'SEXP140+2' AND pb.sku IN ('CEXP140', 'BASE_CHOC140');

INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 2 FROM productos_compuestos pc CROSS JOIN productos_base pb 
WHERE pc.sku = 'SEXP140+2' AND pb.sku = 'PLATINO';

-- CEX140+2
INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 1 FROM productos_compuestos pc CROSS JOIN productos_base pb 
WHERE pc.sku = 'CEX140+2' AND pb.sku = 'CEX140';

INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 2 FROM productos_compuestos pc CROSS JOIN productos_base pb 
WHERE pc.sku = 'CEX140+2' AND pb.sku = 'PLATINO';

-- CEXP140+2
INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 1 FROM productos_compuestos pc CROSS JOIN productos_base pb 
WHERE pc.sku = 'CEXP140+2' AND pb.sku = 'CEXP140';

INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria)
SELECT pc.id, pb.id, 2 FROM productos_compuestos pc CROSS JOIN productos_base pb 
WHERE pc.sku = 'CEXP140+2' AND pb.sku = 'PLATINO';

SELECT '✓ Componentes configurados' AS Paso;

-- ============================================================================
-- PASO 3: CREAR VISTAS
-- ============================================================================

DROP VIEW IF EXISTS ventas_activas;
DROP VIEW IF EXISTS alertas_pendientes;
DROP VIEW IF EXISTS stock_disponible_ml;
DROP VIEW IF EXISTS stock_compuestos;

-- Vista de stock de combos
CREATE VIEW stock_compuestos AS
SELECT 
    pc.id as producto_compuesto_id,
    pc.sku,
    pc.nombre,
    pc.precio_base,
    MIN(FLOOR(pb.stock_actual / c.cantidad_necesaria)) as stock_disponible,
    GROUP_CONCAT(
        CONCAT(pb.sku, ':', pb.stock_actual, '/', c.cantidad_necesaria)
        ORDER BY pb.sku
        SEPARATOR ' | '
    ) as componentes_detalle
FROM productos_compuestos pc
INNER JOIN componentes c ON pc.id = c.producto_compuesto_id
INNER JOIN productos_base pb ON c.producto_base_id = pb.id
WHERE pc.activo = TRUE AND pb.activo = TRUE
GROUP BY pc.id, pc.sku, pc.nombre, pc.precio_base;

-- Vista de stock disponible (productos base + combos)
CREATE VIEW stock_disponible_ml AS
SELECT 
    pb.id,
    pb.sku,
    pb.nombre,
    pb.tipo,
    pb.stock_actual as stock_fisico,
    0 as stock_comprometido,
    pb.stock_actual as stock_disponible,
    pb.stock_minimo_pausar,
    pb.stock_minimo_reactivar,
    'BASE' as tipo_producto,
    CASE 
        WHEN pb.stock_actual <= pb.stock_minimo_pausar THEN 'SIN_STOCK'
        WHEN pb.stock_actual < pb.stock_minimo_reactivar THEN 'STOCK_BAJO'
        ELSE 'DISPONIBLE'
    END as estado_stock
FROM productos_base pb
WHERE pb.activo = TRUE

UNION ALL

SELECT 
    pc.id,
    pc.sku,
    pc.nombre,
    'combo' as tipo,
    NULL as stock_fisico,
    0 as stock_comprometido,
    sc.stock_disponible,
    0 as stock_minimo_pausar,
    1 as stock_minimo_reactivar,
    'COMPUESTO' as tipo_producto,
    CASE 
        WHEN sc.stock_disponible <= 0 THEN 'SIN_STOCK'
        WHEN sc.stock_disponible < 3 THEN 'STOCK_BAJO'
        ELSE 'DISPONIBLE'
    END as estado_stock
FROM productos_compuestos pc
INNER JOIN stock_compuestos sc ON pc.id = sc.producto_compuesto_id
WHERE pc.activo = TRUE;

-- Vista de alertas
CREATE VIEW alertas_pendientes AS
SELECT 
    a.id,
    a.sku,
    a.tipo_alerta,
    a.estado,
    a.fecha_creacion,
    a.fecha_procesada,
    a.mlas_afectados,
    sd.nombre,
    sd.stock_disponible,
    sd.tipo_producto
FROM alertas_stock a
LEFT JOIN stock_disponible_ml sd ON a.sku = sd.sku
WHERE a.estado = 'pendiente'
ORDER BY a.fecha_creacion DESC;

-- Vista de ventas activas
CREATE VIEW ventas_activas AS
SELECT 
    v.id,
    v.numero_venta,
    v.canal,
    v.nombre_cliente,
    v.telefono_cliente,
    v.importe_total,
    v.importe_abonado,
    v.metodo_pago,
    v.tipo_entrega,
    v.estado_pago,
    v.estado_entrega,
    v.fecha_venta,
    v.fecha_entrega_estimada,
    (SELECT COUNT(*) FROM items_venta iv WHERE iv.venta_id = v.id) as cantidad_items,
    (SELECT GROUP_CONCAT(CONCAT(iv.cantidad, 'x ', iv.sku) SEPARATOR ', ')
     FROM items_venta iv 
     WHERE iv.venta_id = v.id) as productos
FROM ventas v
WHERE v.estado_entrega = 'pendiente'
ORDER BY v.fecha_venta DESC;

SELECT '✓ Vistas creadas' AS Paso;

-- ============================================================================
-- RESUMEN FINAL
-- ============================================================================

SELECT '==================== INSTALACIÓN COMPLETADA ====================' AS '';

SELECT tipo, COUNT(*) as cantidad
FROM productos_base 
GROUP BY tipo;

SELECT '---' AS '', COUNT(*) as 'Combos' FROM productos_compuestos;

SELECT '=================================================================' AS '';
SELECT '✅ SISTEMA LISTO PARA USAR' AS '';
SELECT 'Ejecutar 04_VERIFICAR_INSTALACION.sql para confirmar' AS '';
