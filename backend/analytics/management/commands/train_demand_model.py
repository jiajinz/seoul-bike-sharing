import numpy as np
import pandas as pd
from django.core.management.base import BaseCommand
from backend.analytics.models import SeoulBikeHourly
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import cross_val_score, KFold
from sklearn.metrics import mean_absolute_error, mean_squared_error
import joblib
import os

class Command(BaseCommand):
    help = "Train a bike demand prediction model"

    def handle(self, *args, **options):
        self.stdout.write("→ Loading hourly data from DB…")
        data = list(SeoulBikeHourly.objects.all().values())
        df = pd.DataFrame(data)
        self.stdout.write(f"  rows fetched: {len(df)}")

        # Sort by date & hour
        self.stdout.write("→ Sorting and adding time features…")
        df = df.sort_values(["date", "hour"])

        # Feature engineering
        df["hour_sin"] = np.sin(2 * np.pi * df["hour"] / 24)
        df["hour_cos"] = np.cos(2 * np.pi * df["hour"] / 24)
        df["is_holiday"] = df["holiday"].apply(lambda x: 1 if x.lower() != "no holiday" else 0)
        df["season"] = df["seasons"].map({"Winter": 0, "Spring": 1, "Summer": 2, "Autumn": 3})

        features = ["hour_sin", "hour_cos", "temperature", "humidity", "windspeed", "visibility", "dew_point", "solar_radiation", "rainfall", "snowfall", "season", "is_holiday"]
        target = "rented_bike_count"

        X = df[features]
        y = df[target]

        self.stdout.write("→ Training RandomForestRegressor (v2)…")
        model = RandomForestRegressor(n_estimators=200, random_state=42)

        # Cross-validation
        kf = KFold(n_splits=5, shuffle=True, random_state=42)
        mae_scores = -cross_val_score(model, X, y, cv=kf, scoring="neg_mean_absolute_error")
        rmse_scores = np.sqrt(-cross_val_score(model, X, y, cv=kf, scoring="neg_mean_squared_error"))

        model.fit(X, y)

        # Save the model
        os.makedirs("models_store", exist_ok=True)
        model_path = "models_store/model_v2.joblib"
        joblib.dump(model, model_path)

        self.stdout.write(
            f"[RandomForest] v2 trained. MAE={mae_scores.mean():.2f}±{mae_scores.std():.2f}, "
            f"RMSE={rmse_scores.mean():.2f}±{rmse_scores.std():.2f}. "
            f"Saved to {os.path.abspath(model_path)}"
        )
