"""
Comando para inicializar roles y permisos del sistema
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from pos.models import Producto, Venta, Caja, MovimientoStock, GastoCaja


class Command(BaseCommand):
    help = 'Inicializa los roles y permisos del sistema POS'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Inicializando roles y permisos...'))

        # Crear grupos
        self._crear_grupo_administradores()
        self._crear_grupo_vendedores()
        self._crear_grupo_cajeros()
        self._crear_grupo_inventario()

        self.stdout.write(self.style.SUCCESS('[OK] Roles y permisos configurados'))

    def _crear_grupo_administradores(self):
        """Crea el grupo de administradores con todos los permisos"""
        grupo, created = Group.objects.get_or_create(name='Administradores')
        
        if created or not grupo.permissions.exists():
            # Dar todos los permisos
            permisos = Permission.objects.all()
            grupo.permissions.set(permisos)
            self.stdout.write('  [OK] Grupo Administradores configurado')
        else:
            self.stdout.write('  - Grupo Administradores ya existe')

    def _crear_grupo_vendedores(self):
        """Crea el grupo de vendedores"""
        grupo, created = Group.objects.get_or_create(name='Vendedores')
        
        if created or not grupo.permissions.exists():
            permisos = []
            
            # Permisos de Venta
            ct_venta = ContentType.objects.get_for_model(Venta)
            permisos.extend(Permission.objects.filter(
                content_type=ct_venta,
                codename__in=['add_venta', 'view_venta', 'change_venta']
            ))
            
            # Permisos de Producto (solo ver)
            ct_producto = ContentType.objects.get_for_model(Producto)
            permisos.extend(Permission.objects.filter(
                content_type=ct_producto,
                codename='view_producto'
            ))
            
            # Permisos de Caja (ver y usar)
            ct_caja = ContentType.objects.get_for_model(Caja)
            permisos.extend(Permission.objects.filter(
                content_type=ct_caja,
                codename__in=['view_caja']
            ))
            
            grupo.permissions.set(permisos)
            self.stdout.write('  [OK] Grupo Vendedores configurado')
        else:
            self.stdout.write('  - Grupo Vendedores ya existe')

    def _crear_grupo_cajeros(self):
        """Crea el grupo de cajeros"""
        grupo, created = Group.objects.get_or_create(name='Cajeros')
        
        if created or not grupo.permissions.exists():
            permisos = []
            
            # Permisos de Venta
            ct_venta = ContentType.objects.get_for_model(Venta)
            permisos.extend(Permission.objects.filter(
                content_type=ct_venta,
                codename__in=['add_venta', 'view_venta', 'change_venta']
            ))
            
            # Permisos de Producto (solo ver)
            ct_producto = ContentType.objects.get_for_model(Producto)
            permisos.extend(Permission.objects.filter(
                content_type=ct_producto,
                codename='view_producto'
            ))
            
            # Permisos de Caja (completos)
            ct_caja = ContentType.objects.get_for_model(Caja)
            permisos.extend(Permission.objects.filter(
                content_type=ct_caja
            ))
            
            # Permisos de Gastos
            ct_gasto = ContentType.objects.get_for_model(GastoCaja)
            permisos.extend(Permission.objects.filter(
                content_type=ct_gasto,
                codename__in=['add_gastocaja', 'view_gastocaja']
            ))
            
            grupo.permissions.set(permisos)
            self.stdout.write('  [OK] Grupo Cajeros configurado')
        else:
            self.stdout.write('  - Grupo Cajeros ya existe')

    def _crear_grupo_inventario(self):
        """Crea el grupo de gestión de inventario"""
        grupo, created = Group.objects.get_or_create(name='Inventario')
        
        if created or not grupo.permissions.exists():
            permisos = []
            
            # Permisos de Producto (completos)
            ct_producto = ContentType.objects.get_for_model(Producto)
            permisos.extend(Permission.objects.filter(
                content_type=ct_producto
            ))
            
            # Permisos de Movimiento de Stock (completos)
            ct_movimiento = ContentType.objects.get_for_model(MovimientoStock)
            permisos.extend(Permission.objects.filter(
                content_type=ct_movimiento
            ))
            
            grupo.permissions.set(permisos)
            self.stdout.write('  [OK] Grupo Inventario configurado')
        else:
            self.stdout.write('  - Grupo Inventario ya existe')

