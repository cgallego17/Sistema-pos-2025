# -*- coding: utf-8 -*-
"""
Comando para importar productos desde un archivo Excel
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from pos.models import Producto
import openpyxl
import os


class Command(BaseCommand):
    help = 'Importa productos desde un archivo Excel'

    def add_arguments(self, parser):
        parser.add_argument(
            'archivo',
            type=str,
            help='Ruta del archivo Excel a importar'
        )
        parser.add_argument(
            '--actualizar',
            action='store_true',
            help='Actualizar productos existentes si el código ya existe',
        )
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirmar sin preguntar',
        )

    def handle(self, *args, **options):
        archivo = options['archivo']
        
        if not os.path.exists(archivo):
            self.stdout.write(self.style.ERROR(f'El archivo {archivo} no existe'))
            return
        
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('IMPORTACIÓN DE PRODUCTOS DESDE EXCEL'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(f'Archivo: {archivo}')
        self.stdout.write('')
        
        try:
            # Cargar el archivo Excel con data_only=True para obtener valores calculados
            wb = openpyxl.load_workbook(archivo, data_only=True)
            ws = wb.active
            
            # Leer la primera fila como encabezados
            headers = [cell.value for cell in next(ws.iter_rows(min_row=1, max_row=1))]
            self.stdout.write(f'Columnas encontradas: {headers}')
            self.stdout.write('')
            
            # Mapear columnas (buscar por nombre, case-insensitive)
            col_indices = {}
            for idx, header in enumerate(headers):
                if header:
                    header_lower = str(header).lower().strip()
                    if 'codigo' in header_lower and 'barra' not in header_lower:
                        col_indices['codigo'] = idx
                    elif 'nombre' in header_lower and 'atributo' not in header_lower:
                        col_indices['nombre'] = idx
                    elif 'atributo' in header_lower or 'nombreatributo' in header_lower:
                        col_indices['atributo'] = idx
                    elif 'existencia' in header_lower or 'stock' in header_lower:
                        col_indices['stock'] = idx
                    elif 'precio' in header_lower:
                        col_indices['precio'] = idx
                    elif 'barra' in header_lower or 'codigo_barra' in header_lower:
                        col_indices['codigo_barras'] = idx
            
            self.stdout.write(f'Columnas mapeadas: {col_indices}')
            self.stdout.write('')
            
            if 'codigo' not in col_indices or 'nombre' not in col_indices:
                self.stdout.write(self.style.ERROR('ERROR: No se encontraron las columnas requeridas (codigo, nombre)'))
                return
            
            # Leer todas las filas de datos
            productos_a_importar = []
            filas_con_error = []
            
            for row_num, row in enumerate(ws.iter_rows(min_row=2), start=2):
                try:
                    # Obtener valores de las celdas
                    codigo = self._get_cell_value(row, col_indices.get('codigo'))
                    nombre = self._get_cell_value(row, col_indices.get('nombre'))
                    atributo = self._get_cell_value(row, col_indices.get('atributo'))
                    stock = self._get_cell_value(row, col_indices.get('stock'))
                    precio = self._get_cell_value(row, col_indices.get('precio'))
                    codigo_barras = self._get_cell_value(row, col_indices.get('codigo_barras'))
                    
                    # Validar campos requeridos
                    if not codigo or not nombre:
                        continue  # Saltar filas vacías
                    
                    # Limpiar y convertir valores
                    codigo = str(codigo).strip()
                    nombre = str(nombre).strip()
                    
                    # Atributo
                    if atributo:
                        atributo = str(atributo).strip()
                        if atributo.upper() == 'SIN ATRIBUTO' or atributo == '':
                            atributo = None
                    else:
                        atributo = None
                    
                    # Stock
                    if stock is None:
                        stock = 0
                    else:
                        try:
                            stock = int(float(stock))
                            if stock < 0:
                                stock = 0
                        except (ValueError, TypeError):
                            stock = 0
                    
                    # Precio
                    if precio is None:
                        precio = 0
                    else:
                        try:
                            precio = int(float(precio))
                            if precio < 0:
                                precio = 0
                        except (ValueError, TypeError):
                            precio = 0
                    
                    # Código de barras
                    if codigo_barras:
                        try:
                            # Convertir a string y limpiar
                            codigo_barras = str(int(float(codigo_barras))).strip()
                            if codigo_barras == '0' or codigo_barras == '':
                                codigo_barras = None
                        except (ValueError, TypeError):
                            codigo_barras = None
                    else:
                        codigo_barras = None
                    
                    productos_a_importar.append({
                        'codigo': codigo,
                        'nombre': nombre,
                        'atributo': atributo,
                        'stock': stock,
                        'precio': precio,
                        'codigo_barras': codigo_barras,
                        'fila': row_num
                    })
                    
                except Exception as e:
                    filas_con_error.append({
                        'fila': row_num,
                        'error': str(e)
                    })
            
            self.stdout.write(f'Productos encontrados en el archivo: {len(productos_a_importar)}')
            if filas_con_error:
                self.stdout.write(self.style.WARNING(f'Filas con errores: {len(filas_con_error)}'))
            self.stdout.write('')
            
            if not productos_a_importar:
                self.stdout.write(self.style.WARNING('No se encontraron productos para importar'))
                return
            
            # Mostrar muestra de productos
            self.stdout.write('Muestra de productos a importar:')
            for i, prod in enumerate(productos_a_importar[:5], 1):
                self.stdout.write(f'  {i}. {prod["codigo"]} - {prod["nombre"]} (Atributo: {prod["atributo"] or "N/A"}, Stock: {prod["stock"]}, Precio: ${prod["precio"]:,})')
            if len(productos_a_importar) > 5:
                self.stdout.write(f'  ... y {len(productos_a_importar) - 5} más')
            self.stdout.write('')
            
            # Confirmación
            if not options['confirm']:
                respuesta = input('¿Deseas continuar con la importación? (si/no): ')
                if respuesta.lower() != 'si':
                    self.stdout.write(self.style.WARNING('Importación cancelada'))
                    return
            
            # Importar productos
            self.stdout.write(self.style.WARNING('Iniciando importación...'))
            
            productos_creados = 0
            productos_actualizados = 0
            productos_con_error = 0
            
            with transaction.atomic():
                for prod_data in productos_a_importar:
                    try:
                        producto, created = Producto.objects.get_or_create(
                            codigo=prod_data['codigo'],
                            defaults={
                                'nombre': prod_data['nombre'],
                                'atributo': prod_data['atributo'],
                                'precio': prod_data['precio'],
                                'stock': prod_data['stock'],
                                'codigo_barras': prod_data['codigo_barras'],
                                'activo': True
                            }
                        )
                        
                        if created:
                            productos_creados += 1
                        else:
                            # Producto ya existe
                            if options['actualizar']:
                                producto.nombre = prod_data['nombre']
                                producto.atributo = prod_data['atributo']
                                producto.precio = prod_data['precio']
                                producto.stock = prod_data['stock']
                                if prod_data['codigo_barras']:
                                    producto.codigo_barras = prod_data['codigo_barras']
                                producto.activo = True
                                producto.save()
                                productos_actualizados += 1
                            else:
                                # No actualizar, solo contar
                                pass
                                
                    except Exception as e:
                        productos_con_error += 1
                        self.stdout.write(self.style.ERROR(f'Error en fila {prod_data["fila"]} (Código: {prod_data["codigo"]}): {str(e)}'))
            
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS('=' * 70))
            self.stdout.write(self.style.SUCCESS('IMPORTACIÓN COMPLETADA'))
            self.stdout.write(self.style.SUCCESS('=' * 70))
            self.stdout.write(f'Productos creados: {productos_creados}')
            if options['actualizar']:
                self.stdout.write(f'Productos actualizados: {productos_actualizados}')
            self.stdout.write(f'Productos con error: {productos_con_error}')
            
            if filas_con_error:
                self.stdout.write('')
                self.stdout.write(self.style.WARNING('Filas con errores:'))
                for error in filas_con_error[:10]:
                    self.stdout.write(f'  Fila {error["fila"]}: {error["error"]}')
                if len(filas_con_error) > 10:
                    self.stdout.write(f'  ... y {len(filas_con_error) - 10} más')
            
        except Exception as e:
            self.stdout.write('')
            self.stdout.write(self.style.ERROR('=' * 70))
            self.stdout.write(self.style.ERROR('ERROR AL IMPORTAR'))
            self.stdout.write(self.style.ERROR('=' * 70))
            self.stdout.write(self.style.ERROR(f'Error: {str(e)}'))
            import traceback
            self.stdout.write(self.style.ERROR(traceback.format_exc()))
    
    def _get_cell_value(self, row, col_index):
        """Obtener valor de una celda de forma segura"""
        if col_index is None or col_index >= len(row):
            return None
        cell = row[col_index]
        if cell is None:
            return None
        return cell.value


