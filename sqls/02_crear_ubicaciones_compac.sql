-- ============================================
-- SISTEMA DE UBICACIONES PARA COMPAC
-- ============================================

-- PASO 1: Verificar los SKUs actuales de Compac
SELECT sku, nombre, stock_actual 
FROM productos_base 
WHERE sku LIKE 'CCO%' OR sku LIKE 'CCP%'
ORDER BY sku;

-- ============================================
-- PASO 2: Crear SKUs separados por ubicación
-- ============================================

-- COMPAC - Separar en DEP y FULL
-- Asumiendo que el stock actual está todo en depósito

-- Compac 80
UPDATE productos_base SET sku = 'CCO80_DEP', nombre = 'Colchón Compac 80x190 (Depósito)' WHERE sku = 'CCO80';
INSERT INTO productos_base (sku, nombre, tipo, stock_actual, stock_minimo_pausar)
VALUES ('CCO80_FULL', 'Colchón Compac 80x190 (Full ML)', 'colchon', 0, 0);

-- Compac 100
UPDATE productos_base SET sku = 'CCO100_DEP', nombre = 'Colchón Compac 100x200 (Depósito)' WHERE sku = 'CCO100';
INSERT INTO productos_base (sku, nombre, tipo, stock_actual, stock_minimo_pausar)
VALUES ('CCO100_FULL', 'Colchón Compac 100x200 (Full ML)', 'colchon', 0, 0);

-- Compac 140
UPDATE productos_base SET sku = 'CCO140_DEP', nombre = 'Colchón Compac 140x190 (Depósito)' WHERE sku = 'CCO140';
INSERT INTO productos_base (sku, nombre, tipo, stock_actual, stock_minimo_pausar)
VALUES ('CCO140_FULL', 'Colchón Compac 140x190 (Full ML)', 'colchon', 0, 0);

-- Compac 160
UPDATE productos_base SET sku = 'CCO160_DEP', nombre = 'Colchón Compac 160x200 (Depósito)' WHERE sku = 'CCO160';
INSERT INTO productos_base (sku, nombre, tipo, stock_actual, stock_minimo_pausar)
VALUES ('CCO160_FULL', 'Colchón Compac 160x200 (Full ML)', 'colchon', 0, 0);

-- ============================================
-- COMPAC PLUS POCKET - Separar en DEP y FULL
-- ============================================

-- Compac Plus 80
UPDATE productos_base SET sku = 'CCP80_DEP', nombre = 'Colchón Compac Plus Pocket 80x190 (Depósito)' WHERE sku = 'CCP80';
INSERT INTO productos_base (sku, nombre, tipo, stock_actual, stock_minimo_pausar)
VALUES ('CCP80_FULL', 'Colchón Compac Plus Pocket 80x190 (Full ML)', 'colchon', 0, 0);

-- Compac Plus 100
UPDATE productos_base SET sku = 'CCP100_DEP', nombre = 'Colchón Compac Plus Pocket 100x200 (Depósito)' WHERE sku = 'CCP100';
INSERT INTO productos_base (sku, nombre, tipo, stock_actual, stock_minimo_pausar)
VALUES ('CCP100_FULL', 'Colchón Compac Plus Pocket 100x200 (Full ML)', 'colchon', 0, 0);

-- Compac Plus 140
UPDATE productos_base SET sku = 'CCP140_DEP', nombre = 'Colchón Compac Plus Pocket 140x190 (Depósito)' WHERE sku = 'CCP140';
INSERT INTO productos_base (sku, nombre, tipo, stock_actual, stock_minimo_pausar)
VALUES ('CCP140_FULL', 'Colchón Compac Plus Pocket 140x190 (Full ML)', 'colchon', 0, 0);

-- Compac Plus 160
UPDATE productos_base SET sku = 'CCP160_DEP', nombre = 'Colchón Compac Plus Pocket 160x200 (Depósito)' WHERE sku = 'CCP160';
INSERT INTO productos_base (sku, nombre, tipo, stock_actual, stock_minimo_pausar)
VALUES ('CCP160_FULL', 'Colchón Compac Plus Pocket 160x200 (Full ML)', 'colchon', 0, 0);

-- ============================================
-- PASO 3: Verificar que se crearon correctamente
-- ============================================

SELECT sku, nombre, stock_actual 
FROM productos_base 
WHERE sku LIKE 'CCO%' OR sku LIKE 'CCP%'
ORDER BY sku;

-- Deberías ver:
-- CCO80_DEP, CCO80_FULL
-- CCO100_DEP, CCO100_FULL
-- CCO140_DEP, CCO140_FULL
-- CCO160_DEP, CCO160_FULL
-- CCP80_DEP, CCP80_FULL
-- CCP100_DEP, CCP100_FULL
-- CCP140_DEP, CCP140_FULL
-- CCP160_DEP, CCP160_FULL

-- ============================================
-- NOTAS IMPORTANTES:
-- ============================================

-- 1. El stock actual de CCO80, CCO100, etc se mantiene
--    y pasa a CCO80_DEP, CCO100_DEP, etc.

-- 2. Los SKUs _FULL empiezan en 0

-- 3. En cargar_stock ahora verás ambas opciones:
--    - CCO80_DEP (para cargar en depósito)
--    - CCO80_FULL (para cargar directo en Full)

-- 4. Se creará página de transferencia para mover stock
--    de _DEP a _FULL

-- ============================================
-- ROLLBACK (si algo sale mal):
-- ============================================

-- Para volver atrás:
-- UPDATE productos_base SET sku = 'CCO80', nombre = 'Colchón Compac 80x190' WHERE sku = 'CCO80_DEP';
-- DELETE FROM productos_base WHERE sku LIKE '%_FULL';
