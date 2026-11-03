-- 014_mla_catalogo.sql
-- Índice MLA -> producto de catálogo de ML, espejo de lo que ML reporta.
--
-- Motivo: para buscar "mis publis de este catálogo" no servía ninguna fuente
-- existente. sku_catalog_map es la lista de catálogos que monitorea el módulo
-- de competencia (curada, con manual=1), no un inventario: cubría 393 de 833
-- publis de catálogo (47%). Le faltan todos los SKU con Z, que publican en el
-- mismo catálogo que su hermano sin Z, y su sku es UNIQUE, así que no puede
-- representar un SKU publicado en varios catálogos (pasa: SPR14020, DORALX2,
-- PLATINOX2).
--
-- Tampoco alcanza preguntarle a ML en vivo: /products/{id}/items solo devuelve
-- las publicaciones ACTIVAS del catálogo, y justamente las pausadas son las que
-- hay que poder encontrar para reactivarlas o corregirles el precio.
--
-- Se llena desde ML: job diario (scripts/refrescar_catalogo_mla.py) y, gratis,
-- cada vez que se busca en Modificar Publis ML (esa pantalla ya recibe el
-- catalog_product_id de cada publicación que muestra).

CREATE TABLE IF NOT EXISTS mla_catalogo (
    mla_id              VARCHAR(20)  NOT NULL PRIMARY KEY,
    catalog_product_id  VARCHAR(30)  DEFAULT NULL,       -- NULL = publi de listado general
    status              VARCHAR(20)  DEFAULT NULL,       -- active | paused | closed | ...
    actualizado_at      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    KEY idx_catalogo (catalog_product_id),
    KEY idx_actualizado (actualizado_at)
-- utf8mb4_unicode_ci explícito: es la colación del resto del esquema, y sin eso
-- MySQL usa la del servidor (utf8mb4_0900_ai_ci) y los JOIN contra
-- sku_mla_mapeo fallan con "Illegal mix of collations".
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
