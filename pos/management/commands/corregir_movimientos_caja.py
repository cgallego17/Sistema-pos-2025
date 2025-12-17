"""
Comando para corregir problemas encontrados en los movimientos de caja
Ejecutar con: python manage.py corregir_movimientos_caja
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from pos.models import CajaUsuario, GastoCaja, Venta, Caja


class Command(BaseCommand):
    help = 'Corrige problemas en los movimientos de caja'

    def add_arguments(self, parser):
        parser.add_argument(
            '--ejecutar',
            action='store_true',
            help='Ejecuta las correcciones (sin esto solo muestra lo que se haria)',
        )

    def handle(self, *args, **options):
        ejecutar = options['ejecutar']
        
        if not ejecutar:
            self.stdout.write(self.style.WARNING('\n[MODO SIMULACION]'))
            self.stdout.write('Usa --ejecutar para aplicar los cambios\n')
        
        self.stdout.write('\n' + '=' * 80)
        self.stdout.write(self.style.SUCCESS('CORRECCION DE MOVIMIENTOS DE CAJA'))
        self.stdout.write('=' * 80)

        # 1. Corregir gastos fuera del periodo
        self.stdout.write('\n' + '-' * 80)
        self.stdout.write('1. Corrigiendo gastos fuera del periodo de la caja')
        self.stdout.write('-' * 80)
        
        gastos_fuera_periodo = []
        for gasto in GastoCaja.objects.filter(caja_usuario__isnull=False).select_related('caja_usuario'):
            caja = gasto.caja_usuario
            if caja.fecha_cierre:
                if gasto.fecha < caja.fecha_apertura or gasto.fecha > caja.fecha_cierre:
                    gastos_fuera_periodo.append(gasto)
            else:
                if gasto.fecha < caja.fecha_apertura:
                    gastos_fuera_periodo.append(gasto)
        
        if gastos_fuera_periodo:
            self.stdout.write(f'Encontrados {len(gastos_fuera_periodo)} gastos fuera del periodo')
            
            # Buscar o crear la caja correcta para estos gastos
            caja_principal = Caja.objects.filter(numero=1).first()
            if caja_principal:
                # Buscar la caja_usuario correcta para cada gasto
                for gasto in gastos_fuera_periodo:
                    # Buscar caja_usuario que deberia contener este gasto
                    caja_correcta = CajaUsuario.objects.filter(
                        caja=caja_principal,
                        fecha_apertura__lte=gasto.fecha
                    ).order_by('-fecha_apertura').first()
                    
                    if caja_correcta:
                        if caja_correcta.fecha_cierre is None or gasto.fecha <= caja_correcta.fecha_cierre:
                            if ejecutar:
                                gasto.caja_usuario = caja_correcta
                                gasto.save()
                            self.stdout.write(f'  - Gasto ID {gasto.id}: Movido a CajaUsuario {caja_correcta.id}')
                    else:
                        # Crear nueva caja_usuario para este gasto si no existe
                        if ejecutar:
                            nueva_caja = CajaUsuario.objects.create(
                                caja=caja_principal,
                                usuario=gasto.usuario,
                                fecha_apertura=gasto.fecha,
                                monto_inicial=0
                            )
                            gasto.caja_usuario = nueva_caja
                            gasto.save()
                        self.stdout.write(f'  - Gasto ID {gasto.id}: Creada nueva CajaUsuario')
        else:
            self.stdout.write(self.style.SUCCESS('[OK] No hay gastos fuera del periodo'))

        # 2. Verificar retiros en cajas abiertas
        self.stdout.write('\n' + '-' * 80)
        self.stdout.write('2. Verificando retiros en cajas abiertas')
        self.stdout.write('-' * 80)
        
        retiros_abiertas = []
        for retiro in GastoCaja.objects.filter(
            descripcion__icontains='Retiro de dinero al cerrar caja',
            caja_usuario__isnull=False
        ):
            if retiro.caja_usuario and retiro.caja_usuario.fecha_cierre is None:
                retiros_abiertas.append(retiro)
        
        if retiros_abiertas:
            self.stdout.write(f'Encontrados {len(retiros_abiertas)} retiros en cajas abiertas')
            self.stdout.write(self.style.WARNING('  [INFO] Estos retiros deberian estar en cajas cerradas.'))
            self.stdout.write(self.style.WARNING('  Se recomienda cerrar manualmente estas cajas desde la interfaz.'))
            for retiro in retiros_abiertas:
                self.stdout.write(f'  - Retiro ID {retiro.id}, CajaUsuario {retiro.caja_usuario.id}, Monto: ${retiro.monto:,}')
        else:
            self.stdout.write(self.style.SUCCESS('[OK] No hay retiros en cajas abiertas'))

        # 3. Corregir ventas sin CajaUsuario
        self.stdout.write('\n' + '-' * 80)
        self.stdout.write('3. Corrigiendo ventas sin CajaUsuario asociado')
        self.stdout.write('-' * 80)
        
        caja_principal = Caja.objects.filter(numero=1).first()
        if not caja_principal:
            self.stdout.write(self.style.ERROR('[ERROR] No se encontro la Caja Principal'))
            return
        
        ventas_sin_caja = []
        for venta in Venta.objects.filter(caja=caja_principal, completada=True).order_by('fecha'):
            # Buscar CajaUsuario que deberia contener esta venta
            caja_usuario = CajaUsuario.objects.filter(
                caja=caja_principal,
                fecha_apertura__lte=venta.fecha
            ).order_by('-fecha_apertura').first()
            
            if not caja_usuario or (caja_usuario.fecha_cierre and venta.fecha > caja_usuario.fecha_cierre):
                ventas_sin_caja.append(venta)
        
        if ventas_sin_caja:
            self.stdout.write(f'Encontradas {len(ventas_sin_caja)} ventas sin CajaUsuario correcto')
            
            # Agrupar ventas por fecha para crear cajas por dia
            from collections import defaultdict
            ventas_por_dia = defaultdict(list)
            for venta in ventas_sin_caja:
                fecha_dia = venta.fecha.date()
                ventas_por_dia[fecha_dia].append(venta)
            
            self.stdout.write(f'Agrupadas en {len(ventas_por_dia)} dias diferentes')
            
            for fecha_dia, ventas_dia in sorted(ventas_por_dia.items()):
                # Buscar si ya existe una caja para este dia
                caja_existente = CajaUsuario.objects.filter(
                    caja=caja_principal,
                    fecha_apertura__date=fecha_dia
                ).first()
                
                if caja_existente:
                    self.stdout.write(f'  - Fecha {fecha_dia}: Usando CajaUsuario existente {caja_existente.id} ({len(ventas_dia)} ventas)')
                    # Las ventas ya estan asociadas a la caja, solo verificamos
                else:
                    # Crear nueva caja para este dia
                    primera_venta = min(ventas_dia, key=lambda v: v.fecha)
                    if ejecutar:
                        nueva_caja = CajaUsuario.objects.create(
                            caja=caja_principal,
                            usuario=primera_venta.usuario or ventas_dia[0].usuario,
                            fecha_apertura=primera_venta.fecha,
                            monto_inicial=0
                        )
                        self.stdout.write(f'  - Fecha {fecha_dia}: Creada CajaUsuario {nueva_caja.id} ({len(ventas_dia)} ventas)')
                    else:
                        self.stdout.write(f'  - Fecha {fecha_dia}: Se crearia CajaUsuario ({len(ventas_dia)} ventas)')
        else:
            self.stdout.write(self.style.SUCCESS('[OK] Todas las ventas tienen CajaUsuario correcto'))

        # Resumen
        self.stdout.write('\n' + '=' * 80)
        self.stdout.write(self.style.SUCCESS('RESUMEN'))
        self.stdout.write('=' * 80)
        
        if ejecutar:
            self.stdout.write(self.style.SUCCESS('\n[OK] Correcciones aplicadas'))
        else:
            self.stdout.write(self.style.WARNING('\n[MODO SIMULACION]'))
            self.stdout.write('Ejecuta con --ejecutar para aplicar los cambios')
        
        self.stdout.write('\n' + '=' * 80 + '\n')







