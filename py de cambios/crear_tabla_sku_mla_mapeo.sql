-- ============================================================
-- CREAR TABLA DE MAPEO SKU → MLA (Publicaciones de ML)
-- ============================================================

CREATE TABLE IF NOT EXISTS sku_mla_mapeo (
    id INT AUTO_INCREMENT PRIMARY KEY,
    sku VARCHAR(50) NOT NULL,
    mla_id VARCHAR(20) NOT NULL,
    titulo_ml VARCHAR(255),
    activo BOOLEAN DEFAULT TRUE,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_sku_mla (sku, mla_id),
    INDEX idx_sku (sku),
    INDEX idx_mla (mla_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- INSERTAR EJEMPLO DE PRUEBA
-- ============================================================

INSERT INTO sku_mla_mapeo (sku, mla_id, titulo_ml) VALUES
('PAN90BL', 'MLA603027006', 'Panel Ranurado Blanco 260x90cm')
ON DUPLICATE KEY UPDATE 
    titulo_ml = VALUES(titulo_ml),
    activo = TRUE;

-- ============================================================
-- VERIFICAR
-- ============================================================

SELECT * FROM sku_mla_mapeo WHERE sku = 'PAN90BL';
