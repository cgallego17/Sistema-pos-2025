"""
Comando para diagnosticar el estado de la caja y verificar cálculos
"""
import sys
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Sum
from datetime import date

from pos.models import (
    CajaUsuario, Caja, Venta, GastoCaja
)


class Command(BaseCommand):
    help = 'Diagnostica el estado de la caja y verifica los cálculos'

    def handle(self, *args, **options):
        hoy = date.today()
        
        self.stdout.write('=' * 70)
        self.stdout.write('DIAGNÓSTICO DE CAJA')
        self.stdout.write('=' * 70)
        self.stdout.write(f'\nFecha: {hoy.strftime("%d/%m/%Y")}')
        
        # Buscar caja abierta o cerrada del día
        caja_abierta = CajaUsuario.objects.filter(
            fecha_cierre__isnull=True,
            fecha_apertura__date=hoy
        ).first()
        
        caja_cerrada = CajaUsuario.objects.filter(
            fecha_cierre__isnull=False,
            fecha_apertura__date=hoy
        ).order_by('-fecha_cierre').first()
        
        caja_mostrar = caja_abierta or caja_cerrada
        
        if not caja_mostrar:
            self.stdout.write(self.style.WARNING('\nNo hay caja abierta o cerrada para hoy'))
            return
        
        estado = "ABIERTA" if caja_abierta else "CERRADA"
        self.stdout.write(f'\nEstado de la caja: {estado}')
        self.stdout.write(f'Usuario: {caja_mostrar.usuario.get_full_name() or caja_mostrar.usuario.username}')
        self.stdout.write(f'Fecha Apertura: {caja_mostrar.fecha_apertura.strftime("%d/%m/%Y %H:%M:%S")}')
        if caja_mostrar.fecha_cierre:
            self.stdout.write(f'Fecha Cierre: {caja_mostrar.fecha_cierre.strftime("%d/%m/%Y %H:%M:%S")}')
        self.stdout.write(f'Monto Inicial: ${caja_mostrar.monto_inicial:,}')
        if caja_mostrar.monto_final:
            self.stdout.write(f'Monto Final: ${caja_mostrar.monto_final:,}')
        
        # Calcular ventas del día
        inicio_dia = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        fin_dia = timezone.now().replace(hour=23, minute=59, second=59, microsecond=999999)
        
        caja_principal = Caja.objects.filter(numero=1).first()
        if caja_principal:
            ventas_caja = Venta.objects.filter(
                caja=caja_principal,
                fecha__gte=inicio_dia,
                fecha__lte=fin_dia,
                completada=True,
                anulada=False
            )
            total_ventas = ventas_caja.aggregate(total=Sum('total'))['total'] or 0
            total_ventas = int(total_ventas)
            cantidad_ventas = ventas_caja.count()
        else:
            total_ventas = 0
            cantidad_ventas = 0
        
        self.stdout.write(f'\n--- VENTAS ---')
        self.stdout.write(f'Cantidad de ventas: {cantidad_ventas}')
        self.stdout.write(f'Total ventas: ${total_ventas:,}')
        
        # Calcular gastos e ingresos
        gastos_todos = GastoCaja.objects.filter(caja_usuario=caja_mostrar)
        total_gastos_raw = gastos_todos.filter(tipo='gasto').aggregate(total=Sum('monto'))['total'] or 0
        total_ingresos_raw = gastos_todos.filter(tipo='ingreso').aggregate(total=Sum('monto'))['total'] or 0
        
        total_gastos = int(total_gastos_raw)
        total_ingresos = int(total_ingresos_raw)
        
        self.stdout.write(f'\n--- GASTOS E INGRESOS ---')
        self.stdout.write(f'Total gastos: ${total_gastos:,}')
        self.stdout.write(f'Total ingresos: ${total_ingresos:,}')
        
        # Mostrar detalle de gastos
        gastos_detalle = gastos_todos.filter(tipo='gasto').order_by('fecha')
        if gastos_detalle.exists():
            self.stdout.write(f'\nDetalle de gastos:')
            for gasto in gastos_detalle:
                self.stdout.write(f'  - ${gasto.monto:,} - {gasto.descripcion} ({gasto.fecha.strftime("%d/%m/%Y %H:%M")})')
        
        # Mostrar detalle de ingresos
        ingresos_detalle = gastos_todos.filter(tipo='ingreso').order_by('fecha')
        if ingresos_detalle.exists():
            self.stdout.write(f'\nDetalle de ingresos:')
            for ingreso in ingresos_detalle:
                self.stdout.write(f'  + ${ingreso.monto:,} - {ingreso.descripcion} ({ingreso.fecha.strftime("%d/%m/%Y %H:%M")})')
        
        # Calcular saldo
        monto_inicial = int(caja_mostrar.monto_inicial) if caja_mostrar.monto_inicial else 0
        saldo_calculado = monto_inicial + total_ventas + total_ingresos - total_gastos
        
        self.stdout.write(f'\n--- CÁLCULO DEL SALDO ---')
        self.stdout.write(f'Monto Inicial: ${monto_inicial:,}')
        self.stdout.write(f'+ Total Ventas: ${total_ventas:,}')
        self.stdout.write(f'+ Total Ingresos: ${total_ingresos:,}')
        self.stdout.write(f'- Total Gastos: ${total_gastos:,}')
        self.stdout.write(f'= Saldo Calculado: ${saldo_calculado:,}')
        
        if caja_mostrar.monto_final:
            self.stdout.write(f'\nMonto Final (registrado): ${caja_mostrar.monto_final:,}')
            diferencia = abs(saldo_calculado - caja_mostrar.monto_final)
            if diferencia < 1000:
                self.stdout.write(self.style.SUCCESS(f'[OK] El saldo calculado coincide con el monto final'))
            else:
                self.stdout.write(self.style.WARNING(f'[INFO] Diferencia: ${diferencia:,}'))
        
        # Verificar si hay retiros
        retiros = gastos_todos.filter(tipo='gasto', descripcion__icontains='Retiro')
        if retiros.exists():
            total_retiros = retiros.aggregate(total=Sum('monto'))['total'] or 0
            total_retiros = int(total_retiros)
            self.stdout.write(f'\n--- RETIROS ---')
            self.stdout.write(f'Total retirado: ${total_retiros:,}')
            for retiro in retiros:
                self.stdout.write(f'  - ${retiro.monto:,} - {retiro.descripcion} ({retiro.fecha.strftime("%d/%m/%Y %H:%M")})')
            
            saldo_antes_retiros = monto_inicial + total_ventas + total_ingresos - (total_gastos - total_retiros)
            self.stdout.write(f'\nSaldo ANTES de retiros: ${saldo_antes_retiros:,}')
            self.stdout.write(f'Saldo DESPUÉS de retiros: ${saldo_calculado:,}')
        
        self.stdout.write('\n' + '=' * 70)






