-- 011_promos_ml_historial.sql
-- Historial de promociones de Mercado Libre: guarda las DOS caras de cada acción,
-- lo que el panel MOSTRÓ (y se aceptó) y lo que ML terminó APLICANDO.
-- Motivo: aparecieron promos aplicadas con aporte propio muy superior al aceptado
-- y no había ningún registro para reconstruir qué pasó.

CREATE TABLE IF NOT EXISTS promos_ml_historial (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    fecha               DATETIME     DEFAULT CURRENT_TIMESTAMP,
    accion              VARCHAR(20)  NOT NULL,           -- aplicar | quitar | rechequeo | revertir
    origen              VARCHAR(30)  DEFAULT 'panel',    -- panel | lote | script | job
    mla_id              VARCHAR(20)  NOT NULL,
    sku                 VARCHAR(50)  DEFAULT NULL,
    campania_id         VARCHAR(40)  DEFAULT NULL,
    campania_nombre     VARCHAR(120) DEFAULT NULL,
    tipo                VARCHAR(30)  DEFAULT NULL,       -- SMART | PRICE_MATCHING | DEAL | ...

    -- lo que se mostró en pantalla y se aceptó
    mostrado_pct        DECIMAL(7,3) DEFAULT NULL,
    mostrado_precio     INT          DEFAULT NULL,
    mostrado_original   INT          DEFAULT NULL,

    -- lo que ML dejó realmente aplicado (releído de la API después de aplicar)
    aplicado_pct        DECIMAL(7,3) DEFAULT NULL,
    aplicado_meli_pct   DECIMAL(7,3) DEFAULT NULL,
    aplicado_precio     INT          DEFAULT NULL,
    aplicado_original   INT          DEFAULT NULL,

    coincide            TINYINT(1)   DEFAULT NULL,       -- 1 si mostrado ≈ aplicado (±0.5 pts)
    delta_pct           DECIMAL(7,3) DEFAULT NULL,       -- aplicado - mostrado
    supero_limite       TINYINT(1)   DEFAULT 0,          -- 1 si pasó el tope configurado
    revertida           TINYINT(1)   DEFAULT 0,          -- 1 si se deshizo automáticamente
    ok                  TINYINT(1)   DEFAULT 1,
    error               VARCHAR(255) DEFAULT NULL,
    usuario             VARCHAR(100) DEFAULT NULL,

    INDEX idx_fecha (fecha),
    INDEX idx_mla (mla_id),
    INDEX idx_campania (campania_id),
    INDEX idx_supero (supero_limite),
    INDEX idx_coincide (coincide)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Tope de aporte propio: por encima de esto no se aplica (y se revierte si ML lo aplicó igual).
INSERT IGNORE INTO configuracion (clave, valor) VALUES ('promo_max_aporte_pct', '5');
