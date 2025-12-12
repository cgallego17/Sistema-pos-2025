# -*- coding: utf-8 -*-
"""
Comando para probar la funcionalidad de abrir caja
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import date
from pos.models import Caja, CajaUsuario


class Command(BaseCommand):
    help = 'Prueba la funcionalidad de abrir caja'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            default='admin',
            help='Nombre de usuario para la prueba',
        )
        parser.add_argument(
            '--monto',
            type=int,
            default=100000,
            help='Monto inicial para la caja',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('TEST DE ABRIR CAJA'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        
        username = options['username']
        monto_inicial = options['monto']
        hoy = date.today()
        
        # Obtener o crear usuario
        try:
            usuario = User.objects.get(username=username)
            self.stdout.write(self.style.SUCCESS(f'[OK] Usuario encontrado: {usuario.username}'))
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'[ERROR] Usuario no encontrado: {username}'))
            self.stdout.write(self.style.WARNING('Usuarios disponibles:'))
            for u in User.objects.all():
                self.stdout.write(f'  - {u.username}')
            return
        
        # Verificar si ya hay una caja abierta del día actual
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('-' * 70))
        self.stdout.write(self.style.SUCCESS('PASO 1: Verificar cajas existentes'))
        self.stdout.write(self.style.SUCCESS('-' * 70))
        
        cajas_abiertas_hoy = CajaUsuario.objects.filter(
            fecha_cierre__isnull=True,
            fecha_apertura__date=hoy
        )
        
        self.stdout.write(f'Cajas abiertas hoy: {cajas_abiertas_hoy.count()}')
        for caja in cajas_abiertas_hoy:
            self.stdout.write(f'  - ID: {caja.id}, Usuario: {caja.usuario.username}, Monto inicial: ${caja.monto_inicial:,}, Fecha: {caja.fecha_apertura}')
        
        if cajas_abiertas_hoy.exists():
            self.stdout.write(self.style.WARNING('[INFO] Ya hay una caja abierta para hoy. Se cerrará para la prueba.'))
            for caja in cajas_abiertas_hoy:
                caja.fecha_cierre = timezone.now()
                caja.monto_final = caja.monto_inicial
                caja.save()
                self.stdout.write(f'  [OK] Caja #{caja.id} cerrada para la prueba')
        
        # Obtener o crear Caja Principal
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('-' * 70))
        self.stdout.write(self.style.SUCCESS('PASO 2: Obtener o crear Caja Principal'))
        self.stdout.write(self.style.SUCCESS('-' * 70))
        
        caja_principal = Caja.objects.filter(numero=1).first()
        if not caja_principal:
            caja_principal = Caja.objects.create(
                numero=1,
                nombre='Caja Principal',
                activa=True
            )
            self.stdout.write(self.style.SUCCESS(f'[OK] Caja Principal creada: ID={caja_principal.id}'))
        else:
            self.stdout.write(self.style.SUCCESS(f'[OK] Caja Principal encontrada: ID={caja_principal.id}, Nombre={caja_principal.nombre}'))
        
        # Crear nueva caja
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('-' * 70))
        self.stdout.write(self.style.SUCCESS('PASO 3: Crear nueva caja'))
        self.stdout.write(self.style.SUCCESS('-' * 70))
        
        try:
            nueva_caja = CajaUsuario.objects.create(
                caja=caja_principal,
                usuario=usuario,
                monto_inicial=monto_inicial
            )
            
            self.stdout.write(self.style.SUCCESS(f'[OK] Caja creada exitosamente:'))
            self.stdout.write(f'  - ID: {nueva_caja.id}')
            self.stdout.write(f'  - Usuario: {nueva_caja.usuario.username}')
            self.stdout.write(f'  - Monto inicial: ${nueva_caja.monto_inicial:,}')
            self.stdout.write(f'  - Fecha apertura: {nueva_caja.fecha_apertura}')
            self.stdout.write(f'  - Fecha cierre: {nueva_caja.fecha_cierre or "No cerrada"}')
            self.stdout.write(f'  - Caja: {nueva_caja.caja.nombre}')
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'[ERROR] Error al crear caja: {str(e)}'))
            import traceback
            self.stdout.write(traceback.format_exc())
            return
        
        # Verificar que la caja se puede obtener
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('-' * 70))
        self.stdout.write(self.style.SUCCESS('PASO 4: Verificar que la caja se puede obtener'))
        self.stdout.write(self.style.SUCCESS('-' * 70))
        
        caja_obtenida = CajaUsuario.objects.filter(
            fecha_cierre__isnull=True,
            fecha_apertura__date=hoy,
            caja=caja_principal
        ).first()
        
        if caja_obtenida:
            if caja_obtenida.id == nueva_caja.id:
                self.stdout.write(self.style.SUCCESS(f'[OK] Caja obtenida correctamente: ID={caja_obtenida.id}'))
            else:
                self.stdout.write(self.style.WARNING(f'[WARNING] Se obtuvo una caja diferente: ID={caja_obtenida.id} (esperado: {nueva_caja.id})'))
        else:
            self.stdout.write(self.style.ERROR('[ERROR] No se pudo obtener la caja creada'))
        
        # Verificar función obtener_caja_mostrar
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('-' * 70))
        self.stdout.write(self.style.SUCCESS('PASO 5: Verificar función obtener_caja_mostrar'))
        self.stdout.write(self.style.SUCCESS('-' * 70))
        
        try:
            from pos.views import obtener_caja_mostrar
            caja_mostrar = obtener_caja_mostrar(None, hoy)
            if caja_mostrar:
                if caja_mostrar.id == nueva_caja.id:
                    self.stdout.write(self.style.SUCCESS(f'[OK] obtener_caja_mostrar() retorna la caja correcta: ID={caja_mostrar.id}'))
                else:
                    self.stdout.write(self.style.WARNING(f'[WARNING] obtener_caja_mostrar() retorna caja diferente: ID={caja_mostrar.id} (esperado: {nueva_caja.id})'))
            else:
                self.stdout.write(self.style.ERROR('[ERROR] obtener_caja_mostrar() no retorna ninguna caja'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'[ERROR] Error al llamar obtener_caja_mostrar(): {str(e)}'))
            import traceback
            self.stdout.write(traceback.format_exc())
        
        # Resumen final
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('RESUMEN'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(f'Caja creada: ID={nueva_caja.id}')
        self.stdout.write(f'Usuario: {usuario.username}')
        self.stdout.write(f'Monto inicial: ${monto_inicial:,}')
        self.stdout.write(f'Fecha: {hoy}')
        self.stdout.write(f'Estado: {"Abierta" if nueva_caja.fecha_cierre is None else "Cerrada"}')
        
        # Verificar todas las cajas del día
        todas_cajas_hoy = CajaUsuario.objects.filter(fecha_apertura__date=hoy)
        self.stdout.write('')
        self.stdout.write(f'Total de cajas del día: {todas_cajas_hoy.count()}')
        for caja in todas_cajas_hoy:
            estado = "Abierta" if caja.fecha_cierre is None else "Cerrada"
            self.stdout.write(f'  - ID: {caja.id}, Usuario: {caja.usuario.username}, Estado: {estado}, Monto: ${caja.monto_inicial:,}')



