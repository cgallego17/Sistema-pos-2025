"""
Reasigna cajas por día con periodos completos y cierra cajas antiguas.
Objetivo: crear/ajustar CajaUsuario para cada día problemático, cubrir 00:00-23:59:59,
asignar gastos de ese día a la caja correspondiente y dejar solo la caja de hoy abierta.

Uso:
    python manage.py reasignar_cajas_por_dia
"""
from datetime import datetime, time
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from pos.models import Caja, CajaUsuario, GastoCaja


class Command(BaseCommand):
    help = "Reasigna cajas por día y cierra cajas antiguas, dejando solo la de hoy abierta"

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

        # Días a corregir (detectados: 2025-12-13 y 2025-12-14)
        target_dates = [
            datetime(2025, 12, 13, tzinfo=tz).date(),
            datetime(2025, 12, 14, tzinfo=tz).date(),
        ]

        created_or_updated = []

        for d in target_dates:
            apertura_dt = datetime.combine(d, time.min).replace(tzinfo=tz)
            cierre_dt = datetime.combine(d, time.max).replace(tzinfo=tz)

            # Buscar si ya existe una caja para ese día
            cu = (
                CajaUsuario.objects.filter(
                    caja=caja_principal, fecha_apertura__date=d
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

            created_or_updated.append((cu.id, d, action))

            # Asignar gastos de ese día a esta caja
            gastos = GastoCaja.objects.filter(fecha__date=d)
            for g in gastos:
                if g.caja_usuario_id != cu.id:
                    g.caja_usuario = cu
                    g.save(update_fields=["caja_usuario"])

        for cu_id, d, action in created_or_updated:
            self.stdout.write(
                self.style.SUCCESS(f"{action} CajaUsuario {cu_id} para {d}")
            )

        # Cerrar cajas antiguas y dejar solo la caja más reciente de hoy abierta (si existe)
        now = timezone.now()
        today = now.date()
        abiertas = list(
            CajaUsuario.objects.filter(fecha_cierre__isnull=True).order_by(
                "-fecha_apertura"
            )
        )
        keep_id = None
        for c in abiertas:
            if c.fecha_apertura.date() == today:
                keep_id = c.id
                break

        cerradas = []
        for c in abiertas:
            if keep_id and c.id == keep_id:
                continue
            cierre_dt = c.fecha_apertura.replace(
                hour=23, minute=59, second=59, microsecond=0
            )
            c.fecha_cierre = cierre_dt
            c.save(update_fields=["fecha_cierre"])
            cerradas.append(c.id)

        self.stdout.write(
            f"Cajas cerradas: {cerradas}" if cerradas else "No se cerraron cajas adicionales"
        )
        if keep_id:
            self.stdout.write(self.style.SUCCESS(f"Caja abierta mantenida: {keep_id}"))
        else:
            self.stdout.write(self.style.WARNING("No hay caja abierta para el día de hoy"))

        self.stdout.write(self.style.SUCCESS("Proceso completado"))






