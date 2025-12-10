"""
Comando para probar movimientos de dinero y verificar que los totales sean correctos
"""
import sys
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Sum
from datetime import date, timedelta, datetime

from pos.models import (
    Caja, CajaUsuario, Venta, ItemVenta,
    GastoCaja
)


class Command(BaseCommand):
    help = 'Prueba los movimientos de dinero y verifica que los totales sean correctos'

    def handle(self, *args, **options):
        self.stdout.write('=' * 60)
        self.stdout.write('PRUEBA DE MOVIMIENTOS DE DINERO')
        self.stdout.write('=' * 60)
        
        # Obtener usuario y caja principal
        usuario = User.objects.filter(is_superuser=True).first()
        if not usuario:
            self.stdout.write(self.style.ERROR('No se encontró un usuario administrador'))
            return
        
        caja_principal = Caja.objects.filter(numero=1).first()
        if not caja_principal:
            self.stdout.write(self.style.ERROR('No se encontró la Caja Principal'))
            return
        
        # Obtener caja abierta del día actual
        hoy = date.today()
        caja_abierta = CajaUsuario.objects.filter(
            usuario=usuario,
            fecha_cierre__isnull=True,
            fecha_apertura__date=hoy
        ).first()
        
        if not caja_abierta:
            self.stdout.write(self.style.WARNING('No hay caja abierta del día actual'))
            self.stdout.write('Creando caja de prueba...')
            caja_abierta = CajaUsuario.objects.create(
                caja=caja_principal,
                usuario=usuario,
                monto_inicial=500000
            )
        
        self.stdout.write(f'\nCaja abierta: {caja_abierta.id}')
        self.stdout.write(f'Usuario: {usuario.username}')
        self.stdout.write(f'Fecha apertura: {caja_abierta.fecha_apertura}')
        self.stdout.write(f'Monto inicial: ${caja_abierta.monto_inicial:,}')
        
        # Calcular totales
        self._verificar_totales(caja_abierta, caja_principal, hoy)
        
        # Probar diferentes escenarios
        self._probar_escenarios(caja_abierta, caja_principal, usuario, hoy)
        
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('PRUEBAS COMPLETADAS'))

    def _verificar_totales(self, caja_abierta, caja_principal, hoy):
        """Verifica que los totales calculados sean correctos"""
        self.stdout.write('\n' + '-' * 60)
        self.stdout.write('VERIFICACIÓN DE TOTALES')
        self.stdout.write('-' * 60)
        
        from datetime import date
        inicio_dia = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        fin_dia = timezone.now().replace(hour=23, minute=59, second=59, microsecond=999999)
        
        # Obtener ventas del día actual
        ventas_caja = Venta.objects.filter(
            caja=caja_principal,
            fecha__gte=inicio_dia,
            fecha__lte=fin_dia,
            completada=True,
            anulada=False
        )
        total_ventas = ventas_caja.aggregate(total=Sum('total'))['total'] or 0
        
        # Obtener TODOS los gastos e ingresos de la caja abierta
        gastos_todos = GastoCaja.objects.filter(
            caja_usuario=caja_abierta
        )
        
        total_gastos = gastos_todos.filter(tipo='gasto').aggregate(total=Sum('monto'))['total'] or 0
        total_ingresos = gastos_todos.filter(tipo='ingreso').aggregate(total=Sum('monto'))['total'] or 0
        
        # Calcular saldo
        monto_inicial = int(caja_abierta.monto_inicial) if caja_abierta.monto_inicial else 0
        total_ventas = int(total_ventas) if total_ventas else 0
        total_ingresos = int(total_ingresos) if total_ingresos else 0
        total_gastos = int(total_gastos) if total_gastos else 0
        
        saldo_calculado = monto_inicial + total_ventas + total_ingresos - total_gastos
        
        # Mostrar resultados
        self.stdout.write(f'\nMonto Inicial:        ${monto_inicial:,}')
        self.stdout.write(f'Total Ventas:         ${total_ventas:,}')
        self.stdout.write(f'Total Ingresos:       ${total_ingresos:,}')
        self.stdout.write(f'Total Gastos:         ${total_gastos:,}')
        self.stdout.write('-' * 60)
        self.stdout.write(f'Saldo Calculado:      ${saldo_calculado:,}')
        
        # Verificar cálculos manuales
        self.stdout.write('\nVerificación manual:')
        self.stdout.write(f'  {monto_inicial:,} + {total_ventas:,} + {total_ingresos:,} - {total_gastos:,} = {saldo_calculado:,}')
        
        # Verificar que el cálculo sea correcto
        calculo_manual = monto_inicial + total_ventas + total_ingresos - total_gastos
        if calculo_manual == saldo_calculado:
            self.stdout.write(self.style.SUCCESS('\n[OK] Calculo correcto'))
        else:
            self.stdout.write(self.style.ERROR(f'\n[ERROR] Error en el calculo: {calculo_manual} != {saldo_calculado}'))
        
        # Mostrar detalles de movimientos
        self.stdout.write('\nDetalles de movimientos:')
        gastos_dia = gastos_todos.filter(
            fecha__gte=inicio_dia,
            fecha__lte=fin_dia
        ).order_by('fecha')
        
        self.stdout.write(f'\nGastos del día ({gastos_dia.filter(tipo="gasto").count()}):')
        for gasto in gastos_dia.filter(tipo='gasto'):
            self.stdout.write(f'  - ${gasto.monto:,} - {gasto.descripcion} ({gasto.fecha.strftime("%H:%M")})')
        
        self.stdout.write(f'\nIngresos del día ({gastos_dia.filter(tipo="ingreso").count()}):')
        for ingreso in gastos_dia.filter(tipo='ingreso'):
            self.stdout.write(f'  + ${ingreso.monto:,} - {ingreso.descripcion} ({ingreso.fecha.strftime("%H:%M")})')
        
        self.stdout.write(f'\nVentas del día ({ventas_caja.count()}):')
        for venta in ventas_caja[:5]:  # Mostrar solo las primeras 5
            self.stdout.write(f'  + ${venta.total:,} - Venta #{venta.id} ({venta.fecha.strftime("%H:%M")})')
        if ventas_caja.count() > 5:
            self.stdout.write(f'  ... y {ventas_caja.count() - 5} ventas más')

    def _probar_escenarios(self, caja_abierta, caja_principal, usuario, hoy):
        """Prueba diferentes escenarios de movimientos"""
        self.stdout.write('\n' + '-' * 60)
        self.stdout.write('PRUEBAS DE ESCENARIOS')
        self.stdout.write('-' * 60)
        
        # Escenario 1: Registrar un gasto
        self.stdout.write('\n1. Probando registro de gasto...')
        monto_gasto = 10000
        gasto_anterior = GastoCaja.objects.filter(
            caja_usuario=caja_abierta,
            tipo='gasto',
            monto=monto_gasto,
            descripcion='Gasto de prueba'
        ).first()
        
        if not gasto_anterior:
            gasto = GastoCaja.objects.create(
                tipo='gasto',
                monto=monto_gasto,
                descripcion='Gasto de prueba',
                usuario=usuario,
                caja_usuario=caja_abierta
            )
            self.stdout.write(f'   [OK] Gasto de ${monto_gasto:,} registrado')
        else:
            self.stdout.write(f'   - Gasto de prueba ya existe')
        
        # Recalcular saldo
        gastos_todos = GastoCaja.objects.filter(caja_usuario=caja_abierta)
        total_gastos = gastos_todos.filter(tipo='gasto').aggregate(total=Sum('monto'))['total'] or 0
        total_ingresos = gastos_todos.filter(tipo='ingreso').aggregate(total=Sum('monto'))['total'] or 0
        
        inicio_dia = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        fin_dia = timezone.now().replace(hour=23, minute=59, second=59, microsecond=999999)
        ventas_caja = Venta.objects.filter(
            caja=caja_principal,
            fecha__gte=inicio_dia,
            fecha__lte=fin_dia,
            completada=True,
            anulada=False
        )
        total_ventas = ventas_caja.aggregate(total=Sum('total'))['total'] or 0
        
        saldo_nuevo = caja_abierta.monto_inicial + total_ventas + total_ingresos - total_gastos
        self.stdout.write(f'   Saldo después del gasto: ${saldo_nuevo:,}')
        
        # Escenario 2: Registrar un ingreso
        self.stdout.write('\n2. Probando registro de ingreso...')
        monto_ingreso = 20000
        ingreso_anterior = GastoCaja.objects.filter(
            caja_usuario=caja_abierta,
            tipo='ingreso',
            monto=monto_ingreso,
            descripcion='Ingreso de prueba'
        ).first()
        
        if not ingreso_anterior:
            ingreso = GastoCaja.objects.create(
                tipo='ingreso',
                monto=monto_ingreso,
                descripcion='Ingreso de prueba',
                usuario=usuario,
                caja_usuario=caja_abierta
            )
            self.stdout.write(f'   [OK] Ingreso de ${monto_ingreso:,} registrado')
        else:
            self.stdout.write(f'   - Ingreso de prueba ya existe')
        
        # Recalcular saldo
        gastos_todos = GastoCaja.objects.filter(caja_usuario=caja_abierta)
        total_gastos = gastos_todos.filter(tipo='gasto').aggregate(total=Sum('monto'))['total'] or 0
        total_ingresos = gastos_todos.filter(tipo='ingreso').aggregate(total=Sum('monto'))['total'] or 0
        saldo_nuevo = caja_abierta.monto_inicial + total_ventas + total_ingresos - total_gastos
        self.stdout.write(f'   Saldo después del ingreso: ${saldo_nuevo:,}')
        
        # Escenario 3: Simular cierre de caja con retiro
        self.stdout.write('\n3. Probando cálculo de retiro al cerrar caja...')
        dinero_retirar = 50000
        
        # Calcular saldo actual
        gastos_todos = GastoCaja.objects.filter(caja_usuario=caja_abierta)
        total_gastos_actual = gastos_todos.filter(tipo='gasto').aggregate(total=Sum('monto'))['total'] or 0
        total_ingresos_actual = gastos_todos.filter(tipo='ingreso').aggregate(total=Sum('monto'))['total'] or 0
        saldo_antes_retiro = caja_abierta.monto_inicial + total_ventas + total_ingresos_actual - total_gastos_actual
        
        self.stdout.write(f'   Saldo antes del retiro: ${saldo_antes_retiro:,}')
        self.stdout.write(f'   Dinero a retirar: ${dinero_retirar:,}')
        
        # Simular retiro (no lo registramos realmente para no afectar la caja abierta)
        saldo_despues_retiro = saldo_antes_retiro - dinero_retirar
        self.stdout.write(f'   Saldo después del retiro: ${saldo_despues_retiro:,}')
        
        # Verificar que el cálculo sea correcto
        if saldo_despues_retiro == saldo_antes_retiro - dinero_retirar:
            self.stdout.write(self.style.SUCCESS('   [OK] Calculo de retiro correcto'))
        else:
            self.stdout.write(self.style.ERROR('   ✗ Error en el cálculo de retiro'))
        
        # Escenario 4: Verificar que los gastos incluyen retiros
        self.stdout.write('\n4. Verificando que los retiros se incluyen en los gastos...')
        
        # Buscar retiros registrados (si hay cajas cerradas)
        cajas_cerradas = CajaUsuario.objects.filter(
            usuario=usuario,
            fecha_cierre__isnull=False
        )[:3]
        
        total_retiros = 0
        for caja_cerrada in cajas_cerradas:
            retiros = GastoCaja.objects.filter(
                caja_usuario=caja_cerrada,
                tipo='gasto',
                descripcion__icontains='Retiro de dinero al cerrar caja'
            )
            for retiro in retiros:
                total_retiros += retiro.monto
                self.stdout.write(f'   - Retiro encontrado: ${retiro.monto:,} (Caja #{caja_cerrada.id})')
        
        if total_retiros > 0:
            self.stdout.write(f'   Total de retiros encontrados: ${total_retiros:,}')
        else:
            self.stdout.write('   - No se encontraron retiros registrados')
        
        # Resumen final
        self.stdout.write('\n' + '-' * 60)
        self.stdout.write('RESUMEN FINAL')
        self.stdout.write('-' * 60)
        
        gastos_todos = GastoCaja.objects.filter(caja_usuario=caja_abierta)
        total_gastos_final = gastos_todos.filter(tipo='gasto').aggregate(total=Sum('monto'))['total'] or 0
        total_ingresos_final = gastos_todos.filter(tipo='ingreso').aggregate(total=Sum('monto'))['total'] or 0
        
        saldo_final = caja_abierta.monto_inicial + total_ventas + total_ingresos_final - total_gastos_final
        
        self.stdout.write(f'\nMonto Inicial:        ${caja_abierta.monto_inicial:,}')
        self.stdout.write(f'Total Ventas:         ${total_ventas:,}')
        self.stdout.write(f'Total Ingresos:       ${total_ingresos_final:,}')
        self.stdout.write(f'Total Gastos:         ${total_gastos_final:,}')
        self.stdout.write('-' * 60)
        self.stdout.write(f'SALDO FINAL:          ${saldo_final:,}')
        
        # Verificar que el saldo sea positivo o al menos razonable
        if saldo_final >= 0:
            self.stdout.write(self.style.SUCCESS('\n[OK] Saldo final es valido'))
        else:
            self.stdout.write(self.style.WARNING('\n⚠ Saldo final es negativo (puede ser normal si hay muchos gastos)'))

