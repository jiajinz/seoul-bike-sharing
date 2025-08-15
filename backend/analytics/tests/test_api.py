from django.test import TestCase
from analytics.models import SeoulBikeHourly
from datetime import date

class ApiSmokeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        SeoulBikeHourly.objects.create(
            date=date(2018,1,1), hour=0, rented_bike_count=10,
            temperature_c=1.0, humidity_pct=50, windspeed_ms=1.0,
            visibility_10m=2000, dew_point_c=-1.0, solar_radiation_mj_m2=0.0,
            rainfall_mm=0.0, snowfall_cm=0.0, seasons="Winter",
            holiday="No Holiday", functioning_day="Yes"
        )

    def test_kpis_basic(self):
        r = self.client.get("/api/v1/kpis/basic")
        self.assertEqual(r.status_code, 200)
        self.assertIn("total_rides", r.json())

    def test_hourly_list(self):
        r = self.client.get("/api/v1/hourly/")
        self.assertEqual(r.status_code, 200)

    def test_predict_hour_missing(self):
        r = self.client.post("/api/v1/predict/hour", data={}, content_type="application/json")
        self.assertEqual(r.status_code, 400)
