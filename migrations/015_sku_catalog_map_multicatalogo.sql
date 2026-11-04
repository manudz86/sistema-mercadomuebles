-- 015_sku_catalog_map_multicatalogo.sql
-- Un SKU puede estar en VARIOS catálogos de Mercado Libre, y un catálogo puede
-- tener publicaciones de varios SKU nuestros. La tabla lo modelaba como uno a
-- uno (sku UNIQUE), así que para monitorear un segundo catálogo había que
-- inventarle una etiqueta de SKU: PLATINOX2 / PLATINOX2-TOP / PLATINOX2-VELLON
-- son el mismo SKU con tres catálogos distintos.
--
-- Medido: 15 SKU están hoy en más de un catálogo (PLATINOX2 en 4), o sea ~20
-- catálogos que el monitor de competencia no vigilaba.
--
-- La clave pasa a ser el par (sku, catalog_product_id). Nada más cambia: los
-- snapshots ya guardaban catalog_product_id en cada fila, así que los datos
-- históricos siguen siendo válidos y comparables.

ALTER TABLE sku_catalog_map DROP INDEX `sku`;
ALTER TABLE sku_catalog_map ADD UNIQUE KEY `uk_sku_catalogo` (`sku`, `catalog_product_id`);
ALTER TABLE sku_catalog_map ADD INDEX `idx_catalogo` (`catalog_product_id`);
