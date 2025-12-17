"""
Cierra todas las cajas abiertas excepto la más reciente del día actual.
Uso: python manage.py cerrar_cajas_abiertas
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from pos.models import CajaUsuario


class Command(BaseCommand):
    help = "Cierra todas las cajas abiertas excepto la más reciente del día actual"

    def handle(self, *args, **options):
        now = timezone.now()
        today = now.date()

        abiertas = list(
            CajaUsuario.objects.filter(fecha_cierre__isnull=True).order_by(
                "-fecha_apertura"
            )
        )
        if not abiertas:
            self.stdout.write(self.style.SUCCESS("No hay cajas abiertas"))
            return

        # Mantener abierta la más reciente del día de hoy (si existe)
        keep_id = None
        for c in abiertas:
            if c.fecha_apertura.date() == today:
                keep_id = c.id
                break

        self.stdout.write(f"Cajas abiertas antes: {[c.id for c in abiertas]}")
        if keep_id:
            self.stdout.write(f"Se mantiene abierta la caja {keep_id} (día de hoy)")
        else:
            self.stdout.write("No hay cajas del día de hoy; se cerrarán todas.")

        cerradas = []
        for c in abiertas:
            if keep_id and c.id == keep_id:
                continue
            # Cerrar al final del día de apertura para acotar el periodo
            cierre_dt = c.fecha_apertura.replace(
                hour=23, minute=59, second=59, microsecond=0
            )
            c.fecha_cierre = cierre_dt
            c.save(update_fields=["fecha_cierre"])
            cerradas.append(c.id)

        self.stdout.write(f"Cajas cerradas: {cerradas}" if cerradas else "Nada que cerrar")
        self.stdout.write(self.style.SUCCESS("Proceso completado"))






