"""
Comando para crear usuarios del sistema POS
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group, Permission
from django.contrib.contenttypes.models import ContentType
from pos.models import PerfilUsuario
import random


class Command(BaseCommand):
    help = 'Crea usuarios de ejemplo para el sistema POS'

    def add_arguments(self, parser):
        parser.add_argument(
            '--admin',
            action='store_true',
            help='Crear solo usuario administrador',
        )
        parser.add_argument(
            '--vendedor',
            action='store_true',
            help='Crear solo usuario vendedor',
        )
        parser.add_argument(
            '--cajero',
            action='store_true',
            help='Crear solo usuario cajero',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Creando usuarios...'))

        # Crear grupos si no existen
        grupo_admin, _ = Group.objects.get_or_create(name='Administradores')
        grupo_vendedor, _ = Group.objects.get_or_create(name='Vendedores')
        grupo_cajero, _ = Group.objects.get_or_create(name='Cajeros')

        if options['admin'] or not any([options['admin'], options['vendedor'], options['cajero']]):
            self._crear_admin()

        if options['vendedor'] or not any([options['admin'], options['vendedor'], options['cajero']]):
            self._crear_vendedor()

        if options['cajero'] or not any([options['admin'], options['vendedor'], options['cajero']]):
            self._crear_cajero()

        self.stdout.write(self.style.SUCCESS('[OK] Usuarios creados exitosamente'))

    def _crear_admin(self):
        """Crea un usuario administrador"""
        if not User.objects.filter(username='admin').exists():
            user = User.objects.create_user(
                username='admin',
                email='admin@pos.com',
                password='admin123',
                first_name='Administrador',
                last_name='Sistema',
                is_staff=True,
                is_superuser=True
            )
            
            # Crear perfil con PIN
            pin = '1234'
            PerfilUsuario.objects.create(
                usuario=user,
                pin=pin,
                pin_establecido=True
            )
            
            self.stdout.write(f'  [OK] Admin creado: admin / admin123 (PIN: {pin})')
        else:
            self.stdout.write('  - Admin ya existe')

    def _crear_vendedor(self):
        """Crea un usuario vendedor"""
        if not User.objects.filter(username='vendedor').exists():
            user = User.objects.create_user(
                username='vendedor',
                email='vendedor@pos.com',
                password='vendedor123',
                first_name='Juan',
                last_name='Vendedor',
                is_staff=False
            )
            
            # Agregar al grupo de vendedores
            grupo = Group.objects.get(name='Vendedores')
            user.groups.add(grupo)
            
            # Crear perfil con PIN
            pin = str(random.randint(1000, 9999))
            PerfilUsuario.objects.create(
                usuario=user,
                pin=pin,
                pin_establecido=True
            )
            
            self.stdout.write(f'  [OK] Vendedor creado: vendedor / vendedor123 (PIN: {pin})')
        else:
            self.stdout.write('  - Vendedor ya existe')

    def _crear_cajero(self):
        """Crea un usuario cajero"""
        if not User.objects.filter(username='cajero').exists():
            user = User.objects.create_user(
                username='cajero',
                email='cajero@pos.com',
                password='cajero123',
                first_name='María',
                last_name='Cajera',
                is_staff=False
            )
            
            # Agregar al grupo de cajeros
            grupo = Group.objects.get(name='Cajeros')
            user.groups.add(grupo)
            
            # Crear perfil con PIN
            pin = str(random.randint(1000, 9999))
            PerfilUsuario.objects.create(
                usuario=user,
                pin=pin,
                pin_establecido=True
            )
            
            self.stdout.write(f'  [OK] Cajero creado: cajero / cajero123 (PIN: {pin})')
        else:
            self.stdout.write('  - Cajero ya existe')

