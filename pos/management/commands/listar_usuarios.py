"""
Comando para listar usuarios del sistema con sus PINs
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from pos.models import PerfilUsuario


class Command(BaseCommand):
    help = 'Lista todos los usuarios del sistema con sus PINs'

    def add_arguments(self, parser):
        parser.add_argument(
            '--con-pin',
            action='store_true',
            help='Mostrar solo usuarios con PIN',
        )
        parser.add_argument(
            '--sin-pin',
            action='store_true',
            help='Mostrar solo usuarios sin PIN',
        )
        parser.add_argument(
            '--activos',
            action='store_true',
            help='Mostrar solo usuarios activos',
        )

    def handle(self, *args, **options):
        usuarios = User.objects.all()

        if options['activos']:
            usuarios = usuarios.filter(is_active=True)

        self.stdout.write(self.style.SUCCESS('\n=== USUARIOS DEL SISTEMA ===\n'))

        count = 0
        for user in usuarios:
            try:
                perfil = user.perfil
                tiene_pin = perfil.pin_establecido
                pin = perfil.pin if tiene_pin else 'No establecido'
            except PerfilUsuario.DoesNotExist:
                tiene_pin = False
                pin = 'Sin perfil'

            # Filtrar según opciones
            if options['con_pin'] and not tiene_pin:
                continue
            if options['sin_pin'] and tiene_pin:
                continue

            count += 1

            # Información del usuario
            nombre_completo = user.get_full_name() or user.username
            grupos = ', '.join([g.name for g in user.groups.all()]) or 'Sin grupo'
            estado = '[OK] Activo' if user.is_active else '[X] Inactivo'
            tipo = 'SUPERUSER' if user.is_superuser else ('STAFF' if user.is_staff else 'Usuario')

            self.stdout.write(f'Usuario: {user.username}')
            self.stdout.write(f'  Nombre: {nombre_completo}')
            self.stdout.write(f'  Email: {user.email or "No especificado"}')
            self.stdout.write(f'  PIN: {pin}')
            self.stdout.write(f'  Grupos: {grupos}')
            self.stdout.write(f'  Tipo: {tipo}')
            self.stdout.write(f'  Estado: {estado}')
            
            # Mostrar permisos especiales
            if user.is_superuser:
                self.stdout.write(self.style.WARNING('  [!] Tiene todos los permisos (superuser)'))
            
            self.stdout.write('')  # Línea en blanco

        if count == 0:
            self.stdout.write(self.style.WARNING('No se encontraron usuarios'))
        else:
            self.stdout.write(
                self.style.SUCCESS(f'Total de usuarios: {count}')
            )

