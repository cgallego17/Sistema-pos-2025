# -*- coding: utf-8 -*-
"""
Ajusta cierres de caja que quedaron en la madrugada del dia siguiente (hora local),
moviendo SOLO la fecha_cierre al dia anterior para efectos de organizacion/cuadre.

Por defecto hace DRY RUN. Para aplicar: --apply

Criterio por defecto:
- fecha_cierre existe
- fecha_cierre (local) cae antes de --cutoff (por defecto 05:00)
- fecha_cierre (local).date() == fecha_apertura (local).date() + 1 dia
- y el nuevo cierre no puede quedar antes de fecha_apertura

Se ajusta a: (dia_anterior a fecha_cierre local) + --hora_destino (por defecto 23:59:59)
"""
from datetime import datetime, time, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from pos.models import CajaUsuario


def _parse_hhmm(value: str, default_h: int, default_m: int):
    try:
        parts = value.strip().split(":")
        h = int(parts[0])
        m = int(parts[1]) if len(parts) > 1 else 0
        return max(0, min(23, h)), max(0, min(59, m))
    except Exception:
        return default_h, default_m


class Command(BaseCommand):
    help = "Ajusta fecha_cierre de cajas cerradas en madrugada del dia siguiente (DRY RUN por defecto)."

    def add_arguments(self, parser):
        parser.add_argument("--cutoff", default="05:00", help="Hora limite (HH:MM). Ej: 05:00")
        parser.add_argument(
            "--hora-destino",
            default="23:59",
            help="Hora destino en el dia anterior (HH:MM). Se usa 23:59:59 como segundos.",
        )
        parser.add_argument("--desde", help="Fecha desde (YYYY-MM-DD) para filtrar por cierre (local)")
        parser.add_argument("--hasta", help="Fecha hasta (YYYY-MM-DD) para filtrar por cierre (local)")
        parser.add_argument("--usuario", help="Username para filtrar (opcional)")
        parser.add_argument("--apply", action="store_true", help="Aplica los cambios")

    def handle(self, *args, **options):
        tz = timezone.get_current_timezone()
        cutoff_h, cutoff_m = _parse_hhmm(options["cutoff"], 5, 0)
        destino_h, destino_m = _parse_hhmm(options["hora_destino"], 23, 59)
        cutoff_t = time(cutoff_h, cutoff_m)

        apply_changes = bool(options["apply"])
        username = options.get("usuario")

        # Filtrado por rango de cierre local: convertimos a UTC aproximando límites locales.
        desde = options.get("desde")
        hasta = options.get("hasta")
        cierre_ini = None
        cierre_fin = None
        if desde:
            d = datetime.strptime(desde, "%Y-%m-%d").date()
            cierre_ini = timezone.make_aware(datetime.combine(d, time.min), tz)
        if hasta:
            d = datetime.strptime(hasta, "%Y-%m-%d").date()
            cierre_fin = timezone.make_aware(datetime.combine(d, time.max), tz)

        qs = CajaUsuario.objects.filter(fecha_cierre__isnull=False).select_related("usuario", "caja").order_by("fecha_cierre")
        if username:
            qs = qs.filter(usuario__username=username)
        if cierre_ini:
            qs = qs.filter(fecha_cierre__gte=cierre_ini)
        if cierre_fin:
            qs = qs.filter(fecha_cierre__lte=cierre_fin)

        self.stdout.write(self.style.SUCCESS("Ajuste de cierres en madrugada"))
        self.stdout.write(f"TZ: {tz}")
        self.stdout.write(f"Cutoff (madrugada): {cutoff_h:02d}:{cutoff_m:02d}")
        self.stdout.write(f"Hora destino (dia anterior): {destino_h:02d}:{destino_m:02d}:59")
        self.stdout.write(f"Modo: {'APLICAR' if apply_changes else 'DRY RUN'}")
        if username:
            self.stdout.write(f"Usuario: {username}")
        if desde or hasta:
            self.stdout.write(f"Filtro cierre local: {desde or '-'} .. {hasta or '-'}")
        self.stdout.write("")

        candidatos = []
        for cu in qs:
            if not cu.fecha_cierre:
                continue
            apertura_local = timezone.localtime(cu.fecha_apertura, tz)
            cierre_local = timezone.localtime(cu.fecha_cierre, tz)

            # Solo si cerró al día siguiente de la apertura (por calendario local)
            if cierre_local.date() != (apertura_local.date() + timedelta(days=1)):
                continue
            # Solo si cerró antes del cutoff
            if cierre_local.time() >= cutoff_t:
                continue

            nuevo_cierre_local = datetime.combine(
                cierre_local.date() - timedelta(days=1),
                time(destino_h, destino_m, 59),
            )
            nuevo_cierre = timezone.make_aware(nuevo_cierre_local, tz)

            # No permitir que el cierre quede antes de la apertura real
            if nuevo_cierre < cu.fecha_apertura:
                continue

            candidatos.append((cu, apertura_local, cierre_local, nuevo_cierre_local))

        if not candidatos:
            self.stdout.write(self.style.WARNING("No se encontraron cajas candidatas."))
            return

        self.stdout.write(self.style.WARNING(f"Candidatas: {len(candidatos)}"))
        self.stdout.write("ID | Caja | Usuario | Apertura(local) | Cierre(local) | Nuevo cierre(local)")
        for cu, ap_l, ci_l, nuevo_l in candidatos:
            self.stdout.write(
                f"{cu.id} | {cu.caja.numero if cu.caja else '-'} | {cu.usuario.username if cu.usuario else '-'} | "
                f"{ap_l.strftime('%Y-%m-%d %H:%M:%S')} | {ci_l.strftime('%Y-%m-%d %H:%M:%S')} | {nuevo_l.strftime('%Y-%m-%d %H:%M:%S')}"
            )

        if not apply_changes:
            self.stdout.write("")
            self.stdout.write(self.style.SUCCESS("DRY RUN: no se aplicaron cambios."))
            self.stdout.write("Para aplicar: python manage.py ajustar_cierres_madrugada --apply [opciones]")
            return

        actualizados = 0
        for cu, _ap_l, _ci_l, nuevo_l in candidatos:
            cu.fecha_cierre = timezone.make_aware(nuevo_l, tz)
            cu.save(update_fields=["fecha_cierre"])
            actualizados += 1

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"[OK] Cajas actualizadas: {actualizados}"))


