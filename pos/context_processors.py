"""
Context processors para el sistema POS
"""
from django.conf import settings


def sistema_info(request):
    """
    Agrega información del sistema al contexto de las plantillas
    """
    return {
        'SISTEMA_NOMBRE': 'MegaPos By Megadominio.co',
        'SISTEMA_VERSION': '1.0',
        'DEBUG': settings.DEBUG,
    }


def usuario_info(request):
    """
    Agrega información del usuario al contexto
    """
    context = {}
    
    if request.user.is_authenticated:
        context['usuario_autenticado'] = True
        context['usuario_nombre'] = request.user.get_full_name() or request.user.username
        
        # Verificar si tiene perfil con PIN
        if hasattr(request.user, 'perfil'):
            context['usuario_tiene_pin'] = request.user.perfil.pin_establecido
        else:
            context['usuario_tiene_pin'] = False
            
        # Verificar permisos basados en roles
        grupos_usuario = request.user.groups.values_list('name', flat=True)
        
        def tiene_rol(*nombres_roles):
            if request.user.is_superuser:
                return True
            return any(rol in grupos_usuario for rol in nombres_roles)
        
        context['es_admin'] = request.user.is_staff or request.user.is_superuser
        context['es_administrador'] = tiene_rol('Administradores') or request.user.is_superuser
        context['es_cajero'] = tiene_rol('Cajeros')
        context['es_inventario'] = tiene_rol('Inventario')
        context['es_vendedor'] = tiene_rol('Vendedores')
        context['puede_vender'] = request.user.has_perm('pos.add_venta')
        context['puede_gestionar_productos'] = tiene_rol('Administradores', 'Inventario') or request.user.is_superuser
        context['puede_gestionar_cajas'] = tiene_rol('Administradores', 'Cajeros') or request.user.is_superuser
        context['puede_anular_ventas'] = tiene_rol('Administradores') or request.user.is_superuser or request.user.is_staff
    else:
        context['usuario_autenticado'] = False
    
    return context

