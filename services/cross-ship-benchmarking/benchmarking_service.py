#!/usr/bin/env python3
"""
AIOps NAAS v0.4 - Cross-Ship Benchmarking Service

This service provides cross-ship performance benchmarking and correlation analysis:
- Compare operational metrics across ships in the fleet
- Identify outliers and performance anomalies
- Correlate incidents and patterns across multiple ships
- Provide benchmarking reports for fleet optimization
- Generate insights for fleet-wide operational improvements

The service:
1. Collects performance data from all ships via fleet aggregation
2. Calculates statistical benchmarks for each metric category
3. Identifies ships performing outside normal parameters  
4. Correlates incidents and trends across the fleet
5. Provides actionable insights for fleet management
"""

import asyncio
import logging
import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional, Tuple
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
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from scipy.stats import zscore, pearsonr
from scipy.spatial.distance import pdist, squareform

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Benchmarking categories and their metrics
BENCHMARK_CATEGORIES = {
    "operational_efficiency": ["cpu_usage", "memory_usage", "storage_usage", "bandwidth_utilization"],
    "passenger_experience": ["link_quality", "occupancy_rate", "incident_frequency"],  
    "route_performance": ["speed_knots", "fuel_efficiency", "schedule_adherence"],
    "technical_reliability": ["system_uptime", "error_rate", "maintenance_score"]
}

FLEET_SHIPS = [
    {"ship_id": "ship-01", "name": "Caribbean Dream", "route": "Caribbean", "capacity": 3000, "class": "Large"},
    {"ship_id": "ship-02", "name": "Pacific Explorer", "route": "Alaska", "capacity": 2500, "class": "Medium"}, 
    {"ship_id": "ship-03", "name": "Mediterranean Star", "route": "Mediterranean", "capacity": 3500, "class": "Large"},
    {"ship_id": "ship-04", "name": "Northern Aurora", "route": "Northern Europe", "capacity": 2800, "class": "Medium"},
    {"ship_id": "ship-05", "name": "Southern Cross", "route": "South Pacific", "capacity": 3200, "class": "Large"}
]

# Pydantic models
class BenchmarkMetric(BaseModel):
    metric_name: str
    category: str
    fleet_average: float
    fleet_median: float
    fleet_std: float
    fleet_min: float
    fleet_max: float
    percentile_25: float
    percentile_75: float
    
class ShipBenchmark(BaseModel):
    ship_id: str
    ship_name: str
    route: str
    overall_score: float  # 0-100, higher is better
    category_scores: Dict[str, float]
    metrics: Dict[str, float]
    percentile_rank: float  # Where this ship ranks in fleet (0-100)
    outliers: List[str]  # Metrics where ship is outlier
    strengths: List[str]  # Top performing areas
    improvement_areas: List[str]  # Areas needing attention
    
class OutlierDetection(BaseModel):
    ship_id: str
    metric_name: str
    category: str
    actual_value: float
    expected_value: float
    z_score: float
    severity: str  # "LOW", "MEDIUM", "HIGH"
    description: str

class CorrelationInsight(BaseModel):
    insight_id: str
    insight_type: str  # "fleet_pattern", "route_correlation", "incident_correlation"
    title: str
    description: str
    affected_ships: List[str]
    correlation_strength: float  # -1 to 1
    confidence: float
    recommended_actions: List[str]
    
class FleetBenchmarkSummary(BaseModel):
    timestamp: datetime
    total_ships: int
    active_ships: int
    fleet_health_score: float  # Average of all ship scores
    top_performer: str
    bottom_performer: str
    category_averages: Dict[str, float]
    outlier_count: int
    correlation_insights: int

@dataclass
class ShipPerformanceData:
    ship_id: str
    ship_name: str
    route: str
    timestamp: datetime
    metrics: Dict[str, float]

class CrossShipBenchmarkingService:
    """Main cross-ship benchmarking service"""
    
    def __init__(self):
        self.app = FastAPI(title="Cross-Ship Benchmarking Service", version="0.4.0")
        self.setup_middleware()
        self.setup_routes()
        
        # Service dependencies  
        self.clickhouse_client: Optional[ClickHouseClient] = None
        self.nats_client: Optional[nats.NATS] = None
        
        # Benchmarking data and analysis
        self.fleet_data: Dict[str, ShipPerformanceData] = {}
        self.benchmark_metrics: Dict[str, BenchmarkMetric] = {}
        self.ship_benchmarks: Dict[str, ShipBenchmark] = {}
        self.outliers: List[OutlierDetection] = []
        self.correlation_insights: List[CorrelationInsight] = []
        self.last_analysis: Optional[datetime] = None
        
        # Historical performance for trend analysis
        self.performance_history: List[ShipPerformanceData] = []
        
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
                "service": "cross-ship-benchmarking", 
                "version": "0.4.0",
                "timestamp": datetime.now(timezone.utc),
                "last_analysis": self.last_analysis,
                "ships_analyzed": len(self.fleet_data),
                "dependencies": {
                    "clickhouse": self.clickhouse_client is not None,
                    "nats": self.nats_client is not None and self.nats_client.is_connected
                }
            }
        
        @self.app.get("/fleet/summary", response_model=FleetBenchmarkSummary)
        async def get_fleet_benchmark_summary():
            """Get overall fleet benchmarking summary"""
            await self._ensure_current_analysis()
            
            if not self.ship_benchmarks:
                raise HTTPException(status_code=404, detail="No benchmark data available")
            
            # Calculate fleet health score
            ship_scores = [benchmark.overall_score for benchmark in self.ship_benchmarks.values()]
            fleet_health_score = np.mean(ship_scores) if ship_scores else 0.0
            
            # Find top and bottom performers
            top_performer = max(self.ship_benchmarks.items(), key=lambda x: x[1].overall_score)[0] if self.ship_benchmarks else "N/A"
            bottom_performer = min(self.ship_benchmarks.items(), key=lambda x: x[1].overall_score)[0] if self.ship_benchmarks else "N/A"
            
            # Calculate category averages
            category_averages = {}
            if self.ship_benchmarks:
                for category in BENCHMARK_CATEGORIES.keys():
                    scores = [benchmark.category_scores.get(category, 0) for benchmark in self.ship_benchmarks.values()]
                    category_averages[category] = np.mean(scores) if scores else 0.0
            
            return FleetBenchmarkSummary(
                timestamp=datetime.now(timezone.utc),
                total_ships=len(FLEET_SHIPS),
                active_ships=len(self.fleet_data),
                fleet_health_score=fleet_health_score,
                top_performer=top_performer,
                bottom_performer=bottom_performer,
                category_averages=category_averages,
                outlier_count=len(self.outliers),
                correlation_insights=len(self.correlation_insights)
            )
        
        @self.app.get("/benchmarks/metrics", response_model=List[BenchmarkMetric])
        async def get_benchmark_metrics():
            """Get fleet-wide benchmark metrics"""
            await self._ensure_current_analysis()
            return list(self.benchmark_metrics.values())
        
        @self.app.get("/benchmarks/ships", response_model=List[ShipBenchmark])
        async def get_ship_benchmarks(
            ship_id: Optional[str] = Query(None, description="Filter by specific ship ID"),
            category: Optional[str] = Query(None, description="Filter by performance category")
        ):
            """Get benchmarking results for ships"""
            await self._ensure_current_analysis()
            
            benchmarks = list(self.ship_benchmarks.values())
            
            if ship_id:
                benchmarks = [b for b in benchmarks if b.ship_id == ship_id]
            
            # Sort by overall score descending
            benchmarks.sort(key=lambda x: x.overall_score, reverse=True)
            
            return benchmarks
        
        @self.app.get("/outliers", response_model=List[OutlierDetection])
        async def get_outliers(
            severity: Optional[str] = Query(None, description="Filter by severity level"),
            ship_id: Optional[str] = Query(None, description="Filter by ship ID")
        ):
            """Get detected outliers across the fleet"""
            await self._ensure_current_analysis()
            
            outliers = self.outliers.copy()
            
            if severity:
                outliers = [o for o in outliers if o.severity == severity.upper()]
            
            if ship_id:
                outliers = [o for o in outliers if o.ship_id == ship_id]
            
            # Sort by severity and z-score
            severity_order = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
            outliers.sort(key=lambda x: (severity_order.get(x.severity, 0), abs(x.z_score)), reverse=True)
            
            return outliers
        
        @self.app.get("/insights", response_model=List[CorrelationInsight])
        async def get_correlation_insights(
            insight_type: Optional[str] = Query(None, description="Filter by insight type")
        ):
            """Get correlation insights and fleet-wide patterns"""
            await self._ensure_current_analysis()
            
            insights = self.correlation_insights.copy()
            
            if insight_type:
                insights = [i for i in insights if i.insight_type == insight_type]
            
            # Sort by confidence and correlation strength
            insights.sort(key=lambda x: (x.confidence, abs(x.correlation_strength)), reverse=True)
            
            return insights
        
        @self.app.post("/analysis/run")
        async def run_benchmark_analysis():
            """Manually trigger benchmarking analysis"""
            try:
                await self._run_benchmarking_cycle()
                return {
                    "status": "success",
                    "message": "Cross-ship benchmarking analysis completed",
                    "ships_analyzed": len(self.fleet_data),
                    "outliers_detected": len(self.outliers),
                    "insights_generated": len(self.correlation_insights),
                    "timestamp": datetime.now(timezone.utc)
                }
            except Exception as e:
                logger.error(f"Benchmarking analysis failed: {e}")
                raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")
        
        @self.app.get("/comparison/{ship_id}")
        async def get_ship_comparison(ship_id: str):
            """Get detailed comparison of a ship against fleet benchmarks"""
            await self._ensure_current_analysis()
            
            if ship_id not in self.ship_benchmarks:
                raise HTTPException(status_code=404, detail=f"Ship {ship_id} not found in benchmark data")
            
            ship_benchmark = self.ship_benchmarks[ship_id]
            
            # Generate detailed comparison
            comparison = {
                "ship_details": ship_benchmark,
                "metric_comparisons": {},
                "similar_ships": [],
                "improvement_recommendations": []
            }
            
            # Compare each metric against fleet
            for metric_name, metric_value in ship_benchmark.metrics.items():
                if metric_name in self.benchmark_metrics:
                    fleet_metric = self.benchmark_metrics[metric_name]
                    
                    # Calculate percentile
                    percentile = self._calculate_percentile(metric_value, metric_name)
                    
                    comparison["metric_comparisons"][metric_name] = {
                        "ship_value": metric_value,
                        "fleet_average": fleet_metric.fleet_average,
                        "fleet_median": fleet_metric.fleet_median,
                        "percentile": percentile,
                        "deviation": abs(metric_value - fleet_metric.fleet_average),
                        "performance": "above_average" if metric_value > fleet_metric.fleet_average else "below_average"
                    }
            
            # Find similar ships (by overall score)
            ship_score = ship_benchmark.overall_score
            similar_ships = []
            for other_id, other_benchmark in self.ship_benchmarks.items():
                if other_id != ship_id and abs(other_benchmark.overall_score - ship_score) < 10:
                    similar_ships.append({
                        "ship_id": other_id,
                        "ship_name": other_benchmark.ship_name,
                        "route": other_benchmark.route,
                        "score": other_benchmark.overall_score,
                        "score_difference": other_benchmark.overall_score - ship_score
                    })
            
            comparison["similar_ships"] = similar_ships
            
            # Generate improvement recommendations
            recommendations = []
            for area in ship_benchmark.improvement_areas:
                recommendations.extend(self._generate_improvement_recommendations(ship_id, area))
            
            comparison["improvement_recommendations"] = recommendations
            
            return comparison
    
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
            # Continue without ClickHouse for now
        
        try:
            # Initialize NATS
            self.nats_client = await nats.connect("nats://nats:4222")
            logger.info("NATS connection established")
            
        except Exception as e:
            logger.error(f"NATS connection failed: {e}")
            # Continue without NATS for now
    
    async def _ensure_current_analysis(self):
        """Ensure we have current benchmarking analysis"""
        if self.last_analysis is None or \
           self.last_analysis < datetime.now(timezone.utc) - timedelta(minutes=15):
            await self._run_benchmarking_cycle()
    
    async def _run_benchmarking_cycle(self):
        """Run one cycle of cross-ship benchmarking analysis"""
        logger.info("Starting cross-ship benchmarking analysis")
        
        # Step 1: Collect current fleet performance data
        await self._collect_fleet_performance_data()
        
        # Step 2: Calculate benchmark metrics
        await self._calculate_benchmark_metrics()
        
        # Step 3: Analyze each ship against benchmarks
        await self._analyze_ship_performance()
        
        # Step 4: Detect outliers
        await self._detect_outliers()
        
        # Step 5: Generate correlation insights
        await self._generate_correlation_insights()
        
        # Step 6: Publish results to NATS
        if self.nats_client:
            await self._publish_benchmarking_results()
        
        self.last_analysis = datetime.now(timezone.utc)
        logger.info(f"Cross-ship benchmarking analysis completed at {self.last_analysis}")
    
    async def _collect_fleet_performance_data(self):
        """Collect current performance data for all ships"""
        # In a real implementation, this would query the fleet aggregation service or ClickHouse
        # For v0.4 MVP, generating realistic synthetic data
        
        current_time = datetime.now(timezone.utc)
        
        for ship_config in FLEET_SHIPS:
            ship_id = ship_config["ship_id"]
            
            # Generate realistic performance metrics
            # Operational efficiency metrics  
            cpu_usage = max(20, min(90, np.random.normal(55, 15)))
            memory_usage = max(30, min(95, np.random.normal(65, 20)))
            storage_usage = max(40, min(98, np.random.normal(70, 15)))
            bandwidth_utilization = max(20, min(90, np.random.normal(60, 25)))
            
            # Passenger experience metrics
            link_quality = max(0.4, min(1.0, np.random.normal(0.8, 0.15)))
            occupancy_rate = max(0.5, min(1.0, np.random.normal(0.82, 0.12)))
            incident_frequency = max(0, np.random.poisson(2))  # incidents per day
            
            # Route performance metrics (simplified)
            speed_knots = max(8, min(25, np.random.normal(18, 3)))
            fuel_efficiency = max(0.6, min(1.2, np.random.normal(0.9, 0.15)))
            schedule_adherence = max(0.7, min(1.0, np.random.normal(0.92, 0.08)))
            
            # Technical reliability metrics
            system_uptime = max(0.9, min(1.0, np.random.normal(0.98, 0.02)))
            error_rate = max(0, min(10, np.random.exponential(1.5)))
            maintenance_score = max(60, min(100, np.random.normal(85, 12)))
            
            # Add some ship-specific biases to make analysis interesting
            ship_bias = self._get_ship_performance_bias(ship_id)
            
            metrics = {
                "cpu_usage": cpu_usage * ship_bias.get("cpu_factor", 1.0),
                "memory_usage": memory_usage * ship_bias.get("memory_factor", 1.0),  
                "storage_usage": storage_usage * ship_bias.get("storage_factor", 1.0),
                "bandwidth_utilization": bandwidth_utilization * ship_bias.get("bandwidth_factor", 1.0),
                "link_quality": min(1.0, link_quality * ship_bias.get("link_factor", 1.0)),
                "occupancy_rate": min(1.0, occupancy_rate * ship_bias.get("occupancy_factor", 1.0)),
                "incident_frequency": max(0, incident_frequency * ship_bias.get("incident_factor", 1.0)),
                "speed_knots": speed_knots * ship_bias.get("speed_factor", 1.0),
                "fuel_efficiency": fuel_efficiency * ship_bias.get("fuel_factor", 1.0),
                "schedule_adherence": min(1.0, schedule_adherence * ship_bias.get("schedule_factor", 1.0)),
                "system_uptime": min(1.0, system_uptime * ship_bias.get("uptime_factor", 1.0)),
                "error_rate": error_rate * ship_bias.get("error_factor", 1.0),
                "maintenance_score": maintenance_score * ship_bias.get("maintenance_factor", 1.0)
            }
            
            performance_data = ShipPerformanceData(
                ship_id=ship_id,
                ship_name=ship_config["name"],
                route=ship_config["route"],
                timestamp=current_time,
                metrics=metrics
            )
            
            self.fleet_data[ship_id] = performance_data
            
            # Add to history
            self.performance_history.append(performance_data)
            
            # Keep only last 100 records per ship for memory efficiency
            ship_history_count = len([p for p in self.performance_history if p.ship_id == ship_id])
            if ship_history_count > 100:
                # Remove oldest records for this ship
                self.performance_history = [p for p in self.performance_history 
                                          if not (p.ship_id == ship_id and 
                                                p.timestamp < current_time - timedelta(days=7))]
    
    def _get_ship_performance_bias(self, ship_id: str) -> Dict[str, float]:
        """Get ship-specific performance biases to create realistic variation"""
        # Each ship has different strengths and weaknesses for interesting analysis
        biases = {
            "ship-01": {  # Caribbean Dream - Good passenger experience, high resource usage
                "cpu_factor": 1.2, "memory_factor": 1.15, "bandwidth_factor": 1.1,
                "occupancy_factor": 1.05, "incident_factor": 0.8, "maintenance_factor": 0.95
            },
            "ship-02": {  # Pacific Explorer - Efficient operations, average passenger metrics  
                "cpu_factor": 0.85, "memory_factor": 0.9, "fuel_factor": 1.1,
                "link_factor": 0.95, "uptime_factor": 1.02, "error_factor": 0.7
            },
            "ship-03": {  # Mediterranean Star - Premium service, higher costs
                "occupancy_factor": 1.08, "bandwidth_factor": 1.2, "maintenance_factor": 1.1,
                "fuel_factor": 0.9, "schedule_factor": 1.02, "incident_factor": 0.6
            },
            "ship-04": {  # Northern Aurora - Reliable but aging systems
                "uptime_factor": 0.98, "error_factor": 1.3, "maintenance_factor": 0.9,
                "cpu_factor": 1.1, "speed_factor": 0.95, "fuel_factor": 0.95
            },
            "ship-05": {  # Southern Cross - New ship, excellent technical metrics
                "uptime_factor": 1.05, "error_factor": 0.5, "maintenance_factor": 1.15,
                "fuel_factor": 1.05, "link_factor": 1.1, "cpu_factor": 0.9
            }
        }
        
        return biases.get(ship_id, {})
    
    async def _calculate_benchmark_metrics(self):
        """Calculate fleet-wide benchmark metrics"""
        if not self.fleet_data:
            return
        
        # Collect all metric values across fleet
        all_metrics = {}
        for ship_data in self.fleet_data.values():
            for metric_name, value in ship_data.metrics.items():
                if metric_name not in all_metrics:
                    all_metrics[metric_name] = []
                all_metrics[metric_name].append(value)
        
        # Calculate statistics for each metric
        self.benchmark_metrics.clear()
        for metric_name, values in all_metrics.items():
            if not values:
                continue
                
            values_array = np.array(values)
            
            # Find category for this metric
            category = "other"
            for cat, metrics in BENCHMARK_CATEGORIES.items():
                if metric_name in metrics:
                    category = cat
                    break
            
            benchmark = BenchmarkMetric(
                metric_name=metric_name,
                category=category,
                fleet_average=float(np.mean(values_array)),
                fleet_median=float(np.median(values_array)),
                fleet_std=float(np.std(values_array)),
                fleet_min=float(np.min(values_array)),
                fleet_max=float(np.max(values_array)),
                percentile_25=float(np.percentile(values_array, 25)),
                percentile_75=float(np.percentile(values_array, 75))
            )
            
            self.benchmark_metrics[metric_name] = benchmark
    
    async def _analyze_ship_performance(self):
        """Analyze each ship's performance against fleet benchmarks"""
        if not self.fleet_data or not self.benchmark_metrics:
            return
        
        self.ship_benchmarks.clear()
        
        for ship_id, ship_data in self.fleet_data.items():
            # Calculate category scores
            category_scores = {}
            for category, metrics in BENCHMARK_CATEGORIES.items():
                scores = []
                for metric in metrics:
                    if metric in ship_data.metrics and metric in self.benchmark_metrics:
                        percentile = self._calculate_percentile(ship_data.metrics[metric], metric)
                        # Convert percentile to score (higher is better)
                        # For "bad" metrics (like error_rate, cpu_usage), invert the score
                        if self._is_lower_better_metric(metric):
                            score = 100 - percentile
                        else:
                            score = percentile
                        scores.append(score)
                
                category_scores[category] = np.mean(scores) if scores else 50.0
            
            # Calculate overall score
            overall_score = np.mean(list(category_scores.values())) if category_scores else 50.0
            
            # Calculate fleet percentile rank
            all_ship_scores = []
            for other_data in self.fleet_data.values():
                other_category_scores = {}
                for category, metrics in BENCHMARK_CATEGORIES.items():
                    scores = []
                    for metric in metrics:
                        if metric in other_data.metrics and metric in self.benchmark_metrics:
                            percentile = self._calculate_percentile(other_data.metrics[metric], metric)
                            if self._is_lower_better_metric(metric):
                                score = 100 - percentile
                            else:
                                score = percentile
                            scores.append(score)
                    other_category_scores[category] = np.mean(scores) if scores else 50.0
                other_overall_score = np.mean(list(other_category_scores.values())) if other_category_scores else 50.0
                all_ship_scores.append(other_overall_score)
            
            percentile_rank = (np.sum(np.array(all_ship_scores) <= overall_score) / len(all_ship_scores)) * 100
            
            # Identify strengths and improvement areas
            strengths = []
            improvement_areas = []
            outliers = []
            
            for category, score in category_scores.items():
                if score >= 80:
                    strengths.append(category)
                elif score <= 40:
                    improvement_areas.append(category)
            
            # Find outlier metrics
            for metric_name, value in ship_data.metrics.items():
                if metric_name in self.benchmark_metrics:
                    z_score = abs(self._calculate_z_score(value, metric_name))
                    if z_score > 2.0:  # 2 standard deviations
                        outliers.append(metric_name)
            
            # Get ship config
            ship_config = next(ship for ship in FLEET_SHIPS if ship["ship_id"] == ship_id)
            
            benchmark = ShipBenchmark(
                ship_id=ship_id,
                ship_name=ship_config["name"],
                route=ship_config["route"],
                overall_score=overall_score,
                category_scores=category_scores,
                metrics=ship_data.metrics,
                percentile_rank=percentile_rank,
                outliers=outliers,
                strengths=strengths,
                improvement_areas=improvement_areas
            )
            
            self.ship_benchmarks[ship_id] = benchmark
    
    async def _detect_outliers(self):
        """Detect outliers across fleet metrics"""
        self.outliers.clear()
        
        if not self.fleet_data or not self.benchmark_metrics:
            return
        
        for ship_id, ship_data in self.fleet_data.items():
            for metric_name, value in ship_data.metrics.items():
                if metric_name not in self.benchmark_metrics:
                    continue
                
                z_score = self._calculate_z_score(value, metric_name)
                abs_z_score = abs(z_score)
                
                if abs_z_score > 1.5:  # Outlier threshold
                    # Determine severity
                    if abs_z_score > 3.0:
                        severity = "HIGH"
                    elif abs_z_score > 2.0:
                        severity = "MEDIUM"  
                    else:
                        severity = "LOW"
                    
                    benchmark = self.benchmark_metrics[metric_name]
                    expected_value = benchmark.fleet_average
                    
                    # Generate description
                    if z_score > 0:
                        direction = "significantly higher than"
                    else:
                        direction = "significantly lower than"
                    
                    description = f"{metric_name} is {direction} fleet average ({expected_value:.2f})"
                    
                    # Find category
                    category = "other"
                    for cat, metrics in BENCHMARK_CATEGORIES.items():
                        if metric_name in metrics:
                            category = cat
                            break
                    
                    outlier = OutlierDetection(
                        ship_id=ship_id,
                        metric_name=metric_name,
                        category=category,
                        actual_value=value,
                        expected_value=expected_value,
                        z_score=z_score,
                        severity=severity,
                        description=description
                    )
                    
                    self.outliers.append(outlier)
    
    async def _generate_correlation_insights(self):
        """Generate correlation insights and fleet-wide patterns"""
        self.correlation_insights.clear()
        
        if len(self.fleet_data) < 3:  # Need minimum ships for correlation
            return
        
        # Create correlation matrix
        metric_names = list(next(iter(self.fleet_data.values())).metrics.keys())
        correlation_data = []
        
        for ship_data in self.fleet_data.values():
            row = [ship_data.metrics.get(metric, 0) for metric in metric_names]
            correlation_data.append(row)
        
        df = pd.DataFrame(correlation_data, columns=metric_names)
        correlation_matrix = df.corr()
        
        # Find strong correlations
        insights_generated = 0
        for i, metric1 in enumerate(metric_names):
            for j, metric2 in enumerate(metric_names[i+1:], i+1):
                correlation = correlation_matrix.iloc[i, j]
                
                if abs(correlation) > 0.7 and not np.isnan(correlation):  # Strong correlation
                    insight_id = str(uuid.uuid4())
                    
                    if correlation > 0:
                        relationship = "positive correlation"
                        title = f"Strong Positive Correlation: {metric1} and {metric2}"
                    else:
                        relationship = "negative correlation"
                        title = f"Strong Negative Correlation: {metric1} and {metric2}"
                    
                    description = f"Fleet analysis shows {relationship} ({correlation:.2f}) between {metric1} and {metric2} across all ships"
                    
                    # Determine affected ships
                    affected_ships = []
                    for ship_id, ship_data in self.fleet_data.items():
                        val1 = ship_data.metrics.get(metric1, 0)
                        val2 = ship_data.metrics.get(metric2, 0)
                        
                        # Check if this ship follows the correlation pattern
                        if correlation > 0 and val1 > df[metric1].median() and val2 > df[metric2].median():
                            affected_ships.append(ship_id)
                        elif correlation < 0 and val1 > df[metric1].median() and val2 < df[metric2].median():
                            affected_ships.append(ship_id)
                    
                    # Generate recommendations
                    recommendations = self._generate_correlation_recommendations(metric1, metric2, correlation)
                    
                    insight = CorrelationInsight(
                        insight_id=insight_id,
                        insight_type="fleet_pattern",
                        title=title,
                        description=description,
                        affected_ships=affected_ships,
                        correlation_strength=correlation,
                        confidence=min(95, abs(correlation) * 100),
                        recommended_actions=recommendations
                    )
                    
                    self.correlation_insights.append(insight)
                    insights_generated += 1
                    
                    if insights_generated >= 10:  # Limit insights to prevent overwhelming
                        break
            
            if insights_generated >= 10:
                break
        
        # Generate route-based insights
        await self._generate_route_insights()
    
    async def _generate_route_insights(self):
        """Generate insights specific to routes"""
        if len(self.fleet_data) < 2:
            return
        
        # Group ships by route
        route_groups = {}
        for ship_data in self.fleet_data.values():
            route = ship_data.route
            if route not in route_groups:
                route_groups[route] = []
            route_groups[route].append(ship_data)
        
        # Compare routes
        for route, ships in route_groups.items():
            if len(ships) < 1:
                continue
            
            # Calculate route averages
            route_metrics = {}
            for metric_name in BENCHMARK_CATEGORIES["operational_efficiency"]:
                values = [ship.metrics.get(metric_name, 0) for ship in ships]
                route_metrics[metric_name] = np.mean(values) if values else 0
            
            # Compare against fleet average
            notable_differences = []
            for metric_name, route_avg in route_metrics.items():
                if metric_name in self.benchmark_metrics:
                    fleet_avg = self.benchmark_metrics[metric_name].fleet_average
                    diff_percent = abs(route_avg - fleet_avg) / fleet_avg * 100
                    
                    if diff_percent > 20:  # 20% difference threshold
                        notable_differences.append((metric_name, route_avg, fleet_avg, diff_percent))
            
            if notable_differences:
                # Generate route-specific insight
                insight_id = str(uuid.uuid4())
                metric_name, route_avg, fleet_avg, diff_percent = notable_differences[0]  # Most significant
                
                if route_avg > fleet_avg:
                    direction = "higher"
                    performance = "above average"
                else:
                    direction = "lower"
                    performance = "below average"
                
                title = f"Route Performance Pattern: {route}"
                description = f"Ships on {route} route show {performance} {metric_name} ({route_avg:.2f} vs fleet average {fleet_avg:.2f})"
                
                affected_ships = [ship.ship_id for ship in ships]
                
                recommendations = [
                    f"Investigate {route}-specific factors affecting {metric_name}",
                    "Consider route-specific optimization strategies",
                    "Share best practices from top-performing routes"
                ]
                
                insight = CorrelationInsight(
                    insight_id=insight_id,
                    insight_type="route_correlation",
                    title=title,
                    description=description,
                    affected_ships=affected_ships,
                    correlation_strength=0.8,  # Route correlation
                    confidence=85.0,
                    recommended_actions=recommendations
                )
                
                self.correlation_insights.append(insight)
    
    def _calculate_percentile(self, value: float, metric_name: str) -> float:
        """Calculate percentile rank for a metric value"""
        if metric_name not in self.benchmark_metrics:
            return 50.0
        
        benchmark = self.benchmark_metrics[metric_name]
        
        # Collect all fleet values for this metric
        all_values = []
        for ship_data in self.fleet_data.values():
            if metric_name in ship_data.metrics:
                all_values.append(ship_data.metrics[metric_name])
        
        if not all_values:
            return 50.0
        
        all_values.sort()
        
        # Find percentile
        percentile = (np.searchsorted(all_values, value, side='right') / len(all_values)) * 100
        return min(100, max(0, percentile))
    
    def _calculate_z_score(self, value: float, metric_name: str) -> float:
        """Calculate z-score for a metric value"""
        if metric_name not in self.benchmark_metrics:
            return 0.0
        
        benchmark = self.benchmark_metrics[metric_name]
        if benchmark.fleet_std == 0:
            return 0.0
        
        return (value - benchmark.fleet_average) / benchmark.fleet_std
    
    def _is_lower_better_metric(self, metric_name: str) -> bool:
        """Check if lower values are better for this metric"""
        lower_better_metrics = ["cpu_usage", "memory_usage", "storage_usage", "bandwidth_utilization", 
                               "incident_frequency", "error_rate"]
        return metric_name in lower_better_metrics
    
    def _generate_correlation_recommendations(self, metric1: str, metric2: str, correlation: float) -> List[str]:
        """Generate recommendations based on metric correlations"""
        recommendations = []
        
        if correlation > 0:
            recommendations.append(f"Monitor {metric1} as increases may indicate {metric2} will also increase")
            recommendations.append(f"Optimize {metric1} to potentially improve {metric2}")
        else:
            recommendations.append(f"Consider {metric1} when {metric2} is high - they tend to have inverse relationship")
            recommendations.append(f"Balancing {metric1} and {metric2} may optimize overall performance")
        
        recommendations.append("Validate correlation with historical data and operational context")
        return recommendations
    
    def _generate_improvement_recommendations(self, ship_id: str, category: str) -> List[str]:
        """Generate improvement recommendations for a ship in a specific category"""
        recommendations = []
        
        category_recommendations = {
            "operational_efficiency": [
                "Review resource allocation and optimization policies",
                "Consider workload balancing and scheduling improvements",
                "Evaluate system configuration and performance tuning"
            ],
            "passenger_experience": [
                "Enhance network connectivity and bandwidth management", 
                "Review service delivery processes and staff training",
                "Implement proactive incident prevention measures"
            ],
            "route_performance": [
                "Optimize route planning and scheduling",
                "Review fuel consumption and efficiency measures",
                "Evaluate weather routing and operational procedures"
            ],
            "technical_reliability": [
                "Implement predictive maintenance programs",
                "Review system monitoring and alerting",
                "Enhance error handling and recovery procedures"
            ]
        }
        
        base_recommendations = category_recommendations.get(category, [])
        recommendations.extend(base_recommendations)
        
        # Add ship-specific context
        ship_config = next(ship for ship in FLEET_SHIPS if ship["ship_id"] == ship_id)
        recommendations.append(f"Compare with similar ships on {ship_config['route']} route for best practices")
        
        return recommendations
    
    async def _publish_benchmarking_results(self):
        """Publish benchmarking results to NATS"""
        if not self.nats_client:
            return
        
        # Publish fleet summary
        fleet_summary = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "ships_analyzed": len(self.fleet_data),
            "outliers_detected": len(self.outliers),
            "insights_generated": len(self.correlation_insights),
            "top_performers": [ship_id for ship_id, benchmark in self.ship_benchmarks.items() 
                             if benchmark.overall_score >= 80],
            "improvement_needed": [ship_id for ship_id, benchmark in self.ship_benchmarks.items() 
                                 if benchmark.overall_score < 60]
        }
        
        await self.nats_client.publish("fleet.benchmarking.summary", json.dumps(fleet_summary).encode())
        
        # Publish high severity outliers
        high_severity_outliers = [outlier for outlier in self.outliers if outlier.severity == "HIGH"]
        if high_severity_outliers:
            outlier_alert = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "alert_type": "high_severity_outliers",
                "count": len(high_severity_outliers),
                "outliers": [asdict(outlier) for outlier in high_severity_outliers[:5]]  # Limit to top 5
            }
            
            await self.nats_client.publish("fleet.benchmarking.alerts", json.dumps(outlier_alert, default=str).encode())
    
    async def start_background_benchmarking(self):
        """Start background task for periodic benchmarking analysis"""
        async def benchmarking_worker():
            while True:
                try:
                    await self._run_benchmarking_cycle()
                    # Run every 10 minutes for testing, would be longer in production
                    await asyncio.sleep(600)
                except Exception as e:
                    logger.error(f"Background benchmarking error: {e}")
                    await asyncio.sleep(300)  # 5 minute retry on error
        
        # Start the background task
        asyncio.create_task(benchmarking_worker())

# Global service instance
service = CrossShipBenchmarkingService()

@service.app.on_event("startup")
async def startup_event():
    """Initialize service on startup"""
    logger.info("Starting Cross-Ship Benchmarking Service v0.4.0")
    await service.initialize_dependencies()
    await service.start_background_benchmarking()
    logger.info("Cross-Ship Benchmarking Service started successfully")

@service.app.on_event("shutdown") 
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down Cross-Ship Benchmarking Service")
    if service.nats_client:
        await service.nats_client.close()

if __name__ == "__main__":
    uvicorn.run(
        "benchmarking_service:service.app",
        host="0.0.0.0", 
        port=8086,
        log_level="info",
        access_log=True
    )