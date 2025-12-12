# -*- coding: utf-8 -*-
"""
Comando para mover imágenes de productos desde media/productos/productos/ a media/productos/
"""
from django.core.management.base import BaseCommand
from pos.models import Producto
import os
from django.conf import settings
from shutil import move


class Command(BaseCommand):
    help = 'Mueve imágenes de productos desde media/productos/productos/ a media/productos/'

    def handle(self, *args, **options):
        media_root = settings.MEDIA_ROOT
        productos_duplicados_path = os.path.join(media_root, 'productos', 'productos')
        productos_correcto_path = os.path.join(media_root, 'productos')
        
        if not os.path.exists(productos_duplicados_path):
            self.stdout.write(self.style.SUCCESS('No existe la carpeta duplicada media/productos/productos/'))
            return
        
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('MOVIENDO IMÁGENES DE PRODUCTOS'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(f'Origen: {productos_duplicados_path}')
        self.stdout.write(f'Destino: {productos_correcto_path}')
        self.stdout.write('')
        
        archivos_movidos = 0
        archivos_omitidos = 0
        errores = 0
        
        # Obtener todos los archivos en la carpeta duplicada
        if os.path.isdir(productos_duplicados_path):
            archivos = os.listdir(productos_duplicados_path)
            self.stdout.write(f'Archivos encontrados: {len(archivos)}')
            self.stdout.write('')
            
            for archivo in archivos:
                origen = os.path.join(productos_duplicados_path, archivo)
                destino = os.path.join(productos_correcto_path, archivo)
                
                if os.path.isfile(origen):
                    try:
                        # Si el archivo ya existe en el destino, omitirlo
                        if os.path.exists(destino):
                            self.stdout.write(f'  [OMITIDO] {archivo} (ya existe en destino)')
                            archivos_omitidos += 1
                        else:
                            move(origen, destino)
                            self.stdout.write(f'  [MOVIDO] {archivo}')
                            archivos_movidos += 1
                            
                            # Actualizar la referencia en la base de datos si es necesario
                            # Buscar productos que tengan esta imagen en la ruta incorrecta
                            productos = Producto.objects.filter(imagen__isnull=False)
                            for producto in productos:
                                if producto.imagen and 'productos/productos/' in producto.imagen.name:
                                    # Actualizar la ruta
                                    nueva_ruta = producto.imagen.name.replace('productos/productos/', 'productos/')
                                    producto.imagen.name = nueva_ruta
                                    producto.save(update_fields=['imagen'])
                                    
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f'  [ERROR] {archivo}: {str(e)}'))
                        errores += 1
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('RESUMEN'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(f'Archivos movidos: {archivos_movidos}')
        self.stdout.write(f'Archivos omitidos: {archivos_omitidos}')
        self.stdout.write(f'Errores: {errores}')
        self.stdout.write('')
        
        # Intentar eliminar la carpeta vacía
        try:
            if os.path.exists(productos_duplicados_path) and not os.listdir(productos_duplicados_path):
                os.rmdir(productos_duplicados_path)
                self.stdout.write(self.style.SUCCESS('Carpeta duplicada eliminada (estaba vacía)'))
            elif os.path.exists(productos_duplicados_path):
                self.stdout.write(self.style.WARNING(f'La carpeta {productos_duplicados_path} aún contiene archivos'))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'No se pudo eliminar la carpeta: {str(e)}'))
        
        self.stdout.write('')


