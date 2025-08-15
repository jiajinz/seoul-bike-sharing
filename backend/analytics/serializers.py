from rest_framework import serializers
from .models import SeoulBikeHourly, SeoulBikeDailyAgg

class SeoulBikeHourlySerializer(serializers.ModelSerializer):
    class Meta:
        model = SeoulBikeHourly
        fields = [
            "date","hour","rented_bike_count","temperature_c","humidity_pct",
            "windspeed_ms","visibility_10m","dew_point_c","solar_radiation_mj_m2",
            "rainfall_mm","snowfall_cm","seasons","holiday","functioning_day"
        ]

class SeoulBikeDailyAggSerializer(serializers.ModelSerializer):
    class Meta:
        model = SeoulBikeDailyAgg
        fields = [
            "date","total_rides","avg_temp_c","avg_humidity_pct","avg_windspeed_ms",
            "roll7_total","roll30_total","seasons_mode","holiday_any","functioning_all_yes"
        ]
