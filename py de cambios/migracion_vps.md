# Migración Sistema Cannon a VPS con IP Argentina

## Objetivo
Migrar desde Railway (Europa) a VPS con IP argentina/brasileña para evitar el error 429 de ML.

## Proveedor recomendado
**Hostinger VPS** — plan KVM 1 (~$5-7 USD/mes)
- Elegir servidor en **São Paulo, Brasil**
- Sistema operativo: **Ubuntu 22.04**
- Panel: hPanel (amigable para usuarios sin experiencia Linux)

## Pasos de migración

### 1. Contratar VPS
- Entrar a hostinger.com.ar
- Plan VPS KVM 1 con Ubuntu 22.04 en São Paulo
- Guardar las credenciales de acceso (IP, usuario, password)

### 2. Conectarse al VPS
- Descargar **Termius** o **PuTTY** (cliente SSH para Windows)
- Conectarse con: `ssh root@IP_DEL_VPS`

### 3. Instalar dependencias en el VPS
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install python3 python3-pip python3-venv mysql-server nginx git -y
```

### 4. Configurar MySQL en el VPS
```bash
sudo mysql_secure_installation
mysql -u root -p
CREATE DATABASE inventario_cannon CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'cannon'@'localhost' IDENTIFIED BY 'password_seguro';
GRANT ALL PRIVILEGES ON inventario_cannon.* TO 'cannon'@'localhost';
FLUSH PRIVILEGES;
```

### 5. Exportar DB de Railway e importar al VPS
```bash
# Desde tu PC local, exportar con el .bat que ya tenés:
# backup_cannon.bat → genera backup_cannon_FECHA.sql

# Subir el .sql al VPS (desde tu PC):
scp backup_cannon_FECHA.sql root@IP_DEL_VPS:/home/

# En el VPS, importar:
mysql -u cannon -p inventario_cannon < /home/backup_cannon_FECHA.sql
```

### 6. Clonar el repositorio en el VPS
```bash
git clone https://github.com/TU_USUARIO/sistema-mercadomuebles /home/cannon/app
cd /home/cannon/app
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 7. Configurar el .env en el VPS
Crear archivo `config/.env`:
```
DB_HOST=localhost
DB_PORT=3306
DB_NAME=inventario_cannon
DB_USER=cannon
DB_PASSWORD=password_seguro
SECRET_KEY=clave_super_secreta_sistema_cannon_2026
FLASK_ENV=production
DEBUG=False
ML_REDIRECT_URI=https://mercadomuebles.com.ar/ml/callback
ML_APP_ID=2109946238600277
ML_SECRET_KEY=FLwEh7gcKUuc5DvqgaYtO8OyrMDB9R0Z
```

### 8. Configurar Gunicorn como servicio
Crear archivo `/etc/systemd/system/cannon.service`:
```ini
[Unit]
Description=Sistema Cannon
After=network.target

[Service]
User=root
WorkingDirectory=/home/cannon/app
Environment="PATH=/home/cannon/app/venv/bin"
ExecStart=/home/cannon/app/venv/bin/gunicorn --workers 3 --bind 0.0.0.0:5000 --timeout 120 app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable cannon
sudo systemctl start cannon
```

### 9. Configurar Nginx
Crear archivo `/etc/nginx/sites-available/cannon`:
```nginx
server {
    listen 80;
    server_name mercadomuebles.com.ar www.mercadomuebles.com.ar;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        client_max_body_size 16M;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/cannon /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 10. SSL con Let's Encrypt (HTTPS gratis)
```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d mercadomuebles.com.ar -d www.mercadomuebles.com.ar
```

### 11. Apuntar el dominio al VPS
En el panel de tu hosting (hosting-ar.com):
- Entrar a **Dominios** → mercadomuebles.com.ar → **DNS**
- Cambiar el registro **A** para que apunte a la IP del VPS
- Cambiar el registro **www** también a la IP del VPS
- Propagar en ~24hs

### 12. Actualizar ML_REDIRECT_URI en ML Developers
- Entrar a developers.mercadolibre.com.ar
- App → Configuración → Redirect URIs
- Cambiar `https://sistema-mercadomuebles-production.up.railway.app/ml/callback`
- Por `https://mercadomuebles.com.ar/ml/callback`

### 13. Renovar el token de ML
- Entrar al sistema en el nuevo dominio
- Ir a /ventas/ml/configurar_token
- Hacer el flujo de 3 pasos para obtener nuevo token

## Notas importantes
- El token de ML está guardado en la tabla `configuracion` de la DB — se migra automáticamente con el backup
- Railway se puede mantener activo hasta confirmar que el VPS funciona bien
- Una vez confirmado, cancelar el plan de Railway
