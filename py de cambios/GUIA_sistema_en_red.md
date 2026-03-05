# 🌐 SISTEMA EN RED - GUÍA COMPLETA

## 📋 REQUISITOS:

1. **Todas las PCs en la misma red** (WiFi o cable)
2. **1 PC servidor** (la más potente, que queda prendida)
3. **Varias PCs cliente** (solo necesitan navegador)

---

## 🔧 CONFIGURACIÓN (3 PASOS):

---

### PASO 1: CONFIGURAR FLASK PARA RED

En `app.py`, al final del archivo, **BUSCAR:**

```python
if __name__ == '__main__':
    app.run(debug=True)
```

**CAMBIAR A:**

```python
if __name__ == '__main__':
    app.run(
        host='0.0.0.0',      # Escuchar en todas las interfaces
        port=5000,            # Puerto
        debug=False,          # NO usar debug en producción
        threaded=True         # Permitir múltiples conexiones simultáneas
    )
```

**Explicación:**
- `host='0.0.0.0'` → Flask escucha en TODAS las interfaces de red
- `port=5000` → Puerto donde escucha
- `debug=False` → Desactivar modo debug (importante para multi-usuario)
- `threaded=True` → Permite que varios usuarios accedan al mismo tiempo

---

### PASO 2: CONFIGURAR MYSQL PARA RED

MySQL por defecto solo acepta conexiones desde localhost. Hay que permitir conexiones remotas.

#### Opción A - Permitir todas las IPs locales (más fácil):

1. Abrir MySQL Workbench o línea de comandos
2. Ejecutar:

```sql
-- Crear usuario con acceso desde cualquier IP de la red local
CREATE USER 'cannon_user'@'192.168.%' IDENTIFIED BY 'tu_password_segura';

-- Darle todos los permisos en la BD
GRANT ALL PRIVILEGES ON inventario_cannon.* TO 'cannon_user'@'192.168.%';

-- Aplicar cambios
FLUSH PRIVILEGES;
```

3. Actualizar conexión en `app.py`:

```python
def get_db_connection():
    return pymysql.connect(
        host='localhost',  # En el servidor, sigue siendo localhost
        user='cannon_user',
        password='tu_password_segura',
        database='inventario_cannon',
        cursorclass=pymysql.cursors.DictCursor
    )
```

#### Opción B - Usar el usuario root (menos seguro, solo para testing):

```sql
-- Permitir root desde red local
GRANT ALL PRIVILEGES ON inventario_cannon.* TO 'root'@'192.168.%' IDENTIFIED BY 'tu_password';
FLUSH PRIVILEGES;
```

---

### PASO 3: CONFIGURAR FIREWALL DE WINDOWS

El firewall debe permitir conexiones al puerto 5000.

#### Método 1 - Ventana de comandos (Admin):

```cmd
netsh advfirewall firewall add rule name="Flask Cannon" dir=in action=allow protocol=TCP localport=5000
```

#### Método 2 - Interfaz gráfica:

1. Panel de Control → Sistema y Seguridad → Firewall de Windows
2. Configuración avanzada
3. Reglas de entrada → Nueva regla
4. Tipo: Puerto
5. Protocolo: TCP
6. Puerto: 5000
7. Permitir conexión
8. Aplicar a todos los perfiles
9. Nombre: "Sistema Cannon Flask"

---

## 🚀 PUESTA EN MARCHA:

### En la PC SERVIDOR:

1. **Averiguar IP local:**
   ```cmd
   ipconfig
   ```
   Buscar "Dirección IPv4" (ej: 192.168.1.10)

2. **Iniciar Flask:**
   ```cmd
   cd C:\ruta\al\proyecto
   venv\Scripts\activate
   python app.py
   ```

3. **Verificar que aparezca:**
   ```
   * Running on http://0.0.0.0:5000
   * Running on http://192.168.1.10:5000
   ```

### En las PCs CLIENTE:

1. Abrir Chrome/Edge
2. Ir a: `http://192.168.1.10:5000`
   (Reemplazar con la IP del servidor)

---

## ✅ VERIFICACIÓN:

### Test desde el servidor:
```
http://localhost:5000  ✅ Debe funcionar
http://192.168.1.10:5000  ✅ Debe funcionar
```

### Test desde un cliente:
```
http://192.168.1.10:5000  ✅ Debe funcionar
```

---

## ⚡ SOLUCIÓN DE PROBLEMAS:

### Error: "No se puede acceder"

1. **Verificar que Flask esté corriendo:**
   - Ver consola del servidor
   - Debe decir "Running on http://0.0.0.0:5000"

2. **Ping al servidor desde cliente:**
   ```cmd
   ping 192.168.1.10
   ```
   - Debe responder
   - Si no responde, problema de red

3. **Verificar firewall:**
   ```cmd
   netsh advfirewall firewall show rule name="Flask Cannon"
   ```

4. **Verificar puerto correcto:**
   - Servidor debe escuchar en 5000
   - Cliente debe acceder a 5000

### Error: "Access denied for user"

- MySQL no permite conexiones remotas
- Revisar PASO 2

### Error: "Lost connection to MySQL"

- Configurar `wait_timeout` en MySQL:
  ```sql
  SET GLOBAL wait_timeout=28800;
  SET GLOBAL interactive_timeout=28800;
  ```

---

## 🔒 SEGURIDAD (IMPORTANTE):

### 1. Cambiar password de MySQL
```python
password='password_segura_aqui_123'  # NO usar 'root' o '1234'
```

### 2. Desactivar debug en producción
```python
app.run(debug=False)  # MUY IMPORTANTE
```

### 3. NO exponer a Internet
- Solo usar en red local (192.168.x.x)
- NO abrir puertos en el router
- NO acceder desde fuera de la oficina

### 4. Backup automático
Crear tarea programada para backup diario de MySQL:
```cmd
mysqldump -u root -p inventario_cannon > backup_%date%.sql
```

---

## 📱 ACCESO DESDE CELULARES (BONUS):

Si la red WiFi es la misma:

1. En el celular, conectarse a la WiFi de la oficina
2. Abrir navegador
3. Ir a: `http://192.168.1.10:5000`
4. ✅ Funciona igual que en PC

---

## 🎯 RECOMENDACIONES:

### PC Servidor debe tener:
- ✅ 8GB RAM mínimo
- ✅ Windows 10/11
- ✅ Conexión por cable (no WiFi)
- ✅ Quedar prendida siempre
- ✅ IP fija (configurar en router)

### Para 5+ usuarios simultáneos:
```python
app.run(
    host='0.0.0.0',
    port=5000,
    debug=False,
    threaded=True,
    processes=2  # Agregar esta línea para más procesos
)
```

---

## 📊 MONITOREO:

Ver quién está conectado (en consola del servidor):
```
127.0.0.1 - - [13/Feb/2026 15:40:03] "GET /ventas/activas HTTP/1.1" 200
192.168.1.15 - - [13/Feb/2026 15:40:05] "POST /nueva-venta/guardar HTTP/1.1" 302
192.168.1.20 - - [13/Feb/2026 15:40:10] "GET /stock HTTP/1.1" 200
```

Cada línea muestra:
- IP del cliente
- Acción que hizo
- Código de respuesta

---

## ✅ RESUMEN:

1. Cambiar `app.run()` a `host='0.0.0.0'`
2. Configurar MySQL para conexiones remotas
3. Abrir puerto 5000 en firewall
4. Clientes acceden a `http://IP_SERVIDOR:5000`

---

**¡Listo para red!** 🌐
