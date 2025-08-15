from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    SeoulBikeHourlyViewSet,
    SeoulBikeDailyAggViewSet,
    meta_date_bounds,
    kpis_basic,
    kpis_hourly_heatmap,
    predict_hour,
    predict_day,
)

router = DefaultRouter()
router.register("hourly", SeoulBikeHourlyViewSet, basename="hourly")
router.register("daily", SeoulBikeDailyAggViewSet, basename="daily")

urlpatterns = [
    path("", include(router.urls)),
    path("meta/date-bounds", meta_date_bounds),
    path("kpis/basic", kpis_basic),
    path("kpis/hourly-heatmap", kpis_hourly_heatmap),
    path("predict/hour", predict_hour),
    path("predict/day", predict_day),
]
