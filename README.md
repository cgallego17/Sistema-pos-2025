# Sistema POS (Point of Sale)

Sistema de punto de venta desarrollado con Django 4.1.

## Requisitos

- Python 3.8 o superior
- Django 4.1
- Pillow (para manejo de imágenes)

## Instalación

1. Instalar las dependencias:
```bash
pip install -r requirements.txt
```

2. Ejecutar las migraciones (ya están aplicadas):
```bash
python manage.py migrate
```

3. Crear un superusuario para acceder al admin:
```bash
python manage.py createsuperuser
```

4. Ejecutar el servidor:
```bash
python manage.py runserver
```

## Características

- **Gestión de Productos**: Control de inventario con códigos de barras
- **Sistema de Ventas**: Registro de ventas con múltiples métodos de pago
- **Gestión de Cajas**: Control de apertura y cierre de cajas
- **Movimientos de Stock**: Seguimiento de ingresos, salidas y ajustes
- **Gastos e Ingresos**: Registro de gastos e ingresos de caja
- **Clientes Potenciales**: Gestión de leads y contactos
- **Perfiles de Usuario**: Sistema de PIN para acceso rápido

## Acceso

- Admin: http://localhost:8000/admin/
- Sistema: http://localhost:8000/

## Modelos

- **Producto**: Productos del inventario
- **Venta**: Registro de ventas
- **ItemVenta**: Items individuales de cada venta
- **Caja**: Cajas del sistema
- **CajaUsuario**: Apertura/cierre de cajas
- **MovimientoStock**: Historial de movimientos de inventario
- **GastoCaja**: Gastos e ingresos
- **ClientePotencial**: Base de datos de clientes potenciales
- **PerfilUsuario**: Perfiles con PIN de usuario

## Notas

- La base de datos SQLite ya existe con las migraciones aplicadas
- Las imágenes se guardan en la carpeta `media/productos/`
- El proyecto usa zona horaria `America/Santiago` por defecto




