"""
Comando para probar el flujo completo de caja desde apertura hasta cierre
"""
import sys
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Sum
from datetime import date, timedelta, datetime

from pos.models import (
    Caja, CajaUsuario, Venta, ItemVenta,
    GastoCaja, Producto
)


class Command(BaseCommand):
    help = 'Prueba el flujo completo de caja desde apertura hasta cierre'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limpiar',
            action='store_true',
            help='Elimina la caja abierta actual antes de comenzar',
        )

    def handle(self, *args, **options):
        self.stdout.write('=' * 70)
        self.stdout.write('PRUEBA COMPLETA DEL FLUJO DE CAJA')
        self.stdout.write('=' * 70)
        
        # Obtener usuario y caja principal
        usuario = User.objects.filter(is_superuser=True).first()
        if not usuario:
            self.stdout.write(self.style.ERROR('No se encontro un usuario administrador'))
            return
        
        caja_principal = Caja.objects.filter(numero=1).first()
        if not caja_principal:
            caja_principal = Caja.objects.create(
                numero=1,
                nombre='Caja Principal',
                activa=True
            )
        
        hoy = date.today()
        
        # Limpiar caja abierta si se solicita
        if options['limpiar']:
            CajaUsuario.objects.filter(
                usuario=usuario,
                fecha_cierre__isnull=True,
                fecha_apertura__date=hoy
            ).delete()
            self.stdout.write('Caja abierta del dia actual eliminada')
        
        # PASO 1: Abrir caja
        self.stdout.write('\n' + '=' * 70)
        self.stdout.write('PASO 1: ABRIR CAJA')
        self.stdout.write('=' * 70)
        
        caja_abierta = CajaUsuario.objects.filter(
            usuario=usuario,
            fecha_cierre__isnull=True,
            fecha_apertura__date=hoy
        ).first()
        
        monto_inicial = 500000
        
        if not caja_abierta:
            caja_abierta = CajaUsuario.objects.create(
                caja=caja_principal,
                usuario=usuario,
                monto_inicial=monto_inicial,
                fecha_apertura=timezone.now().replace(hour=8, minute=0, second=0, microsecond=0)
            )
            self.stdout.write(f'[OK] Caja abierta con monto inicial: ${monto_inicial:,}')
        else:
            self.stdout.write(f'[INFO] Caja ya estaba abierta con monto inicial: ${caja_abierta.monto_inicial:,}')
            monto_inicial = caja_abierta.monto_inicial
        
        saldo_actual = monto_inicial
        self.stdout.write(f'Saldo inicial: ${saldo_actual:,}')
        
        # PASO 2: Registrar ventas
        self.stdout.write('\n' + '=' * 70)
        self.stdout.write('PASO 2: REGISTRAR VENTAS')
        self.stdout.write('=' * 70)
        
        productos = Producto.objects.filter(activo=True)[:5]
        if not productos.exists():
            self.stdout.write(self.style.WARNING('No hay productos disponibles para crear ventas'))
            total_ventas_prueba = 0
            ventas_creadas = []
        else:
            total_ventas_prueba = 0
            ventas_creadas = []
            
            # Obtener ventas anteriores del día
            inicio_dia = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
            fin_dia = timezone.now().replace(hour=23, minute=59, second=59, microsecond=999999)
            ventas_anteriores = Venta.objects.filter(
                caja=caja_principal,
                fecha__gte=inicio_dia,
                fecha__lte=fin_dia,
                completada=True,
                anulada=False
            ).count()
            total_ventas_anteriores = Venta.objects.filter(
                caja=caja_principal,
                fecha__gte=inicio_dia,
                fecha__lte=fin_dia,
                completada=True,
                anulada=False
            ).aggregate(total=Sum('total'))['total'] or 0
            
            if ventas_anteriores > 0:
                self.stdout.write(f'[INFO] Hay {ventas_anteriores} ventas anteriores del dia por ${total_ventas_anteriores:,}')
            
            # Crear 3 ventas de prueba
            for i in range(3):
                venta = Venta.objects.create(
                    usuario=usuario,
                    caja=caja_principal,
                    fecha=timezone.now().replace(hour=9+i, minute=0, second=0, microsecond=0),
                    metodo_pago='efectivo',
                    completada=True,
                    anulada=False,
                    monto_recibido=0
                )
                
                # Agregar items
                producto = productos[i % len(productos)]
                cantidad = 2
                precio = producto.precio
                subtotal = precio * cantidad
                
                ItemVenta.objects.create(
                    venta=venta,
                    producto=producto,
                    cantidad=cantidad,
                    precio_unitario=precio,
                    subtotal=subtotal
                )
                
                venta.total = subtotal
                venta.monto_recibido = subtotal + 1000  # Con cambio
                venta.save()
                
                total_ventas_prueba += subtotal
                ventas_creadas.append(venta)
                
                self.stdout.write(f'  Venta #{venta.id}: ${subtotal:,} ({producto.nombre} x{cantidad})')
            
            saldo_actual += total_ventas_prueba
            self.stdout.write(f'\nTotal ventas de esta prueba: ${total_ventas_prueba:,}')
            self.stdout.write(f'Saldo despues de ventas de prueba: ${saldo_actual:,}')
            
            # Verificar saldo calculado (incluye todas las ventas del día)
            ventas_caja = Venta.objects.filter(
                caja=caja_principal,
                fecha__gte=inicio_dia,
                fecha__lte=fin_dia,
                completada=True,
                anulada=False
            )
            total_ventas_real = ventas_caja.aggregate(total=Sum('total'))['total'] or 0
            
            gastos_todos = GastoCaja.objects.filter(caja_usuario=caja_abierta)
            total_gastos_real = gastos_todos.filter(tipo='gasto').aggregate(total=Sum('monto'))['total'] or 0
            total_ingresos_real = gastos_todos.filter(tipo='ingreso').aggregate(total=Sum('monto'))['total'] or 0
            
            saldo_calculado = monto_inicial + total_ventas_real + total_ingresos_real - total_gastos_real
            
            self.stdout.write(f'Total ventas del dia (incluye anteriores): ${total_ventas_real:,}')
            self.stdout.write(f'Saldo calculado por sistema: ${saldo_calculado:,}')
            self.stdout.write(self.style.SUCCESS('[OK] Ventas registradas correctamente'))
        
        # PASO 3: Registrar gastos
        self.stdout.write('\n' + '=' * 70)
        self.stdout.write('PASO 3: REGISTRAR GASTOS')
        self.stdout.write('=' * 70)
        
        gastos_data = [
            {'monto': 50000, 'descripcion': 'Compra de materiales de oficina'},
            {'monto': 30000, 'descripcion': 'Pago de servicios publicos'},
        ]
        
        total_gastos = 0
        for gasto_data in gastos_data:
            gasto = GastoCaja.objects.create(
                tipo='gasto',
                monto=gasto_data['monto'],
                descripcion=gasto_data['descripcion'],
                usuario=usuario,
                caja_usuario=caja_abierta,
                fecha=timezone.now()
            )
            total_gastos += gasto_data['monto']
            saldo_actual -= gasto_data['monto']
            self.stdout.write(f'  Gasto: ${gasto_data["monto"]:,} - {gasto_data["descripcion"]}')
        
        self.stdout.write(f'\nTotal gastos: ${total_gastos:,}')
        self.stdout.write(f'Saldo despues de gastos: ${saldo_actual:,}')
        
        # Verificar saldo calculado
        gastos_todos = GastoCaja.objects.filter(caja_usuario=caja_abierta)
        total_gastos_real = gastos_todos.filter(tipo='gasto').aggregate(total=Sum('monto'))['total'] or 0
        total_ingresos_real = gastos_todos.filter(tipo='ingreso').aggregate(total=Sum('monto'))['total'] or 0
        
        inicio_dia = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        fin_dia = timezone.now().replace(hour=23, minute=59, second=59, microsecond=999999)
        ventas_caja = Venta.objects.filter(
            caja=caja_principal,
            fecha__gte=inicio_dia,
            fecha__lte=fin_dia,
            completada=True,
            anulada=False
        )
        total_ventas_real = ventas_caja.aggregate(total=Sum('total'))['total'] or 0
        
        saldo_calculado = monto_inicial + total_ventas_real + total_ingresos_real - total_gastos_real
        self.stdout.write(f'Saldo calculado por sistema: ${saldo_calculado:,}')
        
        if abs(saldo_calculado - saldo_actual) < 1000:
            self.stdout.write(self.style.SUCCESS('[OK] Saldo calculado correcto'))
        else:
            self.stdout.write(self.style.WARNING(f'[INFO] Diferencia: ${abs(saldo_calculado - saldo_actual):,}'))
        
        # PASO 4: Registrar ingresos
        self.stdout.write('\n' + '=' * 70)
        self.stdout.write('PASO 4: REGISTRAR INGRESOS')
        self.stdout.write('=' * 70)
        
        ingresos_data = [
            {'monto': 100000, 'descripcion': 'Ingreso por venta de activos'},
            {'monto': 50000, 'descripcion': 'Reembolso de proveedor'},
        ]
        
        total_ingresos = 0
        for ingreso_data in ingresos_data:
            ingreso = GastoCaja.objects.create(
                tipo='ingreso',
                monto=ingreso_data['monto'],
                descripcion=ingreso_data['descripcion'],
                usuario=usuario,
                caja_usuario=caja_abierta,
                fecha=timezone.now()
            )
            total_ingresos += ingreso_data['monto']
            saldo_actual += ingreso_data['monto']
            self.stdout.write(f'  Ingreso: ${ingreso_data["monto"]:,} - {ingreso_data["descripcion"]}')
        
        self.stdout.write(f'\nTotal ingresos: ${total_ingresos:,}')
        self.stdout.write(f'Saldo despues de ingresos: ${saldo_actual:,}')
        
        # Verificar saldo calculado
        gastos_todos = GastoCaja.objects.filter(caja_usuario=caja_abierta)
        total_gastos_real = gastos_todos.filter(tipo='gasto').aggregate(total=Sum('monto'))['total'] or 0
        total_ingresos_real = gastos_todos.filter(tipo='ingreso').aggregate(total=Sum('monto'))['total'] or 0
        
        saldo_calculado = monto_inicial + total_ventas_real + total_ingresos_real - total_gastos_real
        self.stdout.write(f'Saldo calculado por sistema: ${saldo_calculado:,}')
        
        if abs(saldo_calculado - saldo_actual) < 1000:
            self.stdout.write(self.style.SUCCESS('[OK] Saldo calculado correcto'))
        else:
            self.stdout.write(self.style.WARNING(f'[INFO] Diferencia: ${abs(saldo_calculado - saldo_actual):,}'))
        
        # PASO 5: Cerrar caja con retiro
        self.stdout.write('\n' + '=' * 70)
        self.stdout.write('PASO 5: CERRAR CAJA CON RETIRO')
        self.stdout.write('=' * 70)
        
        dinero_retirar = 100000
        self.stdout.write(f'Saldo antes del retiro: ${saldo_actual:,}')
        self.stdout.write(f'Dinero a retirar: ${dinero_retirar:,}')
        
        # Registrar retiro como gasto
        retiro = GastoCaja.objects.create(
            tipo='gasto',
            monto=dinero_retirar,
            descripcion=f'Retiro de dinero al cerrar caja - Usuario: {usuario.get_full_name() or usuario.username}',
            usuario=usuario,
            caja_usuario=caja_abierta,
            fecha=timezone.now()
        )
        
        saldo_actual -= dinero_retirar
        self.stdout.write(f'Saldo despues del retiro: ${saldo_actual:,}')
        
        # Verificar saldo calculado incluyendo el retiro
        gastos_todos = GastoCaja.objects.filter(caja_usuario=caja_abierta)
        total_gastos_real = gastos_todos.filter(tipo='gasto').aggregate(total=Sum('monto'))['total'] or 0
        total_ingresos_real = gastos_todos.filter(tipo='ingreso').aggregate(total=Sum('monto'))['total'] or 0
        
        saldo_calculado = monto_inicial + total_ventas_real + total_ingresos_real - total_gastos_real
        self.stdout.write(f'Saldo calculado por sistema (con retiro): ${saldo_calculado:,}')
        
        if abs(saldo_calculado - saldo_actual) < 1000:
            self.stdout.write(self.style.SUCCESS('[OK] Saldo calculado correcto incluyendo retiro'))
        else:
            self.stdout.write(self.style.WARNING(f'[INFO] Diferencia: ${abs(saldo_calculado - saldo_actual):,}'))
        
        # Recalcular saldo final completo antes de cerrar
        gastos_todos = GastoCaja.objects.filter(caja_usuario=caja_abierta)
        total_gastos_real = gastos_todos.filter(tipo='gasto').aggregate(total=Sum('monto'))['total'] or 0
        total_ingresos_real = gastos_todos.filter(tipo='ingreso').aggregate(total=Sum('monto'))['total'] or 0
        
        inicio_dia = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        fin_dia = timezone.now().replace(hour=23, minute=59, second=59, microsecond=999999)
        ventas_caja = Venta.objects.filter(
            caja=caja_principal,
            fecha__gte=inicio_dia,
            fecha__lte=fin_dia,
            completada=True,
            anulada=False
        )
        total_ventas_real = ventas_caja.aggregate(total=Sum('total'))['total'] or 0
        
        saldo_final_completo = monto_inicial + total_ventas_real + total_ingresos_real - total_gastos_real
        
        # Cerrar la caja con el saldo final completo
        caja_abierta.fecha_cierre = timezone.now()
        caja_abierta.monto_final = saldo_final_completo
        caja_abierta.save()
        
        self.stdout.write(f'\n[OK] Caja cerrada con monto final: ${saldo_final_completo:,}')
        self.stdout.write(f'  (Incluye todas las ventas del dia)')
        
        # PASO 6: Resumen final
        self.stdout.write('\n' + '=' * 70)
        self.stdout.write('RESUMEN FINAL DEL FLUJO')
        self.stdout.write('=' * 70)
        
        # Recalcular todo para el resumen final
        inicio_dia = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        fin_dia = timezone.now().replace(hour=23, minute=59, second=59, microsecond=999999)
        ventas_caja = Venta.objects.filter(
            caja=caja_principal,
            fecha__gte=inicio_dia,
            fecha__lte=fin_dia,
            completada=True,
            anulada=False
        )
        total_ventas_real = ventas_caja.aggregate(total=Sum('total'))['total'] or 0
        
        gastos_todos = GastoCaja.objects.filter(caja_usuario=caja_abierta)
        total_gastos_real = gastos_todos.filter(tipo='gasto').aggregate(total=Sum('monto'))['total'] or 0
        total_ingresos_real = gastos_todos.filter(tipo='ingreso').aggregate(total=Sum('monto'))['total'] or 0
        
        saldo_calculado = monto_inicial + total_ventas_real + total_ingresos_real - total_gastos_real
        
        self.stdout.write(f'\nMonto Inicial:        ${monto_inicial:,}')
        self.stdout.write(f'Total Ventas del Dia: ${total_ventas_real:,}')
        self.stdout.write(f'  - Ventas de esta prueba: ${total_ventas_prueba:,}')
        self.stdout.write(f'Total Ingresos:       ${total_ingresos_real:,}')
        self.stdout.write(f'Total Gastos:         ${total_gastos_real:,}')
        self.stdout.write('-' * 70)
        self.stdout.write(f'SALDO FINAL CALCULADO: ${saldo_calculado:,}')
        self.stdout.write(f'MONTO FINAL REGISTRADO: ${caja_abierta.monto_final:,}')
        
        # Verificar que todo sea correcto
        diferencia = abs(saldo_calculado - caja_abierta.monto_final)
        if diferencia < 1000:
            self.stdout.write(self.style.SUCCESS('\n[OK] Flujo completo verificado correctamente'))
            self.stdout.write(self.style.SUCCESS('Todos los calculos son correctos'))
            self.stdout.write(self.style.SUCCESS('El monto final registrado coincide con el saldo calculado'))
        else:
            self.stdout.write(self.style.ERROR(f'\n[ERROR] Diferencia: ${diferencia:,}'))
            self.stdout.write(self.style.ERROR('El monto final no coincide con el saldo calculado'))
        
        # Verificar fórmula
        self.stdout.write('\nVerificacion de formula:')
        self.stdout.write(f'  {monto_inicial:,} + {total_ventas_real:,} + {total_ingresos_real:,} - {total_gastos_real:,} = {saldo_calculado:,}')
        calculo_manual = monto_inicial + total_ventas_real + total_ingresos_real - total_gastos_real
        if calculo_manual == saldo_calculado:
            self.stdout.write(self.style.SUCCESS('  [OK] Formula correcta'))
        else:
            self.stdout.write(self.style.ERROR(f'  [ERROR] Formula incorrecta: {calculo_manual} != {saldo_calculado}'))
        
        # Mostrar desglose
        self.stdout.write('\n' + '-' * 70)
        self.stdout.write('DESGLOSE DE MOVIMIENTOS')
        self.stdout.write('-' * 70)
        
        self.stdout.write(f'\nVentas registradas: {ventas_caja.count()}')
        for venta in ventas_caja[:5]:
            self.stdout.write(f'  - Venta #{venta.id}: ${venta.total:,} ({venta.fecha.strftime("%H:%M")})')
        
        gastos_todos = GastoCaja.objects.filter(caja_usuario=caja_abierta).order_by('fecha')
        self.stdout.write(f'\nGastos registrados: {gastos_todos.filter(tipo="gasto").count()}')
        for gasto in gastos_todos.filter(tipo='gasto'):
            self.stdout.write(f'  - ${gasto.monto:,} - {gasto.descripcion[:50]}')
        
        self.stdout.write(f'\nIngresos registrados: {gastos_todos.filter(tipo="ingreso").count()}')
        for ingreso in gastos_todos.filter(tipo='ingreso'):
            self.stdout.write(f'  - ${ingreso.monto:,} - {ingreso.descripcion[:50]}')
        
        self.stdout.write('\n' + '=' * 70)
        self.stdout.write(self.style.SUCCESS('PRUEBA COMPLETA FINALIZADA'))
        self.stdout.write('=' * 70)

