#!/usr/bin/env python3
"""
AIOps NAAS v0.3 - Predictive Satellite Link Health Service

This service implements predictive models for satellite link degradation using:
- Satellite modem KPIs (SNR, Es/No, BER, etc.)
- Ship GPS position and heading
- Weather data integration
- ML-based link quality prediction with lead-time alerts

The service:
1. Collects satellite modem telemetry and environmental data
2. Applies predictive models to forecast link degradation
3. Generates proactive alerts with lead time before degradation
4. Publishes predictions to NATS for remediation workflows
"""

import asyncio
import logging
import json
import time
import math
import random
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import deque
from fastapi import FastAPI, HTTPException
import uvicorn

import requests
from nats.aio.client import Client as NATS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class ModemKPIs:
    """Satellite modem Key Performance Indicators"""
    timestamp: datetime
    snr_db: float  # Signal-to-Noise Ratio
    es_no_db: float  # Energy per symbol to noise density
    ber: float  # Bit Error Rate
    signal_strength_dbm: float  # Received signal strength
    frequency_offset_hz: float  # Frequency offset
    elevation_angle_deg: float  # Dish elevation
    azimuth_angle_deg: float  # Dish azimuth
    rain_fade_margin_db: float  # Rain fade margin

@dataclass 
class ShipTelemetry:
    """Ship position and environmental telemetry"""
    timestamp: datetime
    latitude: float
    longitude: float
    heading_deg: float
    speed_knots: float
    pitch_deg: float  # Ship pitch (bow up/down)
    roll_deg: float   # Ship roll (port/starboard)
    yaw_deg: float    # Ship yaw (heading change)

@dataclass
class WeatherData:
    """Weather conditions affecting satellite link"""
    timestamp: datetime
    precipitation_mm_hr: float  # Rain rate
    cloud_cover_percent: float
    wind_speed_knots: float
    wind_direction_deg: float
    temperature_c: float
    humidity_percent: float
    atmospheric_pressure_mb: float

@dataclass
class LinkPrediction:
    """Satellite link quality prediction"""
    timestamp: datetime
    prediction_horizon_minutes: int
    predicted_quality_score: float  # 0.0 (bad) to 1.0 (excellent)
    degradation_risk_level: str  # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    contributing_factors: List[str]
    confidence: float  # Model confidence 0.0 to 1.0
    recommended_actions: List[str]
    metadata: Dict[str, Any]

@dataclass
class LinkAlert:
    """Proactive link degradation alert"""
    timestamp: datetime
    alert_id: str
    severity: str  # "WARNING", "CRITICAL"
    predicted_degradation_time: datetime
    lead_time_minutes: int
    current_quality: float
    predicted_quality: float
    risk_factors: List[str]
    recommended_actions: List[str]
    ship_id: str
    modem_id: str

class SatelliteLinkPredictor:
    """ML-based satellite link quality predictor"""
    
    def __init__(self):
        # Simple rule-based model for MVP - can be replaced with ML models
        self.snr_threshold_good = 15.0  # dB
        self.snr_threshold_poor = 8.0   # dB
        self.ber_threshold_good = 1e-6
        self.ber_threshold_poor = 1e-4
        self.rain_fade_threshold = 3.0  # dB margin
        
        # Historical data for trend analysis
        self.modem_history = deque(maxlen=100)
        self.weather_history = deque(maxlen=50)
        self.ship_history = deque(maxlen=100)
        
    def predict_link_quality(
        self, 
        modem: ModemKPIs, 
        weather: WeatherData, 
        ship: ShipTelemetry
    ) -> LinkPrediction:
        """Predict satellite link quality based on current conditions"""
        
        # Store historical data
        self.modem_history.append(modem)
        self.weather_history.append(weather)
        self.ship_history.append(ship)
        
        # Calculate base quality score from modem KPIs
        quality_score = self._calculate_base_quality(modem)
        
        # Apply weather impact
        weather_impact = self._calculate_weather_impact(weather)
        quality_score *= weather_impact
        
        # Apply ship movement impact
        movement_impact = self._calculate_movement_impact(ship)
        quality_score *= movement_impact
        
        # Predict trend based on history
        trend_factor = self._calculate_trend_factor()
        future_quality = quality_score * trend_factor
        
        # Determine risk level
        risk_level = self._determine_risk_level(future_quality, quality_score)
        
        # Identify contributing factors
        factors = self._identify_risk_factors(modem, weather, ship, trend_factor)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(risk_level, factors)
        
        return LinkPrediction(
            timestamp=datetime.now(),
            prediction_horizon_minutes=15,  # 15-minute forecast
            predicted_quality_score=max(0.0, min(1.0, future_quality)),
            degradation_risk_level=risk_level,
            contributing_factors=factors,
            confidence=0.85,  # Fixed confidence for MVP
            recommended_actions=recommendations,
            metadata={
                "current_quality": quality_score,
                "weather_impact": weather_impact,
                "movement_impact": movement_impact,
                "trend_factor": trend_factor
            }
        )
    
    def _calculate_base_quality(self, modem: ModemKPIs) -> float:
        """Calculate base quality score from modem KPIs"""
        # SNR contribution (0-1 scale)
        snr_score = max(0, min(1, (modem.snr_db - 5) / 20))
        
        # BER contribution (0-1 scale, inverted)
        ber_score = max(0, min(1, -math.log10(max(modem.ber, 1e-9)) / 9))
        
        # Signal strength contribution
        signal_score = max(0, min(1, (modem.signal_strength_dbm + 100) / 40))
        
        # Rain fade margin contribution
        margin_score = max(0, min(1, modem.rain_fade_margin_db / 10))
        
        # Weighted average
        return (snr_score * 0.4 + ber_score * 0.3 + 
                signal_score * 0.2 + margin_score * 0.1)
    
    def _calculate_weather_impact(self, weather: WeatherData) -> float:
        """Calculate weather impact factor (0-1 scale)"""
        # Rain attenuation impact (Ka/Ku band)
        rain_impact = 1.0
        if weather.precipitation_mm_hr > 0:
            # Simplified rain attenuation model
            rain_impact = max(0.1, 1.0 - (weather.precipitation_mm_hr * 0.1))
        
        # Cloud cover impact (minor)
        cloud_impact = 1.0 - (weather.cloud_cover_percent * 0.001)
        
        # Wind impact on dish stability
        wind_impact = 1.0
        if weather.wind_speed_knots > 30:
            wind_impact = max(0.5, 1.0 - ((weather.wind_speed_knots - 30) * 0.01))
        
        return rain_impact * cloud_impact * wind_impact
    
    def _calculate_movement_impact(self, ship: ShipTelemetry) -> float:
        """Calculate ship movement impact on satellite tracking"""
        # Dish pointing accuracy degrades with ship movement
        pitch_impact = max(0.7, 1.0 - (abs(ship.pitch_deg) * 0.02))
        roll_impact = max(0.7, 1.0 - (abs(ship.roll_deg) * 0.02))
        
        # Speed impact on tracking
        speed_impact = 1.0
        if ship.speed_knots > 20:
            speed_impact = max(0.8, 1.0 - ((ship.speed_knots - 20) * 0.005))
        
        return pitch_impact * roll_impact * speed_impact
    
    def _calculate_trend_factor(self) -> float:
        """Calculate trend factor based on historical data"""
        if len(self.modem_history) < 5:
            return 1.0
        
        # Simple linear trend on SNR
        recent_snr = [m.snr_db for m in list(self.modem_history)[-5:]]
        if len(recent_snr) >= 2:
            trend = (recent_snr[-1] - recent_snr[0]) / len(recent_snr)
            # Convert trend to factor (positive trend = better future quality)
            trend_factor = 1.0 + (trend * 0.05)  # 5% per dB trend
            return max(0.5, min(1.5, trend_factor))
        
        return 1.0
    
    def _determine_risk_level(self, future_quality: float, current_quality: float) -> str:
        """Determine degradation risk level"""
        if future_quality < 0.3:
            return "CRITICAL"
        elif future_quality < 0.5 or (current_quality - future_quality) > 0.3:
            return "HIGH"
        elif future_quality < 0.7 or (current_quality - future_quality) > 0.15:
            return "MEDIUM"
        else:
            return "LOW"
    
    def _identify_risk_factors(
        self, 
        modem: ModemKPIs, 
        weather: WeatherData, 
        ship: ShipTelemetry,
        trend_factor: float
    ) -> List[str]:
        """Identify contributing risk factors"""
        factors = []
        
        if modem.snr_db < self.snr_threshold_poor:
            factors.append("Low SNR")
        if modem.ber > self.ber_threshold_poor:
            factors.append("High BER")
        if modem.rain_fade_margin_db < self.rain_fade_threshold:
            factors.append("Insufficient rain fade margin")
        
        if weather.precipitation_mm_hr > 5:
            factors.append("Heavy precipitation")
        if weather.wind_speed_knots > 40:
            factors.append("High wind conditions")
        
        if abs(ship.pitch_deg) > 15 or abs(ship.roll_deg) > 15:
            factors.append("Excessive ship movement")
        if ship.speed_knots > 25:
            factors.append("High vessel speed")
        
        if trend_factor < 0.9:
            factors.append("Degrading signal trend")
        
        return factors
    
    def _generate_recommendations(self, risk_level: str, factors: List[str]) -> List[str]:
        """Generate recommended actions based on risk assessment"""
        recommendations = []
        
        if risk_level in ["HIGH", "CRITICAL"]:
            recommendations.append("Consider switching to backup satellite")
            recommendations.append("Reduce bandwidth usage")
            recommendations.append("Enable traffic shaping")
        
        if "Heavy precipitation" in factors:
            recommendations.append("Monitor rain radar for duration")
            recommendations.append("Increase error correction")
        
        if "Excessive ship movement" in factors:
            recommendations.append("Check antenna stabilization")
            recommendations.append("Verify dish tracking systems")
        
        if "Low SNR" in factors or "High BER" in factors:
            recommendations.append("Check antenna alignment")
            recommendations.append("Inspect RF connections")
            recommendations.append("Consider power adjustments")
        
        if not recommendations:
            recommendations.append("Continue normal operations")
        
        return recommendations

class LinkHealthService:
    """Main satellite link health prediction service"""
    
    def __init__(self):
        self.predictor = SatelliteLinkPredictor()
        self.nats_client: Optional[NATS] = None
        self.app = FastAPI(title="Link Health Service", version="0.3.0")
        self.health_status = {
            "service_running": False,
            "nats_connected": False,
            "last_prediction": None,
            "predictions_generated": 0,
            "alerts_sent": 0
        }
        self.setup_routes()
        
        # Simulated data sources - replace with real integrations
        self.current_modem_data: Optional[ModemKPIs] = None
        self.current_weather_data: Optional[WeatherData] = None  
        self.current_ship_data: Optional[ShipTelemetry] = None
    
    def setup_routes(self):
        """Setup FastAPI routes"""
        
        @self.app.get("/health")
        async def health_check():
            return self.health_status
        
        @self.app.get("/prediction")
        async def get_current_prediction():
            """Get current link quality prediction"""
            try:
                prediction = await self.generate_prediction()
                return asdict(prediction) if prediction else {"error": "No prediction available"}
            except Exception as e:
                logger.error(f"Error generating prediction: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/simulate/modem")
        async def update_modem_data(data: dict):
            """Update simulated modem data"""
            try:
                self.current_modem_data = ModemKPIs(
                    timestamp=datetime.now(),
                    **{k: float(v) for k, v in data.items() if k != 'timestamp'}
                )
                return {"status": "updated", "data": asdict(self.current_modem_data)}
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Invalid modem data: {e}")
    
    async def connect_nats(self):
        """Connect to NATS message bus"""
        try:
            self.nats_client = NATS()
            await self.nats_client.connect("nats://nats:4222")
            logger.info("Connected to NATS")
            self.health_status["nats_connected"] = True
        except Exception as e:
            logger.error(f"Failed to connect to NATS: {e}")
            self.health_status["nats_connected"] = False
    
    async def publish_prediction(self, prediction: LinkPrediction):
        """Publish prediction to NATS"""
        try:
            if not self.nats_client or self.nats_client.is_closed:
                logger.warning("NATS not connected, cannot publish prediction")
                return
            
            prediction_json = json.dumps(asdict(prediction), default=str)
            await self.nats_client.publish("link.health.prediction", prediction_json.encode())
            logger.info(f"Published link prediction: risk={prediction.degradation_risk_level}, quality={prediction.predicted_quality_score:.3f}")
            
        except Exception as e:
            logger.error(f"Error publishing prediction: {e}")
    
    async def publish_alert(self, alert: LinkAlert):
        """Publish degradation alert to NATS"""
        try:
            if not self.nats_client or self.nats_client.is_closed:
                logger.warning("NATS not connected, cannot publish alert")
                return
            
            alert_json = json.dumps(asdict(alert), default=str)
            await self.nats_client.publish("link.health.alert", alert_json.encode())
            logger.warning(f"Published link alert: {alert.severity} - {alert.lead_time_minutes}min lead time")
            self.health_status["alerts_sent"] += 1
            
        except Exception as e:
            logger.error(f"Error publishing alert: {e}")
    
    async def generate_prediction(self) -> Optional[LinkPrediction]:
        """Generate satellite link quality prediction"""
        try:
            # Get current data (simulated for MVP)
            modem_data = self.get_current_modem_data()
            weather_data = self.get_current_weather_data()
            ship_data = self.get_current_ship_data()
            
            # Generate prediction
            prediction = self.predictor.predict_link_quality(
                modem_data, weather_data, ship_data
            )
            
            self.health_status["last_prediction"] = datetime.now()
            self.health_status["predictions_generated"] += 1
            
            # Publish prediction
            await self.publish_prediction(prediction)
            
            # Generate alert if needed
            if prediction.degradation_risk_level in ["HIGH", "CRITICAL"]:
                alert = self.create_alert_from_prediction(prediction)
                await self.publish_alert(alert)
            
            return prediction
            
        except Exception as e:
            logger.error(f"Error generating prediction: {e}")
            return None
    
    def get_current_modem_data(self) -> ModemKPIs:
        """Get current satellite modem KPIs (simulated)"""
        if self.current_modem_data:
            return self.current_modem_data
        
        # Simulate realistic satellite modem data with some variability
        base_snr = 18 + random.uniform(-3, 2)  # 15-20 dB typical
        return ModemKPIs(
            timestamp=datetime.now(),
            snr_db=base_snr,
            es_no_db=base_snr + random.uniform(2, 5),
            ber=random.uniform(1e-7, 1e-5),
            signal_strength_dbm=-65 + random.uniform(-10, 5),
            frequency_offset_hz=random.uniform(-500, 500),
            elevation_angle_deg=45 + random.uniform(-15, 15),
            azimuth_angle_deg=180 + random.uniform(-90, 90),
            rain_fade_margin_db=6 + random.uniform(-2, 2)
        )
    
    def get_current_weather_data(self) -> WeatherData:
        """Get current weather data (simulated)"""
        if self.current_weather_data:
            return self.current_weather_data
        
        return WeatherData(
            timestamp=datetime.now(),
            precipitation_mm_hr=random.uniform(0, 5),
            cloud_cover_percent=random.uniform(0, 80),
            wind_speed_knots=random.uniform(5, 35),
            wind_direction_deg=random.uniform(0, 360),
            temperature_c=random.uniform(15, 30),
            humidity_percent=random.uniform(40, 85),
            atmospheric_pressure_mb=1013 + random.uniform(-20, 20)
        )
    
    def get_current_ship_data(self) -> ShipTelemetry:
        """Get current ship telemetry (simulated)"""
        if self.current_ship_data:
            return self.current_ship_data
        
        return ShipTelemetry(
            timestamp=datetime.now(),
            latitude=25.7617 + random.uniform(-1, 1),  # Miami area
            longitude=-80.1918 + random.uniform(-1, 1),
            heading_deg=random.uniform(0, 360),
            speed_knots=random.uniform(12, 22),
            pitch_deg=random.uniform(-5, 5),
            roll_deg=random.uniform(-8, 8),
            yaw_deg=random.uniform(-2, 2)
        )
    
    def create_alert_from_prediction(self, prediction: LinkPrediction) -> LinkAlert:
        """Create degradation alert from prediction"""
        return LinkAlert(
            timestamp=datetime.now(),
            alert_id=f"LINK-{int(time.time())}",
            severity="CRITICAL" if prediction.degradation_risk_level == "CRITICAL" else "WARNING",
            predicted_degradation_time=datetime.now() + timedelta(minutes=prediction.prediction_horizon_minutes),
            lead_time_minutes=prediction.prediction_horizon_minutes,
            current_quality=prediction.metadata.get("current_quality", 0.5),
            predicted_quality=prediction.predicted_quality_score,
            risk_factors=prediction.contributing_factors,
            recommended_actions=prediction.recommended_actions,
            ship_id="SHIP-001",  # Simulated
            modem_id="MODEM-SAT-001"  # Simulated
        )
    
    async def prediction_loop(self):
        """Main prediction generation loop"""
        logger.info("Starting prediction loop")
        while True:
            try:
                await self.generate_prediction()
                await asyncio.sleep(60)  # Generate predictions every minute
            except Exception as e:
                logger.error(f"Error in prediction loop: {e}")
                await asyncio.sleep(30)  # Retry after 30 seconds on error
    
    async def health_check_loop(self):
        """Periodic health check loop"""
        while True:
            try:
                self.health_status["service_running"] = True
                await asyncio.sleep(30)  # Health check every 30 seconds
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
                await asyncio.sleep(30)
    
    async def run_background_tasks(self):
        """Run background prediction and health check tasks"""
        await self.connect_nats()
        
        tasks = [
            asyncio.create_task(self.prediction_loop()),
            asyncio.create_task(self.health_check_loop())
        ]
        
        await asyncio.gather(*tasks)

# Global service instance
service = LinkHealthService()

# FastAPI app instance
app = service.app

async def startup():
    """Application startup"""
    logger.info("Starting Link Health Service v0.3")
    # Start background tasks
    asyncio.create_task(service.run_background_tasks())

async def shutdown():
    """Application shutdown"""
    logger.info("Shutting down Link Health Service")
    if service.nats_client:
        await service.nats_client.close()

app.add_event_handler("startup", startup)
app.add_event_handler("shutdown", shutdown)

if __name__ == "__main__":
    uvicorn.run(
        "link_health_service:app",
        host="0.0.0.0",
        port=8082,
        reload=False
    )