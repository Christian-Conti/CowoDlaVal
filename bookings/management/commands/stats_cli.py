from __future__ import annotations

import json
from datetime import date

from django.core.management.base import BaseCommand, CommandError

from bookings.analytics import get_booking_statistics


SPARK = "▁▂▃▄▅▆▇█"


def sparkline(values):
    values = list(values)
    if not values:
        return ""
    maximum = max(values)
    if maximum <= 0:
        return SPARK[0] * len(values)
    return "".join(SPARK[round((value / maximum) * (len(SPARK) - 1))] for value in values)


def bar(value, maximum, width=24):
    if maximum <= 0:
        return ""
    filled = round((value / maximum) * width)
    return "█" * filled + "·" * (width - filled)


class Command(BaseCommand):
    help = "Mostra statistiche e andamento delle prenotazioni."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=30, help="Periodo in giorni (default 30).")
        parser.add_argument("--all", action="store_true", dest="all_time", help="Tutto lo storico.")
        parser.add_argument("--start", help="Data iniziale YYYY-MM-DD.")
        parser.add_argument("--end", help="Data finale YYYY-MM-DD.")
        parser.add_argument("--json", action="store_true", help="Output JSON.")
        parser.add_argument("--trend", action="store_true", help="Stampa anche il dettaglio giornaliero.")

    @staticmethod
    def _parse_date(value):
        if not value:
            return None
        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            raise CommandError(f"Data non valida: {value}. Usa YYYY-MM-DD.") from exc

    def handle(self, *args, **options):
        start = self._parse_date(options.get("start"))
        end = self._parse_date(options.get("end"))
        if start and end and start > end:
            raise CommandError("--start non può essere successivo a --end.")

        stats = get_booking_statistics(
            days=options["days"],
            start=start,
            end=end,
            all_time=options["all_time"],
        )

        if options["json"]:
            self.stdout.write(json.dumps(stats, ensure_ascii=False, indent=2))
            return

        period = stats["period"]
        k = stats["kpi"]
        occupancy = "n/d" if k["occupancy"] is None else f"{k['occupancy']:.1f}%"

        self.stdout.write("")
        self.stdout.write("━" * 72)
        self.stdout.write("  COWO D'LA VAL · STATISTICHE PRENOTAZIONI")
        self.stdout.write("━" * 72)
        self.stdout.write(f"  Periodo  {period['start']} → {period['end']}  ·  {period['days']} giorni")
        self.stdout.write("")

        left = [
            ("Prenotazioni", k["total"]),
            ("Attive", k["active"]),
            ("Confermate", k["confirmed"]),
            ("Cancellate", k["cancelled"]),
            ("Tasso cancellazione", f"{k['cancellation_rate']:.1f}%"),
            ("Utenti unici", k["unique_users"]),
            ("Utenti ricorrenti", k["repeat_users"]),
            ("Tasso ritorno", f"{k['repeat_rate']:.1f}%"),
            ("Occupazione", occupancy),
            ("Desk-days occupati", k["occupied_desk_days"]),
            ("Incassato", f"€ {k['paid_revenue']:.2f}"),
            ("Valore prenotazioni attive", f"€ {k['expected_revenue']:.2f}"),
            ("Importo medio", f"€ {k['average_amount']:.2f}"),
            ("Tasso pagamento", f"{k['payment_rate']:.1f}%"),
            ("Giorno di picco", f"{k['peak_date']} ({k['peak_bookings']})"),
        ]
        for label, value in left:
            self.stdout.write(f"  {label:<31} {value}")

        trend_values = [item["bookings"] for item in stats["trend"]]
        if len(trend_values) > 80:
            step = max(len(trend_values) // 80, 1)
            trend_values = [sum(trend_values[i:i + step]) for i in range(0, len(trend_values), step)]
        self.stdout.write("")
        self.stdout.write("  ANDAMENTO PRENOTAZIONI")
        self.stdout.write(f"  {sparkline(trend_values)}")

        self.stdout.write("")
        self.stdout.write("  GIORNI DELLA SETTIMANA")
        max_weekday = max((item["count"] for item in stats["weekdays"]), default=0)
        for item in stats["weekdays"]:
            self.stdout.write(
                f"    {item['label']:<4} {bar(item['count'], max_weekday, 22)} {item['count']:>4}"
            )

        self.stdout.write("")
        self.stdout.write("  POSTAZIONI PIÙ UTILIZZATE")
        if stats["top_spaces"]:
            maximum = max(item["days"] for item in stats["top_spaces"][:8])
            for item in stats["top_spaces"][:8]:
                name = item["space"][:22]
                self.stdout.write(
                    f"    {name:<22} {bar(item['days'], maximum, 18)} "
                    f"{item['days']:>3} gg · {item['bookings']:>3} booking"
                )
        else:
            self.stdout.write("    Nessun dato.")

        self.stdout.write("")
        self.stdout.write("  STATI")
        if stats["statuses"]:
            maximum = max(item["count"] for item in stats["statuses"])
            for item in stats["statuses"]:
                self.stdout.write(
                    f"    {item['label'][:22]:<22} {bar(item['count'], maximum, 18)} {item['count']:>4}"
                )
        else:
            self.stdout.write("    Nessun dato.")

        if options["trend"]:
            self.stdout.write("")
            self.stdout.write("  DETTAGLIO GIORNALIERO")
            self.stdout.write(f"    {'Data':<12} {'Booking':>8} {'Desk occupati':>14}")
            for item in stats["trend"]:
                self.stdout.write(
                    f"    {item['date']:<12} {item['bookings']:>8} {item['occupied_desks']:>14}"
                )

        self.stdout.write("━" * 72)
