# -*- coding: utf-8 -*-
"""
Comando para poblar imágenes de productos desde una API externa
"""
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from pos.models import Producto
import requests
import os
from urllib.parse import urlparse


class Command(BaseCommand):
    help = 'Pobla las imágenes de productos desde una API externa'

    def add_arguments(self, parser):
        parser.add_argument(
            '--api-url',
            type=str,
            required=True,
            help='URL de la API que devuelve todos los productos (ej: https://api.ejemplo.com/productos)',
        )
        parser.add_argument(
            '--base-url-imagenes',
            type=str,
            default='',
            help='URL base para construir URLs completas de imágenes si son relativas (ej: https://catalogo.tersacosmeticos.com)',
        )
        parser.add_argument(
            '--codigo-field',
            type=str,
            default='codigo',
            help='Nombre del campo en la respuesta JSON que contiene el código del producto (default: codigo)',
        )
        parser.add_argument(
            '--imagen-field',
            type=str,
            default='imagen',
            help='Nombre del campo en la respuesta JSON que contiene la URL de la imagen (default: imagen)',
        )
        parser.add_argument(
            '--sobrescribir',
            action='store_true',
            help='Sobrescribir imágenes existentes',
        )
        parser.add_argument(
            '--timeout',
            type=int,
            default=30,
            help='Timeout en segundos para las peticiones HTTP (default: 30)',
        )
        parser.add_argument(
            '--headers',
            type=str,
            default='',
            help='Headers adicionales en formato JSON (ej: {"Authorization": "Bearer token"})',
        )

    def handle(self, *args, **options):
        api_url = options['api_url']
        base_url_imagenes = options['base_url_imagenes']
        codigo_field = options['codigo_field']
        imagen_field = options['imagen_field']
        sobrescribir = options['sobrescribir']
        timeout = options['timeout']
        headers_str = options['headers']
        
        # Parsear headers si se proporcionan
        headers = {}
        if headers_str:
            import json
            try:
                headers = json.loads(headers_str)
            except json.JSONDecodeError:
                self.stdout.write(self.style.ERROR('Error: Los headers deben estar en formato JSON válido'))
                return
        
        # Si no se proporciona base_url_imagenes, extraerla de api_url
        if not base_url_imagenes:
            from urllib.parse import urlparse
            parsed = urlparse(api_url)
            base_url_imagenes = f"{parsed.scheme}://{parsed.netloc}"
        
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('POBLAR IMÁGENES DESDE API'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(f'URL de la API: {api_url}')
        self.stdout.write(f'URL base para imágenes: {base_url_imagenes}')
        self.stdout.write(f'Campo de código: {codigo_field}')
        self.stdout.write(f'Campo de imagen: {imagen_field}')
        self.stdout.write('')
        
        # Obtener productos sin imagen o todos si se quiere sobrescribir
        if sobrescribir:
            productos = Producto.objects.filter(activo=True)
            self.stdout.write('Modo: Sobrescribir todas las imágenes')
        else:
            productos = Producto.objects.filter(activo=True, imagen__isnull=True) | Producto.objects.filter(activo=True, imagen='')
            self.stdout.write('Modo: Solo productos sin imagen')
        
        total_productos = productos.count()
        self.stdout.write(f'Total de productos locales a procesar: {total_productos}')
        self.stdout.write('')
        
        if total_productos == 0:
            self.stdout.write(self.style.WARNING('No hay productos para procesar'))
            return
        
        # Descargar todos los productos de la API
        self.stdout.write('Descargando productos de la API...', ending=' ')
        try:
            response = requests.get(api_url, headers=headers, timeout=timeout)
            if response.status_code != 200:
                self.stdout.write(self.style.ERROR(f'Error HTTP {response.status_code}'))
                return
            
            productos_api = response.json()
            if not isinstance(productos_api, list):
                self.stdout.write(self.style.ERROR('La API no devolvió un array de productos'))
                return
            
            self.stdout.write(self.style.SUCCESS(f'OK ({len(productos_api)} productos encontrados)'))
            self.stdout.write('')
            
            # Crear un diccionario para búsqueda rápida por código
            productos_api_dict = {}
            for prod_api in productos_api:
                if isinstance(prod_api, dict) and codigo_field in prod_api:
                    codigo = prod_api[codigo_field]
                    productos_api_dict[codigo] = prod_api
            
            self.stdout.write(f'Productos indexados por código: {len(productos_api_dict)}')
            self.stdout.write('')
            
        except requests.exceptions.RequestException as e:
            self.stdout.write(self.style.ERROR(f'Error de conexión: {str(e)}'))
            return
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error al procesar respuesta: {str(e)}'))
            return
        
        productos_actualizados = 0
        productos_con_error = 0
        productos_sin_imagen_api = 0
        productos_no_encontrados = 0
        
        for producto in productos:
            try:
                self.stdout.write(f'Procesando: {producto.codigo} - {producto.nombre[:50]}...', ending=' ')
                
                # Buscar el producto en la API por código
                if producto.codigo not in productos_api_dict:
                    productos_no_encontrados += 1
                    self.stdout.write(self.style.WARNING('No encontrado en API'))
                    continue
                
                prod_api = productos_api_dict[producto.codigo]
                
                # Buscar URL de imagen
                def buscar_imagen_en_objeto(obj):
                    """Buscar URL de imagen en un objeto, probando diferentes campos"""
                    if not isinstance(obj, dict):
                        return None
                    
                    # Buscar en el campo especificado
                    if imagen_field in obj and obj[imagen_field]:
                        return obj[imagen_field]
                    
                    # Buscar en campos comunes alternativos
                    campos_posibles = [
                        'imagen_url', 'url_imagen', 'image_url', 'url_image',
                        'imagen', 'image', 'foto', 'photo', 'picture',
                        'url', 'link', 'src'
                    ]
                    for campo in campos_posibles:
                        if campo in obj and obj[campo]:
                            return obj[campo]
                    return None
                
                imagen_path = buscar_imagen_en_objeto(prod_api)
                
                if not imagen_path:
                    productos_sin_imagen_api += 1
                    self.stdout.write(self.style.WARNING('Sin imagen en API'))
                    continue
                
                # Construir URL completa de la imagen
                if imagen_path.startswith('http://') or imagen_path.startswith('https://'):
                    imagen_url = imagen_path
                elif imagen_path.startswith('/'):
                    imagen_url = f"{base_url_imagenes}{imagen_path}"
                else:
                    imagen_url = f"{base_url_imagenes}/{imagen_path}"
                
                # Descargar la imagen
                try:
                    img_response = requests.get(imagen_url, headers=headers, timeout=timeout, stream=True)
                    
                    if img_response.status_code == 200:
                        # Obtener extensión del archivo
                        parsed_url = urlparse(imagen_url)
                        path = parsed_url.path
                        ext = os.path.splitext(path)[1] or '.jpg'
                        
                        # Validar que sea una imagen
                        content_type = img_response.headers.get('content-type', '')
                        if not content_type.startswith('image/'):
                            productos_con_error += 1
                            self.stdout.write(self.style.ERROR('No es una imagen válida'))
                            continue
                        
                        # Crear nombre de archivo (sin la carpeta, Django usa upload_to automáticamente)
                        filename = f"{producto.codigo}{ext}"
                        
                        # Guardar la imagen
                        producto.imagen.save(
                            filename,
                            ContentFile(img_response.content),
                            save=True
                        )
                        
                        productos_actualizados += 1
                        self.stdout.write(self.style.SUCCESS('OK'))
                    else:
                        productos_con_error += 1
                        self.stdout.write(self.style.ERROR(f'Error HTTP {img_response.status_code}'))
                except requests.exceptions.RequestException as e:
                    productos_con_error += 1
                    self.stdout.write(self.style.ERROR(f'Error al descargar: {str(e)[:50]}'))
                except Exception as e:
                    productos_con_error += 1
                    self.stdout.write(self.style.ERROR(f'Error: {str(e)[:50]}'))
                    
            except Exception as e:
                productos_con_error += 1
                self.stdout.write(self.style.ERROR(f'Error: {str(e)[:50]}'))
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('PROCESO COMPLETADO'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(f'Productos actualizados: {productos_actualizados}')
        self.stdout.write(f'Productos no encontrados en API: {productos_no_encontrados}')
        self.stdout.write(f'Productos sin imagen en API: {productos_sin_imagen_api}')
        self.stdout.write(f'Productos con error: {productos_con_error}')
        self.stdout.write('')

