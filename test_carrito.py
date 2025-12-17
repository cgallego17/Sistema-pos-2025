"""
Script de prueba simple para el sistema de carrito por pestaña
Ejecutar con: python manage.py shell
Luego copiar y pegar este código
"""

import os
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sistema_pos.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.auth import get_user_model
from pos.views import get_carrito, agregar_al_carrito_view
from pos.models import Producto

User = get_user_model()

print("=" * 70)
print("PRUEBA DEL SISTEMA DE CARRITO POR PESTAÑA")
print("=" * 70)

# Crear una sesión de prueba
factory = RequestFactory()
request = factory.post('/agregar_carrito/')

# Configurar sesión
middleware = SessionMiddleware(lambda req: None)
middleware.process_request(request)
request.session.save()

# Obtener usuario
usuario = User.objects.first()
if not usuario:
    print("ERROR: No hay usuarios")
    exit(1)
request.user = usuario

print(f"\n✓ Usuario: {usuario.username}")
print(f"✓ Sesión ID: {request.session.session_key}")

# Generar dos tab_ids diferentes
tab_id_1 = 'tab_1234567890_abc123'
tab_id_2 = 'tab_9876543210_xyz789'

print(f"\n✓ Tab ID Pestaña 1: {tab_id_1}")
print(f"✓ Tab ID Pestaña 2: {tab_id_2}")

# Obtener producto
producto = Producto.objects.filter(activo=True, stock__gt=0).first()
if not producto:
    print("\nERROR: No hay productos")
    exit(1)

print(f"\n✓ Producto: {producto.nombre} (Stock: {producto.stock})")

# Prueba: Carritos independientes
print("\n" + "-" * 70)
print("PRUEBA: Carritos independientes")
print("-" * 70)

# Inicialmente vacíos
carrito_1 = get_carrito(request, tab_id_1)
carrito_2 = get_carrito(request, tab_id_2)
print(f"\nCarrito 1 (inicial): {len(carrito_1)} items")
print(f"Carrito 2 (inicial): {len(carrito_2)} items")

# Agregar a pestaña 1
request.POST = {
    'producto_id': str(producto.id),
    'cantidad': '2',
    'tab_id': tab_id_1,
    'csrfmiddlewaretoken': 'test'
}
print(f"\n→ Agregando 2 unidades a Pestaña 1...")
agregar_al_carrito_view(request)

carrito_1 = get_carrito(request, tab_id_1)
carrito_2 = get_carrito(request, tab_id_2)

print(f"Carrito 1: {len(carrito_1)} items")
print(f"Carrito 2: {len(carrito_2)} items (debe estar vacío)")

if len(carrito_1) == 1 and len(carrito_2) == 0:
    print("✓ ÉXITO: Carritos independientes funcionando")
else:
    print("✗ ERROR: Los carritos se están compartiendo")

# Agregar a pestaña 2
request.POST = {
    'producto_id': str(producto.id),
    'cantidad': '3',
    'tab_id': tab_id_2,
    'csrfmiddlewaretoken': 'test'
}
print(f"\n→ Agregando 3 unidades a Pestaña 2...")
agregar_al_carrito_view(request)

carrito_1 = get_carrito(request, tab_id_1)
carrito_2 = get_carrito(request, tab_id_2)

print(f"\nCarrito 1: {len(carrito_1)} items")
for key, item in carrito_1.items():
    print(f"  - {item['nombre']}: {item['cantidad']} unidades")

print(f"Carrito 2: {len(carrito_2)} items")
for key, item in carrito_2.items():
    print(f"  - {item['nombre']}: {item['cantidad']} unidades")

if len(carrito_1) == 1 and len(carrito_2) == 1:
    item_1 = list(carrito_1.values())[0]
    item_2 = list(carrito_2.values())[0]
    if item_1['cantidad'] == 2 and item_2['cantidad'] == 3:
        print("\n✓✓✓ PRUEBA EXITOSA ✓✓✓")
        print("   Cada pestaña mantiene su propio carrito independiente")
    else:
        print("\n✗ ERROR: Las cantidades no coinciden")
else:
    print("\n✗ ERROR: Número incorrecto de items")

print("\n" + "=" * 70)







