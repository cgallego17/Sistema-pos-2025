import os
import sys
import django

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pos_system.settings')
django.setup()

from pos.models import ConteoFisico, Producto

# Buscar producto
producto = Producto.objects.filter(codigo__iexact='SALO0659').first()
if producto:
    print(f"Producto encontrado:")
    print(f"  ID: {producto.id}")
    print(f"  Codigo: {producto.codigo}")
    print(f"  Atributo: [{producto.atributo}]")
    print(f"  Tipo atributo: {type(producto.atributo)}")
    print()
    
    # Buscar conteos por código
    conteos_codigo = ConteoFisico.objects.filter(codigo__iexact='SALO0659')
    print(f"Conteos encontrados por codigo 'SALO0659': {conteos_codigo.count()}")
    for c in conteos_codigo:
        print(f"  ID: {c.id}, Codigo: [{c.codigo}], Atributo: [{c.atributo}], Tipo: {type(c.atributo)}, Cantidad: {c.cantidad_contada}, Fecha: {c.fecha_conteo}")
    print()
    
    # Buscar con atributo del producto
    atributo_producto = producto.atributo
    if atributo_producto in ('', '-', 'None', 'null') or not atributo_producto:
        atributo_buscar = None
    else:
        atributo_buscar = atributo_producto
    
    print(f"Buscando con atributo: [{atributo_buscar}] (tipo: {type(atributo_buscar)})")
    conteos_filtrados = ConteoFisico.objects.filter(
        codigo__iexact='SALO0659',
        atributo=atributo_buscar
    )
    print(f"Conteos encontrados con filtro: {conteos_filtrados.count()}")
    for c in conteos_filtrados:
        print(f"  ID: {c.id}, Cantidad: {c.cantidad_contada}, Fecha: {c.fecha_conteo}")
else:
    print("Producto no encontrado")
    
# Mostrar todos los conteos físicos recientes
print("\n" + "="*80)
print("Todos los conteos físicos recientes (últimos 10):")
conteos_todos = ConteoFisico.objects.all().order_by('-fecha_conteo')[:10]
for c in conteos_todos:
    print(f"  Codigo: [{c.codigo}], Atributo: [{c.atributo}], Cantidad: {c.cantidad_contada}, Fecha: {c.fecha_conteo}")

