-- Atribución multi-contacto de la tienda web + registro de envíos a Meta CAPI.
-- Solo crea tablas nuevas; no modifica ninguna existente. El código funciona aunque estas
-- tablas no existan (salta el registro), así que el orden deploy/migración no rompe nada.
--
-- Datos personales: email/teléfono se guardan solo como HMAC-SHA256 con SECRET_KEY (no reversible
-- sin la clave). Sirven para unir dispositivos y el chat de WhatsApp con la compra.

-- Cada llegada a la tienda con señal de origen (UTM, fbclid, gclid/gbraid/wbraid, link del bot,
-- referrer externo). vid = cookie propia mm_vid (1 por navegador).
CREATE TABLE IF NOT EXISTS tienda_touchpoints (
    id            BIGINT AUTO_INCREMENT PRIMARY KEY,
    vid           CHAR(24)     NOT NULL,
    ts            DATETIME     NOT NULL COMMENT 'UTC',
    canal         VARCHAR(30)  NOT NULL COMMENT 'Meta Ads / Meta orgánico / Google Ads / Google orgánico / WhatsApp / ...',
    utm_source    VARCHAR(100) NULL,
    utm_medium    VARCHAR(100) NULL,
    utm_campaign  VARCHAR(150) NULL COMMENT 'Meta: ID de campaña',
    utm_content   VARCHAR(150) NULL COMMENT 'Meta: ID de anuncio',
    utm_term      VARCHAR(150) NULL COMMENT 'Meta: ID de conjunto',
    utm_id        VARCHAR(200) NULL,
    fbclid        VARCHAR(500) NULL,
    gclid         VARCHAR(300) NULL,
    gbraid        VARCHAR(300) NULL,
    wbraid        VARCHAR(300) NULL,
    wa_ref        VARCHAR(16)  NULL COMMENT 'marca del chat de WhatsApp (HMAC del teléfono, 16 hex)',
    referrer_host VARCHAR(200) NULL,
    landing_path  VARCHAR(300) NULL,
    dispositivo   VARCHAR(20)  NULL,
    KEY idx_vid_ts (vid, ts),
    KEY idx_ts (ts),
    KEY idx_wa (wa_ref),
    KEY idx_content (utm_content)
);

-- Une navegadores (vid) con una persona: se escribe en cada checkout.
CREATE TABLE IF NOT EXISTS tienda_identidades (
    id       BIGINT AUTO_INCREMENT PRIMARY KEY,
    vid      CHAR(24)    NOT NULL,
    email_h  CHAR(64)    NULL,
    tel_h    CHAR(64)    NULL,
    origen   VARCHAR(20) NOT NULL DEFAULT 'checkout',
    ts       DATETIME    NOT NULL COMMENT 'UTC',
    KEY idx_vid (vid),
    KEY idx_email (email_h),
    KEY idx_tel (tel_h)
);

-- Una fila por venta de la tienda: con qué navegador/persona se compró y qué fbc/fbp se usó.
CREATE TABLE IF NOT EXISTS venta_atribucion (
    numero_venta VARCHAR(50) PRIMARY KEY,
    vid          CHAR(24)     NULL,
    email_h      CHAR(64)     NULL,
    tel_h        CHAR(64)     NULL,
    fbc          VARCHAR(600) NULL,
    fbc_origen   VARCHAR(20)  NULL COMMENT 'cookie | fbclid_registrado',
    fbp          VARCHAR(100) NULL,
    ga_cid       VARCHAR(60)  NULL,
    creado       DATETIME     NOT NULL COMMENT 'UTC'
);

-- Registro de cada envío Purchase a Meta CAPI con la respuesta de Meta.
CREATE TABLE IF NOT EXISTS meta_capi_envios (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    numero_venta    VARCHAR(50)   NOT NULL,
    event_id        VARCHAR(50)   NOT NULL,
    valor           DECIMAL(14,2) NULL,
    enviado         DATETIME      NOT NULL COMMENT 'UTC',
    http_status     INT           NULL,
    events_received INT           NULL,
    fbtrace_id      VARCHAR(100)  NULL,
    tiene_fbc       TINYINT       NOT NULL DEFAULT 0,
    fbc_origen      VARCHAR(20)   NULL,
    tiene_fbp       TINYINT       NOT NULL DEFAULT 0,
    es_prueba       TINYINT       NOT NULL DEFAULT 0 COMMENT '1 = prueba interna DESCMMD, NO se envió',
    error           VARCHAR(300)  NULL,
    KEY idx_venta (numero_venta),
    KEY idx_enviado (enviado)
);

-- Chats de WhatsApp que llegaron desde un anuncio Click-to-WhatsApp (objeto "referral" de Meta).
CREATE TABLE IF NOT EXISTS wa_referrals (
    id          BIGINT AUTO_INCREMENT PRIMARY KEY,
    wa_ref      VARCHAR(16)  NOT NULL,
    tel_h       CHAR(64)     NOT NULL,
    ts          DATETIME     NOT NULL COMMENT 'UTC',
    source_type VARCHAR(30)  NULL COMMENT 'ad / post',
    source_id   VARCHAR(100) NULL COMMENT 'ID del anuncio',
    source_url  VARCHAR(500) NULL,
    headline    VARCHAR(300) NULL,
    ctwa_clid   VARCHAR(300) NULL,
    KEY idx_wa (wa_ref),
    KEY idx_tel (tel_h)
);
