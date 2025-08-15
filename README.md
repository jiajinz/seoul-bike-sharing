# 🚲 Seoul Bike Sharing Demand Forecast & Analytics Dashboard

A full-stack Django + DRF + Pandas project for visualizing, analyzing, and predicting Seoul Bike Sharing demand.  
Includes interactive charts, KPIs, filtering, and machine learning predictions (hourly & daily).

---

## 📌 Features
- **Data ingestion** from CSV into SQLite via Django management commands
- **REST API** with Django REST Framework:
  - Hourly & daily aggregated data
  - KPIs and hourly heatmap
  - Prediction endpoints (hour-level and 24-hour day forecast)
- **Interactive dashboard** (Chart.js) with:
  - KPI cards
  - Daily trend chart (7-day rolling average)
  - Hourly heatmap
  - Forecast form with live chart
- **ML Model** (RandomForestRegressor) trained with seasonal & lag features
- **Caching** for faster KPI & chart responses
- **Test coverage** for API endpoints
- **CI-ready** with GitHub Actions
