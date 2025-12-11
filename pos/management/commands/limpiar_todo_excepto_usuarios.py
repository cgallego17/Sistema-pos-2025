# -*- coding: utf-8 -*-
"""
Comando para limpiar TODOS los datos del sistema EXCEPTO usuarios, grupos y perfiles
ADVERTENCIA: Esta operación es IRREVERSIBLE
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from pos.models import (
    Venta, ItemVenta, GastoCaja, CajaUsuario, 
    MovimientoStock, ClientePotencial,
    IngresoMercancia, ItemIngresoMercancia,
    SalidaMercancia, ItemSalidaMercancia,
    RegistradoraActiva, CajaGastosUsuario,
    Producto
)
from django.db.models import Count


class Command(BaseCommand):
    help = 'Elimina TODOS los datos del sistema EXCEPTO usuarios, grupos y perfiles (IRREVERSIBLE)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirma la eliminación sin preguntar',
        )
        parser.add_argument(
            '--incluir-productos',
            action='store_true',
            help='Incluye la eliminación de productos',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('=' * 70))
        self.stdout.write(self.style.ERROR('ADVERTENCIA: OPERACION IRREVERSIBLE'))
        self.stdout.write(self.style.WARNING('=' * 70))

        # Contar registros existentes
        total_ventas = Venta.objects.count()
        total_items = ItemVenta.objects.count()
        total_gastos = GastoCaja.objects.count()
        total_cajas = CajaUsuario.objects.count()
        total_movimientos_stock = MovimientoStock.objects.count()
        total_clientes = ClientePotencial.objects.count()
        total_ingresos = IngresoMercancia.objects.count()
        total_items_ingresos = ItemIngresoMercancia.objects.count()
        total_salidas = SalidaMercancia.objects.count()
        total_items_salidas = ItemSalidaMercancia.objects.count()
        total_registradoras = RegistradoraActiva.objects.count()
        total_cajas_gastos = CajaGastosUsuario.objects.count()
        total_productos = Producto.objects.count()

        self.stdout.write(f'Se encontraron los siguientes datos:')
        self.stdout.write(f'  - Ventas: {total_ventas:,}')
        self.stdout.write(f'  - Items de Venta: {total_items:,}')
        self.stdout.write(f'  - Movimientos de Caja (Gastos/Ingresos): {total_gastos:,}')
        self.stdout.write(f'  - Cajas de Usuario: {total_cajas:,}')
        self.stdout.write(f'  - Movimientos de Stock: {total_movimientos_stock:,}')
        self.stdout.write(f'  - Clientes Potenciales: {total_clientes:,}')
        self.stdout.write(f'  - Ingresos de Mercancía: {total_ingresos:,}')
        self.stdout.write(f'  - Items de Ingresos: {total_items_ingresos:,}')
        self.stdout.write(f'  - Salidas de Mercancía: {total_salidas:,}')
        self.stdout.write(f'  - Items de Salidas: {total_items_salidas:,}')
        self.stdout.write(f'  - Registradoras Activas: {total_registradoras:,}')
        self.stdout.write(f'  - Cajas Gastos Usuario: {total_cajas_gastos:,}')
        self.stdout.write(f'  - Productos: {total_productos:,}')
        self.stdout.write('')

        total_registros = (
            total_ventas + total_items + total_gastos + total_cajas +
            total_movimientos_stock + total_clientes + total_ingresos +
            total_items_ingresos + total_salidas + total_items_salidas +
            total_registradoras + total_cajas_gastos
        )
        
        if options['incluir_productos']:
            total_registros += total_productos

        if total_registros == 0:
            self.stdout.write(self.style.SUCCESS('[OK] No hay datos para eliminar. La base de datos ya esta limpia.'))
            return
        
        # Confirmación
        if not options['confirm']:
            self.stdout.write(self.style.ERROR('Esta operacion NO se puede deshacer.'))
            if options['incluir_productos']:
                self.stdout.write(self.style.WARNING('Se eliminaran TODOS los productos tambien.'))
            else:
                self.stdout.write(self.style.WARNING('Los productos NO se eliminaran (usa --incluir-productos para eliminarlos).'))
            respuesta = input('Escribe "si" para confirmar la eliminación de TODOS estos datos: ')
            if respuesta.lower() != 'si':
                self.stdout.write(self.style.WARNING('Operación cancelada.'))
                return

        self.stdout.write(self.style.WARNING('Iniciando eliminación de datos...'))
        
        try:
            with transaction.atomic():
                # 1. Eliminar items de venta primero (dependencia de Venta)
                self.stdout.write('  - Eliminando items de venta...')
                items_eliminados = ItemVenta.objects.all().delete()
                self.stdout.write(self.style.SUCCESS(f'    {items_eliminados[0]:,} items eliminados'))
                
                # 2. Eliminar ventas
                self.stdout.write('  - Eliminando ventas...')
                ventas_eliminadas = Venta.objects.all().delete()
                self.stdout.write(self.style.SUCCESS(f'    {ventas_eliminadas[0]:,} ventas eliminadas'))
                
                # 3. Eliminar items de ingresos
                self.stdout.write('  - Eliminando items de ingresos de mercancía...')
                items_ingresos_eliminados = ItemIngresoMercancia.objects.all().delete()
                self.stdout.write(self.style.SUCCESS(f'    {items_ingresos_eliminados[0]:,} items eliminados'))
                
                # 4. Eliminar ingresos de mercancía
                self.stdout.write('  - Eliminando ingresos de mercancía...')
                ingresos_eliminados = IngresoMercancia.objects.all().delete()
                self.stdout.write(self.style.SUCCESS(f'    {ingresos_eliminados[0]:,} ingresos eliminados'))
                
                # 5. Eliminar items de salidas
                self.stdout.write('  - Eliminando items de salidas de mercancía...')
                items_salidas_eliminados = ItemSalidaMercancia.objects.all().delete()
                self.stdout.write(self.style.SUCCESS(f'    {items_salidas_eliminados[0]:,} items eliminados'))
                
                # 6. Eliminar salidas de mercancía
                self.stdout.write('  - Eliminando salidas de mercancía...')
                salidas_eliminadas = SalidaMercancia.objects.all().delete()
                self.stdout.write(self.style.SUCCESS(f'    {salidas_eliminadas[0]:,} salidas eliminadas'))
                
                # 7. Eliminar movimientos de stock
                self.stdout.write('  - Eliminando movimientos de stock...')
                movimientos_eliminados = MovimientoStock.objects.all().delete()
                self.stdout.write(self.style.SUCCESS(f'    {movimientos_eliminados[0]:,} movimientos eliminados'))
                
                # 8. Eliminar movimientos de caja (gastos/ingresos)
                self.stdout.write('  - Eliminando movimientos de caja (gastos/ingresos)...')
                gastos_eliminados = GastoCaja.objects.all().delete()
                self.stdout.write(self.style.SUCCESS(f'    {gastos_eliminados[0]:,} movimientos eliminados'))
                
                # 9. Eliminar cajas de usuario
                self.stdout.write('  - Eliminando cajas de usuario...')
                cajas_eliminadas = CajaUsuario.objects.all().delete()
                self.stdout.write(self.style.SUCCESS(f'    {cajas_eliminadas[0]:,} cajas eliminadas'))
                
                # 10. Eliminar cajas gastos usuario
                self.stdout.write('  - Eliminando cajas gastos usuario...')
                cajas_gastos_eliminadas = CajaGastosUsuario.objects.all().delete()
                self.stdout.write(self.style.SUCCESS(f'    {cajas_gastos_eliminadas[0]:,} cajas eliminadas'))
                
                # 11. Eliminar registradoras activas
                self.stdout.write('  - Eliminando registradoras activas...')
                registradoras_eliminadas = RegistradoraActiva.objects.all().delete()
                self.stdout.write(self.style.SUCCESS(f'    {registradoras_eliminadas[0]:,} registradoras eliminadas'))
                
                # 12. Eliminar clientes potenciales
                self.stdout.write('  - Eliminando clientes potenciales...')
                clientes_eliminados = ClientePotencial.objects.all().delete()
                self.stdout.write(self.style.SUCCESS(f'    {clientes_eliminados[0]:,} clientes eliminados'))
                
                # 13. Eliminar productos (opcional)
                if options['incluir_productos']:
                    self.stdout.write('  - Eliminando productos...')
                    productos_eliminados = Producto.objects.all().delete()
                    self.stdout.write(self.style.SUCCESS(f'    {productos_eliminados[0]:,} productos eliminados'))
                else:
                    self.stdout.write(self.style.WARNING('  - Productos NO eliminados (usa --incluir-productos para eliminarlos)'))
                
                self.stdout.write('')
                self.stdout.write(self.style.SUCCESS('=' * 70))
                self.stdout.write(self.style.SUCCESS('LIMPIEZA COMPLETADA EXITOSAMENTE'))
                self.stdout.write(self.style.SUCCESS('=' * 70))
                self.stdout.write('')
                self.stdout.write(self.style.WARNING('Nota: Los siguientes datos NO se eliminaron:'))
                self.stdout.write(self.style.WARNING('  - Usuarios (User)'))
                self.stdout.write(self.style.WARNING('  - Grupos de usuarios (Group)'))
                self.stdout.write(self.style.WARNING('  - Perfiles de usuario (PerfilUsuario)'))
                self.stdout.write(self.style.WARNING('  - Cajas principales (Caja)'))
                self.stdout.write(self.style.WARNING('  - Cajas de gastos principales (CajaGastos)'))
                if not options['incluir_productos']:
                    self.stdout.write(self.style.WARNING('  - Productos (Producto)'))

        except Exception as e:
            self.stdout.write('')
            self.stdout.write(self.style.ERROR('=' * 70))
            self.stdout.write(self.style.ERROR('ERROR AL ELIMINAR DATOS'))
            self.stdout.write(self.style.ERROR('=' * 70))
            self.stdout.write(self.style.ERROR(f'Se produjo un error: {e}'))
            import traceback
            self.stdout.write(self.style.ERROR(traceback.format_exc()))


