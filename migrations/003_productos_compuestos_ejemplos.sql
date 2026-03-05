-- ============================================================================
-- PRODUCTOS COMPUESTOS - EJEMPLOS DE CONJUNTOS
-- ============================================================================

-- Este archivo contiene ejemplos de cómo se crean los productos compuestos.
-- En la interfaz web podrás crear más conjuntos fácilmente.

-- ============================================================================
-- CONJUNTOS SIMPLES (Colchón + Base/s)
-- ============================================================================

-- Ejemplo 1: Conjunto Princess 20cm 80x190 (colchón + base sabana)
INSERT INTO productos_compuestos (sku, nombre, tipo_compuesto, precio_base, activo) VALUES
('SPR8020', 'Conjunto Princess 20cm 80x190', 'conjunto_simple', 0, TRUE);

-- Obtener IDs para relacionar componentes
SET @conjunto_spr8020_id = LAST_INSERT_ID();
SET @colchon_pr8020_id = (SELECT id FROM productos_base WHERE sku = 'CPR8020');
SET @base_sabana80_id = (SELECT id FROM productos_base WHERE sku = 'BASE_SABANA_80');

INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria) VALUES
(@conjunto_spr8020_id, @colchon_pr8020_id, 1),
(@conjunto_spr8020_id, @base_sabana80_id, 1);

-- Ejemplo 2: Conjunto Doral 140x190 (colchón + base gris)
INSERT INTO productos_compuestos (sku, nombre, tipo_compuesto, precio_base, activo) VALUES
('SDO140', 'Conjunto Doral 140x190', 'conjunto_simple', 0, TRUE);

SET @conjunto_sdo140_id = LAST_INSERT_ID();
SET @colchon_do140_id = (SELECT id FROM productos_base WHERE sku = 'CDO140');
SET @base_gris140_id = (SELECT id FROM productos_base WHERE sku = 'BASE_GRIS_140');

INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria) VALUES
(@conjunto_sdo140_id, @colchon_do140_id, 1),
(@conjunto_sdo140_id, @base_gris140_id, 1);

-- Ejemplo 3: Conjunto Exclusive Pillow 160x200 (colchón + 2 bases chocolate 80x200)
INSERT INTO productos_compuestos (sku, nombre, tipo_compuesto, precio_base, activo) VALUES
('SEXCP160', 'Conjunto Exclusive Pillow 160x200', 'conjunto_simple', 0, TRUE);

SET @conjunto_sexcp160_id = LAST_INSERT_ID();
SET @colchon_excp160_id = (SELECT id FROM productos_base WHERE sku = 'CEXCP160');
SET @base_choc80_200_id = (SELECT id FROM productos_base WHERE sku = 'BASE_CHOCOLATE_80_200');

INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria) VALUES
(@conjunto_sexcp160_id, @colchon_excp160_id, 1),
(@conjunto_sexcp160_id, @base_choc80_200_id, 2); -- 2 bases para medida 160

-- Ejemplo 4: Conjunto Doral Pillow 180x200 (colchón + 2 bases gris 90x200)
INSERT INTO productos_compuestos (sku, nombre, tipo_compuesto, precio_base, activo) VALUES
('SDOP180', 'Conjunto Doral Pillow 180x200', 'conjunto_simple', 0, TRUE);

SET @conjunto_sdop180_id = LAST_INSERT_ID();
SET @colchon_dop180_id = (SELECT id FROM productos_base WHERE sku = 'CDOP180');
SET @base_gris90_200_id = (SELECT id FROM productos_base WHERE sku = 'BASE_GRIS_90_200');

INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria) VALUES
(@conjunto_sdop180_id, @colchon_dop180_id, 1),
(@conjunto_sdop180_id, @base_gris90_200_id, 2); -- 2 bases para medida 180

-- Ejemplo 5: Conjunto Exclusive 200x200 (colchón + 2 bases chocolate 100x200)
INSERT INTO productos_compuestos (sku, nombre, tipo_compuesto, precio_base, activo) VALUES
('SEXC200', 'Conjunto Exclusive 200x200', 'conjunto_simple', 0, TRUE);

SET @conjunto_sexc200_id = LAST_INSERT_ID();
SET @colchon_exc200_id = (SELECT id FROM productos_base WHERE sku = 'CEXC200');
SET @base_choc100_200_id = (SELECT id FROM productos_base WHERE sku = 'BASE_CHOCOLATE_100_200');

INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria) VALUES
(@conjunto_sexc200_id, @colchon_exc200_id, 1),
(@conjunto_sexc200_id, @base_choc100_200_id, 2); -- 2 bases para medida 200

-- ============================================================================
-- COMBOS DE ALMOHADAS
-- ============================================================================

-- Ejemplo: Combo 2 Almohadas Platino
INSERT INTO productos_compuestos (sku, nombre, tipo_compuesto, precio_base, activo) VALUES
('PLATINOX2', 'Combo 2 Almohadas Platino', 'combo_almohadas', 0, TRUE);

SET @combo_platinox2_id = LAST_INSERT_ID();
SET @almohada_platino_id = (SELECT id FROM productos_base WHERE sku = 'ALMP');

INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria) VALUES
(@combo_platinox2_id, @almohada_platino_id, 2); -- 2 almohadas platino

-- ============================================================================
-- CONJUNTOS CON ALMOHADAS
-- ============================================================================

-- Ejemplo: Conjunto Exclusive Pillow 140x190 + 2 Almohadas
-- (Este es el ejemplo de tu imagen: SEXP140Z pero sin el Z que es para publicaciones)
INSERT INTO productos_compuestos (sku, nombre, tipo_compuesto, precio_base, activo) VALUES
('SEXP140_ALM', 'Conjunto Exclusive Pillow 140x190 + 2 Almohadas', 'conjunto_con_almohadas', 0, TRUE);

SET @conjunto_sexp140_alm_id = LAST_INSERT_ID();
SET @colchon_excp140_id = (SELECT id FROM productos_base WHERE sku = 'CEXCP140');
SET @base_choc140_id = (SELECT id FROM productos_base WHERE sku = 'BASE_CHOCOLATE_140');
-- Reutilizamos @almohada_platino_id del ejemplo anterior

INSERT INTO componentes (producto_compuesto_id, producto_base_id, cantidad_necesaria) VALUES
(@conjunto_sexp140_alm_id, @colchon_excp140_id, 1),
(@conjunto_sexp140_alm_id, @base_choc140_id, 1),
(@conjunto_sexp140_alm_id, @almohada_platino_id, 2); -- 2 almohadas

-- ============================================================================
-- NOTAS IMPORTANTES
-- ============================================================================

-- 1. El SKU de los productos compuestos NO lleva el sufijo "Z"
--    El sufijo "Z" se usa solo en las PUBLICACIONES de ML para identificar las que no tienen Flex
--
-- 2. Para conjuntos de medidas grandes (160, 180, 200):
--    - Se usan 2 bases de la mitad del ancho
--    - Ejemplo: conjunto 180x200 usa 2 bases de 90x200
--    - cantidad_necesaria = 2 en la tabla componentes
--
-- 3. El stock disponible de un producto compuesto se calcula automáticamente:
--    stock_disponible = MIN(stock_componente1 / cantidad1, stock_componente2 / cantidad2, ...)
--
-- 4. Cuando se vende un producto compuesto, el sistema descuenta automáticamente
--    el stock de TODOS sus componentes
--
-- 5. Las publicaciones de ML pueden tener diferentes títulos pero apuntar al mismo SKU
