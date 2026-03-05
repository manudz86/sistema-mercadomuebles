# ⚡ SISTEMA EN RED - PASOS RÁPIDOS

## 🎯 CONCEPTO:

1 PC (servidor) corre Flask + MySQL
Las demás PCs acceden vía navegador a `http://IP_SERVIDOR:5000`

---

## ⚡ 3 PASOS:

### 1️⃣ CAMBIAR APP.PY (al final):

```python
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
```

### 2️⃣ ABRIR FIREWALL:

```cmd
netsh advfirewall firewall add rule name="Flask Cannon" dir=in action=allow protocol=TCP localport=5000
```

### 3️⃣ CONFIGURAR MYSQL:

```sql
CREATE USER 'cannon_user'@'192.168.%' IDENTIFIED BY 'password123';
GRANT ALL PRIVILEGES ON inventario_cannon.* TO 'cannon_user'@'192.168.%';
FLUSH PRIVILEGES;
```

Actualizar en `app.py`:
```python
user='cannon_user',
password='password123',
```

---

## 🚀 USAR:

### PC Servidor:
1. Averiguar IP: `ipconfig` → Ej: 192.168.1.10
2. Iniciar: `python app.py`

### PCs Cliente:
1. Abrir Chrome
2. Ir a: `http://192.168.1.10:5000`

---

## ✅ VERIFICAR:

Desde el servidor debe funcionar:
- `http://localhost:5000` ✅
- `http://192.168.1.10:5000` ✅

Desde los clientes:
- `http://192.168.1.10:5000` ✅

---

## 📦 ARCHIVOS:

1. **GUIA_sistema_en_red.md** - Guía completa con troubleshooting
2. **CAMBIO_app_py_red.py** - Cambio específico en app.py
3. **RESUMEN_red.md** - Este archivo

---

**¡3 pasos y listo!** 🌐
