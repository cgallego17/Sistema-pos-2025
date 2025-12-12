from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models.signals import pre_delete
from django.dispatch import receiver


class Producto(models.Model):
    """Modelo para productos del sistema POS"""
    codigo = models.CharField(
        max_length=50, 
        verbose_name='Código',
        db_index=True
    )
    codigo_barras = models.CharField(
        max_length=100, 
        unique=True, 
        null=True, 
        blank=True,
        verbose_name='Código de Barras',
        db_index=True
    )
    nombre = models.CharField(
        max_length=200, 
        verbose_name='Nombre',
        db_index=True
    )
    atributo = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        verbose_name='Atributo',
        help_text='Atributo adicional del producto (ej: color, tamaño, modelo, etc.)'
    )
    precio = models.IntegerField(
        default=0,
        verbose_name='Precio'
    )
    stock = models.IntegerField(
        default=0, 
        verbose_name='Stock'
    )
    activo = models.BooleanField(
        default=True, 
        verbose_name='Activo',
        db_index=True
    )
    imagen = models.ImageField(
        upload_to='productos/', 
        null=True, 
        blank=True,
        verbose_name='Imagen'
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Producto'
        verbose_name_plural = 'Productos'
        ordering = ['nombre']
        constraints = [
            # Restricción única: código + atributo (permitir múltiples productos con mismo código si tienen atributos diferentes)
            models.UniqueConstraint(
                fields=['codigo', 'atributo'],
                name='unique_codigo_atributo'
            ),
        ]
        indexes = [
            models.Index(fields=['activo', 'stock']),
            models.Index(fields=['codigo', 'activo']),
            models.Index(fields=['codigo_barras', 'activo']),
        ]

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


class Caja(models.Model):
    """Modelo para cajas del sistema"""
    numero = models.IntegerField(unique=True, verbose_name='Número de Caja')
    nombre = models.CharField(max_length=100, verbose_name='Nombre')
    activa = models.BooleanField(default=True, verbose_name='Activa')

    class Meta:
        verbose_name = 'Caja'
        verbose_name_plural = 'Cajas'
        ordering = ['numero']

    def __str__(self):
        return f"Caja {self.numero} - {self.nombre}"


class CajaUsuario(models.Model):
    """Modelo para apertura y cierre de cajas por usuario"""
    caja = models.ForeignKey(Caja, on_delete=models.CASCADE, verbose_name='Caja')
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Usuario')
    fecha_apertura = models.DateTimeField(
        default=timezone.now, 
        verbose_name='Fecha de Apertura'
    )
    fecha_cierre = models.DateTimeField(
        null=True, 
        blank=True, 
        verbose_name='Fecha de Cierre'
    )
    monto_inicial = models.IntegerField(
        default=0,
        verbose_name='Monto Inicial'
    )
    monto_final = models.IntegerField(
        null=True, 
        blank=True,
        default=0,
        verbose_name='Monto Final'
    )

    class Meta:
        verbose_name = 'Caja Usuario'
        verbose_name_plural = 'Cajas Usuarios'
        ordering = ['-fecha_apertura']
        indexes = [
            models.Index(fields=['caja', 'fecha_cierre']),
            models.Index(fields=['usuario', 'fecha_cierre']),
        ]

    def __str__(self):
        return f"{self.caja} - {self.usuario.username} ({self.fecha_apertura})"


class Venta(models.Model):
    """Modelo para ventas"""
    METODOS_PAGO = [
        ('efectivo', 'Efectivo'),
        ('tarjeta', 'Tarjeta'),
        ('transferencia', 'Transferencia'),
    ]

    fecha = models.DateTimeField(
        default=timezone.now, 
        verbose_name='Fecha',
        db_index=True
    )
    total = models.IntegerField(
        default=0,
        verbose_name='Total'
    )
    completada = models.BooleanField(
        default=False, 
        verbose_name='Completada',
        db_index=True
    )
    metodo_pago = models.CharField(
        max_length=20, 
        choices=METODOS_PAGO, 
        default='efectivo',
        verbose_name='Método de Pago'
    )
    monto_recibido = models.IntegerField(
        null=True, 
        blank=True,
        default=0,
        verbose_name='Monto Recibido'
    )
    email_cliente = models.EmailField(
        null=True, 
        blank=True,
        verbose_name='Email del Cliente',
        help_text='Email del cliente para envío de recibo'
    )
    
    # Relaciones
    usuario = models.ForeignKey(
        User, 
        on_delete=models.PROTECT, 
        related_name='ventas',
        null=True, 
        blank=True,
        verbose_name='Usuario'
    )
    caja = models.ForeignKey(
        Caja, 
        on_delete=models.PROTECT, 
        related_name='ventas',
        null=True, 
        blank=True,
        verbose_name='Caja'
    )
    vendedor = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='ventas_vendidas',
        null=True,
        blank=True,
        verbose_name='Vendedor',
        help_text='Vendedor asociado a la venta'
    )
    registradora_id = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='Registradora',
        help_text='ID de la registradora (1, 2 o 3) desde donde se realizó la venta',
        db_index=True
    )
    
    # Campos de anulación
    anulada = models.BooleanField(
        default=False, 
        verbose_name='Anulada',
        db_index=True
    )
    fecha_anulacion = models.DateTimeField(
        null=True, 
        blank=True,
        verbose_name='Fecha de Anulación'
    )
    motivo_anulacion = models.TextField(
        null=True, 
        blank=True,
        verbose_name='Motivo de Anulación'
    )
    usuario_anulacion = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name='ventas_anuladas',
        null=True,
        blank=True,
        verbose_name='Usuario que Anuló'
    )
    
    # Campos de edición
    editada = models.BooleanField(
        default=False, 
        verbose_name='Editada',
        db_index=True
    )
    fecha_ultima_edicion = models.DateTimeField(
        null=True, 
        blank=True,
        verbose_name='Fecha de Última Edición'
    )
    motivo_edicion = models.TextField(
        null=True, 
        blank=True,
        verbose_name='Motivo de Edición'
    )
    usuario_ultima_edicion = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name='ventas_editadas',
        null=True,
        blank=True,
        verbose_name='Usuario que Editó'
    )
    monto_devolucion = models.IntegerField(
        null=True,
        blank=True,
        default=0,
        verbose_name='Monto Devolución',
        help_text='Monto devuelto al cliente cuando se editó la venta'
    )
    monto_pago_adicional = models.IntegerField(
        null=True,
        blank=True,
        default=0,
        verbose_name='Monto Pago Adicional',
        help_text='Monto adicional pagado por el cliente cuando se editó la venta'
    )

    class Meta:
        verbose_name = 'Venta'
        verbose_name_plural = 'Ventas'
        ordering = ['-fecha']
        indexes = [
            models.Index(fields=['-fecha', 'completada']),
            models.Index(fields=['caja', 'fecha']),
            models.Index(fields=['usuario', 'fecha']),
        ]

    def __str__(self):
        return f"Venta #{self.id} - {self.fecha}"


class ItemVenta(models.Model):
    """Modelo para items de venta"""
    venta = models.ForeignKey(
        Venta, 
        on_delete=models.CASCADE, 
        related_name='items',
        verbose_name='Venta'
    )
    producto = models.ForeignKey(
        Producto, 
        on_delete=models.CASCADE,
        verbose_name='Producto'
    )
    cantidad = models.IntegerField(verbose_name='Cantidad')
    precio_unitario = models.IntegerField(
        default=0,
        verbose_name='Precio Unitario'
    )
    subtotal = models.IntegerField(
        default=0,
        verbose_name='Subtotal'
    )

    class Meta:
        verbose_name = 'Item de Venta'
        verbose_name_plural = 'Items de Venta'

    def __str__(self):
        return f"{self.producto.nombre} x{self.cantidad}"


class MovimientoStock(models.Model):
    """Modelo para movimientos de stock"""
    TIPOS = [
        ('ingreso', 'Ingreso'),
        ('salida', 'Salida'),
        ('ajuste', 'Ajuste'),
    ]

    producto = models.ForeignKey(
        Producto,
        on_delete=models.CASCADE,
        related_name='movimientos',
        verbose_name='Producto'
    )
    tipo = models.CharField(
        max_length=20,
        choices=TIPOS,
        default='ingreso',
        verbose_name='Tipo'
    )
    cantidad = models.IntegerField(verbose_name='Cantidad')
    stock_anterior = models.IntegerField(verbose_name='Stock Anterior')
    stock_nuevo = models.IntegerField(verbose_name='Stock Nuevo')
    motivo = models.TextField(null=True, blank=True, verbose_name='Motivo')
    fecha = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        verbose_name='Fecha'
    )
    usuario = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Usuario'
    )

    class Meta:
        verbose_name = 'Movimiento de Stock'
        verbose_name_plural = 'Movimientos de Stock'
        ordering = ['-fecha']
        indexes = [
            models.Index(fields=['-fecha', 'producto']),
            models.Index(fields=['producto', 'tipo']),
        ]

    def __str__(self):
        return f"{self.tipo} - {self.producto.nombre} ({self.cantidad})"


class PerfilUsuario(models.Model):
    """Modelo para perfil de usuario con PIN"""
    usuario = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='perfil',
        verbose_name='Usuario'
    )
    pin = models.CharField(
        max_length=4,
        verbose_name='PIN',
        help_text='PIN de 4 dígitos para acceso rápido'
    )
    pin_establecido = models.BooleanField(
        default=False,
        verbose_name='PIN Establecido'
    )
    fecha_creacion_pin = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Fecha de Creación del PIN'
    )

    class Meta:
        verbose_name = 'Perfil de Usuario'
        verbose_name_plural = 'Perfiles de Usuario'

    def __str__(self):
        return f"Perfil de {self.usuario.username}"


class CajaGastos(models.Model):
    """Modelo para caja de gastos"""
    nombre = models.CharField(
        max_length=100,
        default='Caja de Gastos',
        verbose_name='Nombre de la Caja'
    )
    activa = models.BooleanField(default=True, verbose_name='Activa')
    fecha_creacion = models.DateTimeField(
        default=timezone.now,
        verbose_name='Fecha de Creación'
    )

    class Meta:
        verbose_name = 'Caja de Gastos'
        verbose_name_plural = 'Cajas de Gastos'
        ordering = ['-fecha_creacion']

    def __str__(self):
        return self.nombre


class RegistradoraActiva(models.Model):
    """Modelo para rastrear qué usuario tiene cada registradora activa"""
    registradora_id = models.IntegerField(
        unique=True,
        verbose_name='ID de Registradora',
        help_text='ID de la registradora (1, 2 o 3)'
    )
    usuario = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='registradoras_activas',
        verbose_name='Usuario'
    )
    fecha_apertura = models.DateTimeField(
        default=timezone.now,
        verbose_name='Fecha de Apertura'
    )

    class Meta:
        verbose_name = 'Registradora Activa'
        verbose_name_plural = 'Registradoras Activas'
        ordering = ['registradora_id']

    def __str__(self):
        return f"Registradora {self.registradora_id} - {self.usuario.username}"


class CajaGastosUsuario(models.Model):
    """Modelo para apertura y cierre de caja de gastos por usuario"""
    caja_gastos = models.ForeignKey(
        CajaGastos,
        on_delete=models.CASCADE,
        related_name='aperturas',
        verbose_name='Caja de Gastos'
    )
    usuario = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Usuario'
    )
    fecha_apertura = models.DateTimeField(
        default=timezone.now,
        verbose_name='Fecha de Apertura'
    )
    fecha_cierre = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Fecha de Cierre'
    )
    monto_inicial = models.IntegerField(
        default=0,
        verbose_name='Monto Inicial'
    )
    monto_final = models.IntegerField(
        null=True,
        blank=True,
        default=0,
        verbose_name='Monto Final'
    )

    class Meta:
        verbose_name = 'Caja Gastos Usuario'
        verbose_name_plural = 'Cajas Gastos Usuarios'
        ordering = ['-fecha_apertura']
        indexes = [
            models.Index(fields=['usuario', 'fecha_cierre']),
            models.Index(fields=['caja_gastos', 'fecha_cierre']),
        ]

    def __str__(self):
        return f"{self.caja_gastos} - {self.usuario.username}"


class GastoCaja(models.Model):
    """Modelo para gastos/ingresos de caja"""
    TIPOS = [
        ('gasto', 'Gasto'),
        ('ingreso', 'Ingreso'),
    ]

    tipo = models.CharField(
        max_length=10,
        choices=TIPOS,
        default='gasto',
        verbose_name='Tipo'
    )
    monto = models.IntegerField(
        default=0,
        verbose_name='Monto'
    )
    descripcion = models.TextField(
        verbose_name='Descripción',
        help_text='Descripción del gasto o ingreso'
    )
    fecha = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        verbose_name='Fecha'
    )
    usuario = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='gastos_registrados',
        verbose_name='Usuario'
    )
    caja_usuario = models.ForeignKey(
        CajaUsuario,
        on_delete=models.SET_NULL,
        related_name='gastos_antiguos',
        null=True,
        blank=True,
        verbose_name='Caja Usuario (Antigua)'
    )
    caja_gastos_usuario = models.ForeignKey(
        CajaGastosUsuario,
        on_delete=models.CASCADE,
        related_name='gastos',
        null=True,
        blank=True,
        verbose_name='Caja Gastos Usuario'
    )

    class Meta:
        verbose_name = 'Gasto/Ingreso de Caja'
        verbose_name_plural = 'Gastos/Ingresos de Caja'
        ordering = ['-fecha']

    def __str__(self):
        return f"{self.tipo} - ${self.monto}"


class ClientePotencial(models.Model):
    """Modelo para clientes potenciales"""
    TIPOS_INTERES = [
        ('mayorista', 'Venta Mayorista'),
        ('web', 'Venta Web'),
        ('ambos', 'Ambos'),
    ]

    ESTADOS = [
        ('nuevo', 'Nuevo'),
        ('contactado', 'Contactado'),
        ('en_proceso', 'En Proceso'),
        ('convertido', 'Convertido'),
        ('descartado', 'Descartado'),
    ]

    nombre = models.CharField(max_length=200, verbose_name='Nombre Completo')
    email = models.EmailField(verbose_name='Email')
    telefono = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name='Teléfono'
    )
    tipo_interes = models.CharField(
        max_length=20,
        choices=TIPOS_INTERES,
        default='mayorista',
        verbose_name='Tipo de Interés'
    )
    empresa = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        verbose_name='Empresa'
    )
    mensaje = models.TextField(
        null=True,
        blank=True,
        verbose_name='Mensaje o Comentarios'
    )
    estado = models.CharField(
        max_length=20,
        choices=ESTADOS,
        default='nuevo',
        db_index=True,
        verbose_name='Estado'
    )
    fecha_registro = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        verbose_name='Fecha de Registro'
    )
    fecha_contacto = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Fecha de Contacto'
    )
    notas_internas = models.TextField(
        null=True,
        blank=True,
        verbose_name='Notas Internas',
        help_text='Notas privadas para el equipo'
    )
    usuario_contacto = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name='clientes_contactados',
        null=True,
        blank=True,
        verbose_name='Usuario que Contactó'
    )

    class Meta:
        verbose_name = 'Cliente Potencial'
        verbose_name_plural = 'Clientes Potenciales'
        ordering = ['-fecha_registro']
        indexes = [
            models.Index(fields=['-fecha_registro', 'estado']),
            models.Index(fields=['tipo_interes', 'estado']),
            models.Index(fields=['email']),
        ]

    def __str__(self):
        return f"{self.nombre} - {self.email}"


class IngresoMercancia(models.Model):
    """Modelo para registro de ingreso de mercancía"""
    fecha = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        verbose_name='Fecha'
    )
    proveedor = models.CharField(
        max_length=200,
        verbose_name='Proveedor'
    )
    numero_factura = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name='Número de Factura'
    )
    total = models.IntegerField(
        default=0,
        verbose_name='Total'
    )
    observaciones = models.TextField(
        null=True,
        blank=True,
        verbose_name='Observaciones'
    )
    usuario = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='ingresos_mercancia',
        verbose_name='Usuario'
    )
    completado = models.BooleanField(
        default=False,
        verbose_name='Completado'
    )

    class Meta:
        verbose_name = 'Ingreso de Mercancía'
        verbose_name_plural = 'Ingresos de Mercancía'
        ordering = ['-fecha']

    def __str__(self):
        return f"Ingreso #{self.id} - {self.proveedor} ({self.fecha.strftime('%d/%m/%Y')})"


class ItemIngresoMercancia(models.Model):
    """Items de ingreso de mercancía"""
    ingreso = models.ForeignKey(
        IngresoMercancia,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='Ingreso'
    )
    producto = models.ForeignKey(
        Producto,
        on_delete=models.CASCADE,
        verbose_name='Producto'
    )
    cantidad = models.IntegerField(verbose_name='Cantidad')
    precio_compra = models.IntegerField(
        default=0,
        verbose_name='Precio de Compra'
    )
    subtotal = models.IntegerField(
        default=0,
        verbose_name='Subtotal'
    )
    verificado = models.BooleanField(
        default=False,
        verbose_name='Verificado'
    )
    procesado = models.BooleanField(
        default=False,
        verbose_name='Procesado'
    )

    class Meta:
        verbose_name = 'Item de Ingreso'
        verbose_name_plural = 'Items de Ingreso'

    def __str__(self):
        return f"{self.producto.nombre} x{self.cantidad}"


class SalidaMercancia(models.Model):
    """Modelo para registro de salida de mercancía"""
    TIPOS = [
        ('devolucion', 'Devolución'),
        ('merma', 'Merma'),
        ('traslado', 'Traslado'),
        ('donacion', 'Donación'),
        ('otro', 'Otro'),
    ]

    fecha = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        verbose_name='Fecha'
    )
    tipo = models.CharField(
        max_length=20,
        choices=TIPOS,
        default='merma',
        verbose_name='Tipo de Salida'
    )
    destino = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        verbose_name='Destino'
    )
    motivo = models.TextField(
        verbose_name='Motivo'
    )
    usuario = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='salidas_mercancia',
        verbose_name='Usuario'
    )
    completado = models.BooleanField(
        default=False,
        verbose_name='Completado'
    )

    class Meta:
        verbose_name = 'Salida de Mercancía'
        verbose_name_plural = 'Salidas de Mercancía'
        ordering = ['-fecha']

    def __str__(self):
        return f"Salida #{self.id} - {self.get_tipo_display()} ({self.fecha.strftime('%d/%m/%Y')})"


class ItemSalidaMercancia(models.Model):
    """Items de salida de mercancía"""
    salida = models.ForeignKey(
        SalidaMercancia,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='Salida'
    )
    producto = models.ForeignKey(
        Producto,
        on_delete=models.CASCADE,
        verbose_name='Producto'
    )
    cantidad = models.IntegerField(verbose_name='Cantidad')

    class Meta:
        verbose_name = 'Item de Salida'
        verbose_name_plural = 'Items de Salida'

    def __str__(self):
        return f"{self.producto.nombre} x{self.cantidad}"


class CampanaMarketing(models.Model):
    """Modelo para campañas de marketing"""
    ESTADOS = [
        ('planificada', 'Planificada'),
        ('activa', 'Activa'),
        ('pausada', 'Pausada'),
        ('finalizada', 'Finalizada'),
    ]

    TIPOS = [
        ('email', 'Email'),
        ('sms', 'SMS'),
        ('redes_sociales', 'Redes Sociales'),
        ('promocion', 'Promoción'),
        ('descuento', 'Descuento'),
    ]

    nombre = models.CharField(
        max_length=200,
        verbose_name='Nombre de la Campaña'
    )
    tipo = models.CharField(
        max_length=20,
        choices=TIPOS,
        verbose_name='Tipo de Campaña'
    )
    descripcion = models.TextField(
        verbose_name='Descripción'
    )
    fecha_inicio = models.DateField(
        verbose_name='Fecha de Inicio'
    )
    fecha_fin = models.DateField(
        null=True,
        blank=True,
        verbose_name='Fecha de Fin'
    )
    estado = models.CharField(
        max_length=20,
        choices=ESTADOS,
        default='planificada',
        verbose_name='Estado'
    )
    presupuesto = models.IntegerField(
        null=True,
        blank=True,
        default=0,
        verbose_name='Presupuesto'
    )
    productos = models.ManyToManyField(
        Producto,
        blank=True,
        verbose_name='Productos Relacionados'
    )
    descuento_porcentaje = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='% Descuento'
    )
    usuario_creador = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='campanas_creadas',
        verbose_name='Creado por'
    )
    fecha_creacion = models.DateTimeField(
        default=timezone.now,
        verbose_name='Fecha de Creación'
    )

    class Meta:
        verbose_name = 'Campaña de Marketing'
        verbose_name_plural = 'Campañas de Marketing'
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f"{self.nombre} - {self.get_estado_display()}"


# ============================================
# SEÑALES PARA MANTENER INTEGRIDAD DE DATOS
# ============================================

@receiver(pre_delete, sender=IngresoMercancia)
def eliminar_movimientos_ingreso(sender, instance, **kwargs):
    """Eliminar movimientos de stock asociados cuando se elimina un ingreso"""
    MovimientoStock.objects.filter(
        motivo__startswith=f'Ingreso #{instance.id}'
    ).delete()


@receiver(pre_delete, sender=SalidaMercancia)
def eliminar_movimientos_salida(sender, instance, **kwargs):
    """Eliminar movimientos de stock asociados cuando se elimina una salida"""
    MovimientoStock.objects.filter(
        motivo__startswith=f'Salida #{instance.id}'
    ).delete()

