"""
Comando para revisar movimientos de caja y detectar incongruencias
Ejecutar con: python manage.py revisar_movimientos_caja
"""
from django.core.management.base import BaseCommand
from django.db.models import Q, Sum, Count
from django.utils import timezone
from datetime import timedelta
from pos.models import (
    Caja, CajaUsuario, Venta, GastoCaja, ItemVenta
)


class Command(BaseCommand):
    help = 'Revisa los movimientos de caja y detecta incongruencias'

    def add_arguments(self, parser):
        parser.add_argument(
            '--detallado',
            action='store_true',
            help='Muestra detalles de cada incongruencia encontrada',
        )

    def print_section(self, title):
        """Imprimir una seccion con formato"""
        self.stdout.write('\n' + '=' * 80)
        self.stdout.write(self.style.SUCCESS(title))
        self.stdout.write('=' * 80)

    def print_subsection(self, title):
        """Imprimir una subseccion"""
        self.stdout.write('\n' + '-' * 80)
        self.stdout.write(self.style.WARNING(title))
        self.stdout.write('-' * 80)

    def handle(self, *args, **options):
        detallado = options['detallado']
        
        self.print_section('REVISION DE MOVIMIENTOS DE CAJA')
        
        problemas_encontrados = []
        total_problemas = 0

        # 1. Verificar GastosCaja sin caja_usuario asociada
        self.print_subsection('1. Gastos sin Caja Usuario asociada')
        gastos_sin_caja = GastoCaja.objects.filter(
            caja_usuario__isnull=True,
            caja_gastos_usuario__isnull=True
        )
        count_sin_caja = gastos_sin_caja.count()
        if count_sin_caja > 0:
            problemas_encontrados.append(f'Gastos sin caja: {count_sin_caja}')
            total_problemas += count_sin_caja
            self.stdout.write(self.style.ERROR(f'[ERROR] {count_sin_caja} gastos sin caja_usuario ni caja_gastos_usuario'))
            if detallado:
                for gasto in gastos_sin_caja[:10]:
                    self.stdout.write(f'  - ID: {gasto.id}, Tipo: {gasto.tipo}, Monto: ${gasto.monto:,}, Fecha: {gasto.fecha}, Usuario: {gasto.usuario.username}')
        else:
            self.stdout.write(self.style.SUCCESS('[OK] Todos los gastos tienen caja asociada'))

        # 2. Verificar GastosCaja con fechas fuera del periodo de la caja
        self.print_subsection('2. Gastos con fechas fuera del periodo de la caja')
        gastos_fuera_periodo = []
        for gasto in GastoCaja.objects.filter(caja_usuario__isnull=False).select_related('caja_usuario'):
            caja = gasto.caja_usuario
            if caja.fecha_cierre:
                # Caja cerrada: fecha debe estar entre apertura y cierre
                if gasto.fecha < caja.fecha_apertura or gasto.fecha > caja.fecha_cierre:
                    gastos_fuera_periodo.append(gasto)
            else:
                # Caja abierta: fecha debe ser >= apertura
                if gasto.fecha < caja.fecha_apertura:
                    gastos_fuera_periodo.append(gasto)
        
        if gastos_fuera_periodo:
            problemas_encontrados.append(f'Gastos fuera de periodo: {len(gastos_fuera_periodo)}')
            total_problemas += len(gastos_fuera_periodo)
            self.stdout.write(self.style.ERROR(f'[ERROR] {len(gastos_fuera_periodo)} gastos con fechas fuera del periodo de su caja'))
            if detallado:
                for gasto in gastos_fuera_periodo[:10]:
                    caja = gasto.caja_usuario
                    self.stdout.write(f'  - Gasto ID: {gasto.id}, Fecha: {gasto.fecha}')
                    self.stdout.write(f'    Caja: {caja.id}, Apertura: {caja.fecha_apertura}, Cierre: {caja.fecha_cierre or "Abierta"}')
        else:
            self.stdout.write(self.style.SUCCESS('[OK] Todos los gastos estan dentro del periodo de su caja'))

        # 3. Verificar Ventas sin caja asociada
        self.print_subsection('3. Ventas sin caja asociada')
        ventas_sin_caja = Venta.objects.filter(caja__isnull=True, completada=True)
        count_ventas_sin_caja = ventas_sin_caja.count()
        if count_ventas_sin_caja > 0:
            problemas_encontrados.append(f'Ventas sin caja: {count_ventas_sin_caja}')
            total_problemas += count_ventas_sin_caja
            self.stdout.write(self.style.ERROR(f'[ERROR] {count_ventas_sin_caja} ventas completadas sin caja asociada'))
            if detallado:
                for venta in ventas_sin_caja[:10]:
                    self.stdout.write(f'  - Venta ID: {venta.id}, Total: ${venta.total:,}, Fecha: {venta.fecha}, Usuario: {venta.usuario.username if venta.usuario else "N/A"}')
        else:
            self.stdout.write(self.style.SUCCESS('[OK] Todas las ventas tienen caja asociada'))

        # 4. Verificar Retiros marcados como gastos (deberian identificarse por descripcion)
        self.print_subsection('4. Retiros de cierre de caja identificados correctamente')
        retiros = GastoCaja.objects.filter(
            descripcion__icontains='Retiro de dinero al cerrar caja'
        )
        count_retiros = retiros.count()
        self.stdout.write(f'[INFO] {count_retiros} retiros de cierre de caja encontrados')
        
        # Verificar que los retiros esten asociados a cajas cerradas
        retiros_sin_cierre = []
        for retiro in retiros:
            if retiro.caja_usuario and retiro.caja_usuario.fecha_cierre is None:
                retiros_sin_cierre.append(retiro)
        
        if retiros_sin_cierre:
            problemas_encontrados.append(f'Retiros en cajas abiertas: {len(retiros_sin_cierre)}')
            total_problemas += len(retiros_sin_cierre)
            self.stdout.write(self.style.ERROR(f'[ERROR] {len(retiros_sin_cierre)} retiros en cajas que aun estan abiertas'))
            if detallado:
                for retiro in retiros_sin_cierre[:10]:
                    self.stdout.write(f'  - Retiro ID: {retiro.id}, Monto: ${retiro.monto:,}, Caja: {retiro.caja_usuario.id if retiro.caja_usuario else "N/A"}')
        else:
            self.stdout.write(self.style.SUCCESS('[OK] Todos los retiros estan en cajas cerradas'))

        # 5. Verificar duplicados de gastos (mismo monto, misma descripcion, misma fecha)
        self.print_subsection('5. Gastos duplicados potenciales')
        from django.db.models import Count
        duplicados = GastoCaja.objects.values(
            'monto', 'descripcion', 'fecha', 'tipo', 'caja_usuario'
        ).annotate(
            count=Count('id')
        ).filter(count__gt=1)
        
        if duplicados:
            total_duplicados = sum(d['count'] - 1 for d in duplicados)
            problemas_encontrados.append(f'Gastos duplicados: {total_duplicados}')
            total_problemas += total_duplicados
            self.stdout.write(self.style.ERROR(f'[ERROR] {len(duplicados)} grupos de gastos duplicados ({total_duplicados} duplicados totales)'))
            if detallado:
                for dup in duplicados[:10]:
                    self.stdout.write(f'  - Monto: ${dup["monto"]:,}, Tipo: {dup["tipo"]}, Fecha: {dup["fecha"]}, Cantidad: {dup["count"]}')
        else:
            self.stdout.write(self.style.SUCCESS('[OK] No se encontraron gastos duplicados'))

        # 6. Verificar ventas con fechas inconsistentes con su caja
        self.print_subsection('6. Ventas con fechas inconsistentes con su caja')
        ventas_inconsistentes = []
        for venta in Venta.objects.filter(caja__isnull=False, completada=True).select_related('caja'):
            # Buscar la caja_usuario que deberia contener esta venta
            caja_usuario = CajaUsuario.objects.filter(
                caja=venta.caja,
                fecha_apertura__lte=venta.fecha
            ).order_by('-fecha_apertura').first()
            
            if caja_usuario:
                if caja_usuario.fecha_cierre:
                    if venta.fecha > caja_usuario.fecha_cierre:
                        ventas_inconsistentes.append((venta, caja_usuario))
                # Si la caja esta abierta, la venta debe ser >= fecha_apertura (ya filtrado)
            else:
                # No se encontro caja_usuario para esta venta
                ventas_inconsistentes.append((venta, None))
        
        if ventas_inconsistentes:
            problemas_encontrados.append(f'Ventas con fechas inconsistentes: {len(ventas_inconsistentes)}')
            total_problemas += len(ventas_inconsistentes)
            self.stdout.write(self.style.ERROR(f'[ERROR] {len(ventas_inconsistentes)} ventas con fechas inconsistentes'))
            if detallado:
                for venta, caja in ventas_inconsistentes[:10]:
                    self.stdout.write(f'  - Venta ID: {venta.id}, Fecha: {venta.fecha}, Total: ${venta.total:,}')
                    if caja:
                        self.stdout.write(f'    Caja: {caja.id}, Apertura: {caja.fecha_apertura}, Cierre: {caja.fecha_cierre or "Abierta"}')
                    else:
                        self.stdout.write(f'    Caja: No se encontro CajaUsuario para esta venta')
        else:
            self.stdout.write(self.style.SUCCESS('[OK] Todas las ventas tienen fechas consistentes con su caja'))

        # 7. Verificar gastos con montos negativos o cero
        self.print_subsection('7. Gastos con montos invalidos')
        gastos_invalidos = GastoCaja.objects.filter(Q(monto__lte=0))
        count_invalidos = gastos_invalidos.count()
        if count_invalidos > 0:
            problemas_encontrados.append(f'Gastos con montos invalidos: {count_invalidos}')
            total_problemas += count_invalidos
            self.stdout.write(self.style.ERROR(f'[ERROR] {count_invalidos} gastos con monto <= 0'))
            if detallado:
                for gasto in gastos_invalidos[:10]:
                    self.stdout.write(f'  - Gasto ID: {gasto.id}, Tipo: {gasto.tipo}, Monto: ${gasto.monto:,}, Descripcion: {gasto.descripcion[:50]}')
        else:
            self.stdout.write(self.style.SUCCESS('[OK] Todos los gastos tienen montos validos'))

        # 8. Verificar cajas con gastos pero sin ventas
        self.print_subsection('8. Cajas con gastos pero sin ventas')
        cajas_sin_ventas = []
        for caja_usuario in CajaUsuario.objects.all():
            gastos_count = GastoCaja.objects.filter(caja_usuario=caja_usuario).count()
            ventas_count = Venta.objects.filter(
                caja=caja_usuario.caja,
                fecha__gte=caja_usuario.fecha_apertura,
                fecha__lte=(caja_usuario.fecha_cierre or timezone.now()),
                completada=True
            ).count()
            
            if gastos_count > 0 and ventas_count == 0:
                cajas_sin_ventas.append((caja_usuario, gastos_count))
        
        if cajas_sin_ventas:
            self.stdout.write(self.style.WARNING(f'[INFO] {len(cajas_sin_ventas)} cajas con gastos pero sin ventas (puede ser normal)'))
            if detallado:
                for caja, gastos in cajas_sin_ventas[:10]:
                    self.stdout.write(f'  - Caja ID: {caja.id}, Gastos: {gastos}, Apertura: {caja.fecha_apertura}')
        else:
            self.stdout.write(self.style.SUCCESS('[OK] Todas las cajas con gastos tienen ventas'))

        # 9. Estadisticas generales
        self.print_subsection('9. Estadisticas generales')
        total_gastos = GastoCaja.objects.count()
        total_ventas = Venta.objects.filter(completada=True).count()
        total_cajas = CajaUsuario.objects.count()
        cajas_abiertas = CajaUsuario.objects.filter(fecha_cierre__isnull=True).count()
        cajas_cerradas = CajaUsuario.objects.filter(fecha_cierre__isnull=False).count()
        
        self.stdout.write(f'Total de gastos/ingresos: {total_gastos:,}')
        self.stdout.write(f'Total de ventas completadas: {total_ventas:,}')
        self.stdout.write(f'Total de cajas: {total_cajas:,}')
        self.stdout.write(f'  - Cajas abiertas: {cajas_abiertas}')
        self.stdout.write(f'  - Cajas cerradas: {cajas_cerradas}')
        
        # Calcular totales
        total_gastos_monto = GastoCaja.objects.filter(tipo='gasto').exclude(
            descripcion__icontains='Retiro de dinero al cerrar caja'
        ).aggregate(total=Sum('monto'))['total'] or 0
        total_ingresos_monto = GastoCaja.objects.filter(tipo='ingreso').aggregate(total=Sum('monto'))['total'] or 0
        total_ventas_monto = Venta.objects.filter(completada=True, anulada=False).aggregate(total=Sum('total'))['total'] or 0
        
        self.stdout.write(f'\nTotales:')
        self.stdout.write(f'  - Gastos (sin retiros): ${total_gastos_monto:,}')
        self.stdout.write(f'  - Ingresos: ${total_ingresos_monto:,}')
        self.stdout.write(f'  - Ventas: ${total_ventas_monto:,}')

        # Resumen final
        self.print_section('RESUMEN')
        if total_problemas > 0:
            self.stdout.write(self.style.ERROR(f'\n[ATENCION] Se encontraron {total_problemas} problemas:'))
            for problema in problemas_encontrados:
                self.stdout.write(f'  - {problema}')
            self.stdout.write(self.style.WARNING('\nSe recomienda revisar estos problemas antes de continuar.'))
        else:
            self.stdout.write(self.style.SUCCESS('\n[OK] No se encontraron problemas en los movimientos de caja.'))
            self.stdout.write(self.style.SUCCESS('Todos los movimientos estan correctamente asociados y validados.'))
        
        self.stdout.write('\n' + '=' * 80 + '\n')







