-- ============================================================================
-- MÓDULO DE GESTIÓN DE VENTAS
-- ============================================================================

-- Tabla de clientes
CREATE TABLE clientes (
    id INT PRIMARY KEY AUTO_INCREMENT,
    nombre VARCHAR(255) NOT NULL,
    telefono VARCHAR(50),
    email VARCHAR(255),
    direccion TEXT,
    zona_geografica VARCHAR(100),
    notas TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_telefono (telefono),
    INDEX idx_nombre (nombre)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Tabla de ventas
CREATE TABLE ventas (
    id INT PRIMARY KEY AUTO_INCREMENT,
    
    -- Identificación
    numero_venta VARCHAR(50) UNIQUE COMMENT 'Número interno o apodo',
    mla_code VARCHAR(50) COMMENT 'MLA de ML si aplica',
    
    -- Cliente
    cliente_id INT,
    nombre_cliente VARCHAR(255),
    telefono_cliente VARCHAR(50),
    
    -- Fechas
    fecha_venta DATETIME NOT NULL,
    fecha_entrega_estimada DATE,
    fecha_entrega_real DATETIME COMMENT 'Fecha y hora real de entrega/retiro',
    
    -- Canal de venta
    canal ENUM('ml', 'web', 'mostrador', 'whatsapp', 'telefono', 'otro') NOT NULL DEFAULT 'mostrador',
    
    -- Importes
    importe_total DECIMAL(10,2) NOT NULL,
    importe_abonado DECIMAL(10,2) DEFAULT 0,
    metodo_pago VARCHAR(100) COMMENT 'Efectivo, transferencia, tarjeta, etc',
    
    -- Entrega
    tipo_entrega ENUM('retiro', 'envio') NOT NULL,
    direccion_entrega TEXT,
    
    -- Método de envío
    metodo_envio ENUM('mercadoenvios', 'flex', 'zippin', 'delega', 'propio') COMMENT 'Método de envío',
    zona_envio ENUM('sur', 'norte-noroeste', 'oeste', 'capital') COMMENT 'Solo para envío propio',
    
    -- Responsable de entrega (cuando está en_proceso)
    responsable_entrega ENUM('lean', 'leo', 'ezequiel', 'tucu', 'antonio', 
                             'zip-lunes', 'zip-martes', 'zip-miercoles', 'zip-jueves', 'zip-viernes') 
                        COMMENT 'Quién entrega cuando está en proceso',
    
    -- Estado
    estado_pago ENUM('pendiente', 'parcial', 'pagado') DEFAULT 'pendiente',
    estado_entrega ENUM('pendiente', 'en_proceso', 'entregado', 'retirado') DEFAULT 'pendiente',
    
    -- Control de stock
    stock_descontado BOOLEAN DEFAULT FALSE COMMENT 'TRUE cuando se descontó el stock físico',
    fecha_descuento_stock DATETIME COMMENT 'Cuándo se descontó el stock',
    
    -- Observaciones
    notas TEXT,
    
    -- Auditoría
    usuario_registro VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (cliente_id) REFERENCES clientes(id) ON DELETE SET NULL,
    
    INDEX idx_fecha_venta (fecha_venta),
    INDEX idx_canal (canal),
    INDEX idx_estado_pago (estado_pago),
    INDEX idx_estado_entrega (estado_entrega),
    INDEX idx_mla (mla_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Tabla de items de venta (detalle)
CREATE TABLE ventas_items (
    id INT PRIMARY KEY AUTO_INCREMENT,
    venta_id INT NOT NULL,
    
    -- Producto (puede ser base o compuesto)
    producto_base_id INT,
    producto_compuesto_id INT,
    
    -- Datos del producto en el momento de la venta
    sku VARCHAR(50) NOT NULL,
    descripcion VARCHAR(500) NOT NULL,
    
    -- Cantidades y precios
    cantidad INT NOT NULL,
    precio_unitario DECIMAL(10,2) NOT NULL,
    precio_total DECIMAL(10,2) NOT NULL,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (venta_id) REFERENCES ventas(id) ON DELETE CASCADE,
    FOREIGN KEY (producto_base_id) REFERENCES productos_base(id) ON DELETE SET NULL,
    FOREIGN KEY (producto_compuesto_id) REFERENCES productos_compuestos(id) ON DELETE SET NULL,
    
    -- Al menos uno debe estar presente
    CHECK (producto_base_id IS NOT NULL OR producto_compuesto_id IS NOT NULL),
    
    INDEX idx_venta (venta_id),
    INDEX idx_sku (sku)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Tabla de alertas de stock
CREATE TABLE alertas_stock (
    id INT PRIMARY KEY AUTO_INCREMENT,
    
    -- Producto afectado (base o compuesto)
    producto_base_id INT,
    producto_compuesto_id INT,
    sku VARCHAR(50) NOT NULL,
    nombre_producto VARCHAR(255) NOT NULL,
    
    -- Tipo de alerta
    tipo_alerta ENUM('sin_stock', 'stock_bajo', 'stock_critico') NOT NULL,
    
    -- Acción sugerida
    accion_sugerida ENUM('pausar_flex', 'modificar_demora', 'reactivar_flex', 'quitar_demora') NOT NULL,
    
    -- Stock en el momento de la alerta
    stock_actual INT NOT NULL,
    stock_minimo INT,
    
    -- MLAs afectados (JSON array)
    mlas_afectados JSON COMMENT 'Array de MLAs que necesitan acción',
    
    -- Estado de la alerta
    estado ENUM('pendiente', 'procesada', 'ignorada') DEFAULT 'pendiente',
    fecha_procesada DATETIME,
    usuario_proceso VARCHAR(100),
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (producto_base_id) REFERENCES productos_base(id) ON DELETE CASCADE,
    FOREIGN KEY (producto_compuesto_id) REFERENCES productos_compuestos(id) ON DELETE CASCADE,
    
    INDEX idx_estado (estado),
    INDEX idx_tipo (tipo_alerta),
    INDEX idx_fecha (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Vista para VENTAS ACTIVAS (pendiente)
CREATE VIEW ventas_activas AS
SELECT 
    v.id,
    v.numero_venta,
    v.mla_code,
    v.nombre_cliente,
    v.telefono_cliente,
    v.fecha_venta,
    v.fecha_entrega_estimada,
    v.canal,
    v.tipo_entrega,
    v.metodo_envio,
    v.zona_envio,
    v.direccion_entrega,
    v.importe_total,
    v.importe_abonado,
    (v.importe_total - v.importe_abonado) as saldo_pendiente,
    v.estado_pago,
    v.estado_entrega,
    v.stock_descontado,
    v.notas,
    GROUP_CONCAT(CONCAT(vi.cantidad, 'x ', vi.descripcion) SEPARATOR ', ') as productos
FROM ventas v
LEFT JOIN ventas_items vi ON v.id = vi.venta_id
WHERE v.estado_entrega = 'pendiente'
GROUP BY v.id
ORDER BY v.fecha_venta DESC;

-- Vista para VENTAS EN PROCESO DE ENTREGA
CREATE VIEW ventas_en_proceso AS
SELECT 
    v.id,
    v.numero_venta,
    v.mla_code,
    v.nombre_cliente,
    v.telefono_cliente,
    v.fecha_venta,
    v.fecha_entrega_estimada,
    v.canal,
    v.tipo_entrega,
    v.metodo_envio,
    v.responsable_entrega,
    v.zona_envio,
    v.direccion_entrega,
    v.importe_total,
    v.estado_pago,
    v.notas,
    GROUP_CONCAT(CONCAT(vi.cantidad, 'x ', vi.descripcion) SEPARATOR ', ') as productos
FROM ventas v
LEFT JOIN ventas_items vi ON v.id = vi.venta_id
WHERE v.estado_entrega = 'en_proceso'
GROUP BY v.id
ORDER BY 
    v.responsable_entrega,
    v.fecha_entrega_estimada;

-- Vista para VENTAS HISTÓRICAS (entregadas o retiradas)
CREATE VIEW ventas_historicas AS
SELECT 
    v.id,
    v.numero_venta,
    v.mla_code,
    v.nombre_cliente,
    v.telefono_cliente,
    v.fecha_venta,
    v.fecha_entrega_real,
    v.canal,
    v.tipo_entrega,
    v.metodo_envio,
    v.responsable_entrega,
    v.importe_total,
    v.estado_pago,
    v.estado_entrega,
    GROUP_CONCAT(CONCAT(vi.cantidad, 'x ', vi.descripcion) SEPARATOR ', ') as productos
FROM ventas v
LEFT JOIN ventas_items vi ON v.id = vi.venta_id
WHERE v.estado_entrega IN ('entregado', 'retirado')
GROUP BY v.id
ORDER BY v.fecha_venta DESC;  -- Ordenado por fecha de venta, NO por entrega

-- Vista para ver ventas pendientes de pago
CREATE VIEW ventas_pendientes_pago AS
SELECT 
    v.id,
    v.numero_venta,
    v.nombre_cliente,
    v.telefono_cliente,
    v.fecha_venta,
    v.canal,
    v.importe_total,
    v.importe_abonado,
    (v.importe_total - v.importe_abonado) as saldo_pendiente,
    v.estado_pago,
    GROUP_CONCAT(CONCAT(vi.cantidad, 'x ', vi.descripcion) SEPARATOR ', ') as productos
FROM ventas v
LEFT JOIN ventas_items vi ON v.id = vi.venta_id
WHERE v.estado_pago != 'pagado'
GROUP BY v.id
ORDER BY v.fecha_venta DESC;

-- Vista de alertas pendientes
CREATE VIEW alertas_pendientes AS
SELECT 
    a.*,
    CASE 
        WHEN a.producto_base_id IS NOT NULL THEN pb.nombre
        WHEN a.producto_compuesto_id IS NOT NULL THEN pc.nombre
    END as nombre_producto_completo
FROM alertas_stock a
LEFT JOIN productos_base pb ON a.producto_base_id = pb.id
LEFT JOIN productos_compuestos pc ON a.producto_compuesto_id = pc.id
WHERE a.estado = 'pendiente'
ORDER BY 
    CASE a.tipo_alerta
        WHEN 'sin_stock' THEN 1
        WHEN 'stock_critico' THEN 2
        WHEN 'stock_bajo' THEN 3
    END,
    a.created_at DESC;

-- Vista para calcular stock comprometido en ventas (pendientes + en proceso)
CREATE VIEW stock_comprometido_ventas AS
SELECT 
    vi.sku,
    SUM(vi.cantidad) as cantidad_comprometida
FROM ventas_items vi
JOIN ventas v ON vi.venta_id = v.id
WHERE v.stock_descontado = FALSE 
  AND v.estado_entrega IN ('pendiente', 'en_proceso')
GROUP BY vi.sku;

-- Vista de stock disponible real (para publicar en ML)
CREATE VIEW stock_disponible_ml AS
SELECT 
    pb.id,
    pb.sku,
    pb.nombre,
    pb.tipo,
    pb.stock_actual as stock_fisico,
    COALESCE(scv.cantidad_comprometida, 0) as stock_comprometido,
    (pb.stock_actual - COALESCE(scv.cantidad_comprometida, 0)) as stock_disponible_ml,
    pb.stock_minimo_pausar,
    pb.stock_minimo_reactivar,
    CASE 
        WHEN (pb.stock_actual - COALESCE(scv.cantidad_comprometida, 0)) <= pb.stock_minimo_pausar THEN 'SIN_STOCK'
        WHEN (pb.stock_actual - COALESCE(scv.cantidad_comprometida, 0)) <= pb.stock_minimo_reactivar THEN 'STOCK_BAJO'
        ELSE 'OK'
    END as estado_stock
FROM productos_base pb
LEFT JOIN stock_comprometido_ventas scv ON pb.sku = scv.sku
WHERE pb.activo = TRUE;
