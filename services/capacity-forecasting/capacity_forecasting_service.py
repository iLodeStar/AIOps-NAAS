#!/usr/bin/env python3
"""
AIOps NAAS v0.4 - Capacity Forecasting Service

This service provides capacity prediction for seasonal cruise traffic:
- Historical data analysis for booking patterns
- Time-series forecasting models for occupancy prediction
- Seasonal trend analysis across different routes
- Revenue and capacity optimization recommendations
- Integration with fleet aggregation data

The service:
1. Analyzes historical capacity and booking data from ClickHouse
2. Builds time-series forecasting models for each route/ship
3. Predicts seasonal capacity needs and booking trends
4. Provides actionable recommendations for capacity planning
5. Publishes forecasting alerts to NATS for capacity thresholds
"""

import asyncio
import logging
import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, asdict
import random
import math

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware  
from pydantic import BaseModel, Field
import uvicorn
import nats
from clickhouse_driver import Client as ClickHouseClient
import requests
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures
from sklearn.metrics import mean_absolute_error, mean_squared_error
from statsmodels.tsa.seasonal import seasonal_decompose
from statsmodels.tsa.holtwinters import ExponentialSmoothing

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Seasonal patterns for different cruise routes
SEASONAL_PATTERNS = {
    "Caribbean": {"peak_months": [12, 1, 2, 3], "low_months": [8, 9], "peak_multiplier": 1.4},
    "Alaska": {"peak_months": [6, 7, 8], "low_months": [11, 12, 1, 2], "peak_multiplier": 1.6},
    "Mediterranean": {"peak_months": [6, 7, 8, 9], "low_months": [12, 1, 2], "peak_multiplier": 1.3},
    "Northern Europe": {"peak_months": [6, 7, 8], "low_months": [11, 12, 1, 2], "peak_multiplier": 1.5},
    "South Pacific": {"peak_months": [11, 12, 1, 2], "low_months": [6, 7, 8], "peak_multiplier": 1.2}
}

# Pydantic models
class CapacityForecast(BaseModel):
    ship_id: str
    route: str
    forecast_date: datetime
    predicted_occupancy: int
    predicted_occupancy_rate: float
    confidence_lower: float
    confidence_upper: float
    seasonal_factor: float
    trend_direction: str  # "increasing", "decreasing", "stable"
    
class RouteForecast(BaseModel):
    route: str
    forecast_period: str  # "next_30_days", "next_quarter", "next_year"
    total_capacity: int
    predicted_demand: int
    utilization_rate: float
    revenue_projection: float
    recommendations: List[str]
    
class CapacityAlert(BaseModel):
    alert_id: str
    ship_id: str
    route: str
    alert_type: str  # "overbooking_risk", "underutilization", "seasonal_peak"
    severity: str
    threshold_value: float
    predicted_value: float
    alert_date: datetime
    recommended_actions: List[str]

class HistoricalDataPoint(BaseModel):
    date: datetime
    ship_id: str
    route: str
    capacity: int
    occupancy: int
    booking_rate: float
    revenue_per_passenger: float

@dataclass
class ForecastingMetrics:
    model_type: str
    mae: float  # Mean Absolute Error
    mse: float  # Mean Squared Error
    rmse: float  # Root Mean Squared Error
    mape: float  # Mean Absolute Percentage Error
    accuracy: float
    last_trained: datetime

class CapacityForecastingService:
    """Main capacity forecasting service"""
    
    def __init__(self):
        self.app = FastAPI(title="Capacity Forecasting Service", version="0.4.0")
        self.setup_middleware()
        self.setup_routes()
        
        # Service dependencies  
        self.clickhouse_client: Optional[ClickHouseClient] = None
        self.nats_client: Optional[nats.NATS] = None
        
        # Forecasting models and cache
        self.route_models: Dict[str, Any] = {}
        self.ship_models: Dict[str, Any] = {}
        self.model_metrics: Dict[str, ForecastingMetrics] = {}
        self.last_training: Optional[datetime] = None
        
        # Historical data cache  
        self.historical_data: Optional[pd.DataFrame] = None
        self.last_data_refresh: Optional[datetime] = None
        
    def setup_middleware(self):
        """Setup FastAPI middleware"""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    def setup_routes(self):
        """Setup API routes"""
        
        @self.app.get("/health")
        async def health_check():
            return {
                "status": "healthy",
                "service": "capacity-forecasting", 
                "version": "0.4.0",
                "timestamp": datetime.now(timezone.utc),
                "models_trained": len(self.route_models) + len(self.ship_models),
                "last_training": self.last_training,
                "dependencies": {
                    "clickhouse": self.clickhouse_client is not None,
                    "nats": self.nats_client is not None and self.nats_client.is_connected
                }
            }
        
        @self.app.get("/forecast/ships", response_model=List[CapacityForecast])
        async def get_ship_forecasts(
            ship_id: Optional[str] = Query(None, description="Filter by specific ship ID"),
            days_ahead: int = Query(30, ge=1, le=365, description="Number of days to forecast")
        ):
            """Get capacity forecasts for individual ships"""
            await self._ensure_data_and_models()
            
            forecasts = []
            ships_to_process = [ship_id] if ship_id else ["ship-01", "ship-02", "ship-03", "ship-04", "ship-05"]
            
            for ship in ships_to_process:
                ship_forecasts = await self._generate_ship_forecast(ship, days_ahead)
                forecasts.extend(ship_forecasts)
            
            return forecasts
        
        @self.app.get("/forecast/routes", response_model=List[RouteForecast])
        async def get_route_forecasts(
            route: Optional[str] = Query(None, description="Filter by specific route"),
            period: str = Query("next_30_days", description="Forecast period")
        ):
            """Get capacity forecasts aggregated by route"""
            await self._ensure_data_and_models()
            
            routes_to_process = [route] if route else list(SEASONAL_PATTERNS.keys())
            forecasts = []
            
            for route_name in routes_to_process:
                route_forecast = await self._generate_route_forecast(route_name, period)
                if route_forecast:
                    forecasts.append(route_forecast)
            
            return forecasts
        
        @self.app.get("/alerts", response_model=List[CapacityAlert])
        async def get_capacity_alerts():
            """Get current capacity alerts and recommendations"""
            await self._ensure_data_and_models()
            
            alerts = []
            current_time = datetime.now(timezone.utc)
            
            # Generate alerts for each ship based on forecasts
            for ship_id in ["ship-01", "ship-02", "ship-03", "ship-04", "ship-05"]:
                ship_alerts = await self._generate_capacity_alerts(ship_id)
                alerts.extend(ship_alerts)
            
            return alerts
        
        @self.app.get("/historical", response_model=List[HistoricalDataPoint])
        async def get_historical_data(
            ship_id: Optional[str] = Query(None),
            route: Optional[str] = Query(None),
            days_back: int = Query(90, ge=1, le=730)
        ):
            """Get historical capacity and booking data"""
            # For v0.4 MVP, generate synthetic historical data
            # In production, this would query ClickHouse
            return await self._generate_synthetic_historical_data(ship_id, route, days_back)
        
        @self.app.post("/models/retrain")
        async def retrain_models():
            """Manually trigger model retraining"""
            try:
                await self._refresh_historical_data()
                await self._train_forecasting_models()
                return {
                    "status": "success",
                    "message": "Forecasting models retrained",
                    "models_trained": len(self.route_models) + len(self.ship_models),
                    "timestamp": datetime.now(timezone.utc)
                }
            except Exception as e:
                logger.error(f"Model retraining failed: {e}")
                raise HTTPException(status_code=500, detail=f"Retraining failed: {e}")
        
        @self.app.get("/models/metrics")
        async def get_model_metrics():
            """Get model performance metrics"""
            return {
                "model_metrics": {name: asdict(metrics) for name, metrics in self.model_metrics.items()},
                "last_training": self.last_training,
                "models_count": len(self.route_models) + len(self.ship_models)
            }
    
    async def initialize_dependencies(self):
        """Initialize external service connections"""
        try:
            # Initialize ClickHouse
            self.clickhouse_client = ClickHouseClient(
                host='clickhouse',
                port=9000,
                user='default', 
                password='clickhouse123',
                database='default'
            )
            
            # Test ClickHouse connection
            self.clickhouse_client.execute("SELECT 1")
            logger.info("ClickHouse connection established")
            
        except Exception as e:
            logger.error(f"ClickHouse connection failed: {e}")
            # Continue without ClickHouse - use synthetic data
        
        try:
            # Initialize NATS
            self.nats_client = await nats.connect("nats://nats:4222")
            logger.info("NATS connection established")
            
        except Exception as e:
            logger.error(f"NATS connection failed: {e}")
            # Continue without NATS for now
    
    async def _ensure_data_and_models(self):
        """Ensure we have data and trained models"""
        if self.historical_data is None or self.last_data_refresh is None or \
           self.last_data_refresh < datetime.now(timezone.utc) - timedelta(hours=1):
            await self._refresh_historical_data()
        
        if not self.route_models or not self.ship_models or self.last_training is None or \
           self.last_training < datetime.now(timezone.utc) - timedelta(hours=6):
            await self._train_forecasting_models()
    
    async def _refresh_historical_data(self):
        """Refresh historical data from ClickHouse or generate synthetic data"""
        logger.info("Refreshing historical capacity data")
        
        # For v0.4 MVP, generate synthetic data
        # In production, this would query ClickHouse fleet.capacity_history table
        self.historical_data = await self._generate_comprehensive_historical_data()
        self.last_data_refresh = datetime.now(timezone.utc)
        
        logger.info(f"Refreshed {len(self.historical_data)} historical data points")
    
    async def _generate_comprehensive_historical_data(self) -> pd.DataFrame:
        """Generate realistic historical data for all ships and routes"""
        data = []
        current_date = datetime.now(timezone.utc)
        
        # Generate 2 years of historical data
        for days_back in range(730, 0, -1):
            date = current_date - timedelta(days=days_back)
            
            for ship_id in ["ship-01", "ship-02", "ship-03", "ship-04", "ship-05"]:
                # Map ship to route and capacity
                ship_routes = {
                    "ship-01": ("Caribbean", 3000),
                    "ship-02": ("Alaska", 2500),
                    "ship-03": ("Mediterranean", 3500), 
                    "ship-04": ("Northern Europe", 2800),
                    "ship-05": ("South Pacific", 3200)
                }
                
                route, capacity = ship_routes[ship_id]
                
                # Apply seasonal patterns
                seasonal_pattern = SEASONAL_PATTERNS[route]
                month = date.month
                
                if month in seasonal_pattern["peak_months"]:
                    seasonal_factor = seasonal_pattern["peak_multiplier"]
                elif month in seasonal_pattern["low_months"]:
                    seasonal_factor = 0.7
                else:
                    seasonal_factor = 1.0
                
                # Add weekly pattern (higher occupancy on weekends)
                weekly_factor = 1.1 if date.weekday() >= 5 else 0.95
                
                # Base occupancy rate with trend and noise
                base_rate = 0.75 + 0.05 * math.sin(days_back / 365 * 2 * math.pi)  # Annual trend
                occupancy_rate = base_rate * seasonal_factor * weekly_factor
                occupancy_rate += random.uniform(-0.1, 0.1)  # Random noise
                occupancy_rate = max(0.3, min(0.98, occupancy_rate))
                
                occupancy = int(capacity * occupancy_rate)
                booking_rate = min(1.0, occupancy_rate + random.uniform(0.02, 0.08))
                revenue_per_passenger = random.uniform(800, 1500) * seasonal_factor
                
                data.append({
                    'date': date,
                    'ship_id': ship_id,
                    'route': route,
                    'capacity': capacity,
                    'occupancy': occupancy,
                    'occupancy_rate': occupancy_rate,
                    'booking_rate': booking_rate,
                    'revenue_per_passenger': revenue_per_passenger
                })
        
        return pd.DataFrame(data)
    
    async def _train_forecasting_models(self):
        """Train time-series forecasting models for routes and ships"""
        if self.historical_data is None:
            await self._refresh_historical_data()
        
        logger.info("Training capacity forecasting models")
        
        # Train route-level models
        for route in self.historical_data['route'].unique():
            route_data = self.historical_data[self.historical_data['route'] == route]
            route_model = await self._train_route_model(route, route_data)
            if route_model:
                self.route_models[route] = route_model
        
        # Train ship-level models
        for ship_id in self.historical_data['ship_id'].unique():
            ship_data = self.historical_data[self.historical_data['ship_id'] == ship_id]
            ship_model = await self._train_ship_model(ship_id, ship_data)
            if ship_model:
                self.ship_models[ship_id] = ship_model
        
        self.last_training = datetime.now(timezone.utc)
        logger.info(f"Trained {len(self.route_models)} route models and {len(self.ship_models)} ship models")
    
    async def _train_route_model(self, route: str, data: pd.DataFrame) -> Optional[Dict]:
        """Train forecasting model for a specific route"""
        if len(data) < 30:  # Need minimum data points
            return None
        
        try:
            # Prepare time series data
            daily_data = data.groupby('date').agg({
                'occupancy': 'sum',
                'capacity': 'sum',
                'occupancy_rate': 'mean',
                'revenue_per_passenger': 'mean'
            }).reset_index()
            
            daily_data = daily_data.sort_values('date')
            
            # Use exponential smoothing for seasonal time series
            occupancy_ts = daily_data['occupancy_rate'].values
            
            model = ExponentialSmoothing(
                occupancy_ts,
                trend='add',
                seasonal='add',
                seasonal_periods=30  # Monthly seasonality
            )
            fitted_model = model.fit()
            
            # Calculate metrics on last 30 days
            train_size = len(occupancy_ts) - 30
            if train_size < 30:
                train_size = int(len(occupancy_ts) * 0.8)
            
            train_data = occupancy_ts[:train_size]
            test_data = occupancy_ts[train_size:]
            
            if len(test_data) > 0:
                predictions = fitted_model.forecast(len(test_data))
                mae = mean_absolute_error(test_data, predictions)
                mse = mean_squared_error(test_data, predictions)
                mape = np.mean(np.abs((test_data - predictions) / test_data)) * 100
                
                metrics = ForecastingMetrics(
                    model_type="ExponentialSmoothing",
                    mae=mae,
                    mse=mse,
                    rmse=np.sqrt(mse),
                    mape=mape,
                    accuracy=max(0, 100 - mape),
                    last_trained=datetime.now(timezone.utc)
                )
                
                self.model_metrics[f"route_{route}"] = metrics
            
            return {
                'model': fitted_model,
                'type': 'ExponentialSmoothing',
                'last_data_point': daily_data.iloc[-1],
                'seasonal_pattern': SEASONAL_PATTERNS.get(route, {}),
                'training_data_points': len(data)
            }
            
        except Exception as e:
            logger.error(f"Failed to train model for route {route}: {e}")
            return None
    
    async def _train_ship_model(self, ship_id: str, data: pd.DataFrame) -> Optional[Dict]:
        """Train forecasting model for a specific ship"""
        if len(data) < 30:  # Need minimum data points
            return None
        
        try:
            # Simple linear model with polynomial features for ship-level forecasting
            data_sorted = data.sort_values('date')
            
            # Convert dates to numerical features
            data_sorted['days_since_start'] = (data_sorted['date'] - data_sorted['date'].min()).dt.days
            data_sorted['month'] = data_sorted['date'].dt.month
            data_sorted['day_of_week'] = data_sorted['date'].dt.dayofweek
            
            # Features: days, month, day_of_week
            X = data_sorted[['days_since_start', 'month', 'day_of_week']].values
            y = data_sorted['occupancy_rate'].values
            
            # Polynomial features for better fitting
            poly_features = PolynomialFeatures(degree=2, include_bias=False)
            X_poly = poly_features.fit_transform(X)
            
            # Train model
            model = LinearRegression()
            model.fit(X_poly, y)
            
            # Calculate metrics
            predictions = model.predict(X_poly)
            mae = mean_absolute_error(y, predictions)
            mse = mean_squared_error(y, predictions) 
            mape = np.mean(np.abs((y - predictions) / y)) * 100
            
            metrics = ForecastingMetrics(
                model_type="PolynomialRegression",
                mae=mae,
                mse=mse,
                rmse=np.sqrt(mse),
                mape=mape,
                accuracy=max(0, 100 - mape),
                last_trained=datetime.now(timezone.utc)
            )
            
            self.model_metrics[f"ship_{ship_id}"] = metrics
            
            return {
                'model': model,
                'poly_features': poly_features,
                'type': 'PolynomialRegression',
                'start_date': data_sorted['date'].min(),
                'last_data_point': data_sorted.iloc[-1],
                'training_data_points': len(data)
            }
            
        except Exception as e:
            logger.error(f"Failed to train model for ship {ship_id}: {e}")
            return None
    
    async def _generate_ship_forecast(self, ship_id: str, days_ahead: int) -> List[CapacityForecast]:
        """Generate forecasts for a specific ship"""
        if ship_id not in self.ship_models:
            return []
        
        ship_model_info = self.ship_models[ship_id]
        model = ship_model_info['model']
        poly_features = ship_model_info['poly_features']
        start_date = ship_model_info['start_date']
        
        # Map ship to route and capacity
        ship_routes = {
            "ship-01": ("Caribbean", 3000),
            "ship-02": ("Alaska", 2500),
            "ship-03": ("Mediterranean", 3500), 
            "ship-04": ("Northern Europe", 2800),
            "ship-05": ("South Pacific", 3200)
        }
        
        route, capacity = ship_routes.get(ship_id, ("Unknown", 3000))
        
        forecasts = []
        current_time = datetime.now(timezone.utc)
        
        for day_offset in range(1, days_ahead + 1):
            forecast_date = current_time + timedelta(days=day_offset)
            days_since_start = (forecast_date - start_date).days
            
            # Prepare features
            X_forecast = np.array([[days_since_start, forecast_date.month, forecast_date.weekday()]])
            X_forecast_poly = poly_features.transform(X_forecast)
            
            # Make prediction
            predicted_rate = model.predict(X_forecast_poly)[0]
            
            # Apply seasonal factors
            seasonal_pattern = SEASONAL_PATTERNS.get(route, {"peak_months": [], "low_months": [], "peak_multiplier": 1.0})
            if forecast_date.month in seasonal_pattern["peak_months"]:
                seasonal_factor = seasonal_pattern["peak_multiplier"]
            elif forecast_date.month in seasonal_pattern["low_months"]:
                seasonal_factor = 0.7
            else:
                seasonal_factor = 1.0
            
            predicted_rate = max(0.3, min(0.98, predicted_rate * seasonal_factor))
            predicted_occupancy = int(capacity * predicted_rate)
            
            # Generate confidence intervals (simplified)
            confidence_range = 0.1  # ±10%
            confidence_lower = max(0.0, predicted_rate - confidence_range)
            confidence_upper = min(1.0, predicted_rate + confidence_range)
            
            # Determine trend direction
            trend_direction = "stable"
            if day_offset > 7:  # Compare to a week ahead
                prev_date = current_time + timedelta(days=day_offset - 7)
                prev_days_since_start = (prev_date - start_date).days
                X_prev = np.array([[prev_days_since_start, prev_date.month, prev_date.weekday()]])
                X_prev_poly = poly_features.transform(X_prev)
                prev_predicted_rate = model.predict(X_prev_poly)[0]
                
                if predicted_rate > prev_predicted_rate + 0.05:
                    trend_direction = "increasing"
                elif predicted_rate < prev_predicted_rate - 0.05:
                    trend_direction = "decreasing"
            
            forecast = CapacityForecast(
                ship_id=ship_id,
                route=route,
                forecast_date=forecast_date,
                predicted_occupancy=predicted_occupancy,
                predicted_occupancy_rate=predicted_rate,
                confidence_lower=confidence_lower,
                confidence_upper=confidence_upper,
                seasonal_factor=seasonal_factor,
                trend_direction=trend_direction
            )
            
            forecasts.append(forecast)
        
        return forecasts
    
    async def _generate_route_forecast(self, route: str, period: str) -> Optional[RouteForecast]:
        """Generate aggregated forecast for a route"""
        if route not in self.route_models:
            return None
        
        route_model_info = self.route_models[route]
        model = route_model_info['model']
        
        # Determine forecast period
        if period == "next_30_days":
            forecast_days = 30
        elif period == "next_quarter":
            forecast_days = 90
        elif period == "next_year":
            forecast_days = 365
        else:
            forecast_days = 30
        
        # Generate route-level predictions
        try:
            predictions = model.forecast(forecast_days)
            
            # Calculate aggregate metrics
            avg_occupancy_rate = np.mean(predictions)
            
            # Get ships on this route
            route_ships = {
                "Caribbean": [("ship-01", 3000)],
                "Alaska": [("ship-02", 2500)],
                "Mediterranean": [("ship-03", 3500)],
                "Northern Europe": [("ship-04", 2800)],
                "South Pacific": [("ship-05", 3200)]
            }
            
            ships = route_ships.get(route, [])
            total_capacity = sum(capacity for _, capacity in ships)
            predicted_demand = int(total_capacity * avg_occupancy_rate)
            
            # Revenue projection (simplified)
            seasonal_pattern = SEASONAL_PATTERNS.get(route, {"peak_multiplier": 1.0})
            base_revenue_per_passenger = 1000 * seasonal_pattern.get("peak_multiplier", 1.0)
            revenue_projection = predicted_demand * base_revenue_per_passenger * (forecast_days / 30)
            
            # Generate recommendations
            recommendations = []
            if avg_occupancy_rate > 0.9:
                recommendations.append("Consider increasing capacity or pricing for this route")
                recommendations.append("High demand predicted - optimize revenue management")
            elif avg_occupancy_rate < 0.6:
                recommendations.append("Low utilization predicted - consider promotional pricing")
                recommendations.append("Evaluate route profitability and capacity allocation")
            else:
                recommendations.append("Capacity utilization within normal range")
            
            if route in ["Alaska", "Northern Europe"] and datetime.now().month in [10, 11, 12, 1, 2]:
                recommendations.append("Off-season for this route - consider repositioning ships")
            
            return RouteForecast(
                route=route,
                forecast_period=period,
                total_capacity=total_capacity * forecast_days,  # Total capacity over period
                predicted_demand=predicted_demand * forecast_days,
                utilization_rate=avg_occupancy_rate,
                revenue_projection=revenue_projection,
                recommendations=recommendations
            )
            
        except Exception as e:
            logger.error(f"Failed to generate route forecast for {route}: {e}")
            return None
    
    async def _generate_capacity_alerts(self, ship_id: str) -> List[CapacityAlert]:
        """Generate capacity alerts for a ship"""
        alerts = []
        
        # Get 30-day forecast
        forecasts = await self._generate_ship_forecast(ship_id, 30)
        if not forecasts:
            return alerts
        
        current_time = datetime.now(timezone.utc)
        
        # Map ship to route
        ship_routes = {
            "ship-01": "Caribbean",
            "ship-02": "Alaska", 
            "ship-03": "Mediterranean",
            "ship-04": "Northern Europe",
            "ship-05": "South Pacific"
        }
        
        route = ship_routes.get(ship_id, "Unknown")
        
        # Check for overbooking risk (>95% predicted occupancy)
        high_occupancy_days = [f for f in forecasts if f.predicted_occupancy_rate > 0.95]
        if high_occupancy_days:
            alert = CapacityAlert(
                alert_id=str(uuid.uuid4()),
                ship_id=ship_id,
                route=route,
                alert_type="overbooking_risk",
                severity="HIGH",
                threshold_value=0.95,
                predicted_value=max(f.predicted_occupancy_rate for f in high_occupancy_days),
                alert_date=current_time,
                recommended_actions=[
                    "Review booking policies and availability",
                    "Consider yield management strategies",
                    "Monitor cancellation rates closely"
                ]
            )
            alerts.append(alert)
        
        # Check for underutilization (<60% predicted occupancy)
        low_occupancy_days = [f for f in forecasts if f.predicted_occupancy_rate < 0.6]
        if len(low_occupancy_days) > 10:  # More than 10 days of low occupancy
            alert = CapacityAlert(
                alert_id=str(uuid.uuid4()),
                ship_id=ship_id,
                route=route,
                alert_type="underutilization",
                severity="MEDIUM",
                threshold_value=0.6,
                predicted_value=min(f.predicted_occupancy_rate for f in low_occupancy_days),
                alert_date=current_time,
                recommended_actions=[
                    "Consider promotional pricing campaigns",
                    "Evaluate itinerary adjustments",
                    "Reassess market demand for this route"
                ]
            )
            alerts.append(alert)
        
        # Check for seasonal peaks
        next_month = (current_time + timedelta(days=30)).month
        seasonal_pattern = SEASONAL_PATTERNS.get(route, {})
        if next_month in seasonal_pattern.get("peak_months", []):
            alert = CapacityAlert(
                alert_id=str(uuid.uuid4()),
                ship_id=ship_id,
                route=route,
                alert_type="seasonal_peak",
                severity="INFO",
                threshold_value=seasonal_pattern.get("peak_multiplier", 1.0),
                predicted_value=seasonal_pattern.get("peak_multiplier", 1.0),
                alert_date=current_time,
                recommended_actions=[
                    "Prepare for seasonal peak demand",
                    "Ensure adequate staffing levels",
                    "Optimize pricing for peak season"
                ]
            )
            alerts.append(alert)
        
        return alerts
    
    async def _generate_synthetic_historical_data(self, ship_id: Optional[str], route: Optional[str], days_back: int) -> List[HistoricalDataPoint]:
        """Generate synthetic historical data for API responses"""
        if self.historical_data is None:
            await self._refresh_historical_data()
        
        # Filter data
        filtered_data = self.historical_data.copy()
        
        if ship_id:
            filtered_data = filtered_data[filtered_data['ship_id'] == ship_id]
        
        if route:
            filtered_data = filtered_data[filtered_data['route'] == route]
        
        # Get last N days
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_back)
        filtered_data = filtered_data[filtered_data['date'] >= cutoff_date]
        
        # Convert to API model
        historical_points = []
        for _, row in filtered_data.iterrows():
            point = HistoricalDataPoint(
                date=row['date'],
                ship_id=row['ship_id'],
                route=row['route'],
                capacity=row['capacity'],
                occupancy=row['occupancy'],
                booking_rate=row['booking_rate'],
                revenue_per_passenger=row['revenue_per_passenger']
            )
            historical_points.append(point)
        
        return historical_points[:1000]  # Limit response size
    
    async def start_background_forecasting(self):
        """Start background task for periodic model retraining"""
        async def forecasting_worker():
            while True:
                try:
                    await self._ensure_data_and_models()
                    
                    # Publish forecasting updates to NATS
                    if self.nats_client:
                        summary = {
                            "models_trained": len(self.route_models) + len(self.ship_models),
                            "last_training": self.last_training.isoformat() if self.last_training else None,
                            "routes": list(self.route_models.keys()),
                            "ships": list(self.ship_models.keys()),
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                        
                        await self.nats_client.publish("fleet.forecasting.status", json.dumps(summary).encode())
                    
                    # Retrain every 6 hours
                    await asyncio.sleep(6 * 3600)
                    
                except Exception as e:
                    logger.error(f"Background forecasting error: {e}")
                    await asyncio.sleep(1800)  # 30 minute retry on error
        
        # Start the background task
        asyncio.create_task(forecasting_worker())

# Global service instance
service = CapacityForecastingService()

@service.app.on_event("startup")
async def startup_event():
    """Initialize service on startup"""
    logger.info("Starting Capacity Forecasting Service v0.4.0")
    await service.initialize_dependencies()
    await service.start_background_forecasting()
    logger.info("Capacity Forecasting Service started successfully")

@service.app.on_event("shutdown") 
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down Capacity Forecasting Service")
    if service.nats_client:
        await service.nats_client.close()

if __name__ == "__main__":
    uvicorn.run(
        "capacity_forecasting_service:service.app",
        host="0.0.0.0", 
        port=8085,
        log_level="info",
        access_log=True
    )