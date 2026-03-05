-- ============================================================================
-- CORREGIR SKUs DE COMPAC
-- ============================================================================

USE inventario_cannon;
SET SQL_SAFE_UPDATES = 0;

-- Compac
UPDATE productos_base SET sku = 'CCO80' WHERE sku = 'CCOMP80';
UPDATE productos_base SET sku = 'CCO100' WHERE sku = 'CCOMP100200';
UPDATE productos_base SET sku = 'CCO140' WHERE sku = 'CCOMP140';
UPDATE productos_base SET sku = 'CCO160' WHERE sku = 'CCOMP160';

-- Compac Plus Pocket
UPDATE productos_base SET sku = 'CCP80' WHERE sku = 'CCOMPP80';
UPDATE productos_base SET sku = 'CCP100' WHERE sku = 'CCOMPP100200';
UPDATE productos_base SET sku = 'CCP140' WHERE sku = 'CCOMPP140';
UPDATE productos_base SET sku = 'CCP160' WHERE sku = 'CCOMPP160';

SET SQL_SAFE_UPDATES = 1;

SELECT '✅ SKUs de Compac corregidos' AS Resultado;
