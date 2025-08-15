from rest_framework import viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response

from django.utils.dateparse import parse_date
from django.db.models import Avg, Sum, Min, Max
from django.db.models.functions import ExtractWeekDay
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator

import calendar
from pathlib import Path
from joblib import load

from .models import SeoulBikeHourly, SeoulBikeDailyAgg
from .serializers import SeoulBikeHourlySerializer, SeoulBikeDailyAggSerializer


# -----------------------
# Utilities
# -----------------------
def _apply_filters(request, qs):
    start = request.GET.get("start")
    end = request.GET.get("end")
    season = request.GET.get("season")
    if start:
        qs = qs.filter(date__gte=parse_date(start))
    if end:
        qs = qs.filter(date__lte=parse_date(end))
    if season:
        qs = qs.filter(seasons=season)
    return qs


_model_cache = {"model": None}
def _get_model():
    if _model_cache["model"] is None:
        base = Path(__file__).resolve().parents[2] / "models_store"
        for name in ["model_v2.joblib", "model_v1.joblib"]:
            p = base / name
            if p.exists():
                _model_cache["model"] = load(p)
                break
        if _model_cache["model"] is None:
            raise RuntimeError("No trained model found in models_store/")
    return _model_cache["model"]


# -----------------------
# ViewSets
# -----------------------
@method_decorator(cache_page(60), name="list")
class SeoulBikeHourlyViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SeoulBikeHourly.objects.all().order_by("date", "hour")
    serializer_class = SeoulBikeHourlySerializer

@method_decorator(cache_page(60), name="list")
class SeoulBikeDailyAggViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = SeoulBikeDailyAggSerializer
    def get_queryset(self):
        qs = SeoulBikeDailyAgg.objects.all().order_by("date")
        return _apply_filters(self.request, qs)


# -----------------------
# Endpoints (KPIs, meta)
# -----------------------
@api_view(["GET"])
@cache_page(60)
def meta_date_bounds(request):
    bounds = SeoulBikeHourly.objects.aggregate(start=Min("date"), end=Max("date"))
    return Response({"start": bounds["start"], "end": bounds["end"]})

@api_view(["GET"])
@cache_page(60)
def kpis_basic(request):
    qs = _apply_filters(request, SeoulBikeHourly.objects.all())
    out = {
        "rows": qs.count(),
        "total_rides": qs.aggregate(v=Sum("rented_bike_count"))["v"] or 0,
        "avg_temp_c": round(qs.aggregate(v=Avg("temperature_c"))["v"] or 0, 2),
        "avg_humidity_pct": round(qs.aggregate(v=Avg("humidity_pct"))["v"] or 0, 2),
        "avg_rides_per_hour": round(qs.aggregate(v=Avg("rented_bike_count"))["v"] or 0, 2),
    }
    return Response(out)

@api_view(["GET"])
@cache_page(60)
def kpis_hourly_heatmap(request):
    qs = _apply_filters(request, SeoulBikeHourly.objects.all())
    qs = qs.annotate(weekday=ExtractWeekDay("date"))  # 1..7 (Sun..Sat)
    rows = qs.values("weekday", "hour").annotate(avg_rides=Avg("rented_bike_count"))

    # Build 7x24 matrix (Sun..Sat x 0..23)
    matrix = [[0.0 for _ in range(24)] for _ in range(7)]
    for r in rows:
        wd = int(r["weekday"]) - 1
        hr = int(r["hour"])
        matrix[wd][hr] = round(r["avg_rides"] or 0.0, 2)

    return Response({
        "matrix": matrix,
        "weekdays": ["Sun","Mon","Tue","Wed","Thu","Fri","Sat"],
        "hours": list(range(24))
    })


# -----------------------
# Prediction Endpoints
# -----------------------
@api_view(["POST"])
def predict_hour(request):
    """
    JSON:
    {
      "date":"2018-01-15", "hour":7,
      "temperature_c":-3.0, "humidity_pct":50, "windspeed_ms":1.2, "visibility_10m":2000,
      "dew_point_c":-5.0, "solar_radiation_mj_m2":0.0, "rainfall_mm":0.0, "snowfall_cm":0.0,
      "seasons":"Winter", "holiday":"No Holiday", "functioning_day":"Yes"
    }
    """
    payload = request.data
    required = ["date","hour","temperature_c","humidity_pct","windspeed_ms","visibility_10m",
                "dew_point_c","solar_radiation_mj_m2","rainfall_mm","snowfall_cm",
                "seasons","holiday","functioning_day"]
    missing = [k for k in required if k not in payload]
    if missing:
        return Response({"error": f"Missing fields: {missing}"}, status=400)

    import pandas as pd
    weekday = pd.to_datetime(payload["date"]).weekday()
    month = pd.to_datetime(payload["date"]).month

    row = {
        "hour": int(payload["hour"]),
        "temperature_c": float(payload["temperature_c"]),
        "humidity_pct": float(payload["humidity_pct"]),
        "windspeed_ms": float(payload["windspeed_ms"]),
        "visibility_10m": float(payload["visibility_10m"]),
        "dew_point_c": float(payload["dew_point_c"]),
        "solar_radiation_mj_m2": float(payload["solar_radiation_mj_m2"]),
        "rainfall_mm": float(payload["rainfall_mm"]),
        "snowfall_cm": float(payload["snowfall_cm"]),
        "weekday": int(weekday),
        "month": int(month),
        "seasons": str(payload["seasons"]),
        "holiday": str(payload["holiday"]),
        "functioning_day": str(payload["functioning_day"]),
        # v2 model also uses cyclic & lag/rolling internally via pipeline preprocessing
        "hour_sin": 0.0, "hour_cos": 0.0, "month_sin": 0.0, "month_cos": 0.0,
        "lag_1": 0.0, "lag_24": 0.0, "roll3_same_hour": 0.0, "roll7_same_hour": 0.0,
        "delta_temperature_c_24h": 0.0, "delta_humidity_pct_24h": 0.0, "delta_windspeed_ms_24h": 0.0,
        "delta_visibility_10m_24h": 0.0, "delta_dew_point_c_24h": 0.0, "delta_solar_radiation_mj_m2_24h": 0.0,
        "delta_rainfall_mm_24h": 0.0, "delta_snowfall_cm_24h": 0.0,
        "rain_flag": 1 if float(payload["rainfall_mm"]) > 0 else 0,
        "snow_flag": 1 if float(payload["snowfall_cm"]) > 0 else 0,
    }

    import pandas as pd
    X = pd.DataFrame([row])
    model = _get_model()
    yhat = float(model.predict(X)[0])
    return Response({"predicted_rented_bike_count": round(yhat, 2)})


from django.db.models import Avg  # for seasonal hourly medians/means
def _seasonal_hourly_weather(season: str):
    agg = SeoulBikeHourly.objects.filter(seasons=season).values("hour").annotate(
        temperature_c=Avg("temperature_c"),
        humidity_pct=Avg("humidity_pct"),
        windspeed_ms=Avg("windspeed_ms"),
        visibility_10m=Avg("visibility_10m"),
        dew_point_c=Avg("dew_point_c"),
        solar_radiation_mj_m2=Avg("solar_radiation_mj_m2"),
        rainfall_mm=Avg("rainfall_mm"),
        snowfall_cm=Avg("snowfall_cm"),
    )
    return {a["hour"]: a for a in agg}

@api_view(["POST"])
def predict_day(request):
    """
    JSON: { "date":"2018-01-15", "seasons":"Winter", "holiday":"No Holiday", "functioning_day":"Yes" }
    Returns: { "date":..., "hours":[0..23], "pred":[...] }
    """
    payload = request.data
    for k in ["date","seasons","holiday","functioning_day"]:
        if k not in payload:
            return Response({"error": f"Missing field {k}"}, status=400)

    import pandas as pd
    day = pd.to_datetime(payload["date"])
    season = str(payload["seasons"])
    holiday = str(payload["holiday"])
    fday = str(payload["functioning_day"])
    weekday = int(day.weekday())
    month = int(day.month)

    weather = _seasonal_hourly_weather(season)
    if not weather:
        return Response({"error": "No weather stats for given season"}, status=400)

    rows = []
    for h in range(24):
        w = weather.get(h, {})
        rows.append({
            "hour": h,
            "temperature_c": float(w.get("temperature_c", 0.0)),
            "humidity_pct": float(w.get("humidity_pct", 0.0)),
            "windspeed_ms": float(w.get("windspeed_ms", 0.0)),
            "visibility_10m": float(w.get("visibility_10m", 0.0)),
            "dew_point_c": float(w.get("dew_point_c", 0.0)),
            "solar_radiation_mj_m2": float(w.get("solar_radiation_mj_m2", 0.0)),
            "rainfall_mm": float(w.get("rainfall_mm", 0.0)),
            "snowfall_cm": float(w.get("snowfall_cm", 0.0)),
            "weekday": weekday,
            "month": month,
            "seasons": season,
            "holiday": holiday,
            "functioning_day": fday,
            # engineered inputs default 0 for inference
            "hour_sin": 0.0, "hour_cos": 0.0, "month_sin": 0.0, "month_cos": 0.0,
            "lag_1": 0.0, "lag_24": 0.0, "roll3_same_hour": 0.0, "roll7_same_hour": 0.0,
            "delta_temperature_c_24h": 0.0, "delta_humidity_pct_24h": 0.0, "delta_windspeed_ms_24h": 0.0,
            "delta_visibility_10m_24h": 0.0, "delta_dew_point_c_24h": 0.0, "delta_solar_radiation_mj_m2_24h": 0.0,
            "delta_rainfall_mm_24h": 0.0, "delta_snowfall_cm_24h": 0.0,
            "rain_flag": 1 if float(w.get("rainfall_mm", 0.0)) > 0 else 0,
            "snow_flag": 1 if float(w.get("snowfall_cm", 0.0)) > 0 else 0,
        })

    import pandas as pd
    X = pd.DataFrame(rows)
    model = _get_model()
    yhat = model.predict(X)

    return Response({
        "date": str(day.date()),
        "hours": list(range(24)),
        "pred": [round(float(v), 2) for v in yhat]
    })
