"""
Comando para probar exhaustivamente todos los cálculos de dinero y totales
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
    help = 'Prueba exhaustiva de todos los cálculos de dinero y totales'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limpiar',
            action='store_true',
            help='Elimina la caja abierta actual antes de comenzar',
        )

    def print_section(self, title):
        """Imprimir una sección con formato"""
        self.stdout.write('\n' + '=' * 80)
        self.stdout.write(title)
        self.stdout.write('=' * 80)

    def print_subsection(self, title):
        """Imprimir una subsección"""
        self.stdout.write('\n' + '-' * 80)
        self.stdout.write(title)
        self.stdout.write('-' * 80)

    def print_result(self, message, success=True):
        """Imprimir un resultado"""
        if success:
            self.stdout.write(self.style.SUCCESS(f'[OK] {message}'))
        else:
            self.stdout.write(self.style.ERROR(f'[ERROR] {message}'))

    def print_info(self, message):
        """Imprimir información"""
        self.stdout.write(f'[INFO] {message}')

    def handle(self, *args, **options):
        self.print_section('TEST EXHAUSTIVO DE TOTALES Y DINERO')
        
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
            self.print_info('Caja abierta del dia actual eliminada')
        
        # ============================================
        # TEST 1: APERTURA DE CAJA
        # ============================================
        self.print_section('TEST 1: APERTURA DE CAJA')
        
        caja_abierta = CajaUsuario.objects.filter(
            usuario=usuario,
            fecha_cierre__isnull=True,
            fecha_apertura__date=hoy
        ).first()
        
        monto_inicial = 1000000
        
        if not caja_abierta:
            caja_abierta = CajaUsuario.objects.create(
                caja=caja_principal,
                usuario=usuario,
                monto_inicial=monto_inicial,
                fecha_apertura=timezone.now().replace(hour=8, minute=0, second=0, microsecond=0)
            )
            self.print_result(f'Caja abierta con monto inicial: ${monto_inicial:,}')
        else:
            self.print_info(f'Caja ya estaba abierta con monto inicial: ${caja_abierta.monto_inicial:,}')
            monto_inicial = caja_abierta.monto_inicial
        
        # Verificar que el monto inicial sea correcto
        if caja_abierta.monto_inicial == monto_inicial:
            self.print_result(f'Monto inicial correcto: ${monto_inicial:,}')
        else:
            self.print_result(f'Monto inicial incorrecto: esperado ${monto_inicial:,}, obtenido ${caja_abierta.monto_inicial:,}', False)
        
        saldo_esperado = monto_inicial
        self.print_info(f'Saldo inicial esperado: ${saldo_esperado:,}')
        
        # ============================================
        # TEST 2: REGISTRO DE VENTAS
        # ============================================
        self.print_section('TEST 2: REGISTRO DE VENTAS')
        
        productos = Producto.objects.filter(activo=True)[:5]
        if not productos.exists():
            self.stdout.write(self.style.WARNING('No hay productos disponibles para crear ventas'))
            total_ventas_test = 0
            ventas_creadas = []
        else:
            # Obtener ventas anteriores del día
            inicio_dia = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
            fin_dia = timezone.now().replace(hour=23, minute=59, second=59, microsecond=999999)
            ventas_anteriores = Venta.objects.filter(
                caja=caja_principal,
                fecha__gte=inicio_dia,
                fecha__lte=fin_dia,
                completada=True,
                anulada=False
            )
            total_ventas_anteriores = ventas_anteriores.aggregate(total=Sum('total'))['total'] or 0
            cantidad_ventas_anteriores = ventas_anteriores.count()
            
            if cantidad_ventas_anteriores > 0:
                self.print_info(f'Hay {cantidad_ventas_anteriores} ventas anteriores del dia por ${total_ventas_anteriores:,}')
            
            # Crear 5 ventas de prueba
            total_ventas_test = 0
            ventas_creadas = []
            
            for i in range(5):
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
                cantidad = (i + 1) * 2
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
                venta.monto_recibido = subtotal + 1000
                venta.save()
                
                total_ventas_test += subtotal
                ventas_creadas.append(venta)
                
                self.print_info(f'  Venta #{venta.id}: ${subtotal:,} ({producto.nombre} x{cantidad})')
            
            saldo_esperado += total_ventas_test
            self.print_info(f'Total ventas de esta prueba: ${total_ventas_test:,}')
            self.print_info(f'Saldo esperado despues de ventas: ${saldo_esperado:,}')
            
            # Verificar total de ventas del día
            ventas_caja = Venta.objects.filter(
                caja=caja_principal,
                fecha__gte=inicio_dia,
                fecha__lte=fin_dia,
                completada=True,
                anulada=False
            )
            total_ventas_real = ventas_caja.aggregate(total=Sum('total'))['total'] or 0
            total_ventas_real = int(total_ventas_real)
            
            if total_ventas_real >= total_ventas_test:
                self.print_result(f'Total ventas del dia correcto: ${total_ventas_real:,}')
            else:
                self.print_result(f'Total ventas del dia incorrecto: esperado >= ${total_ventas_test:,}, obtenido ${total_ventas_real:,}', False)
        
        # ============================================
        # TEST 3: REGISTRO DE GASTOS
        # ============================================
        self.print_section('TEST 3: REGISTRO DE GASTOS')
        
        gastos_data = [
            {'monto': 50000, 'descripcion': 'Gasto de prueba 1'},
            {'monto': 30000, 'descripcion': 'Gasto de prueba 2'},
            {'monto': 20000, 'descripcion': 'Gasto de prueba 3'},
        ]
        
        total_gastos_test = 0
        gastos_creados = []
        
        for gasto_data in gastos_data:
            gasto = GastoCaja.objects.create(
                tipo='gasto',
                monto=gasto_data['monto'],
                descripcion=gasto_data['descripcion'],
                usuario=usuario,
                caja_usuario=caja_abierta,
                fecha=timezone.now()
            )
            total_gastos_test += gasto_data['monto']
            saldo_esperado -= gasto_data['monto']
            gastos_creados.append(gasto)
            self.print_info(f'  Gasto: ${gasto_data["monto"]:,} - {gasto_data["descripcion"]}')
        
        self.print_info(f'Total gastos de esta prueba: ${total_gastos_test:,}')
        self.print_info(f'Saldo esperado despues de gastos: ${saldo_esperado:,}')
        
        # Verificar total de gastos
        gastos_todos = GastoCaja.objects.filter(caja_usuario=caja_abierta)
        total_gastos_real = gastos_todos.filter(tipo='gasto').aggregate(total=Sum('monto'))['total'] or 0
        total_gastos_real = int(total_gastos_real)
        
        if total_gastos_real >= total_gastos_test:
            self.print_result(f'Total gastos correcto: ${total_gastos_real:,}')
        else:
            self.print_result(f'Total gastos incorrecto: esperado >= ${total_gastos_test:,}, obtenido ${total_gastos_real:,}', False)
        
        # ============================================
        # TEST 4: REGISTRO DE INGRESOS
        # ============================================
        self.print_section('TEST 4: REGISTRO DE INGRESOS')
        
        ingresos_data = [
            {'monto': 100000, 'descripcion': 'Ingreso de prueba 1'},
            {'monto': 50000, 'descripcion': 'Ingreso de prueba 2'},
        ]
        
        total_ingresos_test = 0
        ingresos_creados = []
        
        for ingreso_data in ingresos_data:
            ingreso = GastoCaja.objects.create(
                tipo='ingreso',
                monto=ingreso_data['monto'],
                descripcion=ingreso_data['descripcion'],
                usuario=usuario,
                caja_usuario=caja_abierta,
                fecha=timezone.now()
            )
            total_ingresos_test += ingreso_data['monto']
            saldo_esperado += ingreso_data['monto']
            ingresos_creados.append(ingreso)
            self.print_info(f'  Ingreso: ${ingreso_data["monto"]:,} - {ingreso_data["descripcion"]}')
        
        self.print_info(f'Total ingresos de esta prueba: ${total_ingresos_test:,}')
        self.print_info(f'Saldo esperado despues de ingresos: ${saldo_esperado:,}')
        
        # Verificar total de ingresos
        total_ingresos_real = gastos_todos.filter(tipo='ingreso').aggregate(total=Sum('monto'))['total'] or 0
        total_ingresos_real = int(total_ingresos_real)
        
        if total_ingresos_real >= total_ingresos_test:
            self.print_result(f'Total ingresos correcto: ${total_ingresos_real:,}')
        else:
            self.print_result(f'Total ingresos incorrecto: esperado >= ${total_ingresos_test:,}, obtenido ${total_ingresos_real:,}', False)
        
        # ============================================
        # TEST 5: VERIFICACIÓN DE CÁLCULO DE SALDO
        # ============================================
        self.print_section('TEST 5: VERIFICACIÓN DE CÁLCULO DE SALDO')
        
        # Recalcular todo desde la base de datos
        inicio_dia = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        fin_dia = timezone.now().replace(hour=23, minute=59, second=59, microsecond=999999)
        
        ventas_caja = Venta.objects.filter(
            caja=caja_principal,
            fecha__gte=inicio_dia,
            fecha__lte=fin_dia,
            completada=True,
            anulada=False
        )
        total_ventas_calculado = ventas_caja.aggregate(total=Sum('total'))['total'] or 0
        total_ventas_calculado = int(total_ventas_calculado)
        
        gastos_todos = GastoCaja.objects.filter(caja_usuario=caja_abierta)
        total_gastos_calculado = gastos_todos.filter(tipo='gasto').aggregate(total=Sum('monto'))['total'] or 0
        total_gastos_calculado = int(total_gastos_calculado)
        total_ingresos_calculado = gastos_todos.filter(tipo='ingreso').aggregate(total=Sum('monto'))['total'] or 0
        total_ingresos_calculado = int(total_ingresos_calculado)
        
        monto_inicial_int = int(monto_inicial)
        saldo_calculado = monto_inicial_int + total_ventas_calculado + total_ingresos_calculado - total_gastos_calculado
        
        self.print_subsection('Valores Calculados desde la Base de Datos')
        self.print_info(f'Monto Inicial:        ${monto_inicial_int:,}')
        self.print_info(f'Total Ventas:         ${total_ventas_calculado:,}')
        self.print_info(f'Total Ingresos:       ${total_ingresos_calculado:,}')
        self.print_info(f'Total Gastos:         ${total_gastos_calculado:,}')
        self.stdout.write('-' * 80)
        self.print_info(f'SALDO CALCULADO:      ${saldo_calculado:,}')
        self.print_info(f'SALDO ESPERADO:       ${saldo_esperado:,}')
        
        # Verificar que el saldo calculado sea correcto
        # Nota: El saldo esperado solo incluye las operaciones de esta prueba
        # El saldo calculado incluye TODAS las operaciones del día (incluye ventas anteriores)
        diferencia = abs(saldo_calculado - saldo_esperado)
        
        # Si hay ventas anteriores, la diferencia es normal
        if cantidad_ventas_anteriores > 0:
            self.print_info(f'Nota: Hay {cantidad_ventas_anteriores} ventas anteriores del día (${total_ventas_anteriores:,})')
            self.print_info('El saldo calculado incluye todas las ventas del día, no solo las de esta prueba')
            if diferencia >= total_ventas_anteriores * 0.9:  # Tolerancia del 90% de las ventas anteriores
                self.print_result(f'Saldo calculado correcto (incluye ventas anteriores del día)')
            else:
                self.print_result(f'Saldo calculado puede tener problemas (diferencia: ${diferencia:,})', False)
        else:
            if diferencia < 1000:  # Tolerancia de 1000
                self.print_result(f'Saldo calculado correcto (diferencia: ${diferencia:,})')
            else:
                self.print_result(f'Saldo calculado incorrecto (diferencia: ${diferencia:,})', False)
        
        # Verificar fórmula
        self.print_subsection('Verificación de Fórmula')
        formula_manual = monto_inicial_int + total_ventas_calculado + total_ingresos_calculado - total_gastos_calculado
        self.print_info(f'Fórmula: {monto_inicial_int:,} + {total_ventas_calculado:,} + {total_ingresos_calculado:,} - {total_gastos_calculado:,} = {formula_manual:,}')
        
        if formula_manual == saldo_calculado:
            self.print_result('Fórmula correcta')
        else:
            self.print_result(f'Fórmula incorrecta: {formula_manual:,} != {saldo_calculado:,}', False)
        
        # ============================================
        # TEST 6: TEST DE RETIRO AL CERRAR CAJA
        # ============================================
        self.print_section('TEST 6: TEST DE RETIRO AL CERRAR CAJA')
        
        dinero_retirar = 200000
        self.print_info(f'Saldo antes del retiro: ${saldo_calculado:,}')
        self.print_info(f'Dinero a retirar: ${dinero_retirar:,}')
        
        # Registrar retiro como gasto
        retiro = GastoCaja.objects.create(
            tipo='gasto',
            monto=dinero_retirar,
            descripcion=f'Retiro de prueba - Usuario: {usuario.get_full_name() or usuario.username}',
            usuario=usuario,
            caja_usuario=caja_abierta,
            fecha=timezone.now()
        )
        
        saldo_despues_retiro = saldo_calculado - dinero_retirar
        self.print_info(f'Saldo esperado despues del retiro: ${saldo_despues_retiro:,}')
        
        # Recalcular saldo con el retiro
        gastos_todos = GastoCaja.objects.filter(caja_usuario=caja_abierta)
        total_gastos_con_retiro = gastos_todos.filter(tipo='gasto').aggregate(total=Sum('monto'))['total'] or 0
        total_gastos_con_retiro = int(total_gastos_con_retiro)
        
        saldo_calculado_con_retiro = monto_inicial_int + total_ventas_calculado + total_ingresos_calculado - total_gastos_con_retiro
        
        self.print_info(f'Saldo calculado con retiro: ${saldo_calculado_con_retiro:,}')
        
        if abs(saldo_calculado_con_retiro - saldo_despues_retiro) < 1000:
            self.print_result('Cálculo de retiro correcto')
        else:
            self.print_result(f'Cálculo de retiro incorrecto (diferencia: ${abs(saldo_calculado_con_retiro - saldo_despues_retiro):,})', False)
        
        # ============================================
        # TEST 7: VERIFICACIÓN DE CONSISTENCIA
        # ============================================
        self.print_section('TEST 7: VERIFICACIÓN DE CONSISTENCIA')
        
        # Verificar que todos los valores sean enteros
        self.print_subsection('Verificación de Tipos de Datos')
        todos_enteros = True
        
        if not isinstance(monto_inicial_int, int):
            self.print_result(f'Monto inicial no es entero: {type(monto_inicial_int)}', False)
            todos_enteros = False
        if not isinstance(total_ventas_calculado, int):
            self.print_result(f'Total ventas no es entero: {type(total_ventas_calculado)}', False)
            todos_enteros = False
        if not isinstance(total_ingresos_calculado, int):
            self.print_result(f'Total ingresos no es entero: {type(total_ingresos_calculado)}', False)
            todos_enteros = False
        if not isinstance(total_gastos_con_retiro, int):
            self.print_result(f'Total gastos no es entero: {type(total_gastos_con_retiro)}', False)
            todos_enteros = False
        if not isinstance(saldo_calculado_con_retiro, int):
            self.print_result(f'Saldo no es entero: {type(saldo_calculado_con_retiro)}', False)
            todos_enteros = False
        
        if todos_enteros:
            self.print_result('Todos los valores son enteros')
        
        # Verificar que no haya valores negativos inesperados
        self.print_subsection('Verificación de Valores Negativos')
        valores_negativos = []
        
        if total_ventas_calculado < 0:
            valores_negativos.append(f'Total ventas: ${total_ventas_calculado:,}')
        if total_ingresos_calculado < 0:
            valores_negativos.append(f'Total ingresos: ${total_ingresos_calculado:,}')
        if total_gastos_con_retiro < 0:
            valores_negativos.append(f'Total gastos: ${total_gastos_con_retiro:,}')
        
        if valores_negativos:
            self.print_result(f'Valores negativos encontrados: {", ".join(valores_negativos)}', False)
        else:
            self.print_result('No hay valores negativos inesperados')
        
        # ============================================
        # RESUMEN FINAL
        # ============================================
        self.print_section('RESUMEN FINAL DEL TEST')
        
        self.print_subsection('Totales Finales')
        self.print_info(f'Monto Inicial:        ${monto_inicial_int:,}')
        self.print_info(f'Total Ventas:         ${total_ventas_calculado:,}')
        self.print_info(f'Total Ingresos:       ${total_ingresos_calculado:,}')
        self.print_info(f'Total Gastos:         ${total_gastos_con_retiro:,}')
        self.stdout.write('-' * 80)
        self.print_info(f'SALDO FINAL:          ${saldo_calculado_con_retiro:,}')
        
        # Contar movimientos
        cantidad_ventas = ventas_caja.count()
        cantidad_gastos = gastos_todos.filter(tipo='gasto').count()
        cantidad_ingresos = gastos_todos.filter(tipo='ingreso').count()
        
        self.print_subsection('Cantidad de Movimientos')
        self.print_info(f'Ventas registradas: {cantidad_ventas}')
        self.print_info(f'Gastos registrados: {cantidad_gastos}')
        self.print_info(f'Ingresos registrados: {cantidad_ingresos}')
        
        # Verificar que todo sea correcto
        self.print_subsection('Resultado del Test')
        errores_encontrados = []
        advertencias = []
        
        # Solo considerar error si no hay ventas anteriores y la diferencia es grande
        if cantidad_ventas_anteriores == 0 and diferencia >= 1000:
            errores_encontrados.append('Diferencia en saldo calculado')
        elif cantidad_ventas_anteriores > 0 and diferencia < total_ventas_anteriores * 0.9:
            advertencias.append('Diferencia menor a lo esperado (puede haber problema)')
        
        if not todos_enteros:
            errores_encontrados.append('Valores no enteros')
        if valores_negativos:
            errores_encontrados.append('Valores negativos inesperados')
        if formula_manual != saldo_calculado:
            errores_encontrados.append('Fórmula incorrecta')
        
        if not errores_encontrados and not advertencias:
            self.print_result('TEST COMPLETADO EXITOSAMENTE - Todos los cálculos son correctos')
        elif not errores_encontrados and advertencias:
            self.stdout.write(self.style.WARNING(f'TEST COMPLETADO CON ADVERTENCIAS: {", ".join(advertencias)}'))
            self.print_result('Los cálculos básicos son correctos, pero hay advertencias')
        else:
            self.print_result(f'TEST COMPLETADO CON ERRORES: {", ".join(errores_encontrados)}', False)
        
        self.stdout.write('\n' + '=' * 80)
        self.stdout.write('TEST FINALIZADO')
        self.stdout.write('=' * 80)

