"""
Reasigna ventas inconsistentes (sin CajaUsuario válida) a la caja del día correspondiente.
Uso: python manage.py reasignar_ventas_inconsistentes
"""
from collections import Counter
from datetime import datetime, time, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from pos.models import Caja, CajaUsuario, Venta


class Command(BaseCommand):
    help = "Reasigna ventas inconsistentes a cajas por día"

    def handle(self, *args, **options):
        User = get_user_model()
        tz = timezone.get_current_timezone()

        caja_principal = Caja.objects.filter(numero=1).first()
        if not caja_principal:
            self.stdout.write(self.style.ERROR("No se encontró Caja Principal (numero=1)"))
            return

        superuser = User.objects.filter(is_superuser=True).first() or User.objects.first()
        if not superuser:
            self.stdout.write(self.style.ERROR("No se encontró usuario para asignar a las cajas"))
            return

        bad = []
        for v in Venta.objects.filter(completada=True):
            cu = (
                CajaUsuario.objects.filter(
                    caja=caja_principal, fecha_apertura__lte=v.fecha
                )
                .order_by("-fecha_apertura")
                .first()
            )
            if not cu or (cu.fecha_cierre and v.fecha > cu.fecha_cierre):
                bad.append(v)

        if not bad:
            self.stdout.write(self.style.SUCCESS("No hay ventas inconsistentes"))
            return

        cnt = Counter([v.fecha.date() for v in bad])
        self.stdout.write(f"Ventas inconsistentes: {len(bad)}")
        for fecha, num in cnt.most_common():
            self.stdout.write(f"  {fecha}: {num} ventas")

        # Crear o ajustar cajas por cada fecha con inconsistencias
        cajas_creadas = []
        for fecha in cnt:
            # Ampliar rango para cubrir desfases horarios
            apertura_dt = datetime.combine(fecha, time.min).replace(tzinfo=tz) - timedelta(hours=12)
            cierre_dt = datetime.combine(fecha, time.max).replace(tzinfo=tz) + timedelta(hours=12)

            cu = (
                CajaUsuario.objects.filter(
                    caja=caja_principal, fecha_apertura__date=fecha
                ).order_by("fecha_apertura")
            ).first()
            if cu:
                cu.fecha_apertura = apertura_dt
                cu.fecha_cierre = cierre_dt
                if not cu.usuario:
                    cu.usuario = superuser
                cu.save(update_fields=["fecha_apertura", "fecha_cierre", "usuario"])
                action = "Actualizada"
            else:
                cu = CajaUsuario.objects.create(
                    caja=caja_principal,
                    usuario=superuser,
                    fecha_apertura=apertura_dt,
                    fecha_cierre=cierre_dt,
                    monto_inicial=0,
                )
                action = "Creada"
            cajas_creadas.append((cu.id, fecha, action))

        for cu_id, fecha, action in cajas_creadas:
            self.stdout.write(self.style.SUCCESS(f"{action} CajaUsuario {cu_id} para {fecha}"))

        self.stdout.write(self.style.SUCCESS("Proceso completado"))

