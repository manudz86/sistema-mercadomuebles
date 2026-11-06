-- Recupero de carritos abandonados (Email Marketing → Recupero de carritos)
-- recupero_envios: un registro por mail enviado (para no repetir y medir clicks y conversiones).
-- email_bajas: clientes que pidieron no recibir más mails de marketing (link del pie del mail).

CREATE TABLE IF NOT EXISTS recupero_envios (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    email         VARCHAR(255) NOT NULL,
    ref           VARCHAR(32)  NOT NULL,
    cupon_id      INT          NULL,
    cupon_codigo  VARCHAR(50)  NULL,
    plantilla     VARCHAR(50)  NULL,
    total_mail    DECIMAL(12,2) NULL,
    items_json    TEXT         NULL,
    fecha_envio   TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    click_at      TIMESTAMP    NULL,
    clicks        INT          NOT NULL DEFAULT 0,
    INDEX idx_email (email),
    INDEX idx_ref (ref),
    INDEX idx_cupon (cupon_codigo)
);

CREATE TABLE IF NOT EXISTS email_bajas (
    email   VARCHAR(255) PRIMARY KEY,
    origen  VARCHAR(50)  NULL,
    fecha   TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);
