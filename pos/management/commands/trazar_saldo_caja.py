# -*- coding: utf-8 -*-
"""
Comando para trazar el cálculo del saldo en caja
"""
from django.core.management.base import BaseCommand
from pos.models import Caja, CajaUsuario, Venta, GastoCaja
from django.db.models import Sum, Count
from django.utils import timezone
from datetime import date


class Command(BaseCommand):
    help = 'Traza el cálculo del saldo en caja para identificar problemas'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('TRAZABILIDAD DEL SALDO EN CAJA'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write('')
        
        # Obtener Caja Principal
        caja_principal = Caja.objects.filter(numero=1).first()
        if not caja_principal:
            self.stdout.write(self.style.ERROR('No existe la Caja Principal'))
            return
        
        # Obtener la única caja del sistema
        caja_unica = CajaUsuario.objects.filter(caja=caja_principal).order_by('-fecha_apertura').first()
        if not caja_unica:
            self.stdout.write(self.style.ERROR('No existe ninguna caja'))
            return
        
        self.stdout.write(self.style.SUCCESS(f'Caja encontrada: ID={caja_unica.id}'))
        self.stdout.write(f'  - Fecha apertura: {caja_unica.fecha_apertura}')
        self.stdout.write(f'  - Fecha cierre: {caja_unica.fecha_cierre or "Abierta"}')
        self.stdout.write(f'  - Monto inicial: ${caja_unica.monto_inicial:,}')
        self.stdout.write(f'  - Monto final: ${caja_unica.monto_final or 0:,}')
        self.stdout.write('')
        
        # Determinar período de la caja
        if caja_unica.fecha_cierre:
            inicio_periodo = caja_unica.fecha_apertura
            fin_periodo = caja_unica.fecha_cierre
            self.stdout.write(f'Período: {inicio_periodo.date()} a {fin_periodo.date()}')
        else:
            inicio_periodo = caja_unica.fecha_apertura
            fin_periodo = timezone.now()
            hoy = date.today()
            inicio_dia = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
            fin_dia = timezone.now().replace(hour=23, minute=59, second=59, microsecond=999999)
            self.stdout.write(f'Período: {inicio_dia.date()} (caja abierta)')
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('-' * 70))
        self.stdout.write(self.style.SUCCESS('1. VENTAS'))
        self.stdout.write(self.style.SUCCESS('-' * 70))
        
        # Obtener todas las ventas del período
        if caja_unica.fecha_cierre:
            ventas_todas = Venta.objects.filter(
                fecha__gte=caja_unica.fecha_apertura,
                fecha__lte=caja_unica.fecha_cierre,
                completada=True
            )
        else:
            ventas_todas = Venta.objects.filter(
                fecha__gte=inicio_dia,
                fecha__lte=fin_dia,
                completada=True
            )
        
        ventas_validas = ventas_todas.filter(anulada=False)
        ventas_anuladas = ventas_todas.filter(anulada=True)
        
        total_ventas_validas = ventas_validas.aggregate(total=Sum('total'))['total'] or 0
        total_ventas_anuladas = ventas_anuladas.aggregate(total=Sum('total'))['total'] or 0
        
        self.stdout.write(f'Total ventas válidas: ${int(total_ventas_validas):,} ({ventas_validas.count()} ventas)')
        self.stdout.write(f'Total ventas anuladas: ${int(total_ventas_anuladas):,} ({ventas_anuladas.count()} ventas)')
        self.stdout.write('')
        
        # Detalle de ventas anuladas
        if ventas_anuladas.exists():
            self.stdout.write('  Detalle ventas anuladas:')
            for venta in ventas_anuladas.order_by('fecha'):
                self.stdout.write(f'    - Venta #{venta.id}: ${venta.total:,} ({venta.get_metodo_pago_display()})')
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('-' * 70))
        self.stdout.write(self.style.SUCCESS('2. GASTOS E INGRESOS'))
        self.stdout.write(self.style.SUCCESS('-' * 70))
        
        # Obtener todos los gastos e ingresos
        gastos_todos = GastoCaja.objects.filter(caja_usuario=caja_unica)
        gastos = gastos_todos.filter(tipo='gasto')
        ingresos = gastos_todos.filter(tipo='ingreso')
        
        total_gastos = gastos.aggregate(total=Sum('monto'))['total'] or 0
        total_ingresos = ingresos.aggregate(total=Sum('monto'))['total'] or 0
        
        self.stdout.write(f'Total gastos: ${int(total_gastos):,} ({gastos.count()} gastos)')
        self.stdout.write(f'Total ingresos: ${int(total_ingresos):,} ({ingresos.count()} ingresos)')
        self.stdout.write('')
        
        # Detalle de gastos
        if gastos.exists():
            self.stdout.write('  Detalle gastos:')
            for gasto in gastos.order_by('fecha'):
                es_devolucion = 'Devolución por anulación' in gasto.descripcion
                tipo_gasto = 'DEVOLUCIÓN' if es_devolucion else 'GASTO'
                self.stdout.write(f'    - {tipo_gasto}: ${gasto.monto:,} - {gasto.descripcion[:60]}')
        
        # Detalle de ingresos
        if ingresos.exists():
            self.stdout.write('  Detalle ingresos:')
            for ingreso in ingresos.order_by('fecha'):
                self.stdout.write(f'    - ${ingreso.monto:,} - {ingreso.descripcion[:60]}')
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('-' * 70))
        self.stdout.write(self.style.SUCCESS('3. CÁLCULO DEL SALDO'))
        self.stdout.write(self.style.SUCCESS('-' * 70))
        
        monto_inicial = int(caja_unica.monto_inicial) if caja_unica.monto_inicial else 0
        total_ventas = int(total_ventas_validas)
        total_anuladas = int(total_ventas_anuladas)
        total_gastos_int = int(total_gastos)
        total_ingresos_int = int(total_ingresos)
        
        self.stdout.write(f'Monto inicial: ${monto_inicial:,}')
        self.stdout.write(f'Total ventas válidas: ${total_ventas:,}')
        self.stdout.write(f'Total ventas anuladas: ${total_anuladas:,}')
        self.stdout.write(f'Total ingresos: ${total_ingresos_int:,}')
        self.stdout.write(f'Total gastos: ${total_gastos_int:,}')
        self.stdout.write('')
        
        # Calcular saldo de diferentes formas
        saldo_formula_1 = monto_inicial + total_ventas - total_anuladas + total_ingresos_int - total_gastos_int
        saldo_formula_2 = monto_inicial + total_ventas + total_ingresos_int - total_gastos_int
        
        self.stdout.write(self.style.WARNING('Fórmula 1 (restando anuladas):'))
        self.stdout.write(f'  {monto_inicial:,} + {total_ventas:,} - {total_anuladas:,} + {total_ingresos_int:,} - {total_gastos_int:,} = ${saldo_formula_1:,}')
        self.stdout.write('')
        
        self.stdout.write(self.style.WARNING('Fórmula 2 (sin restar anuladas):'))
        self.stdout.write(f'  {monto_inicial:,} + {total_ventas:,} + {total_ingresos_int:,} - {total_gastos_int:,} = ${saldo_formula_2:,}')
        self.stdout.write('')
        
        # Verificar gastos de devolución
        gastos_devolucion = gastos.filter(descripcion__icontains='Devolución por anulación')
        total_gastos_devolucion = gastos_devolucion.aggregate(total=Sum('monto'))['total'] or 0
        
        self.stdout.write(self.style.SUCCESS('-' * 70))
        self.stdout.write(self.style.SUCCESS('4. ANÁLISIS DE DEVOLUCIONES'))
        self.stdout.write(self.style.SUCCESS('-' * 70))
        
        self.stdout.write(f'Total gastos de devolución: ${int(total_gastos_devolucion):,}')
        self.stdout.write(f'Total ventas anuladas: ${total_anuladas:,}')
        self.stdout.write('')
        
        if total_gastos_devolucion > 0:
            self.stdout.write('  Detalle gastos de devolución:')
            for gasto in gastos_devolucion.order_by('fecha'):
                # Extraer ID de venta de la descripción
                import re
                match = re.search(r'venta #(\d+)', gasto.descripcion, re.IGNORECASE)
                venta_id = match.group(1) if match else 'N/A'
                self.stdout.write(f'    - Venta #{venta_id}: ${gasto.monto:,}')
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('-' * 70))
        self.stdout.write(self.style.SUCCESS('5. RESUMEN'))
        self.stdout.write(self.style.SUCCESS('-' * 70))
        
        self.stdout.write(f'Monto inicial: ${monto_inicial:,}')
        self.stdout.write(f'Ventas válidas: ${total_ventas:,}')
        self.stdout.write(f'Ingresos: ${total_ingresos_int:,}')
        self.stdout.write(f'Gastos (incluye devoluciones): ${total_gastos_int:,}')
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'Saldo calculado (Fórmula 2): ${saldo_formula_2:,}'))
        
        if caja_unica.monto_final:
            self.stdout.write(self.style.WARNING(f'Monto final registrado: ${int(caja_unica.monto_final):,}'))
            diferencia = saldo_formula_2 - int(caja_unica.monto_final)
            if diferencia != 0:
                self.stdout.write(self.style.ERROR(f'Diferencia: ${diferencia:,}'))
            else:
                self.stdout.write(self.style.SUCCESS('¡El saldo cuadra!'))
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 70))




