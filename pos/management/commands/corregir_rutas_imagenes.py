# -*- coding: utf-8 -*-
"""
Comando para corregir las rutas de imágenes en la base de datos
"""
from django.core.management.base import BaseCommand
from pos.models import Producto


class Command(BaseCommand):
    help = 'Corrige las rutas de imágenes en la base de datos (de productos/productos/ a productos/)'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('CORRIGIENDO RUTAS DE IMÁGENES EN BASE DE DATOS'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write('')
        
        productos_actualizados = 0
        productos_con_ruta_incorrecta = 0
        
        productos = Producto.objects.filter(imagen__isnull=False).exclude(imagen='')
        
        for producto in productos:
            if producto.imagen and 'productos/productos/' in producto.imagen.name:
                productos_con_ruta_incorrecta += 1
                # Corregir la ruta
                nueva_ruta = producto.imagen.name.replace('productos/productos/', 'productos/')
                producto.imagen.name = nueva_ruta
                producto.save(update_fields=['imagen'])
                productos_actualizados += 1
                self.stdout.write(f'  [CORREGIDO] {producto.codigo}: {producto.imagen.name}')
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('RESUMEN'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(f'Productos con ruta incorrecta encontrados: {productos_con_ruta_incorrecta}')
        self.stdout.write(f'Productos actualizados: {productos_actualizados}')
        self.stdout.write('')

