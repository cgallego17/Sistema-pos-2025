"""
Comando para generar PINs para usuarios sin PIN
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from pos.models import PerfilUsuario
from django.utils import timezone
import random


class Command(BaseCommand):
    help = 'Genera PINs de 4 dígitos para usuarios que no tienen'

    def add_arguments(self, parser):
        parser.add_argument(
            '--usuario',
            type=str,
            help='Username del usuario específico para generar PIN',
        )
        parser.add_argument(
            '--regenerar',
            action='store_true',
            help='Regenerar PIN incluso si ya existe',
        )

    def handle(self, *args, **options):
        username = options.get('usuario')
        regenerar = options.get('regenerar', False)

        if username:
            # Generar PIN para un usuario específico
            try:
                user = User.objects.get(username=username)
                self._generar_pin_usuario(user, regenerar)
            except User.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'Usuario "{username}" no encontrado')
                )
        else:
            # Generar PINs para todos los usuarios sin PIN
            usuarios = User.objects.all()
            count = 0
            
            for user in usuarios:
                if self._generar_pin_usuario(user, regenerar):
                    count += 1
            
            if count > 0:
                self.stdout.write(
                    self.style.SUCCESS(f'[OK] Se generaron {count} PINs')
                )
            else:
                self.stdout.write('Todos los usuarios ya tienen PIN')

    def _generar_pin_usuario(self, user, regenerar=False):
        """
        Genera un PIN para un usuario
        Retorna True si se generó un nuevo PIN
        """
        try:
            perfil = user.perfil
            
            if perfil.pin_establecido and not regenerar:
                self.stdout.write(
                    f'  - {user.username} ya tiene PIN: {perfil.pin}'
                )
                return False
            
            # Regenerar PIN
            nuevo_pin = str(random.randint(1000, 9999))
            perfil.pin = nuevo_pin
            perfil.pin_establecido = True
            perfil.fecha_creacion_pin = timezone.now()
            perfil.save()
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'  [OK] PIN regenerado para {user.username}: {nuevo_pin}'
                )
            )
            return True
            
        except PerfilUsuario.DoesNotExist:
            # Crear perfil con PIN
            nuevo_pin = str(random.randint(1000, 9999))
            PerfilUsuario.objects.create(
                usuario=user,
                pin=nuevo_pin,
                pin_establecido=True,
                fecha_creacion_pin=timezone.now()
            )
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'  [OK] PIN creado para {user.username}: {nuevo_pin}'
                )
            )
            return True

