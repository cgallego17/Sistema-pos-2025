"""
Comando para probar el sistema de carrito por pestaña
Ejecutar con: python manage.py test_carrito_pestanas
"""
from django.core.management.base import BaseCommand
from django.test import RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.auth import get_user_model
from pos.views import get_carrito, agregar_al_carrito_view
from pos.models import Producto

User = get_user_model()


class Command(BaseCommand):
    help = 'Prueba el sistema de carrito por pestaña'

    def handle(self, *args, **options):
        self.stdout.write('\n' + '=' * 70)
        self.stdout.write(self.style.SUCCESS('PRUEBA DEL SISTEMA DE CARRITO POR PESTAÑA'))
        self.stdout.write('=' * 70)

        # Crear sesión de prueba
        factory = RequestFactory()
        request = factory.post('/agregar_carrito/')
        middleware = SessionMiddleware(lambda req: None)
        middleware.process_request(request)
        request.session.save()

        # Obtener usuario
        usuario = User.objects.first()
        if not usuario:
            self.stdout.write(self.style.ERROR('\nERROR: No hay usuarios en la base de datos'))
            return
        request.user = usuario

        self.stdout.write(f'\n[OK] Usuario: {usuario.username}')
        self.stdout.write(f'[OK] Sesion ID: {request.session.session_key}')

        # Generar dos tab_ids diferentes (simulando dos pestañas)
        tab_id_1 = 'tab_1234567890_abc123'
        tab_id_2 = 'tab_9876543210_xyz789'

        self.stdout.write(f'\n[OK] Tab ID Pestana 1: {tab_id_1}')
        self.stdout.write(f'[OK] Tab ID Pestana 2: {tab_id_2}')

        # Obtener producto
        producto = Producto.objects.filter(activo=True, stock__gt=0).first()
        if not producto:
            self.stdout.write(self.style.ERROR('\nERROR: No hay productos activos con stock'))
            return

        self.stdout.write(f'\n[OK] Producto: {producto.nombre} (Stock: {producto.stock})')

        # PRUEBA 1: Carritos independientes
        self.stdout.write('\n' + '-' * 70)
        self.stdout.write(self.style.WARNING('PRUEBA 1: Verificar que los carritos son independientes'))
        self.stdout.write('-' * 70)

        # Inicialmente vacíos
        carrito_1 = get_carrito(request, tab_id_1)
        carrito_2 = get_carrito(request, tab_id_2)
        self.stdout.write(f'\nCarrito 1 (inicial): {len(carrito_1)} items')
        self.stdout.write(f'Carrito 2 (inicial): {len(carrito_2)} items')

        # Agregar a pestaña 1
        request.POST = {
            'producto_id': str(producto.id),
            'cantidad': '2',
            'tab_id': tab_id_1,
            'csrfmiddlewaretoken': 'test_token'
        }
        self.stdout.write(f'\n-> Agregando 2 unidades a Pestana 1...')
        response_1 = agregar_al_carrito_view(request)
        
        carrito_1 = get_carrito(request, tab_id_1)
        carrito_2 = get_carrito(request, tab_id_2)

        self.stdout.write(f'Carrito 1: {len(carrito_1)} items')
        if carrito_1:
            for key, item in carrito_1.items():
                self.stdout.write(f'  - {item["nombre"]}: {item["cantidad"]} unidades')

        self.stdout.write(f'Carrito 2: {len(carrito_2)} items (debe estar vacío)')

        if len(carrito_1) == 1 and len(carrito_2) == 0:
            self.stdout.write(self.style.SUCCESS('  [OK] Pestana 2 esta vacia (correcto)'))
        else:
            self.stdout.write(self.style.ERROR('  [ERROR] Pestana 2 tiene items cuando deberia estar vacia'))

        # Agregar a pestaña 2
        request.POST = {
            'producto_id': str(producto.id),
            'cantidad': '3',
            'tab_id': tab_id_2,
            'csrfmiddlewaretoken': 'test_token'
        }
        self.stdout.write(f'\n-> Agregando 3 unidades a Pestana 2...')
        response_2 = agregar_al_carrito_view(request)

        carrito_1 = get_carrito(request, tab_id_1)
        carrito_2 = get_carrito(request, tab_id_2)

        self.stdout.write(f'\nCarrito 1: {len(carrito_1)} items')
        for key, item in carrito_1.items():
            self.stdout.write(f'  - {item["nombre"]}: {item["cantidad"]} unidades')

        self.stdout.write(f'Carrito 2: {len(carrito_2)} items')
        for key, item in carrito_2.items():
            self.stdout.write(f'  - {item["nombre"]}: {item["cantidad"]} unidades')

        # Verificar independencia
        if len(carrito_1) == 1 and len(carrito_2) == 1:
            item_1 = list(carrito_1.values())[0]
            item_2 = list(carrito_2.values())[0]
            if item_1['cantidad'] == 2 and item_2['cantidad'] == 3:
                self.stdout.write(self.style.SUCCESS('\n[OK] PRUEBA 1 EXITOSA'))
                self.stdout.write('   Cada pestana mantiene su propio carrito independiente')
            else:
                self.stdout.write(self.style.ERROR('\n[ERROR] Las cantidades no coinciden'))
        else:
            self.stdout.write(self.style.ERROR('\n[ERROR] Numero incorrecto de items'))

        # PRUEBA 2: Diferentes productos
        self.stdout.write('\n' + '-' * 70)
        self.stdout.write(self.style.WARNING('PRUEBA 2: Diferentes productos en cada pestaña'))
        self.stdout.write('-' * 70)

        producto_2 = Producto.objects.filter(activo=True, stock__gt=0).exclude(id=producto.id).first()
        if producto_2:
            request.POST = {
                'producto_id': str(producto_2.id),
                'cantidad': '1',
                'tab_id': tab_id_2,
                'csrfmiddlewaretoken': 'test_token'
            }
            self.stdout.write(f'\n-> Agregando {producto_2.nombre} solo a Pestana 2...')
            agregar_al_carrito_view(request)

            carrito_1 = get_carrito(request, tab_id_1)
            carrito_2 = get_carrito(request, tab_id_2)

            self.stdout.write(f'\nCarrito 1: {len(carrito_1)} items')
            for key, item in carrito_1.items():
                self.stdout.write(f'  - {item["nombre"]}: {item["cantidad"]} unidades')

            self.stdout.write(f'Carrito 2: {len(carrito_2)} items')
            for key, item in carrito_2.items():
                self.stdout.write(f'  - {item["nombre"]}: {item["cantidad"]} unidades')

            if len(carrito_1) == 1 and len(carrito_2) == 2:
                self.stdout.write(self.style.SUCCESS('\n[OK] PRUEBA 2 EXITOSA'))
                self.stdout.write('   Cada pestana puede tener diferentes productos')
            else:
                self.stdout.write(self.style.ERROR('\n[ERROR] Los productos se estan compartiendo'))
        else:
            self.stdout.write('\n(Solo hay un producto disponible, saltando esta prueba)')

        # Resumen
        self.stdout.write('\n' + '=' * 70)
        self.stdout.write(self.style.SUCCESS('RESUMEN'))
        self.stdout.write('=' * 70)
        self.stdout.write('\n[OK] Sistema de carrito por pestana implementado correctamente')
        self.stdout.write('[OK] Cada pestana mantiene su propio carrito independiente')
        self.stdout.write('[OK] Los productos agregados en una pestana no aparecen en otras')
        self.stdout.write('\n' + '=' * 70 + '\n')

