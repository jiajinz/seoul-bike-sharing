from django.core.management.base import BaseCommand
from analytics.models import SeoulBikeHourly, SeoulBikeDailyAgg
import pandas as pd

def mode_or_empty(series):
    if series.empty:
        return ""
    # series is strings ("Spring", "No", "Yes") – get mode safely
    try:
        return series.mode().iloc[0]
    except Exception:
        return str(series.iloc[0])

class Command(BaseCommand):
    help = "Aggregate hourly → daily and compute rolling 7/30 day totals."

    def handle(self, *args, **opts):
        qs = SeoulBikeHourly.objects.all().values(
            "date", "rented_bike_count", "temperature_c", "humidity_pct",
            "windspeed_ms", "seasons", "holiday", "functioning_day"
        )
        df = pd.DataFrame(list(qs))
        if df.empty:
            self.stdout.write("No hourly data to aggregate.")
            return

        df["holiday_flag"] = df["holiday"].astype(str).str.lower().str.contains("holiday")
        df["function_yes"] = df["functioning_day"].astype(str).str.lower().str.startswith("y")

        g = df.groupby("date", as_index=False).agg(
            total_rides=("rented_bike_count", "sum"),
            avg_temp_c=("temperature_c", "mean"),
            avg_humidity_pct=("humidity_pct", "mean"),
            avg_windspeed_ms=("windspeed_ms", "mean"),
            seasons_mode=("seasons", mode_or_empty),
            holiday_any=("holiday_flag", "any"),
            functioning_all_yes=("function_yes", "all"),
        ).sort_values("date")

        # rolling windows (centered on the past 7/30 days)
        g["roll7_total"] = g["total_rides"].rolling(7, min_periods=1).mean()
        g["roll30_total"] = g["total_rides"].rolling(30, min_periods=1).mean()

        # upsert strategy: replace all
        SeoulBikeDailyAgg.objects.all().delete()
        objs = [
            SeoulBikeDailyAgg(
                date=row.date,
                total_rides=int(row.total_rides),
                avg_temp_c=float(row.avg_temp_c),
                avg_humidity_pct=float(row.avg_humidity_pct),
                avg_windspeed_ms=float(row.avg_windspeed_ms),
                roll7_total=float(row.roll7_total) if pd.notna(row.roll7_total) else None,
                roll30_total=float(row.roll30_total) if pd.notna(row.roll30_total) else None,
                seasons_mode=str(row.seasons_mode or ""),
                holiday_any=bool(row.holiday_any),
                functioning_all_yes=bool(row.functioning_all_yes),
            )
            for _, row in g.iterrows()
        ]
        SeoulBikeDailyAgg.objects.bulk_create(objs)
        self.stdout.write(self.style.SUCCESS(f"Built {len(objs)} daily aggregates."))
