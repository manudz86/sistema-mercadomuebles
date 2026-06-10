-- 009_fraude_bloqueos_whitelist.sql
-- (1) Registro de bloqueos del gate antifraude (velocidad + blocklist) para que
--     sean visibles en /intentos-pago (solapa Bloqueos).
-- (2) Whitelist: columna 'lista' en fraude_blocklist. lista='block' (default) son
--     bloqueos manuales; lista='allow' son EXCEPCIONES que eximen de las reglas
--     de velocidad (la blocklist manual sigue mandando).

ALTER TABLE fraude_blocklist
    ADD COLUMN lista VARCHAR(10) NOT NULL DEFAULT 'block' AFTER tipo;

CREATE TABLE IF NOT EXISTS fraude_bloqueos (
    id        INT AUTO_INCREMENT PRIMARY KEY,
    fecha     DATETIME     DEFAULT CURRENT_TIMESTAMP,
    motivo    VARCHAR(30)  DEFAULT NULL,   -- velocidad_tarjeta | velocidad_envio | blocklist:*
    dni       VARCHAR(30)  DEFAULT NULL,
    email     VARCHAR(150) DEFAULT NULL,
    telefono  VARCHAR(50)  DEFAULT NULL,
    direccion VARCHAR(255) DEFAULT NULL,
    bin       VARCHAR(10)  DEFAULT NULL,
    last4     VARCHAR(4)   DEFAULT NULL,
    ref       VARCHAR(40)  DEFAULT NULL,
    KEY idx_fecha (fecha)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
