-- Zipnova (recolecciones + estado de envíos) y mensajes de ML sin leer por venta.
-- Solo crea tablas nuevas; no modifica ninguna existente. El código funciona aunque estas
-- tablas no existan (los íconos y la página quedan vacíos), así que el orden deploy/migración
-- no rompe nada.
--
-- Datos personales: no se guardan nombres ni direcciones de destinatarios. Quedan solo dentro
-- del PDF de Zipnova (data/zipnova_recolecciones/, fuera de git), que se sirve con login.

-- Envíos de Zipnova (API GET /shipments), enlazados a la venta del sistema.
CREATE TABLE IF NOT EXISTS zipnova_envios (
    zipnova_id        BIGINT       NOT NULL PRIMARY KEY,
    external_id       VARCHAR(40)  NULL COMMENT 'ML: id de envío de ML · Web: numero_venta',
    numero_venta      VARCHAR(100) NULL COMMENT 'ventas.numero_venta; vacío = no se encontró la venta',
    guia              VARCHAR(40)  NULL COMMENT 'delivery_id de Zipnova (0999-...)',
    status            VARCHAR(40)  NULL,
    status_name       VARCHAR(80)  NULL,
    carrier_id        INT          NULL,
    carrier           VARCHAR(80)  NULL,
    tracking_url      VARCHAR(255) NULL,
    tracking_ext_url  VARCHAR(255) NULL,
    creado_at         DATETIME     NULL COMMENT 'UTC',
    last_status_at    DATETIME     NULL COMMENT 'UTC',
    actualizado       TIMESTAMP    DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    KEY idx_zn_ext (external_id),
    KEY idx_zn_venta (numero_venta),
    KEY idx_zn_guia (guia)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Una recolección programada (mail "Nueva recolección de ZIPNOVA programada para el ..." + PDF).
CREATE TABLE IF NOT EXISTS zipnova_recolecciones (
    pickup_id         INT          NOT NULL PRIMARY KEY COMMENT 'PICKUP #nnn del PDF',
    fecha_retiro      DATE         NOT NULL,
    origen            VARCHAR(100) NULL,
    generado_at       DATETIME     NULL COMMENT 'hora AR, según el PDF',
    mail_message_id   VARCHAR(255) NULL,
    mail_recibido_at  DATETIME     NULL COMMENT 'UTC',
    pdf_archivo       VARCHAR(255) NULL,
    total_envios      INT          NULL,
    total_bultos      INT          NULL,
    total_kg          DECIMAL(10,2) NULL,
    total_m3          DECIMAL(10,4) NULL,
    creado            TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    KEY idx_zr_fecha (fecha_retiro)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Envíos listados en el PDF de cada recolección (sin datos del destinatario).
CREATE TABLE IF NOT EXISTS zipnova_recoleccion_envios (
    pickup_id         INT          NOT NULL,
    external_id       VARCHAR(40)  NOT NULL,
    guia              VARCHAR(40)  NULL,
    orden             INT          NULL,
    bultos            INT          NULL,
    kg                DECIMAL(10,2) NULL,
    detalle           VARCHAR(500) NULL COMMENT 'SKU de cada bulto',
    PRIMARY KEY (pickup_id, external_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Mail diario "Resumen de recolecciones del día dd/mm/aaaa": qué se llevó efectivamente.
CREATE TABLE IF NOT EXISTS zipnova_resumenes (
    fecha             DATE         NOT NULL PRIMARY KEY,
    mail_message_id   VARCHAR(255) NULL,
    mail_recibido_at  DATETIME     NULL COMMENT 'UTC',
    recolectados      TEXT         NULL COMMENT 'JSON: [{external_id, guia}]',
    no_recolectados   TEXT         NULL COMMENT 'JSON: [{external_id, guia}] si el mail trae esa sección',
    texto             TEXT         NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Estado de los jobs de sincronización (última corrida y resultado, para la página y el throttle).
CREATE TABLE IF NOT EXISTS zipnova_jobs (
    job               VARCHAR(40)  NOT NULL PRIMARY KEY,
    ultimo            DATETIME     NULL COMMENT 'UTC',
    resultado         VARCHAR(500) NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Mensajes de compradores de ML sin leer (GET /messages/unread), por orden.
-- Se reconstruye entera en cada sincronización.
CREATE TABLE IF NOT EXISTS ml_mensajes_no_leidos (
    order_id          BIGINT       NOT NULL PRIMARY KEY,
    pack_id           BIGINT       NULL,
    cantidad          INT          NOT NULL,
    actualizado       TIMESTAMP    DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    KEY idx_mnl_pack (pack_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
