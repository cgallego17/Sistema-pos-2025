"""
Comando para identificar y limpiar movimientos de stock huérfanos
"""
from django.core.management.base import BaseCommand
from pos.models import MovimientoStock, IngresoMercancia, SalidaMercancia


class Command(BaseCommand):
    help = 'Identifica y opcionalmente elimina movimientos de stock huérfanos'

    def add_arguments(self, parser):
        parser.add_argument(
            '--eliminar',
            action='store_true',
            help='Eliminar movimientos huérfanos (por defecto solo muestra)',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('ANALISIS DE MOVIMIENTOS HUERFANOS'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write('')
        
        # Obtener todos los IDs de ingresos y salidas existentes
        ingresos_ids = set(IngresoMercancia.objects.values_list('id', flat=True))
        salidas_ids = set(SalidaMercancia.objects.values_list('id', flat=True))
        
        self.stdout.write(f'Ingresos existentes: {len(ingresos_ids)}')
        self.stdout.write(f'Salidas existentes: {len(salidas_ids)}')
        self.stdout.write('')
        
        # Analizar movimientos de ingresos
        movimientos_ingresos = MovimientoStock.objects.filter(
            motivo__startswith='Ingreso #'
        )
        
        movimientos_huerfanos = []
        
        for mov in movimientos_ingresos:
            # Extraer ID del ingreso del motivo
            try:
                # Formato: "Ingreso #5 - Bazar Cristian"
                ingreso_id = int(mov.motivo.split('#')[1].split()[0])
                if ingreso_id not in ingresos_ids:
                    movimientos_huerfanos.append(mov)
            except (ValueError, IndexError):
                # Si no se puede extraer el ID, considerar como huérfano potencial
                pass
        
        # Analizar movimientos de salidas
        movimientos_salidas = MovimientoStock.objects.filter(
            motivo__startswith='Salida #'
        )
        
        for mov in movimientos_salidas:
            try:
                salida_id = int(mov.motivo.split('#')[1].split()[0])
                if salida_id not in salidas_ids:
                    movimientos_huerfanos.append(mov)
            except (ValueError, IndexError):
                pass
        
        self.stdout.write(f'Movimientos huérfanos encontrados: {len(movimientos_huerfanos)}')
        self.stdout.write('')
        
        if movimientos_huerfanos:
            self.stdout.write('Detalle de movimientos huérfanos:')
            for mov in movimientos_huerfanos[:10]:
                fecha_str = mov.fecha.strftime('%d/%m/%Y %H:%M')
                self.stdout.write(
                    f'  - Movimiento #{mov.id}: {mov.tipo} de {mov.cantidad} unidades '
                    f'({fecha_str}) - {mov.motivo[:60]}'
                )
            if len(movimientos_huerfanos) > 10:
                self.stdout.write(f'  ... y {len(movimientos_huerfanos) - 10} más')
            self.stdout.write('')
            
            if options['eliminar']:
                total_eliminados = len(movimientos_huerfanos)
                for mov in movimientos_huerfanos:
                    mov.delete()
                self.stdout.write(
                    self.style.SUCCESS(
                        f'[OK] Eliminados {total_eliminados} movimientos huérfanos'
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        'Para eliminar estos movimientos, ejecuta: '
                        'python manage.py limpiar_movimientos_huerfanos --eliminar'
                    )
                )
        else:
            self.stdout.write(self.style.SUCCESS('[OK] No se encontraron movimientos huérfanos'))
        
        self.stdout.write('')




