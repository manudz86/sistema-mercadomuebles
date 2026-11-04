-- 016_promo_excepciones.sql
-- Excepciones autorizadas a mano al tope de aporte propio en promos de ML.
--
-- El job de las 7:15 quita toda promo cuyo aporte propio supere el tope
-- (configuracion.promo_max_aporte_pct, 5%), porque ML sube el aporte DESPUÉS de
-- aplicada: hubo promos aceptadas al 3,1% que terminaron en 17,2%. Esa red se
-- mantiene, pero antes no había forma de decir "esta la pongo a propósito".
--
-- La excepción NO es un permiso en blanco:
--   * vale para un par (publicación, campaña), no para el MLA entero;
--   * guarda el tope que se aceptó: si ML sube el aporte por encima de ese
--     número, la promo se quita igual.
-- Arriba de todo queda el tope duro (configuracion.promo_tope_duro_pct, 25%),
-- que ni con excepción se puede pasar.
--
-- Reemplaza la lista por coma en configuracion['promo_excepciones'], que no
-- distinguía campaña ni porcentaje. Esa clave se migra y deja de leerse.

CREATE TABLE IF NOT EXISTS promo_excepciones (
    id               INT AUTO_INCREMENT PRIMARY KEY,
    mla_id           VARCHAR(20)  NOT NULL,
    campania_id      VARCHAR(40)  NOT NULL,
    tipo             VARCHAR(30)  DEFAULT NULL,       -- SMART | DEAL | PRICE_MATCHING | ...
    campania_nombre  VARCHAR(120) DEFAULT NULL,
    sku              VARCHAR(50)  DEFAULT NULL,
    tope_pct         DECIMAL(7,3) NOT NULL,           -- el aporte que se aceptó
    motivo           VARCHAR(255) DEFAULT NULL,
    creado_por       VARCHAR(50)  DEFAULT NULL,
    creado_at        TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,

    UNIQUE KEY uk_mla_campania (mla_id, campania_id),
    KEY idx_mla (mla_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Tope duro: ni con excepción se aplica una promo por encima de esto.
INSERT INTO configuracion (clave, valor)
VALUES ('promo_tope_duro_pct', '25')
ON DUPLICATE KEY UPDATE clave = clave;
