-- ============================================================
-- AGREGAR CAMPO PARA TRACKEAR QUÉ TIPO DE PUBLICACIONES SE PROCESÓ
-- ============================================================

ALTER TABLE alertas_stock 
ADD COLUMN tipo_procesado VARCHAR(20) DEFAULT NULL 
COMMENT 'normal, z, ambos - indica qué variante fue procesada';

-- Verificar
DESCRIBE alertas_stock;

-- ============================================================
-- VALORES POSIBLES:
-- NULL = nada procesado aún
-- 'normal' = solo publicaciones normales procesadas
-- 'z' = solo publicaciones con Z procesadas  
-- 'ambos' = ambas procesadas (se marca estado='procesada')
-- ============================================================
