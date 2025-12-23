#!/usr/bin/env python
"""
Script para generar reporte de movimientos del producto SALO0659
"""
import os
import sys
import django
from datetime import datetime

# Configurar Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'miapp.settings')
django.setup()

from pos.models import (
    Producto, MovimientoStock, ItemVenta, Venta,
    ItemIngresoMercancia, IngresoMercancia,
    ItemSalidaMercancia, SalidaMercancia,
    ConteoFisico
)
from django.db.models import Sum, Q

def generar_reporte(codigo_producto='SALO0659'):
    """Genera un reporte completo de movimientos para un producto"""
    
    print("=" * 80)
    print(f"REPORTE DE MOVIMIENTOS - PRODUCTO: {codigo_producto}")
    print("=" * 80)
    print()
    
    # Buscar productos con ese código (puede haber varios con diferentes atributos)
    productos = Producto.objects.filter(codigo__iexact=codigo_producto)
    
    if not productos.exists():
        print(f"❌ No se encontró ningún producto con código: {codigo_producto}")
        return
    
    print(f"📦 PRODUCTOS ENCONTRADOS: {productos.count()}")
    print("-" * 80)
    for prod in productos:
        atributo = prod.atributo if prod.atributo else '(sin atributo)'
        print(f"  • ID: {prod.id} | Nombre: {prod.nombre} | Atributo: {atributo} | Stock Actual: {prod.stock}")
    print()
    
    total_ingresos = 0
    total_salidas = 0
    total_ajustes = 0
    total_ventas = 0
    total_ingresos_mercancia = 0
    total_salidas_mercancia = 0
    
    for producto in productos:
        print("=" * 80)
        atributo = producto.atributo if producto.atributo else '(sin atributo)'
        print(f"PRODUCTO: {producto.nombre} | Atributo: {atributo}")
        print("=" * 80)
        print()
        
        # 1. MOVIMIENTOS DE STOCK
        print("📊 MOVIMIENTOS DE STOCK (MovimientoStock)")
        print("-" * 80)
        movimientos = MovimientoStock.objects.filter(producto=producto).order_by('-fecha')
        
        if movimientos.exists():
            ingresos = movimientos.filter(tipo='ingreso')
            salidas = movimientos.filter(tipo='salida')
            ajustes = movimientos.filter(tipo='ajuste')
            
            total_ingresos += ingresos.aggregate(Sum('cantidad'))['cantidad__sum'] or 0
            total_salidas += salidas.aggregate(Sum('cantidad'))['cantidad__sum'] or 0
            total_ajustes += ajustes.aggregate(Sum('cantidad'))['cantidad__sum'] or 0
            
            print(f"  Total Ingresos: {ingresos.aggregate(Sum('cantidad'))['cantidad__sum'] or 0}")
            print(f"  Total Salidas: {salidas.aggregate(Sum('cantidad'))['cantidad__sum'] or 0}")
            print(f"  Total Ajustes: {ajustes.aggregate(Sum('cantidad'))['cantidad__sum'] or 0}")
            print()
            print("  Detalle de movimientos (últimos 20):")
            for mov in movimientos[:20]:
                fecha_str = mov.fecha.strftime('%Y-%m-%d %H:%M:%S')
                usuario_str = mov.usuario.username if mov.usuario else 'N/A'
                print(f"    [{fecha_str}] {mov.tipo.upper():10} | Cantidad: {mov.cantidad:6} | "
                      f"Stock: {mov.stock_anterior} → {mov.stock_nuevo} | Usuario: {usuario_str}")
                if mov.motivo:
                    print(f"      Motivo: {mov.motivo[:100]}")
        else:
            print("  No hay movimientos de stock registrados")
        print()
        
        # 2. VENTAS (ItemVenta)
        print("💰 VENTAS (ItemVenta)")
        print("-" * 80)
        ventas = ItemVenta.objects.filter(
            producto=producto,
            venta__completada=True,
            venta__anulada=False
        ).order_by('-venta__fecha')
        
        if ventas.exists():
            total_ventas_producto = ventas.aggregate(Sum('cantidad'))['cantidad__sum'] or 0
            total_ventas += total_ventas_producto
            print(f"  Total Ventas: {total_ventas_producto} unidades")
            print()
            print("  Detalle de ventas (últimos 20):")
            for item in ventas[:20]:
                venta = item.venta
                fecha_str = venta.fecha.strftime('%Y-%m-%d %H:%M:%S')
                print(f"    [{fecha_str}] Cantidad: {item.cantidad:6} | "
                      f"Precio Unit: ${item.precio_unitario:,} | Total: ${item.subtotal:,} | "
                      f"Venta ID: {venta.id}")
        else:
            print("  No hay ventas registradas")
        print()
        
        # 3. INGRESOS DE MERCANCÍA
        print("📥 INGRESOS DE MERCANCÍA (ItemIngresoMercancia)")
        print("-" * 80)
        ingresos_merc = ItemIngresoMercancia.objects.filter(producto=producto).order_by('-ingreso__fecha')
        
        if ingresos_merc.exists():
            total_ingresos_merc_producto = ingresos_merc.aggregate(Sum('cantidad'))['cantidad__sum'] or 0
            total_ingresos_mercancia += total_ingresos_merc_producto
            print(f"  Total Ingresos de Mercancía: {total_ingresos_merc_producto} unidades")
            print()
            print("  Detalle de ingresos (últimos 20):")
            for item in ingresos_merc[:20]:
                ingreso = item.ingreso
                fecha_str = ingreso.fecha.strftime('%Y-%m-%d %H:%M:%S')
                print(f"    [{fecha_str}] Cantidad: {item.cantidad:6} | "
                      f"Ingreso ID: {ingreso.id} | Proveedor: {ingreso.proveedor or 'N/A'}")
        else:
            print("  No hay ingresos de mercancía registrados")
        print()
        
        # 4. SALIDAS DE MERCANCÍA
        print("📤 SALIDAS DE MERCANCÍA (ItemSalidaMercancia)")
        print("-" * 80)
        salidas_merc = ItemSalidaMercancia.objects.filter(producto=producto).order_by('-salida__fecha')
        
        if salidas_merc.exists():
            total_salidas_merc_producto = salidas_merc.aggregate(Sum('cantidad'))['cantidad__sum'] or 0
            total_salidas_mercancia += total_salidas_merc_producto
            print(f"  Total Salidas de Mercancía: {total_salidas_merc_producto} unidades")
            print()
            print("  Detalle de salidas (últimos 20):")
            for item in salidas_merc[:20]:
                salida = item.salida
                fecha_str = salida.fecha.strftime('%Y-%m-%d %H:%M:%S')
                print(f"    [{fecha_str}] Cantidad: {item.cantidad:6} | "
                      f"Salida ID: {salida.id} | Motivo: {salida.motivo[:50] if salida.motivo else 'N/A'}")
        else:
            print("  No hay salidas de mercancía registradas")
        print()
        
        # 5. CONTEO FÍSICO
        print("🔢 CONTEO FÍSICO (ConteoFisico)")
        print("-" * 80)
        conteos = ConteoFisico.objects.filter(
            codigo=producto.codigo,
            atributo=producto.atributo or ''
        ).order_by('-fecha_conteo')
        
        if conteos.exists():
            print(f"  Total Conteos Físicos: {conteos.count()}")
            print()
            print("  Detalle de conteos (últimos 10):")
            for conteo in conteos[:10]:
                fecha_str = conteo.fecha_conteo.strftime('%Y-%m-%d %H:%M:%S')
                usuario_str = conteo.usuario.username if conteo.usuario else 'N/A'
                print(f"    [{fecha_str}] Cantidad Contada: {conteo.cantidad_contada:6} | "
                      f"Usuario: {usuario_str}")
                if conteo.observaciones:
                    print(f"      Observaciones: {conteo.observaciones[:100]}")
        else:
            print("  No hay conteos físicos registrados")
        print()
    
    # RESUMEN GENERAL
    print("=" * 80)
    print("📈 RESUMEN GENERAL")
    print("=" * 80)
    print(f"  Total Ingresos (MovimientoStock):     {total_ingresos:>10}")
    print(f"  Total Salidas (MovimientoStock):      {total_salidas:>10}")
    print(f"  Total Ajustes (MovimientoStock):       {total_ajustes:>10}")
    print(f"  Total Ventas (ItemVenta):               {total_ventas:>10}")
    print(f"  Total Ingresos Mercancía:               {total_ingresos_mercancia:>10}")
    print(f"  Total Salidas Mercancía:                {total_salidas_mercancia:>10}")
    print()
    print(f"  Balance Neto (Ingresos - Salidas):     {total_ingresos - total_salidas:>10}")
    print("=" * 80)

if __name__ == '__main__':
    generar_reporte('SALO0659')

