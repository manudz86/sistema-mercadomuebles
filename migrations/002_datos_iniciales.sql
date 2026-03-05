-- ============================================================================
-- DATOS INICIALES - COEFICIENTES Y PRODUCTOS BASE
-- ============================================================================

-- ============================================================================
-- COEFICIENTES DE FINANCIACIÓN
-- ============================================================================

INSERT INTO coeficientes_financiacion (nombre, cuotas, coeficiente, comision_ml_porcentaje, fecha_desde, activo) VALUES
('1 pago', 1, 1.0000, 13.00, '2025-02-01', TRUE),
('Cuota simple', 1, 1.0900, 15.00, '2025-02-01', TRUE),
('3 cuotas', 3, 1.2000, 20.00, '2025-02-01', TRUE),
('6 cuotas', 6, 1.3500, 25.00, '2025-02-01', TRUE),
('9 cuotas', 9, 1.5500, 30.00, '2025-02-01', TRUE),
('12 cuotas', 12, 1.6800, 35.00, '2025-02-01', TRUE);

-- ============================================================================
-- BASES
-- ============================================================================

-- BASES SABANA (para Princess 20cm y Soñar, hasta 140x190)
INSERT INTO productos_base (sku, nombre, tipo, tipo_base, medida, stock_actual, precio_base, activo) VALUES
('BASE_SABANA_80', 'Base Sabana 80x190', 'base', 'sabana', '80x190', 8, 0, TRUE),
('BASE_SABANA_90', 'Base Sabana 90x190', 'base', 'sabana', '90x190', 0, 0, TRUE),
('BASE_SABANA_100', 'Base Sabana 100x190', 'base', 'sabana', '100x190', 0, 0, TRUE),
('BASE_SABANA_140', 'Base Sabana 140x190', 'base', 'sabana', '140x190', 0, 0, TRUE);

-- BASES GRIS (para Doral, Doral Pillow, Princess 23, Renovation, Renovation Europillow)
INSERT INTO productos_base (sku, nombre, tipo, tipo_base, medida, stock_actual, precio_base, activo) VALUES
('BASE_GRIS_80', 'Base Gris 80x190', 'base', 'gris', '80x190', 0, 0, TRUE),
('BASE_GRIS_90', 'Base Gris 90x190', 'base', 'gris', '90x190', 0, 0, TRUE),
('BASE_GRIS_100', 'Base Gris 100x190', 'base', 'gris', '100x190', 12, 0, TRUE),
('BASE_GRIS_140', 'Base Gris 140x190', 'base', 'gris', '140x190', 12, 0, TRUE),
('BASE_GRIS_150', 'Base Gris 150x190', 'base', 'gris', '150x190', 0, 0, TRUE),
('BASE_GRIS_80_200', 'Base Gris 80x200', 'base', 'gris', '80x200', 0, 0, TRUE),
('BASE_GRIS_90_200', 'Base Gris 90x200', 'base', 'gris', '90x200', 0, 0, TRUE),
('BASE_GRIS_100_200', 'Base Gris 100x200', 'base', 'gris', '100x200', 0, 0, TRUE);

-- BASES CHOCOLATE (para Exclusive y Exclusive Pillow)
INSERT INTO productos_base (sku, nombre, tipo, tipo_base, medida, stock_actual, precio_base, activo) VALUES
('BASE_CHOCOLATE_80', 'Base Chocolate 80x190', 'base', 'chocolate', '80x190', 0, 0, TRUE),
('BASE_CHOCOLATE_90', 'Base Chocolate 90x190', 'base', 'chocolate', '90x190', 0, 0, TRUE),
('BASE_CHOCOLATE_100', 'Base Chocolate 100x190', 'base', 'chocolate', '100x190', 0, 0, TRUE),
('BASE_CHOCOLATE_140', 'Base Chocolate 140x190', 'base', 'chocolate', '140x190', 2, 0, TRUE),
('BASE_CHOCOLATE_150', 'Base Chocolate 150x190', 'base', 'chocolate', '150x190', 0, 0, TRUE),
('BASE_CHOCOLATE_80_200', 'Base Chocolate 80x200', 'base', 'chocolate', '80x200', 0, 0, TRUE),
('BASE_CHOCOLATE_90_200', 'Base Chocolate 90x200', 'base', 'chocolate', '90x200', 0, 0, TRUE),
('BASE_CHOCOLATE_100_200', 'Base Chocolate 100x200', 'base', 'chocolate', '100x200', 0, 0, TRUE);

-- BASES SUBLIME (para Sublime Europillow, desde 140x190)
INSERT INTO productos_base (sku, nombre, tipo, tipo_base, medida, stock_actual, precio_base, activo) VALUES
('BASE_SUBLIME_140', 'Base Sublime 140x190', 'base', 'sublime', '140x190', 0, 0, TRUE),
('BASE_SUBLIME_150', 'Base Sublime 150x190', 'base', 'sublime', '150x190', 0, 0, TRUE),
('BASE_SUBLIME_80_200', 'Base Sublime 80x200', 'base', 'sublime', '80x200', 0, 0, TRUE),
('BASE_SUBLIME_90_200', 'Base Sublime 90x200', 'base', 'sublime', '90x200', 0, 0, TRUE),
('BASE_SUBLIME_100_200', 'Base Sublime 100x200', 'base', 'sublime', '100x200', 0, 0, TRUE);

-- ============================================================================
-- COLCHONES - LÍNEA ESPUMA
-- ============================================================================

-- TROPICAL (solo colchón, 80, 90, 100)
INSERT INTO productos_base (sku, nombre, tipo, linea, modelo, medida, stock_actual, precio_base, activo) VALUES
('CTR80', 'Colchón Tropical 80x190', 'colchon', 'espuma', 'Tropical', '80x190', 0, 0, TRUE),
('CTR90', 'Colchón Tropical 90x190', 'colchon', 'espuma', 'Tropical', '90x190', 0, 0, TRUE),
('CTR100', 'Colchón Tropical 100x190', 'colchon', 'espuma', 'Tropical', '100x190', 0, 0, TRUE);

-- PRINCESS 20CM (80, 90, 100, 140)
INSERT INTO productos_base (sku, nombre, tipo, linea, modelo, medida, stock_actual, precio_base, activo) VALUES
('CPR8020', 'Colchón Princess 20cm 80x190', 'colchon', 'espuma', 'Princess 20cm', '80x190', 6, 0, TRUE),
('CPR9020', 'Colchón Princess 20cm 90x190', 'colchon', 'espuma', 'Princess 20cm', '90x190', 0, 0, TRUE),
('CPR10020', 'Colchón Princess 20cm 100x190', 'colchon', 'espuma', 'Princess 20cm', '100x190', 0, 0, TRUE),
('CPR14020', 'Colchón Princess 20cm 140x190', 'colchon', 'espuma', 'Princess 20cm', '140x190', 0, 0, TRUE);

-- PRINCESS 23CM (80, 90, 100, 140, 150, 160, 180, 200)
INSERT INTO productos_base (sku, nombre, tipo, linea, modelo, medida, stock_actual, precio_base, activo) VALUES
('CPR8023', 'Colchón Princess 23cm 80x190', 'colchon', 'espuma', 'Princess 23cm', '80x190', 0, 0, TRUE),
('CPR9023', 'Colchón Princess 23cm 90x190', 'colchon', 'espuma', 'Princess 23cm', '90x190', 0, 0, TRUE),
('CPR10023', 'Colchón Princess 23cm 100x190', 'colchon', 'espuma', 'Princess 23cm', '100x190', 5, 0, TRUE),
('CPR14023', 'Colchón Princess 23cm 140x190', 'colchon', 'espuma', 'Princess 23cm', '140x190', 0, 0, TRUE),
('CPR15023', 'Colchón Princess 23cm 150x190', 'colchon', 'espuma', 'Princess 23cm', '150x190', 0, 0, TRUE),
('CPR16023', 'Colchón Princess 23cm 160x200', 'colchon', 'espuma', 'Princess 23cm', '160x200', 0, 0, TRUE),
('CPR18023', 'Colchón Princess 23cm 180x200', 'colchon', 'espuma', 'Princess 23cm', '180x200', 0, 0, TRUE),
('CPR20023', 'Colchón Princess 23cm 200x200', 'colchon', 'espuma', 'Princess 23cm', '200x200', 0, 0, TRUE);

-- EXCLUSIVE (todas las medidas excepto 100x200)
INSERT INTO productos_base (sku, nombre, tipo, linea, modelo, medida, stock_actual, precio_base, activo) VALUES
('CEXC80', 'Colchón Exclusive 80x190', 'colchon', 'espuma', 'Exclusive', '80x190', 0, 0, TRUE),
('CEXC90', 'Colchón Exclusive 90x190', 'colchon', 'espuma', 'Exclusive', '90x190', 0, 0, TRUE),
('CEXC100', 'Colchón Exclusive 100x190', 'colchon', 'espuma', 'Exclusive', '100x190', 0, 0, TRUE),
('CEXC140', 'Colchón Exclusive 140x190', 'colchon', 'espuma', 'Exclusive', '140x190', 2, 0, TRUE),
('CEXC150', 'Colchón Exclusive 150x190', 'colchon', 'espuma', 'Exclusive', '150x190', 0, 0, TRUE),
('CEXC160', 'Colchón Exclusive 160x200', 'colchon', 'espuma', 'Exclusive', '160x200', 0, 0, TRUE),
('CEXC180', 'Colchón Exclusive 180x200', 'colchon', 'espuma', 'Exclusive', '180x200', 0, 0, TRUE),
('CEXC200', 'Colchón Exclusive 200x200', 'colchon', 'espuma', 'Exclusive', '200x200', 0, 0, TRUE);

-- EXCLUSIVE CON PILLOW (todas las medidas excepto 100x200)
INSERT INTO productos_base (sku, nombre, tipo, linea, modelo, medida, stock_actual, precio_base, activo) VALUES
('CEXCP80', 'Colchón Exclusive con Pillow 80x190', 'colchon', 'espuma', 'Exclusive Pillow', '80x190', 0, 0, TRUE),
('CEXCP90', 'Colchón Exclusive con Pillow 90x190', 'colchon', 'espuma', 'Exclusive Pillow', '90x190', 0, 0, TRUE),
('CEXCP100', 'Colchón Exclusive con Pillow 100x190', 'colchon', 'espuma', 'Exclusive Pillow', '100x190', 0, 0, TRUE),
('CEXCP140', 'Colchón Exclusive con Pillow 140x190', 'colchon', 'espuma', 'Exclusive Pillow', '140x190', 0, 0, TRUE),
('CEXCP150', 'Colchón Exclusive con Pillow 150x190', 'colchon', 'espuma', 'Exclusive Pillow', '150x190', 0, 0, TRUE),
('CEXCP160', 'Colchón Exclusive con Pillow 160x200', 'colchon', 'espuma', 'Exclusive Pillow', '160x200', 0, 0, TRUE),
('CEXCP180', 'Colchón Exclusive con Pillow 180x200', 'colchon', 'espuma', 'Exclusive Pillow', '180x200', 0, 0, TRUE),
('CEXCP200', 'Colchón Exclusive con Pillow 200x200', 'colchon', 'espuma', 'Exclusive Pillow', '200x200', 0, 0, TRUE);

-- RENOVATION (todas las medidas excepto 100x200)
INSERT INTO productos_base (sku, nombre, tipo, linea, modelo, medida, stock_actual, precio_base, activo) VALUES
('CREN80', 'Colchón Renovation 80x190', 'colchon', 'espuma', 'Renovation', '80x190', 0, 0, TRUE),
('CREN90', 'Colchón Renovation 90x190', 'colchon', 'espuma', 'Renovation', '90x190', 0, 0, TRUE),
('CREN100', 'Colchón Renovation 100x190', 'colchon', 'espuma', 'Renovation', '100x190', 0, 0, TRUE),
('CREN140', 'Colchón Renovation 140x190', 'colchon', 'espuma', 'Renovation', '140x190', 0, 0, TRUE),
('CREN150', 'Colchón Renovation 150x190', 'colchon', 'espuma', 'Renovation', '150x190', 0, 0, TRUE),
('CREN160', 'Colchón Renovation 160x200', 'colchon', 'espuma', 'Renovation', '160x200', 0, 0, TRUE),
('CREN180', 'Colchón Renovation 180x200', 'colchon', 'espuma', 'Renovation', '180x200', 0, 0, TRUE),
('CREN200', 'Colchón Renovation 200x200', 'colchon', 'espuma', 'Renovation', '200x200', 0, 0, TRUE);

-- RENOVATION EUROPILLOW (todas las medidas excepto 100x200)
INSERT INTO productos_base (sku, nombre, tipo, linea, modelo, medida, stock_actual, precio_base, activo) VALUES
('CRENEP80', 'Colchón Renovation Europillow 80x190', 'colchon', 'espuma', 'Renovation Europillow', '80x190', 0, 0, TRUE),
('CRENEP90', 'Colchón Renovation Europillow 90x190', 'colchon', 'espuma', 'Renovation Europillow', '90x190', 0, 0, TRUE),
('CRENEP100', 'Colchón Renovation Europillow 100x190', 'colchon', 'espuma', 'Renovation Europillow', '100x190', 0, 0, TRUE),
('CRENEP140', 'Colchón Renovation Europillow 140x190', 'colchon', 'espuma', 'Renovation Europillow', '140x190', 0, 0, TRUE),
('CRENEP150', 'Colchón Renovation Europillow 150x190', 'colchon', 'espuma', 'Renovation Europillow', '150x190', 0, 0, TRUE),
('CRENEP160', 'Colchón Renovation Europillow 160x200', 'colchon', 'espuma', 'Renovation Europillow', '160x200', 0, 0, TRUE),
('CRENEP180', 'Colchón Renovation Europillow 180x200', 'colchon', 'espuma', 'Renovation Europillow', '180x200', 0, 0, TRUE),
('CRENEP200', 'Colchón Renovation Europillow 200x200', 'colchon', 'espuma', 'Renovation Europillow', '200x200', 0, 0, TRUE);

-- ============================================================================
-- COLCHONES - LÍNEA RESORTES
-- ============================================================================

-- SOÑAR (80, 90, 100, 140)
INSERT INTO productos_base (sku, nombre, tipo, linea, modelo, medida, stock_actual, precio_base, activo) VALUES
('CSON80', 'Colchón Soñar 80x190', 'colchon', 'resortes', 'Soñar', '80x190', 0, 0, TRUE),
('CSON90', 'Colchón Soñar 90x190', 'colchon', 'resortes', 'Soñar', '90x190', 0, 0, TRUE),
('CSON100', 'Colchón Soñar 100x190', 'colchon', 'resortes', 'Soñar', '100x190', 0, 0, TRUE),
('CSON140', 'Colchón Soñar 140x190', 'colchon', 'resortes', 'Soñar', '140x190', 0, 0, TRUE);

-- DORAL (todas las medidas)
INSERT INTO productos_base (sku, nombre, tipo, linea, modelo, medida, stock_actual, precio_base, activo) VALUES
('CDO80', 'Colchón Doral 80x190', 'colchon', 'resortes', 'Doral', '80x190', 5, 0, TRUE),
('CDO90', 'Colchón Doral 90x190', 'colchon', 'resortes', 'Doral', '90x190', 0, 0, TRUE),
('CDO100', 'Colchón Doral 100x190', 'colchon', 'resortes', 'Doral', '100x190', 2, 0, TRUE),
('CDO140', 'Colchón Doral 140x190', 'colchon', 'resortes', 'Doral', '140x190', 3, 0, TRUE),
('CDO150', 'Colchón Doral 150x190', 'colchon', 'resortes', 'Doral', '150x190', 0, 0, TRUE),
('CDO160', 'Colchón Doral 160x200', 'colchon', 'resortes', 'Doral', '160x200', 0, 0, TRUE),
('CDO180', 'Colchón Doral 180x200', 'colchon', 'resortes', 'Doral', '180x200', 0, 0, TRUE),
('CDO200', 'Colchón Doral 200x200', 'colchon', 'resortes', 'Doral', '200x200', 0, 0, TRUE);

-- DORAL CON PILLOW (desde 140)
INSERT INTO productos_base (sku, nombre, tipo, linea, modelo, medida, stock_actual, precio_base, activo) VALUES
('CDOP140', 'Colchón Doral con Pillow 140x190', 'colchon', 'resortes', 'Doral Pillow', '140x190', 0, 0, TRUE),
('CDOP150', 'Colchón Doral con Pillow 150x190', 'colchon', 'resortes', 'Doral Pillow', '150x190', 0, 0, TRUE),
('CDOP160', 'Colchón Doral con Pillow 160x200', 'colchon', 'resortes', 'Doral Pillow', '160x200', 0, 0, TRUE),
('CDOP180', 'Colchón Doral con Pillow 180x200', 'colchon', 'resortes', 'Doral Pillow', '180x200', 0, 0, TRUE),
('CDOP200', 'Colchón Doral con Pillow 200x200', 'colchon', 'resortes', 'Doral Pillow', '200x200', 0, 0, TRUE);

-- SUBLIME EUROPILLOW (desde 140)
INSERT INTO productos_base (sku, nombre, tipo, linea, modelo, medida, stock_actual, precio_base, activo) VALUES
('CSUB140', 'Colchón Sublime Europillow 140x190', 'colchon', 'resortes', 'Sublime Europillow', '140x190', 0, 0, TRUE),
('CSUB150', 'Colchón Sublime Europillow 150x190', 'colchon', 'resortes', 'Sublime Europillow', '150x190', 0, 0, TRUE),
('CSUB160', 'Colchón Sublime Europillow 160x200', 'colchon', 'resortes', 'Sublime Europillow', '160x200', 0, 0, TRUE),
('CSUB180', 'Colchón Sublime Europillow 180x200', 'colchon', 'resortes', 'Sublime Europillow', '180x200', 0, 0, TRUE),
('CSUB200', 'Colchón Sublime Europillow 200x200', 'colchon', 'resortes', 'Sublime Europillow', '200x200', 0, 0, TRUE);

-- ============================================================================
-- COLCHONES - LÍNEA BOX (EN CAJA)
-- ============================================================================

-- COMPAC (80, 100x200, 140, 160)
INSERT INTO productos_base (sku, nombre, tipo, linea, modelo, medida, stock_actual, precio_base, activo) VALUES
('CCOMP80', 'Colchón Compac 80x190', 'colchon', 'box', 'Compac', '80x190', 0, 0, TRUE),
('CCOMP100X200', 'Colchón Compac 100x200', 'colchon', 'box', 'Compac', '100x200', 0, 0, TRUE),
('CCOMP140', 'Colchón Compac 140x190', 'colchon', 'box', 'Compac', '140x190', 0, 0, TRUE),
('CCOMP160', 'Colchón Compac 160x200', 'colchon', 'box', 'Compac', '160x200', 0, 0, TRUE);

-- COMPAC PLUS POCKET (80, 100x200, 140, 160)
INSERT INTO productos_base (sku, nombre, tipo, linea, modelo, medida, stock_actual, precio_base, activo) VALUES
('CCOMPP80', 'Colchón Compac Plus Pocket 80x190', 'colchon', 'box', 'Compac Plus Pocket', '80x190', 0, 0, TRUE),
('CCOMPP100X200', 'Colchón Compac Plus Pocket 100x200', 'colchon', 'box', 'Compac Plus Pocket', '100x200', 0, 0, TRUE),
('CCOMPP140', 'Colchón Compac Plus Pocket 140x190', 'colchon', 'box', 'Compac Plus Pocket', '140x190', 0, 0, TRUE),
('CCOMPP160', 'Colchón Compac Plus Pocket 160x200', 'colchon', 'box', 'Compac Plus Pocket', '160x200', 0, 0, TRUE);

-- ============================================================================
-- ALMOHADAS
-- ============================================================================

INSERT INTO productos_base (sku, nombre, tipo, modelo_almohada, stock_actual, stock_minimo_pausar, stock_minimo_reactivar, precio_base, activo) VALUES
('ALMP', 'Almohada Platino', 'almohada', 'Platino', 0, 20, 40, 0, TRUE),
('ALMD', 'Almohada Doral', 'almohada', 'Doral', 0, 0, 1, 0, TRUE),
('ALME', 'Almohada Exclusive', 'almohada', 'Exclusive', 0, 0, 1, 0, TRUE),
('ALMVC', 'Almohada Visco Clásica', 'almohada', 'Visco Clásica', 0, 0, 1, 0, TRUE),
('ALMVCV', 'Almohada Visco Cervical', 'almohada', 'Visco Cervical', 0, 0, 1, 0, TRUE),
('ALMS', 'Almohada Sublime', 'almohada', 'Sublime', 0, 0, 1, 0, TRUE),
('ALMR', 'Almohada Renovation', 'almohada', 'Renovation', 0, 0, 1, 0, TRUE),
('ALMDUAL', 'Almohada Dual', 'almohada', 'Dual', 0, 0, 1, 0, TRUE);
