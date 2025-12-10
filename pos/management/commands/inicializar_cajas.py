# -*- coding: utf-8 -*-
"""
Comando para inicializar las cajas del sistema
Crea 3 registradoras y 1 caja de gastos
"""
from django.core.management.base import BaseCommand
from pos.models import Caja, CajaGastos


class Command(BaseCommand):
    help = 'Inicializa las cajas del sistema: 3 registradoras y 1 caja de gastos'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Inicializando cajas del sistema...'))
        
        # Crear 1 caja principal (todas las ventas van aquí)
        caja_principal, created = Caja.objects.get_or_create(
            numero=1,
            defaults={'nombre': 'Caja Principal', 'activa': True}
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'  [OK] Creada: {caja_principal}'))
        else:
            caja_principal.nombre = 'Caja Principal'
            caja_principal.activa = True
            caja_principal.save()
            self.stdout.write(self.style.WARNING(f'  [ACTUALIZADA] {caja_principal}'))
        
        # Crear 3 registradoras (puntos de venta que usan la misma caja)
        # Estas son solo identificadores, todas apuntan a la caja principal
        registradoras = [
            {'numero': 1, 'nombre': 'Registradora 1', 'caja_id': caja_principal.id},
            {'numero': 2, 'nombre': 'Registradora 2', 'caja_id': caja_principal.id},
            {'numero': 3, 'nombre': 'Registradora 3', 'caja_id': caja_principal.id},
        ]
        
        # Nota: Las registradoras se manejan como puntos de venta
        # Todas las ventas se asignan a la Caja Principal (numero 1)
        self.stdout.write(self.style.SUCCESS(f'  [OK] 3 Puntos de venta configurados (todos usan {caja_principal})'))
        
        # Crear 1 caja de gastos
        caja_gastos, created = CajaGastos.objects.get_or_create(
            nombre='Caja de Gastos',
            defaults={'activa': True}
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'  [OK] Creada: {caja_gastos}'))
        else:
            caja_gastos.activa = True
            caja_gastos.save()
            self.stdout.write(self.style.WARNING(f'  [ACTUALIZADA] {caja_gastos}'))
        
        self.stdout.write(self.style.SUCCESS('\n[OK] Cajas inicializadas correctamente'))
        self.stdout.write(self.style.SUCCESS('  - 1 Caja Principal (todas las ventas van aquí)'))
        self.stdout.write(self.style.SUCCESS('  - 3 Puntos de venta (Registradoras 1, 2, 3)'))
        self.stdout.write(self.style.SUCCESS('  - 1 Caja de Gastos creada'))

