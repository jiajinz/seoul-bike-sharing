from django.db import models

class SeoulBikeHourly(models.Model):
    # core keys
    date = models.DateField()
    hour = models.PositiveSmallIntegerField()

    # target
    rented_bike_count = models.IntegerField()

    # weather/fetures
    temperature_c = models.FloatField()
    humidity_pct = models.FloatField()
    windspeed_ms = models.FloatField()
    visibility_10m = models.FloatField()
    dew_point_c = models.FloatField()
    solar_radiation_mj_m2 = models.FloatField()
    rainfall_mm = models.FloatField()
    snowfall_cm = models.FloatField()

    # catergorical flags
    seasons = models.CharField(max_length=16) # e.g., Spring, Summer, Autumn, Winter
    holiday = models.CharField(max_length=8) # e.g., Holiday/No Holiday
    functioning_day = models.CharField(max_length=8) # e.g., Yes/No

    ingested_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("date", "hour")
        indexes = [
            models.Index(fields=["date"]),
            models.Index(fields=["hour"]),
            models.Index(fields=["seasons"]),
            models.Index(fields=["functioning_day"]),
        ]

    def __str__(self):
        return f"{self.date} {self.hour:02d}: {self.rented_bike_count}"

class SeoulBikeDailyAgg(models.Model):
    date = models.DateField(primary_key=True)

    total_rides = models.IntegerField()
    avg_temp_c = models.FloatField()
    avg_humidity_pct = models.FloatField()
    avg_windspeed_ms = models.FloatField()

    # rolling windows (computed)
    roll7_total = models.FloatField(null=True, blank=True)
    roll30_total = models.FloatField(null=True, blank=True)

    seasons_mode = models.CharField(max_length=16, default="", blank=True)
    holiday_any = models.BooleanField(default=False)          # any Holiday on that date
    functioning_all_yes = models.BooleanField(default=True)   # all hours were 'Yes'

    ingested_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["date"])]
