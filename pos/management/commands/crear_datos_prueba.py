"""
Comando para crear datos de prueba del sistema POS
"""
import sys
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group
from django.utils import timezone
from datetime import date, timedelta, datetime
import random

from pos.models import (
    Producto, Caja, CajaUsuario, Venta, ItemVenta,
    MovimientoStock, GastoCaja
)


class Command(BaseCommand):
    help = 'Crea datos de prueba para el sistema POS'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limpiar',
            action='store_true',
            help='Elimina todos los datos existentes antes de crear nuevos',
        )

    def handle(self, *args, **options):
        if options['limpiar']:
            self.stdout.write('Limpiando datos existentes...')
            self._limpiar_datos()
        
        self.stdout.write('Creando datos de prueba...')
        
        # Crear usuarios si no existen
        usuarios = self._crear_usuarios()
        
        # Crear productos
        productos = self._crear_productos()
        
        # Crear caja principal
        caja_principal = self._crear_caja_principal()
        
        # Crear cajas de días anteriores (cerradas)
        self._crear_cajas_anteriores(usuarios, caja_principal)
        
        # Crear caja abierta del día actual
        caja_abierta = self._crear_caja_abierta(usuarios[0], caja_principal)
        
        # Crear ventas del día actual
        self._crear_ventas_dia_actual(usuarios, productos, caja_principal)
        
        # Crear ventas de días anteriores
        self._crear_ventas_dias_anteriores(usuarios, productos, caja_principal)
        
        # Crear gastos e ingresos del día actual
        self._crear_movimientos_caja(caja_abierta, usuarios[0])
        
        # Crear movimientos de stock
        self._crear_movimientos_stock(productos, usuarios[0])
        
        self.stdout.write(self.style.SUCCESS('\n[OK] Datos de prueba creados exitosamente'))
        self.stdout.write('\nResumen:')
        self.stdout.write(f'  - Usuarios: {User.objects.count()}')
        self.stdout.write(f'  - Productos: {Producto.objects.count()}')
        self.stdout.write(f'  - Ventas: {Venta.objects.count()}')
        self.stdout.write(f'  - Cajas: {CajaUsuario.objects.count()}')
        self.stdout.write(f'  - Movimientos de caja: {GastoCaja.objects.count()}')

    def _limpiar_datos(self):
        """Elimina todos los datos de prueba"""
        ItemVenta.objects.all().delete()
        Venta.objects.all().delete()
        GastoCaja.objects.all().delete()
        CajaUsuario.objects.all().delete()
        MovimientoStock.objects.all().delete()
        Producto.objects.all().delete()
        # No eliminar usuarios ni cajas principales

    def _crear_usuarios(self):
        """Crea usuarios de prueba si no existen"""
        usuarios = []
        
        # Usuario administrador
        admin, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@pos.com',
                'first_name': 'Administrador',
                'last_name': 'Sistema',
                'is_staff': True,
                'is_superuser': True
            }
        )
        if created:
            admin.set_password('admin123')
            admin.save()
            grupo_admin = Group.objects.get(name='Administradores')
            admin.groups.add(grupo_admin)
            self.stdout.write('  [OK] Usuario admin creado')
        usuarios.append(admin)
        
        # Usuario cajero
        cajero, created = User.objects.get_or_create(
            username='cajero',
            defaults={
                'email': 'cajero@pos.com',
                'first_name': 'Juan',
                'last_name': 'Cajero'
            }
        )
        if created:
            cajero.set_password('cajero123')
            cajero.save()
            grupo_cajero = Group.objects.get(name='Cajeros')
            cajero.groups.add(grupo_cajero)
            self.stdout.write('  [OK] Usuario cajero creado')
        usuarios.append(cajero)
        
        # Usuario vendedor
        vendedor, created = User.objects.get_or_create(
            username='vendedor',
            defaults={
                'email': 'vendedor@pos.com',
                'first_name': 'María',
                'last_name': 'Vendedora'
            }
        )
        if created:
            vendedor.set_password('vendedor123')
            vendedor.save()
            grupo_vendedor = Group.objects.get(name='Vendedores')
            vendedor.groups.add(grupo_vendedor)
            self.stdout.write('  [OK] Usuario vendedor creado')
        usuarios.append(vendedor)
        
        return usuarios

    def _crear_productos(self):
        """Crea productos de prueba"""
        productos_data = [
            {'codigo': 'PROD001', 'nombre': 'Shampoo Reparador 500ml', 'precio': 25000, 'stock': 50},
            {'codigo': 'PROD002', 'nombre': 'Acondicionador Hidratante 500ml', 'precio': 28000, 'stock': 45},
            {'codigo': 'PROD003', 'nombre': 'Mascarilla Capilar 400ml', 'precio': 35000, 'stock': 30},
            {'codigo': 'PROD004', 'nombre': 'Crema Facial Noche 50ml', 'precio': 45000, 'stock': 25},
            {'codigo': 'PROD005', 'nombre': 'Serum Vitamina C 30ml', 'precio': 55000, 'stock': 20},
            {'codigo': 'PROD006', 'nombre': 'Protector Solar SPF50 100ml', 'precio': 38000, 'stock': 40},
            {'codigo': 'PROD007', 'nombre': 'Jabón Facial Limpieza Profunda', 'precio': 15000, 'stock': 60},
            {'codigo': 'PROD008', 'nombre': 'Tónico Facial 200ml', 'precio': 22000, 'stock': 35},
            {'codigo': 'PROD009', 'nombre': 'Crema Corporal 500ml', 'precio': 32000, 'stock': 50},
            {'codigo': 'PROD010', 'nombre': 'Aceite Corporal 250ml', 'precio': 42000, 'stock': 30},
            {'codigo': 'PROD011', 'nombre': 'Desodorante Roll-On 50ml', 'precio': 12000, 'stock': 80},
            {'codigo': 'PROD012', 'nombre': 'Perfume Eau de Toilette 100ml', 'precio': 85000, 'stock': 15},
            {'codigo': 'PROD013', 'nombre': 'Labial Mate 4g', 'precio': 18000, 'stock': 70},
            {'codigo': 'PROD014', 'nombre': 'Máscara de Pestañas', 'precio': 25000, 'stock': 55},
            {'codigo': 'PROD015', 'nombre': 'Base Líquida 30ml', 'precio': 45000, 'stock': 40},
        ]
        
        productos = []
        for prod_data in productos_data:
            producto, created = Producto.objects.get_or_create(
                codigo=prod_data['codigo'],
                defaults={
                    'nombre': prod_data['nombre'],
                    'precio': prod_data['precio'],
                    'stock': prod_data['stock'],
                    'activo': True
                }
            )
            if created:
                productos.append(producto)
            else:
                productos.append(producto)
        
        self.stdout.write(f'  [OK] {len(productos)} productos creados/verificados')
        return productos

    def _crear_caja_principal(self):
        """Crea la caja principal si no existe"""
        caja, created = Caja.objects.get_or_create(
            numero=1,
            defaults={
                'nombre': 'Caja Principal',
                'activa': True
            }
        )
        if created:
            self.stdout.write('  [OK] Caja Principal creada')
        return caja

    def _crear_cajas_anteriores(self, usuarios, caja_principal):
        """Crea cajas cerradas de días anteriores"""
        hoy = date.today()
        
        for i in range(1, 4):  # Últimos 3 días
            fecha_apertura_date = hoy - timedelta(days=i)
            fecha_cierre_date = fecha_apertura_date
            
            # Crear caja cerrada
            fecha_apertura = timezone.make_aware(
                datetime.combine(fecha_apertura_date, datetime.min.time())
            ).replace(hour=8, minute=0)
            
            fecha_cierre = timezone.make_aware(
                datetime.combine(fecha_cierre_date, datetime.min.time())
            ).replace(hour=22, minute=0)
            
            caja_usuario = CajaUsuario.objects.create(
                caja=caja_principal,
                usuario=usuarios[0],
                monto_inicial=500000,
                fecha_apertura=fecha_apertura,
                fecha_cierre=fecha_cierre,
                monto_final=750000 + random.randint(-50000, 100000)
            )
        
        self.stdout.write('  [OK] Cajas de días anteriores creadas')

    def _crear_caja_abierta(self, usuario, caja_principal):
        """Crea una caja abierta del día actual"""
        hoy = date.today()
        
        # Verificar si ya existe una caja abierta
        caja_abierta = CajaUsuario.objects.filter(
            usuario=usuario,
            fecha_cierre__isnull=True,
            fecha_apertura__date=hoy
        ).first()
        
        if not caja_abierta:
            caja_abierta = CajaUsuario.objects.create(
                caja=caja_principal,
                usuario=usuario,
                monto_inicial=500000,
                fecha_apertura=timezone.now().replace(hour=8, minute=0, second=0, microsecond=0)
            )
            self.stdout.write('  [OK] Caja abierta del día actual creada')
        else:
            self.stdout.write('  - Caja abierta del día actual ya existe')
        
        return caja_abierta

    def _crear_ventas_dia_actual(self, usuarios, productos, caja_principal):
        """Crea ventas del día actual"""
        hoy = date.today()
        inicio_dia = timezone.now().replace(hour=8, minute=0, second=0, microsecond=0)
        
        # Crear 10-15 ventas del día actual
        num_ventas = random.randint(10, 15)
        
        for i in range(num_ventas):
            # Hora aleatoria del día
            hora = random.randint(8, 20)
            minuto = random.randint(0, 59)
            fecha_venta = inicio_dia.replace(hour=hora, minute=minuto)
            
            # Usuario aleatorio
            usuario = random.choice(usuarios)
            vendedor = random.choice(usuarios) if random.random() > 0.3 else None
            
            # Método de pago aleatorio
            metodo_pago = random.choice(['efectivo', 'tarjeta', 'transferencia'])
            
            # Crear venta
            venta = Venta.objects.create(
                usuario=usuario,
                vendedor=vendedor,
                caja=caja_principal,
                fecha=fecha_venta,
                metodo_pago=metodo_pago,
                completada=True,
                anulada=False
            )
            
            # Agregar items a la venta
            num_items = random.randint(1, 5)
            productos_venta = random.sample(productos, min(num_items, len(productos)))
            total = 0
            
            for producto in productos_venta:
                cantidad = random.randint(1, 3)
                precio = producto.precio
                subtotal = precio * cantidad
                
                ItemVenta.objects.create(
                    venta=venta,
                    producto=producto,
                    cantidad=cantidad,
                    precio_unitario=precio,
                    subtotal=subtotal
                )
                
                total += subtotal
            
            venta.total = total
            if metodo_pago == 'efectivo':
                venta.monto_recibido = total + random.randint(0, 10000)
            venta.save()
        
        self.stdout.write(f'  [OK] {num_ventas} ventas del día actual creadas')

    def _crear_ventas_dias_anteriores(self, usuarios, productos, caja_principal):
        """Crea ventas de días anteriores"""
        hoy = date.today()
        
        for i in range(1, 4):  # Últimos 3 días
            fecha_venta = hoy - timedelta(days=i)
            num_ventas = random.randint(8, 12)
            
            for j in range(num_ventas):
                hora = random.randint(8, 20)
                minuto = random.randint(0, 59)
                fecha = timezone.make_aware(
                    datetime.combine(fecha_venta, datetime.min.time())
                ).replace(hour=hora, minute=minuto)
                
                usuario = random.choice(usuarios)
                vendedor = random.choice(usuarios) if random.random() > 0.3 else None
                metodo_pago = random.choice(['efectivo', 'tarjeta', 'transferencia'])
                
                venta = Venta.objects.create(
                    usuario=usuario,
                    vendedor=vendedor,
                    caja=caja_principal,
                    fecha=fecha,
                    metodo_pago=metodo_pago,
                    completada=True,
                    anulada=False
                )
                
                num_items = random.randint(1, 4)
                productos_venta = random.sample(productos, min(num_items, len(productos)))
                total = 0
                
                for producto in productos_venta:
                    cantidad = random.randint(1, 3)
                    precio = producto.precio
                    subtotal = precio * cantidad
                    
                    ItemVenta.objects.create(
                        venta=venta,
                        producto=producto,
                        cantidad=cantidad,
                        precio_unitario=precio,
                        subtotal=subtotal
                    )
                    
                    total += subtotal
                
                venta.total = total
                if metodo_pago == 'efectivo':
                    venta.monto_recibido = total + random.randint(0, 10000)
                venta.save()
        
        self.stdout.write('  [OK] Ventas de días anteriores creadas')

    def _crear_movimientos_caja(self, caja_abierta, usuario):
        """Crea gastos e ingresos del día actual"""
        hoy = date.today()
        inicio_dia = timezone.now().replace(hour=8, minute=0, second=0, microsecond=0)
        
        # Crear algunos gastos
        gastos_data = [
            {'monto': 50000, 'descripcion': 'Compra de materiales de oficina'},
            {'monto': 30000, 'descripcion': 'Pago de servicios públicos'},
            {'monto': 25000, 'descripcion': 'Gasto en publicidad'},
        ]
        
        for gasto_data in gastos_data:
            hora = random.randint(9, 17)
            minuto = random.randint(0, 59)
            fecha_gasto = inicio_dia.replace(hour=hora, minute=minuto)
            
            GastoCaja.objects.create(
                tipo='gasto',
                monto=gasto_data['monto'],
                descripcion=gasto_data['descripcion'],
                usuario=usuario,
                caja_usuario=caja_abierta,
                fecha=fecha_gasto
            )
        
        # Crear algunos ingresos
        ingresos_data = [
            {'monto': 100000, 'descripcion': 'Ingreso por venta de activos'},
            {'monto': 50000, 'descripcion': 'Reembolso de proveedor'},
        ]
        
        for ingreso_data in ingresos_data:
            hora = random.randint(10, 16)
            minuto = random.randint(0, 59)
            fecha_ingreso = inicio_dia.replace(hour=hora, minute=minuto)
            
            GastoCaja.objects.create(
                tipo='ingreso',
                monto=ingreso_data['monto'],
                descripcion=ingreso_data['descripcion'],
                usuario=usuario,
                caja_usuario=caja_abierta,
                fecha=fecha_ingreso
            )
        
        self.stdout.write('  [OK] Movimientos de caja creados')

    def _crear_movimientos_stock(self, productos, usuario):
        """Crea movimientos de stock"""
        for producto in productos[:5]:  # Solo algunos productos
            # Movimiento de ingreso
            MovimientoStock.objects.create(
                producto=producto,
                tipo='ingreso',
                cantidad=random.randint(10, 50),
                stock_anterior=producto.stock - random.randint(10, 50),
                stock_nuevo=producto.stock,
                motivo='Ingreso de mercancía de prueba',
                usuario=usuario,
                fecha=timezone.now() - timedelta(days=random.randint(1, 7))
            )
        
        self.stdout.write('  [OK] Movimientos de stock creados')

