-- ============================================================================
-- SISTEMA DE GESTIÓN DE INVENTARIO Y PUBLICACIONES - CANNON
-- Base de datos inicial
-- ============================================================================

-- Tabla de productos BASE (físicos: colchones, bases, almohadas)
CREATE TABLE productos_base (
    id INT PRIMARY KEY AUTO_INCREMENT,
    sku VARCHAR(50) UNIQUE NOT NULL,
    nombre VARCHAR(255) NOT NULL,
    tipo ENUM('colchon', 'base', 'almohada') NOT NULL,
    
    -- Campos específicos para COLCHONES
    linea VARCHAR(50) NULL COMMENT 'espuma, resortes, box',
    modelo VARCHAR(100) NULL,
    medida VARCHAR(20) NULL COMMENT '80x190, 140x190, etc',
    
    -- Campos específicos para BASES
    tipo_base VARCHAR(50) NULL COMMENT 'gris, chocolate, sabana, sublime',
    
    -- Campos específicos para ALMOHADAS
    modelo_almohada VARCHAR(100) NULL,
    
    -- Stock y control
    stock_actual INT DEFAULT 0,
    stock_minimo_pausar INT DEFAULT 0 COMMENT '0 para mayoría, 20 para platino',
    stock_minimo_reactivar INT DEFAULT 1 COMMENT '1 para mayoría, 40 para platino',
    
    -- Precio
    precio_base DECIMAL(10,2) DEFAULT 0,
    
    -- Control
    activo BOOLEAN DEFAULT TRUE,
    notas TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_tipo (tipo),
    INDEX idx_sku (sku),
    INDEX idx_activo (activo)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Tabla de productos COMPUESTOS (virtuales: conjuntos, combos)
CREATE TABLE productos_compuestos (
    id INT PRIMARY KEY AUTO_INCREMENT,
    sku VARCHAR(50) UNIQUE NOT NULL,
    nombre VARCHAR(255) NOT NULL,
    descripcion TEXT,
    tipo_compuesto VARCHAR(50) COMMENT 'conjunto_simple, combo_almohadas, conjunto_con_almohadas',
    
    -- Precio
    precio_base DECIMAL(10,2) DEFAULT 0,
    
    -- Control
    activo BOOLEAN DEFAULT TRUE,
    notas TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_sku (sku),
    INDEX idx_activo (activo)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Componentes de productos compuestos
CREATE TABLE componentes (
    id INT PRIMARY KEY AUTO_INCREMENT,
    producto_compuesto_id INT NOT NULL,
    producto_base_id INT NOT NULL,
    cantidad_necesaria INT DEFAULT 1,
    
    FOREIGN KEY (producto_compuesto_id) REFERENCES productos_compuestos(id) ON DELETE CASCADE,
    FOREIGN KEY (producto_base_id) REFERENCES productos_base(id) ON DELETE RESTRICT,
    
    INDEX idx_compuesto (producto_compuesto_id),
    INDEX idx_base (producto_base_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Tabla de coeficientes de financiación
CREATE TABLE coeficientes_financiacion (
    id INT PRIMARY KEY AUTO_INCREMENT,
    nombre VARCHAR(100) NOT NULL COMMENT '1 pago, Cuota simple, 3 cuotas, etc',
    cuotas INT NOT NULL,
    coeficiente DECIMAL(6,4) NOT NULL COMMENT 'Multiplicador sobre precio base',
    comision_ml_porcentaje DECIMAL(5,2) COMMENT 'Comisión de ML para referencia',
    
    -- Control de aplicación
    aplica_colchones BOOLEAN DEFAULT TRUE,
    aplica_almohadas BOOLEAN DEFAULT TRUE,
    
    -- Vigencia
    activo BOOLEAN DEFAULT TRUE,
    fecha_desde DATE NOT NULL,
    fecha_hasta DATE NULL,
    
    notas TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_activo (activo),
    INDEX idx_vigencia (fecha_desde, fecha_hasta)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Tabla de publicaciones de Mercado Libre
CREATE TABLE publicaciones_ml (
    id INT PRIMARY KEY AUTO_INCREMENT,
    mla_code VARCHAR(50) UNIQUE NOT NULL COMMENT 'MLA123456789',
    
    -- Relación con productos (puede ser base O compuesto, no ambos)
    producto_base_id INT NULL,
    producto_compuesto_id INT NULL,
    
    -- Datos de la publicación
    titulo VARCHAR(500) NOT NULL,
    coeficiente_financiacion_id INT NOT NULL,
    precio_publicado DECIMAL(10,2),
    
    -- Tipo de envío
    tiene_flex BOOLEAN DEFAULT TRUE COMMENT 'TRUE=Flex, FALSE=No Flex (Z)',
    demora_dias_sin_stock INT DEFAULT 15,
    
    -- Estado
    estado VARCHAR(20) DEFAULT 'active' COMMENT 'active, paused, closed, etc',
    stock_publicado INT DEFAULT 0,
    ultima_sincronizacion TIMESTAMP NULL,
    
    -- Metadata
    tipo_catalogo VARCHAR(50) DEFAULT 'custom' COMMENT 'catalog o custom',
    notas TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (producto_base_id) REFERENCES productos_base(id) ON DELETE SET NULL,
    FOREIGN KEY (producto_compuesto_id) REFERENCES productos_compuestos(id) ON DELETE SET NULL,
    FOREIGN KEY (coeficiente_financiacion_id) REFERENCES coeficientes_financiacion(id) ON DELETE RESTRICT,
    
    -- Validación: debe tener al menos uno
    CHECK (producto_base_id IS NOT NULL OR producto_compuesto_id IS NOT NULL),
    
    INDEX idx_mla (mla_code),
    INDEX idx_estado (estado),
    INDEX idx_producto_base (producto_base_id),
    INDEX idx_producto_compuesto (producto_compuesto_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Movimientos de stock (entradas y salidas)
CREATE TABLE movimientos_stock (
    id INT PRIMARY KEY AUTO_INCREMENT,
    producto_base_id INT NOT NULL,
    
    tipo_movimiento ENUM('entrada', 'salida', 'ajuste') NOT NULL,
    cantidad INT NOT NULL COMMENT 'Positivo para entrada, negativo para salida',
    
    stock_anterior INT NOT NULL,
    stock_nuevo INT NOT NULL,
    
    -- Contexto del movimiento
    motivo VARCHAR(255) COMMENT 'reposicion_proveedor, venta_ml, venta_mostrador, ajuste_inventario, etc',
    canal VARCHAR(50) COMMENT 'ml, web, mostrador, sistema',
    referencia VARCHAR(255) COMMENT 'ID de venta, nro de remito, MLA, etc',
    
    -- Usuario que realizó el movimiento
    usuario VARCHAR(100),
    
    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (producto_base_id) REFERENCES productos_base(id) ON DELETE CASCADE,
    
    INDEX idx_producto (producto_base_id),
    INDEX idx_tipo (tipo_movimiento),
    INDEX idx_fecha (fecha),
    INDEX idx_canal (canal)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Historial de cambios en publicaciones ML
CREATE TABLE historial_publicaciones (
    id INT PRIMARY KEY AUTO_INCREMENT,
    publicacion_id INT NOT NULL,
    
    accion VARCHAR(100) NOT NULL COMMENT 'pausada, reactivada, demora_modificada, precio_actualizado, stock_actualizado',
    
    valor_anterior VARCHAR(500),
    valor_nuevo VARCHAR(500),
    
    stock_momento INT COMMENT 'Stock del producto cuando se realizó el cambio',
    
    resultado VARCHAR(20) DEFAULT 'exitoso' COMMENT 'exitoso, fallido, pendiente',
    mensaje_error TEXT,
    
    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (publicacion_id) REFERENCES publicaciones_ml(id) ON DELETE CASCADE,
    
    INDEX idx_publicacion (publicacion_id),
    INDEX idx_fecha (fecha),
    INDEX idx_accion (accion)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Tabla de configuración general del sistema
CREATE TABLE configuracion (
    id INT PRIMARY KEY AUTO_INCREMENT,
    clave VARCHAR(100) UNIQUE NOT NULL,
    valor TEXT,
    tipo VARCHAR(20) DEFAULT 'string' COMMENT 'string, number, boolean, json',
    descripcion TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Insertar configuraciones iniciales
INSERT INTO configuracion (clave, valor, tipo, descripcion) VALUES
('ml_app_id', '', 'string', 'Application ID de Mercado Libre'),
('ml_secret_key', '', 'string', 'Secret Key de Mercado Libre'),
('ml_access_token', '', 'string', 'Access Token de Mercado Libre'),
('ml_refresh_token', '', 'string', 'Refresh Token de Mercado Libre'),
('ml_user_id', '', 'string', 'User ID del vendedor en ML'),
('sincronizacion_auto_activa', 'true', 'boolean', 'Activar sincronización automática con ML'),
('intervalo_sincronizacion_minutos', '15', 'number', 'Intervalo de sincronización automática en minutos'),
('demora_dias_default_sin_stock', '15', 'number', 'Días de demora por defecto para publicaciones sin Flex sin stock');
