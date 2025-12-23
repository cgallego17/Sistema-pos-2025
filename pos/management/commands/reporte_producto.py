from django.core.management.base import BaseCommand
from pos.models import (
    Producto, MovimientoStock, ItemVenta, Venta,
    ItemIngresoMercancia, IngresoMercancia,
    ItemSalidaMercancia, SalidaMercancia,
    ConteoFisico
)
from django.db.models import Sum


class Command(BaseCommand):
    help = 'Genera un reporte completo de movimientos para un producto'

    def add_arguments(self, parser):
        parser.add_argument('codigo', type=str, help='Código del producto a reportar')

    def handle(self, *args, **options):
        codigo_producto = options['codigo'].upper()
        
        self.stdout.write("=" * 80)
        self.stdout.write(self.style.SUCCESS(f"REPORTE DE MOVIMIENTOS - PRODUCTO: {codigo_producto}"))
        self.stdout.write("=" * 80)
        self.stdout.write("")
        
        # Buscar productos con ese código
        productos = Producto.objects.filter(codigo__iexact=codigo_producto)
        
        if not productos.exists():
            self.stdout.write(self.style.ERROR(f"[ERROR] No se encontro ningun producto con codigo: {codigo_producto}"))
            return
        
        self.stdout.write(f"PRODUCTOS ENCONTRADOS: {productos.count()}")
        self.stdout.write("-" * 80)
        for prod in productos:
            atributo = prod.atributo if prod.atributo else "(sin atributo)"
            # Calcular stock inicial: Stock Actual + Salidas - Ingresos
            movimientos_prod = MovimientoStock.objects.filter(producto=prod)
            total_ingresos_prod = movimientos_prod.filter(tipo='ingreso').aggregate(Sum('cantidad'))['cantidad__sum'] or 0
            total_salidas_prod = movimientos_prod.filter(tipo='salida').aggregate(Sum('cantidad'))['cantidad__sum'] or 0
            total_ajustes_prod = movimientos_prod.filter(tipo='ajuste').aggregate(Sum('cantidad'))['cantidad__sum'] or 0
            # Stock inicial = Stock actual - (Ingresos - Salidas + Ajustes)
            # O mejor: Stock inicial = Stock actual - Neto
            neto = total_ingresos_prod - total_salidas_prod + total_ajustes_prod
            stock_inicial = prod.stock - neto
            self.stdout.write(f"  • ID: {prod.id} | Nombre: {prod.nombre} | Atributo: {atributo}")
            self.stdout.write(f"    Stock Inicial: {stock_inicial} | Stock Actual: {prod.stock}")
        self.stdout.write("")
        
        total_ingresos = 0
        total_salidas = 0
        total_ajustes = 0
        total_ventas = 0
        total_ingresos_mercancia = 0
        total_salidas_mercancia = 0
        total_conteos_fisicos = 0
        cantidad_contada_total = 0
        
        for producto in productos:
            self.stdout.write("=" * 80)
            atributo = producto.atributo if producto.atributo else "(sin atributo)"
            # Calcular stock inicial para este producto
            movimientos_prod = MovimientoStock.objects.filter(producto=producto)
            total_ingresos_prod = movimientos_prod.filter(tipo='ingreso').aggregate(Sum('cantidad'))['cantidad__sum'] or 0
            total_salidas_prod = movimientos_prod.filter(tipo='salida').aggregate(Sum('cantidad'))['cantidad__sum'] or 0
            total_ajustes_prod = movimientos_prod.filter(tipo='ajuste').aggregate(Sum('cantidad'))['cantidad__sum'] or 0
            neto = total_ingresos_prod - total_salidas_prod + total_ajustes_prod
            stock_inicial = producto.stock - neto
            
            self.stdout.write(f"PRODUCTO: {producto.nombre} | Atributo: {atributo}")
            self.stdout.write(f"Stock Inicial: {stock_inicial} | Stock Actual: {producto.stock}")
            self.stdout.write("=" * 80)
            self.stdout.write("")
            
            # 1. MOVIMIENTOS DE STOCK
            self.stdout.write("[MOVIMIENTOS] MOVIMIENTOS DE STOCK (MovimientoStock)")
            self.stdout.write("-" * 80)
            movimientos = MovimientoStock.objects.filter(producto=producto).order_by('-fecha')
            
            if movimientos.exists():
                ingresos = movimientos.filter(tipo='ingreso')
                salidas = movimientos.filter(tipo='salida')
                ajustes = movimientos.filter(tipo='ajuste')
                
                # Separar salidas por tipo
                salidas_por_venta = salidas.filter(motivo__icontains='Venta')
                salidas_inventario = salidas.exclude(motivo__icontains='Venta')
                
                sum_ingresos = ingresos.aggregate(Sum('cantidad'))['cantidad__sum'] or 0
                sum_salidas = salidas.aggregate(Sum('cantidad'))['cantidad__sum'] or 0
                sum_ajustes = ajustes.aggregate(Sum('cantidad'))['cantidad__sum'] or 0
                sum_salidas_ventas = salidas_por_venta.aggregate(Sum('cantidad'))['cantidad__sum'] or 0
                sum_salidas_inv = salidas_inventario.aggregate(Sum('cantidad'))['cantidad__sum'] or 0
                
                total_ingresos += sum_ingresos
                total_salidas += sum_salidas
                total_ajustes += sum_ajustes
                
                self.stdout.write(f"  Total Ingresos: {sum_ingresos}")
                self.stdout.write(f"  Total Salidas: {sum_salidas}")
                self.stdout.write(f"    - Salidas por Ventas: {sum_salidas_ventas}")
                self.stdout.write(f"    - Salidas de Inventario: {sum_salidas_inv}")
                self.stdout.write(f"  Total Ajustes: {sum_ajustes}")
                self.stdout.write("")
                self.stdout.write("  Detalle de movimientos (ultimos 20):")
                for mov in movimientos[:20]:
                    fecha_str = mov.fecha.strftime('%Y-%m-%d %H:%M:%S')
                    usuario_str = mov.usuario.username if mov.usuario else 'N/A'
                    tipo_mov = mov.tipo.upper()
                    if mov.tipo == 'salida':
                        if mov.motivo and 'Venta' in mov.motivo:
                            tipo_mov = 'SALIDA-VENTA'
                        else:
                            tipo_mov = 'SALIDA-INV'
                    self.stdout.write(
                        f"    [{fecha_str}] {tipo_mov:15} | "
                        f"Cantidad: {mov.cantidad:6} | "
                        f"Stock: {mov.stock_anterior} -> {mov.stock_nuevo} | "
                        f"Usuario: {usuario_str}"
                    )
                    if mov.motivo:
                        motivo_short = mov.motivo[:100] + "..." if len(mov.motivo) > 100 else mov.motivo
                        self.stdout.write(f"      Motivo: {motivo_short}")
            else:
                self.stdout.write("  No hay movimientos de stock registrados")
            self.stdout.write("")
            
            # 2. VENTAS (ItemVenta)
            self.stdout.write("[VENTAS] VENTAS (ItemVenta)")
            self.stdout.write("-" * 80)
            ventas = ItemVenta.objects.filter(
                producto=producto,
                venta__completada=True,
                venta__anulada=False
            ).order_by('-venta__fecha')
            
            if ventas.exists():
                total_ventas_producto = ventas.aggregate(Sum('cantidad'))['cantidad__sum'] or 0
                total_ventas += total_ventas_producto
                self.stdout.write(f"  Total Ventas: {total_ventas_producto} unidades")
                self.stdout.write("")
                self.stdout.write("  Detalle de ventas (últimos 20):")
                for item in ventas[:20]:
                    venta = item.venta
                    fecha_str = venta.fecha.strftime('%Y-%m-%d %H:%M:%S')
                    self.stdout.write(
                        f"    [{fecha_str}] Cantidad: {item.cantidad:6} | "
                        f"Precio Unit: ${item.precio_unitario:,} | "
                        f"Total: ${item.subtotal:,} | "
                        f"Venta ID: {venta.id}"
                    )
            else:
                self.stdout.write("  No hay ventas registradas")
            self.stdout.write("")
            
            # 3. INGRESOS DE MERCANCÍA
            self.stdout.write("[INGRESOS] INGRESOS DE MERCANCIA (ItemIngresoMercancia)")
            self.stdout.write("-" * 80)
            ingresos_merc = ItemIngresoMercancia.objects.filter(producto=producto).order_by('-ingreso__fecha')
            
            if ingresos_merc.exists():
                total_ingresos_merc_producto = ingresos_merc.aggregate(Sum('cantidad'))['cantidad__sum'] or 0
                total_ingresos_mercancia += total_ingresos_merc_producto
                self.stdout.write(f"  Total Ingresos de Mercancía: {total_ingresos_merc_producto} unidades")
                self.stdout.write("")
                self.stdout.write("  Detalle de ingresos (últimos 20):")
                for item in ingresos_merc[:20]:
                    ingreso = item.ingreso
                    fecha_str = ingreso.fecha.strftime('%Y-%m-%d %H:%M:%S')
                    self.stdout.write(
                        f"    [{fecha_str}] Cantidad: {item.cantidad:6} | "
                        f"Ingreso ID: {ingreso.id} | "
                        f"Proveedor: {ingreso.proveedor or 'N/A'}"
                    )
            else:
                self.stdout.write("  No hay ingresos de mercancía registrados")
            self.stdout.write("")
            
            # 4. SALIDAS DE MERCANCÍA
            self.stdout.write("[SALIDAS] SALIDAS DE MERCANCIA (ItemSalidaMercancia)")
            self.stdout.write("-" * 80)
            salidas_merc = ItemSalidaMercancia.objects.filter(producto=producto).order_by('-salida__fecha')
            
            if salidas_merc.exists():
                total_salidas_merc_producto = salidas_merc.aggregate(Sum('cantidad'))['cantidad__sum'] or 0
                total_salidas_mercancia += total_salidas_merc_producto
                self.stdout.write(f"  Total Salidas de Mercancía: {total_salidas_merc_producto} unidades")
                self.stdout.write("")
                self.stdout.write("  Detalle de salidas (últimos 20):")
                for item in salidas_merc[:20]:
                    salida = item.salida
                    fecha_str = salida.fecha.strftime('%Y-%m-%d %H:%M:%S')
                    motivo_short = (salida.motivo[:50] + "...") if salida.motivo and len(salida.motivo) > 50 else (salida.motivo or 'N/A')
                    self.stdout.write(
                        f"    [{fecha_str}] Cantidad: {item.cantidad:6} | "
                        f"Salida ID: {salida.id} | "
                        f"Motivo: {motivo_short}"
                    )
            else:
                self.stdout.write("  No hay salidas de mercancía registradas")
            self.stdout.write("")
            
            # 5. CONTEO FÍSICO
            self.stdout.write("[CONTEO] CONTEO FISICO (ConteoFisico)")
            self.stdout.write("-" * 80)
            # Normalizar atributo: quitar espacios y convertir valores vacíos a None
            atributo_buscar = producto.atributo
            if atributo_buscar:
                atributo_buscar = atributo_buscar.strip()  # Quitar espacios al inicio y final
                if atributo_buscar in ('', '-', 'None', 'null'):
                    atributo_buscar = None
            else:
                atributo_buscar = None
            
            # Buscar conteos con el código (case insensitive) y atributo normalizado
            # Primero buscar por código, luego filtrar por atributo normalizado
            conteos_codigo = ConteoFisico.objects.filter(codigo__iexact=producto.codigo)
            conteos = []
            for conteo in conteos_codigo:
                # Normalizar atributo del conteo para comparar
                atributo_conteo = conteo.atributo
                if atributo_conteo:
                    atributo_conteo = atributo_conteo.strip()
                    if atributo_conteo in ('', '-', 'None', 'null'):
                        atributo_conteo = None
                else:
                    atributo_conteo = None
                
                # Comparar atributos normalizados
                if atributo_buscar == atributo_conteo:
                    conteos.append(conteo)
            
            # Ordenar por fecha
            conteos = sorted(conteos, key=lambda x: x.fecha_conteo, reverse=True)
            
            if conteos:
                total_conteos_fisicos += len(conteos)
                # Obtener el último conteo (más reciente) para este producto
                ultimo_conteo = conteos[0] if conteos else None
                if ultimo_conteo:
                    cantidad_contada_total += ultimo_conteo.cantidad_contada
                
                self.stdout.write(f"  Total Conteos Físicos: {len(conteos)}")
                if ultimo_conteo:
                    self.stdout.write(f"  Último Conteo: {ultimo_conteo.cantidad_contada} unidades")
                self.stdout.write("")
                self.stdout.write("  Detalle de conteos (últimos 10):")
                for conteo in conteos[:10]:
                    fecha_str = conteo.fecha_conteo.strftime('%Y-%m-%d %H:%M:%S')
                    usuario_str = conteo.usuario.username if conteo.usuario else 'N/A'
                    self.stdout.write(
                        f"    [{fecha_str}] Cantidad Contada: {conteo.cantidad_contada:6} | "
                        f"Usuario: {usuario_str}"
                    )
                    if conteo.observaciones:
                        obs_short = conteo.observaciones[:100] + "..." if len(conteo.observaciones) > 100 else conteo.observaciones
                        self.stdout.write(f"      Observaciones: {obs_short}")
            else:
                self.stdout.write("  No hay conteos físicos registrados")
            self.stdout.write("")
        
        # Calcular salidas por tipo desde MovimientoStock
        total_salidas_por_venta_ms = 0
        total_salidas_inventario_ms = 0
        
        for producto in productos:
            salidas_ms = MovimientoStock.objects.filter(
                producto=producto, 
                tipo='salida'
            )
            salidas_venta = salidas_ms.filter(motivo__icontains='Venta')
            salidas_inv = salidas_ms.exclude(motivo__icontains='Venta')
            total_salidas_por_venta_ms += salidas_venta.aggregate(Sum('cantidad'))['cantidad__sum'] or 0
            total_salidas_inventario_ms += salidas_inv.aggregate(Sum('cantidad'))['cantidad__sum'] or 0
        
        # Calcular stock inicial total
        stock_inicial_total = 0
        stock_actual_total = 0
        for producto in productos:
            movimientos_prod = MovimientoStock.objects.filter(producto=producto)
            total_ingresos_prod = movimientos_prod.filter(tipo='ingreso').aggregate(Sum('cantidad'))['cantidad__sum'] or 0
            total_salidas_prod = movimientos_prod.filter(tipo='salida').aggregate(Sum('cantidad'))['cantidad__sum'] or 0
            total_ajustes_prod = movimientos_prod.filter(tipo='ajuste').aggregate(Sum('cantidad'))['cantidad__sum'] or 0
            neto = total_ingresos_prod - total_salidas_prod + total_ajustes_prod
            stock_inicial_total += (producto.stock - neto)
            stock_actual_total += producto.stock
        
        # RESUMEN GENERAL
        self.stdout.write("=" * 80)
        self.stdout.write("[RESUMEN] RESUMEN GENERAL")
        self.stdout.write("=" * 80)
        self.stdout.write(f"  Stock Inicial:                          {stock_inicial_total:>10}")
        self.stdout.write(f"  Stock Actual:                           {stock_actual_total:>10}")
        self.stdout.write("")
        self.stdout.write(f"  Total Ingresos (MovimientoStock):     {total_ingresos:>10}")
        self.stdout.write(f"  Total Salidas (MovimientoStock):      {total_salidas:>10}")
        self.stdout.write(f"    - Salidas por Ventas:                {total_salidas_por_venta_ms:>10}")
        self.stdout.write(f"    - Salidas de Inventario:              {total_salidas_inventario_ms:>10}")
        self.stdout.write(f"  Total Ajustes (MovimientoStock):       {total_ajustes:>10}")
        self.stdout.write("")
        self.stdout.write(f"  Total Ventas (ItemVenta):               {total_ventas:>10}")
        self.stdout.write(f"  Total Ingresos Mercancia:               {total_ingresos_mercancia:>10}")
        self.stdout.write(f"  Total Salidas Mercancia:                {total_salidas_mercancia:>10}")
        self.stdout.write(f"  Total Conteos Físicos:                   {total_conteos_fisicos:>10}")
        if cantidad_contada_total > 0:
            self.stdout.write(f"  Cantidad Contada (Último Conteo):        {cantidad_contada_total:>10}")
        self.stdout.write("")
        self.stdout.write("  COMPARACION:")
        self.stdout.write(f"    Ventas (ItemVenta):                   {total_ventas:>10}")
        self.stdout.write(f"    Salidas por Ventas (MovStock):        {total_salidas_por_venta_ms:>10}")
        self.stdout.write(f"    Diferencia:                           {abs(total_ventas - total_salidas_por_venta_ms):>10}")
        self.stdout.write("")
        self.stdout.write(f"    Salidas Inventario (MovStock):         {total_salidas_inventario_ms:>10}")
        self.stdout.write(f"    Salidas Mercancia (ItemSalida):        {total_salidas_mercancia:>10}")
        self.stdout.write(f"    Diferencia:                           {abs(total_salidas_inventario_ms - total_salidas_mercancia):>10}")
        self.stdout.write("")
        self.stdout.write("  VERIFICACION:")
        stock_calculado = stock_inicial_total + total_ingresos - total_salidas + total_ajustes
        self.stdout.write(f"    Stock Inicial:                         {stock_inicial_total:>10}")
        self.stdout.write(f"    + Ingresos:                            {total_ingresos:>10}")
        self.stdout.write(f"    - Salidas:                             {total_salidas:>10}")
        self.stdout.write(f"    + Ajustes:                              {total_ajustes:>10}")
        self.stdout.write(f"    = Stock Final Calculado:               {stock_calculado:>10}")
        self.stdout.write(f"    Stock Actual:                          {stock_actual_total:>10}")
        self.stdout.write(f"    Diferencia:                             {abs(stock_calculado - stock_actual_total):>10}")
        self.stdout.write("")
        self.stdout.write("  RESUMEN FINAL:")
        self.stdout.write(f"    Diferencia (Ingresos - Salidas):       {total_ingresos - total_salidas:>10}")
        self.stdout.write(f"    Stock Final (Inicial + Neto):          {stock_calculado:>10}")
        if cantidad_contada_total > 0:
            diferencia_conteo = cantidad_contada_total - stock_calculado
            self.stdout.write(f"    Conteo Físico:                         {cantidad_contada_total:>10}")
            self.stdout.write(f"    Diferencia (Conteo - Stock Calculado): {diferencia_conteo:>10}")
        self.stdout.write("=" * 80)

