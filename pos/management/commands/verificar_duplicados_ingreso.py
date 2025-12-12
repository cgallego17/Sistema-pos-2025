# -*- coding: utf-8 -*-
"""
Comando para verificar productos duplicados en un ingreso
"""
from django.core.management.base import BaseCommand
from pos.models import IngresoMercancia
from collections import Counter


class Command(BaseCommand):
    help = 'Verifica productos duplicados en un ingreso'

    def add_arguments(self, parser):
        parser.add_argument(
            'ingreso_id',
            type=int,
            help='ID del ingreso a verificar'
        )

    def handle(self, *args, **options):
        ingreso_id = options['ingreso_id']
        
        try:
            ingreso = IngresoMercancia.objects.get(id=ingreso_id)
        except IngresoMercancia.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Ingreso #{ingreso_id} no existe'))
            return
        
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('VERIFICACIÓN DE DUPLICADOS EN INGRESO'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(f'Ingreso ID: #{ingreso.id}')
        self.stdout.write(f'Total items: {ingreso.items.count()}')
        self.stdout.write('')
        
        # Contar items por código + atributo
        items_keys = []
        items_detalle = {}
        
        for item in ingreso.items.all():
            clave = (item.producto.codigo, item.producto.atributo)
            items_keys.append(clave)
            if clave not in items_detalle:
                items_detalle[clave] = []
            items_detalle[clave].append({
                'item_id': item.id,
                'cantidad': item.cantidad
            })
        
        # Encontrar duplicados
        contador = Counter(items_keys)
        duplicados = {k: v for k, v in contador.items() if v > 1}
        
        if duplicados:
            self.stdout.write(self.style.WARNING('=' * 70))
            self.stdout.write(self.style.WARNING('PRODUCTOS DUPLICADOS EN EL INGRESO'))
            self.stdout.write(self.style.WARNING('=' * 70))
            for (codigo, atributo), count in duplicados.items():
                atributo_str = atributo if atributo else 'SIN ATRIBUTO'
                self.stdout.write(f'  {codigo} - Atributo: {atributo_str} - Aparece {count} veces')
                for detalle in items_detalle[(codigo, atributo)]:
                    self.stdout.write(f'    Item ID: {detalle["item_id"]} - Cantidad: {detalle["cantidad"]}')
            self.stdout.write('')
        else:
            self.stdout.write(self.style.SUCCESS('[OK] No hay productos duplicados en el ingreso'))
            self.stdout.write('')


