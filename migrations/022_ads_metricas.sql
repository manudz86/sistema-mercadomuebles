-- 022: métricas diarias de Meta Ads y Google Ads (vía API de Windsor.ai) para comparar
-- lo que cada plataforma se adjudica contra nuestras ventas (ver ads_bp.py).
-- Las llena el job diario (y el botón "Actualizar"); se reescriben los últimos 14 días
-- porque las plataformas siguen sumando conversiones tarde.

-- Una fila por día × plataforma × campaña × conjunto (Meta) / grupo de anuncios (Google) × anuncio
-- (anuncio solo en Meta; en Google queda '' y el detalle llega hasta el grupo).
-- fecha = día del clic/impresión según la plataforma (no el día de la venta).
CREATE TABLE IF NOT EXISTS ads_metricas_diarias (
    fecha          DATE          NOT NULL,
    plataforma     VARCHAR(10)   NOT NULL,          -- 'meta' | 'google'
    campana_id     VARCHAR(40)   NOT NULL,
    campana        VARCHAR(255)  NULL,
    grupo_id       VARCHAR(40)   NOT NULL DEFAULT '',
    grupo          VARCHAR(255)  NULL,
    anuncio_id     VARCHAR(40)   NOT NULL DEFAULT '',
    anuncio        VARCHAR(255)  NULL,
    impresiones    INT           NOT NULL DEFAULT 0,
    clics          INT           NOT NULL DEFAULT 0,  -- Meta: clics en el enlace; Google: clics
    gasto          DECIMAL(14,2) NOT NULL DEFAULT 0,
    compras        DECIMAL(10,2) NOT NULL DEFAULT 0,  -- lo que la plataforma se adjudica
    valor_compras  DECIMAL(16,2) NOT NULL DEFAULT 0,
    actualizado    TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (fecha, plataforma, campana_id, grupo_id, anuncio_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Clics de Google Ads con su gclid: permite saber de qué campaña vino cada venta
-- (tienda_touchpoints.gclid). No tiene datos personales.
CREATE TABLE IF NOT EXISTS ads_google_clics (
    gclid       VARCHAR(300) NOT NULL,
    fecha       DATE         NOT NULL,
    campana_id  VARCHAR(40)  NULL,
    campana     VARCHAR(255) NULL,
    grupo_id    VARCHAR(40)  NULL,
    grupo       VARCHAR(255) NULL,
    PRIMARY KEY (gclid(191)),
    KEY idx_fecha (fecha)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
