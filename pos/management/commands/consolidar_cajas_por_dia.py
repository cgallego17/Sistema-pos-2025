# -*- coding: utf-8 -*-
"""
Consolida cajas duplicadas por dia (zona horaria local), reasignando GastoCaja
de cajas "reconstruidas" (monto_inicial=0 y monto_final=0) a una sola CajaUsuario.

Seguro por defecto: DRY RUN (no aplica cambios) a menos que se use --apply.
"""
from datetime import date, datetime, time, timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from pos.models import Caja, CajaUsuario, GastoCaja


def _parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


class Command(BaseCommand):
    help = "Consolida cajas duplicadas por dia, reasignando gastos/ingresos y eliminando duplicados vacios."

    def add_arguments(self, parser):
        parser.add_argument("--username", required=True, help="Username a consolidar (ej: carmenza.moncada)")
        parser.add_argument("--desde", required=True, help="Fecha desde (YYYY-MM-DD)")
        parser.add_argument("--hasta", required=True, help="Fecha hasta (YYYY-MM-DD)")
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Aplica cambios (si no se usa, solo muestra lo que haria).",
        )

    def handle(self, *args, **options):
        username = options["username"]
        desde = _parse_date(options["desde"])
        hasta = _parse_date(options["hasta"])
        apply_changes = bool(options["apply"])

        if hasta < desde:
            desde, hasta = hasta, desde

        user = User.objects.filter(username=username).first()
        if not user:
            self.stdout.write(self.style.ERROR(f"[ERROR] No existe el usuario: {username}"))
            return

        caja_principal = Caja.objects.filter(numero=1).first()
        if not caja_principal:
            self.stdout.write(self.style.ERROR("[ERROR] No existe Caja Principal (numero=1)"))
            return

        tz = timezone.get_current_timezone()
        self.stdout.write(self.style.SUCCESS("Consolidacion de cajas por dia"))
        self.stdout.write(f"Usuario: {username}")
        self.stdout.write(f"Rango: {desde.isoformat()} a {hasta.isoformat()} ({tz})")
        self.stdout.write(f"Modo: {'APLICAR' if apply_changes else 'DRY RUN'}")
        self.stdout.write("")

        total_reasignados = 0
        total_cajas_eliminadas = 0
        total_cajas_normalizadas = 0

        d = desde
        while d <= hasta:
            inicio_dt = timezone.make_aware(datetime.combine(d, time.min), tz)
            fin_dt = timezone.make_aware(datetime.combine(d, time.max), tz)

            # Cajas candidatas SOLO si son "reconstruidas" (0/0), para no tocar sesiones reales.
            cajas_dia = list(
                CajaUsuario.objects.filter(
                    caja=caja_principal,
                    usuario=user,
                    fecha_apertura__lte=fin_dt,
                )
                .filter(Q(fecha_cierre__gte=inicio_dt) | Q(fecha_cierre__isnull=True))
                .filter(monto_inicial=0, monto_final=0)
                .order_by("id")
            )

            # Gastos/ingresos del dia para ese usuario, cuya caja_usuario sea NULL o "reconstruida"
            gastos_dia = GastoCaja.objects.filter(
                usuario=user,
                fecha__gte=inicio_dt,
                fecha__lte=fin_dt,
            ).filter(
                Q(caja_usuario__isnull=True)
                | Q(caja_usuario__monto_inicial=0, caja_usuario__monto_final=0)
            )

            if not cajas_dia and not gastos_dia.exists():
                d += timedelta(days=1)
                continue

            self.stdout.write(self.style.WARNING(f"--- Dia {d.isoformat()} ---"))
            self.stdout.write(f"Cajas candidatas (0/0) solapadas: {[c.id for c in cajas_dia]}")
            self.stdout.write(f"Gastos/ingresos del dia (reconstruidos o sin caja): {gastos_dia.count()}")

            # Elegir/crear caja canonica del dia
            canon = None
            for cu in cajas_dia:
                if cu.fecha_apertura == inicio_dt and cu.fecha_cierre == fin_dt:
                    canon = cu
                    break
            if canon is None and cajas_dia:
                canon = cajas_dia[0]

            if canon is None:
                # No hay caja del dia, pero hay gastos sueltos/reconstruidos: crear una.
                if apply_changes:
                    canon = CajaUsuario.objects.create(
                        caja=caja_principal,
                        usuario=user,
                        fecha_apertura=inicio_dt,
                        fecha_cierre=fin_dt,
                        monto_inicial=0,
                        monto_final=0,
                    )
                else:
                    self.stdout.write("Se crearia una caja canonica 00:00-23:59 para este dia.")
                    # No podemos reasignar sin ID real en dry run; seguimos.
                    d += timedelta(days=1)
                    continue

            # Normalizar periodo a dia completo (solo si es reconstruida)
            if canon.fecha_apertura != inicio_dt or canon.fecha_cierre != fin_dt:
                self.stdout.write(
                    f"Normalizar caja canonica ID={canon.id}: {canon.fecha_apertura}..{canon.fecha_cierre} -> {inicio_dt}..{fin_dt}"
                )
                if apply_changes:
                    canon.fecha_apertura = inicio_dt
                    canon.fecha_cierre = fin_dt
                    canon.save(update_fields=["fecha_apertura", "fecha_cierre"])
                    total_cajas_normalizadas += 1

            # Reasignar gastos/ingresos del dia a canonica
            if apply_changes:
                updated = gastos_dia.update(caja_usuario=canon)
                total_reasignados += int(updated)
                self.stdout.write(f"Reasignados a caja ID={canon.id}: {updated}")
            else:
                self.stdout.write(f"Se reasignarian {gastos_dia.count()} movimientos a caja ID={canon.id}.")

            # Eliminar duplicados vacios (0/0 y sin movimientos)
            if cajas_dia:
                for cu in cajas_dia:
                    if cu.id == canon.id:
                        continue
                    if apply_changes:
                        if not GastoCaja.objects.filter(caja_usuario=cu).exists():
                            cu_id = cu.id
                            cu.delete()
                            total_cajas_eliminadas += 1
                            self.stdout.write(f"Eliminada caja duplicada vacia ID={cu_id}")
                    else:
                        self.stdout.write(f"Se intentaria eliminar caja duplicada ID={cu.id} si queda sin movimientos.")

            self.stdout.write("")
            d += timedelta(days=1)

        self.stdout.write(self.style.SUCCESS("=== Resumen ==="))
        self.stdout.write(f"Movimientos reasignados: {total_reasignados}")
        self.stdout.write(f"Cajas normalizadas a dia completo: {total_cajas_normalizadas}")
        self.stdout.write(f"Cajas duplicadas eliminadas: {total_cajas_eliminadas}")

