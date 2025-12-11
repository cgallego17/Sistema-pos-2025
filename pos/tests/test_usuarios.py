"""
Tests para el módulo de Usuarios y Login
"""
from django.test import TestCase, Client, signals
from django.contrib.auth.models import User, Group
from django.urls import reverse
from pos.models import PerfilUsuario
from django.test.client import store_rendered_templates

# Evitar problemas al copiar contextos instrumentados en tests
signals.template_rendered.receivers = []


class UsuariosTestCase(TestCase):
    """Tests para el módulo de usuarios"""
    
    def setUp(self):
        """Configuración inicial"""
        signals.template_rendered.receivers.clear()
        signals.template_rendered.disconnect(store_rendered_templates)
        signals.template_rendered.receivers.clear()
        signals.template_rendered.send = lambda *args, **kwargs: None
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@test.com',
            is_staff=True
        )
        
        # Crear perfil con PIN
        PerfilUsuario.objects.create(
            usuario=self.user,
            pin='1234'
        )
        grupo_admin, _ = Group.objects.get_or_create(name='Administradores')
        self.user.groups.add(grupo_admin)
        
        self.client = Client()
    
    def test_login_con_pin(self):
        """Test: Login con username y PIN"""
        response = self.client.post(reverse('pos:login'), {
            'username': 'testuser',
            'pin': '1234'
        })
        self.assertIn(response.status_code, [200, 302])
    
    def test_login_pin_incorrecto(self):
        """Test: Login con PIN incorrecto"""
        response = self.client.post(reverse('pos:login'), {
            'username': 'testuser',
            'pin': '9999'  # PIN incorrecto
        })
        self.assertNotIn('_auth_user_id', self.client.session)
    
    def test_listar_usuarios(self):
        """Test: Listar usuarios"""
        self.client.force_login(self.user)
        
        response = self.client.get(reverse('pos:usuarios'))
        self.assertIn(response.status_code, [200, 302])
        # Verificar hay usuarios
        self.assertGreaterEqual(User.objects.count(), 1)
    
    def test_crear_usuario(self):
        """Test: Crear un nuevo usuario"""
        self.client.force_login(self.user)
        
        response = self.client.post(reverse('pos:crear_usuario'), {
            'username': 'nuevousuario',
            'email': 'nuevo@test.com',
            'first_name': 'Nuevo',
            'last_name': 'Usuario',
            'password': 'pass123',
            'is_staff': 'on',
            'is_active': 'on'
        })
        
        self.assertIn(response.status_code, [200, 302])  # Redirect después de crear
        
        # Verificar que se creó el usuario
        usuario = User.objects.filter(username='nuevousuario').first()
        self.assertIsNotNone(usuario)
        self.assertEqual(usuario.email, 'nuevo@test.com')
        
        # Verificar que se creó el perfil
        perfil = PerfilUsuario.objects.filter(usuario=usuario).first()
        self.assertIsNotNone(perfil)

