-- ============================================================================
-- AGREGAR PRODUCTOS COMPAC Y COMPAC PLUS EN FULL (DEPÓSITO ML)
-- ============================================================================

USE inventario_cannon;

-- Compac Full (depósito ML)
INSERT INTO productos_base (sku, nombre, tipo, stock_actual, stock_minimo_pausar, stock_minimo_reactivar, precio_base)
VALUES
('CCO80_FULL', 'Compac 80x190 (Full ML)', 'colchon', 0, 2, 5, 150000),
('CCO100_FULL', 'Compac 100x200 (Full ML)', 'colchon', 0, 2, 5, 180000),
('CCO140_FULL', 'Compac 140x190 (Full ML)', 'colchon', 0, 2, 5, 220000),
('CCO160_FULL', 'Compac 160x200 (Full ML)', 'colchon', 0, 2, 5, 250000);

-- Compac Plus Pocket Full (depósito ML)
INSERT INTO productos_base (sku, nombre, tipo, stock_actual, stock_minimo_pausar, stock_minimo_reactivar, precio_base)
VALUES
('CCP80_FULL', 'Compac Plus Pocket 80x190 (Full ML)', 'colchon', 0, 2, 5, 170000),
('CCP100_FULL', 'Compac Plus Pocket 100x200 (Full ML)', 'colchon', 0, 2, 5, 200000),
('CCP140_FULL', 'Compac Plus Pocket 140x190 (Full ML)', 'colchon', 0, 2, 5, 240000),
('CCP160_FULL', 'Compac Plus Pocket 160x200 (Full ML)', 'colchon', 0, 2, 5, 270000);

-- Verificar que se agregaron
SELECT sku, nombre, stock_actual 
FROM productos_base 
WHERE sku LIKE '%_FULL'
ORDER BY sku;

-- Resultado esperado: 8 productos (4 Compac Full + 4 Compac Plus Full)
