import pandas as pd
from django.core.management.base import BaseCommand
from analytics.models import SeoulBikeHourly
from pathlib import Path

COLUMN_MAP = {
    "Date": "date",
    "Rented Bike Count": "rented_bike_count",
    "Hour": "hour",
    "Temperature(°C)": "temperature_c",
    "Humidity(%)": "humidity_pct",
    "Wind speed (m/s)": "windspeed_ms",
    "Visibility (10m)": "visibility_10m",
    "Dew point temperature(°C)": "dew_point_c",
    "Solar Radiation (MJ/m2)": "solar_radiation_mj_m2",
    "Rainfall(mm)": "rainfall_mm",
    "Snowfall (cm)": "snowfall_cm",
    "Seasons": "seasons",
    "Holiday": "holiday",
    "Functioning Day": "functioning_day",
}

class Command(BaseCommand):
    help = "Ingest SeoulBikeData.csv into SeoulBikeHourly (typed)."

    def add_arguments(self, parser):
        parser.add_argument("--path", required=True, help="Path to SeoulBikeData.csv")
        parser.add_argument("--truncate", action="store_true", help="Delete existing rows before ingest")

    def handle(self, *args, **opts):
        csv_path = Path(opts["path"])
        if not csv_path.exists():
            raise SystemExit(f"File {csv_path} does not exist")

        if opts["truncate"]:
            SeoulBikeHourly.objects.all().delete()

        # read CSV with exact colum names preserved
        try:
            df = pd.read_csv(csv_path)
        except UnicodeDecodeError:
            df = pd.read_csv(csv_path, encoding="latin1")

        # normalize column names to the COLUMN_MAP keys
        cols = {c.strip(): c.strip() for c in df.columns}
        df.rename(columns=cols, inplace=True)

        # ensure required columns exist
        missing = [k for k in COLUMN_MAP.keys() if k not in df.columns]
        if missing:
            self.stdout.write(self.style.WARNING(f"Warning: missing columns {missing}. Trying alternate spellings where possible."))

        # rename to our model field names where possible
        rename_dict = {}
        for src, dst in COLUMN_MAP.items():
            if src in df.columns:
                rename_dict[src] = dst
        df = df.rename(columns=rename_dict)

        # parse/convert types
        try:
            df["date"] = pd.to_datetime(df["date"], format="%d/%m/%Y", errors="coerce").dt.date
        except Exception:
            df["date"] = pd.to_datetime(df["date"], dayfirst=True, errors="coerce").dt.date

        df["hour"] = pd.to_numeric(df["hour"], errors="coerce").fillna(0).astype(int)

        numeric_cols = [
            "rented_bike_count", "temperature_c", "humidity_pct", "windspeed_ms",
            "visibility_10m", "dew_point_c", "solar_radiation_mj_m2", "rainfall_mm", "snowfall_cm"
        ]
        for c in numeric_cols:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

        # fill categorical fallbacks
        for c in ["seasons", "holiday", "functioning_day"]:
            if c in df.columns:
                df[c] = df[c].astype(str)
            else:
                df[c] = "Unknown"

        # build model instances (upsert-like by unique (date,hour))
        rows = []
        for rec in df.to_dict(orient="records"):
            rows.append(SeoulBikeHourly(
                date=rec["date"],
                hour=rec["hour"],
                rented_bike_count=int(rec.get("rented_bike_count", 0)),
                temperature_c=float(rec.get("temperature_c", 0)),
                humidity_pct=float(rec.get("humidity_pct", 0)),
                windspeed_ms=float(rec.get("windspeed_ms", 0)),
                visibility_10m=int(rec.get("visibility_10m", 0)),
                dew_point_c=float(rec.get("dew_point_c", 0)),
                solar_radiation_mj_m2=float(rec.get("solar_radiation_mj_m2", 0)),
                rainfall_mm=float(rec.get("rainfall_mm", 0)),
                snowfall_cm=float(rec.get("snowfall_cm", 0)),
                seasons=rec.get("seasons", "Unknown"),
                holiday=rec.get("holiday", "Unknown"),
                functioning_day=rec.get("functioning_day", "Unknown"),
            ))
        # simple strategy: wipe duplicates if they violate unique constraint, so use bulk_create(ignore_conflicts=True)
        SeoulBikeHourly.objects.bulk_create(rows, ignore_conflicts=True)
        self.stdout.write(self.style.SUCCESS(f"Ingested {len(rows)} rows from {csv_path.name}."))