-- ============================================================================
-- PARTE 1: CORREGIR SKUs DE COLCHONES
-- Ejecutar primero este script
-- ============================================================================

USE inventario_cannon;
SET SQL_SAFE_UPDATES = 0;

-- Renovation: CREN → CRE
UPDATE productos_base SET sku = 'CRE80' WHERE sku = 'CREN80';
UPDATE productos_base SET sku = 'CRE90' WHERE sku = 'CREN90';
UPDATE productos_base SET sku = 'CRE100' WHERE sku = 'CREN100';
UPDATE productos_base SET sku = 'CRE140' WHERE sku = 'CREN140';
UPDATE productos_base SET sku = 'CRE150' WHERE sku = 'CREN150';
UPDATE productos_base SET sku = 'CRE160' WHERE sku = 'CREN160';
UPDATE productos_base SET sku = 'CRE180' WHERE sku = 'CREN180';
UPDATE productos_base SET sku = 'CRE200' WHERE sku = 'CREN200';

-- Renovation Europillow: CRENEP → CREP
UPDATE productos_base SET sku = 'CREP80' WHERE sku = 'CRENEP80';
UPDATE productos_base SET sku = 'CREP90' WHERE sku = 'CRENEP90';
UPDATE productos_base SET sku = 'CREP100' WHERE sku = 'CRENEP100';
UPDATE productos_base SET sku = 'CREP140' WHERE sku = 'CRENEP140';
UPDATE productos_base SET sku = 'CREP150' WHERE sku = 'CRENEP150';
UPDATE productos_base SET sku = 'CREP160' WHERE sku = 'CRENEP160';
UPDATE productos_base SET sku = 'CREP180' WHERE sku = 'CRENEP180';
UPDATE productos_base SET sku = 'CREP200' WHERE sku = 'CRENEP200';

-- Soñar: CSON → CSO
UPDATE productos_base SET sku = 'CSO80' WHERE sku = 'CSON80';
UPDATE productos_base SET sku = 'CSO90' WHERE sku = 'CSON90';
UPDATE productos_base SET sku = 'CSO100' WHERE sku = 'CSON100';
UPDATE productos_base SET sku = 'CSO140' WHERE sku = 'CSON140';

-- Sublime: CSUB → CSUP
UPDATE productos_base SET sku = 'CSUP140' WHERE sku = 'CSUB140';
UPDATE productos_base SET sku = 'CSUP150' WHERE sku = 'CSUB150';
UPDATE productos_base SET sku = 'CSUP160' WHERE sku = 'CSUB160';
UPDATE productos_base SET sku = 'CSUP180' WHERE sku = 'CSUB180';
UPDATE productos_base SET sku = 'CSUP200' WHERE sku = 'CSUB200';

SET SQL_SAFE_UPDATES = 1;

SELECT '✅ SKUs corregidos' AS Resultado;
SELECT '⏭️  Ahora ejecutar PARTE 2' AS 'Siguiente Paso';
