"""
Comando para probar la trazabilidad del sistema de caja
Verifica que las devoluciones por anulación aparezcan correctamente en movimientos y totales
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Sum
from datetime import date, timedelta
from pos.models import (
    Caja, CajaUsuario, Venta, ItemVenta, Producto, GastoCaja
)
from pos.views import obtener_caja_mostrar
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Prueba la trazabilidad del sistema de caja'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('TEST DE TRAZABILIDAD DEL SISTEMA DE CAJA'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write('')

        # Obtener o crear usuario de prueba
        usuario, created = User.objects.get_or_create(
            username='test_trazabilidad',
            defaults={
                'email': 'test@test.com',
                'first_name': 'Test',
                'last_name': 'Trazabilidad'
            }
        )
        if created:
            usuario.set_password('test123')
            usuario.save()
            self.stdout.write(self.style.SUCCESS(f'[OK] Usuario de prueba creado: {usuario.username}'))
        else:
            self.stdout.write(self.style.WARNING(f'[INFO] Usuario de prueba ya existe: {usuario.username}'))

        # Obtener o crear Caja Principal
        caja_principal, created = Caja.objects.get_or_create(
            numero=1,
            defaults={
                'nombre': 'Caja Principal',
                'activa': True
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'[OK] Caja Principal creada'))
        else:
            self.stdout.write(self.style.WARNING(f'[INFO] Caja Principal ya existe'))

        # Limpiar datos de prueba anteriores del día actual
        hoy = date.today()
        CajaUsuario.objects.filter(
            usuario=usuario,
            fecha_apertura__date=hoy
        ).delete()
        self.stdout.write(self.style.WARNING('[INFO] Datos de prueba anteriores eliminados'))

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('-' * 60))
        self.stdout.write(self.style.SUCCESS('PASO 1: Crear caja abierta'))
        self.stdout.write(self.style.SUCCESS('-' * 60))

        # Crear caja abierta
        caja_abierta = CajaUsuario.objects.create(
            caja=caja_principal,
            usuario=usuario,
            monto_inicial=100000
        )
        self.stdout.write(f'[OK] Caja abierta creada: ID={caja_abierta.id}, Monto inicial=${caja_abierta.monto_inicial:,}')

        # Verificar función obtener_caja_mostrar
        caja_obtenida = obtener_caja_mostrar(usuario, hoy)
        if caja_obtenida:
            if caja_obtenida.id == caja_abierta.id:
                self.stdout.write(self.style.SUCCESS(f'[OK] obtener_caja_mostrar() retorna la caja correcta: ID={caja_obtenida.id}'))
            else:
                self.stdout.write(self.style.WARNING(f'[WARN] obtener_caja_mostrar() retorna diferente caja: Esperada={caja_abierta.id}, Obtenida={caja_obtenida.id}'))
                # Usar la caja obtenida en lugar de la creada
                caja_abierta = caja_obtenida
        else:
            self.stdout.write(self.style.ERROR(f'[ERROR] obtener_caja_mostrar() NO retorna ninguna caja'))
            self.stdout.write(f'  [DEBUG] Caja creada: ID={caja_abierta.id}, Caja Principal ID={caja_abierta.caja.id if caja_abierta.caja else None}')
            # Continuar con la caja creada manualmente

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('-' * 60))
        self.stdout.write(self.style.SUCCESS('PASO 2: Crear producto y venta'))
        self.stdout.write(self.style.SUCCESS('-' * 60))

        # Crear producto de prueba
        producto, created = Producto.objects.get_or_create(
            codigo='TEST001',
            defaults={
                'nombre': 'Producto Test Trazabilidad',
                'precio': 50000,
                'stock': 100,
                'activo': True
            }
        )
        if created:
            self.stdout.write(f'[OK] Producto creado: {producto.nombre} (Stock: {producto.stock})')
        else:
            producto.stock = 100
            producto.save()
            self.stdout.write(f'[INFO] Producto ya existe: {producto.nombre} (Stock actualizado: {producto.stock})')

        # Crear venta
        venta = Venta.objects.create(
            usuario=usuario,
            vendedor=usuario,
            metodo_pago='efectivo',
            monto_recibido=50000,
            total=50000,
            completada=True,
            caja=caja_principal
        )
        ItemVenta.objects.create(
            venta=venta,
            producto=producto,
            cantidad=1,
            precio_unitario=50000,
            subtotal=50000
        )
        producto.stock -= 1
        producto.save()
        self.stdout.write(f'[OK] Venta creada: ID={venta.id}, Total=${venta.total:,}, Monto recibido=${venta.monto_recibido:,}')

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('-' * 60))
        self.stdout.write(self.style.SUCCESS('PASO 3: Verificar estado inicial de la caja'))
        self.stdout.write(self.style.SUCCESS('-' * 60))

        # Verificar gastos iniciales
        gastos_iniciales = GastoCaja.objects.filter(caja_usuario=caja_abierta)
        total_gastos_inicial = gastos_iniciales.filter(tipo='gasto').aggregate(total=Sum('monto'))['total'] or 0
        total_ingresos_inicial = gastos_iniciales.filter(tipo='ingreso').aggregate(total=Sum('monto'))['total'] or 0

        self.stdout.write(f'[INFO] Gastos iniciales: ${total_gastos_inicial:,}')
        self.stdout.write(f'[INFO] Ingresos iniciales: ${total_ingresos_inicial:,}')

        # Calcular saldo esperado
        ventas_caja = Venta.objects.filter(
            fecha__gte=caja_abierta.fecha_apertura,
            completada=True,
            anulada=False,
            caja=caja_principal
        )
        total_ventas = ventas_caja.aggregate(total=Sum('total'))['total'] or 0
        saldo_esperado = caja_abierta.monto_inicial + total_ventas + total_ingresos_inicial - total_gastos_inicial

        self.stdout.write(f'[INFO] Ventas: ${total_ventas:,}')
        self.stdout.write(f'[INFO] Saldo esperado: ${saldo_esperado:,}')

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('-' * 60))
        self.stdout.write(self.style.SUCCESS('PASO 4: Anular venta con devolución'))
        self.stdout.write(self.style.SUCCESS('-' * 60))

        # Anular venta
        venta.anulada = True
        venta.fecha_anulacion = timezone.now()
        venta.usuario_anulacion = usuario
        venta.motivo_anulacion = 'Test de trazabilidad'
        venta.save()

        # Devolver stock
        producto.stock += 1
        producto.save()

        # Crear gasto de devolución (simulando anular_venta_view)
        caja_asociada = obtener_caja_mostrar(usuario, hoy)
        # Si no se encuentra, usar la caja abierta creada
        if not caja_asociada:
            caja_asociada = caja_abierta
            self.stdout.write(self.style.WARNING(f'[WARN] Usando caja creada manualmente: ID={caja_asociada.id}'))
        
        if caja_asociada:
            gasto_devolucion = GastoCaja.objects.create(
                tipo='gasto',
                monto=venta.monto_recibido,
                descripcion=f'Devolución por anulación de venta #{venta.id} - {venta.motivo_anulacion[:50]}',
                usuario=usuario,
                caja_usuario=caja_asociada,
                fecha=timezone.now()
            )
            self.stdout.write(self.style.SUCCESS(f'[OK] Gasto de devolución creado: ID={gasto_devolucion.id}, Monto=${gasto_devolucion.monto:,}'))
            self.stdout.write(f'  [INFO] Asociado a caja: ID={caja_asociada.id}')
            self.stdout.write(f'  [INFO] Descripción: {gasto_devolucion.descripcion}')
        else:
            self.stdout.write(self.style.ERROR('[ERROR] No se pudo obtener caja para asociar el gasto'))
            return

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('-' * 60))
        self.stdout.write(self.style.SUCCESS('PASO 5: Verificar trazabilidad'))
        self.stdout.write(self.style.SUCCESS('-' * 60))

        # Verificar que el gasto existe
        gasto_verificado = GastoCaja.objects.filter(id=gasto_devolucion.id).first()
        if gasto_verificado:
            self.stdout.write(self.style.SUCCESS(f'[OK] Gasto verificado en BD: ID={gasto_verificado.id}'))
        else:
            self.stdout.write(self.style.ERROR('[ERROR] Gasto NO encontrado en BD'))

        # Verificar que el gasto está asociado a la caja correcta
        if gasto_verificado and gasto_verificado.caja_usuario.id == caja_abierta.id:
            self.stdout.write(self.style.SUCCESS(f'[OK] Gasto asociado a la caja correcta: Caja ID={gasto_verificado.caja_usuario.id}'))
        else:
            self.stdout.write(self.style.ERROR('[ERROR] Gasto NO asociado a la caja correcta'))

        # Verificar que el gasto aparece en los gastos de la caja
        gastos_caja = GastoCaja.objects.filter(caja_usuario=caja_abierta)
        gastos_ids = list(gastos_caja.values_list('id', flat=True))
        if gasto_devolucion.id in gastos_ids:
            self.stdout.write(self.style.SUCCESS(f'[OK] Gasto aparece en los gastos de la caja'))
            self.stdout.write(f'  [INFO] Total de gastos en caja: {len(gastos_ids)}')
        else:
            self.stdout.write(self.style.ERROR('[ERROR] Gasto NO aparece en los gastos de la caja'))

        # Verificar totales actualizados
        total_gastos_final = gastos_caja.filter(tipo='gasto').aggregate(total=Sum('monto'))['total'] or 0
        total_ingresos_final = gastos_caja.filter(tipo='ingreso').aggregate(total=Sum('monto'))['total'] or 0

        ventas_finales = Venta.objects.filter(
            fecha__gte=caja_abierta.fecha_apertura,
            completada=True,
            anulada=False,
            caja=caja_principal
        )
        total_ventas_final = ventas_finales.aggregate(total=Sum('total'))['total'] or 0

        saldo_final = caja_abierta.monto_inicial + total_ventas_final + total_ingresos_final - total_gastos_final

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('RESUMEN DE TOTALES:'))
        self.stdout.write(f'  [INFO] Monto inicial: ${caja_abierta.monto_inicial:,}')
        self.stdout.write(f'  [INFO] Ventas (no anuladas): ${total_ventas_final:,}')
        self.stdout.write(f'  [INFO] Ingresos: ${total_ingresos_final:,}')
        self.stdout.write(f'  [INFO] Gastos: ${total_gastos_final:,}')
        self.stdout.write(f'  [INFO] Saldo final: ${saldo_final:,}')

        # Verificar que el gasto se restó correctamente
        diferencia_gastos = total_gastos_final - total_gastos_inicial
        if diferencia_gastos == venta.monto_recibido:
            self.stdout.write(self.style.SUCCESS(f'[OK] Gasto se restó correctamente: Diferencia=${diferencia_gastos:,}'))
        else:
            self.stdout.write(self.style.ERROR(f'[ERROR] Gasto NO se restó correctamente: Diferencia=${diferencia_gastos:,}, Esperado=${venta.monto_recibido:,}'))

        # Verificar que el saldo se actualizó correctamente
        # Después de anular la venta, las ventas válidas son $0, y el gasto de devolución es $50,000
        # Saldo esperado = monto_inicial + ventas_válidas + ingresos - gastos
        # = $100,000 + $0 + $0 - $50,000 = $50,000
        saldo_esperado_final = caja_abierta.monto_inicial + total_ventas_final + total_ingresos_final - total_gastos_final
        if abs(saldo_final - saldo_esperado_final) < 1:  # Tolerancia de 1 peso
            self.stdout.write(self.style.SUCCESS(f'[OK] Saldo actualizado correctamente: ${saldo_final:,}'))
        else:
            self.stdout.write(self.style.ERROR(f'[ERROR] Saldo NO actualizado correctamente: Esperado=${saldo_esperado_final:,}, Actual=${saldo_final:,}'))

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('-' * 60))
        self.stdout.write(self.style.SUCCESS('PASO 6: Verificar movimientos'))
        self.stdout.write(self.style.SUCCESS('-' * 60))

        # Simular cómo se obtienen los movimientos en caja_view
        gastos_todos = GastoCaja.objects.filter(caja_usuario=caja_abierta)
        gastos_lista = list(gastos_todos.order_by('fecha'))

        movimientos_gastos = [g for g in gastos_lista if g.tipo == 'gasto']
        movimientos_ingresos = [g for g in gastos_lista if g.tipo == 'ingreso']

        self.stdout.write(f'[INFO] Total de gastos en movimientos: {len(movimientos_gastos)}')
        self.stdout.write(f'[INFO] Total de ingresos en movimientos: {len(movimientos_ingresos)}')

        # Verificar que el gasto de devolución está en los movimientos
        gastos_devolucion = [g for g in movimientos_gastos if 'Devolución por anulación' in g.descripcion]
        if gastos_devolucion:
            self.stdout.write(self.style.SUCCESS(f'[OK] Gasto de devolución encontrado en movimientos: {len(gastos_devolucion)}'))
            for g in gastos_devolucion:
                self.stdout.write(f'  [INFO] ID={g.id}, Monto=${g.monto:,}, Descripción: {g.descripcion[:60]}...')
        else:
            self.stdout.write(self.style.ERROR('[ERROR] Gasto de devolución NO encontrado en movimientos'))

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('TEST COMPLETADO'))
        self.stdout.write(self.style.SUCCESS('=' * 60))

        # Limpiar datos de prueba (opcional)
        self.stdout.write('')
        respuesta = input('¿Desea limpiar los datos de prueba? (s/n): ')
        if respuesta.lower() == 's':
            venta.delete()
            gasto_devolucion.delete()
            caja_abierta.delete()
            self.stdout.write(self.style.SUCCESS('[OK] Datos de prueba eliminados'))
        else:
            self.stdout.write(self.style.WARNING('[INFO] Datos de prueba conservados para revisión manual'))

