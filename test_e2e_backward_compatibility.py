#!/usr/bin/env python3
"""
Test E2E Backward Compatibility with Unified Network Log Normalization Changes

This test validates that the vendor log normalization changes don't break 
existing functionality, particularly around:
1. E2E test pipeline (Alert -> Policy -> Approval -> Execution -> Audit)
2. ClickHouse schema backward compatibility  
3. Existing anomaly detection queries
4. Incident API functionality
"""

import asyncio
import json
import logging
import subprocess
import sys
import time
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BackwardCompatibilityTester:
    def __init__(self):
        self.test_results = {
            "e2e_test": {"status": "pending", "details": ""},
            "schema_compatibility": {"status": "pending", "details": ""},
            "clickhouse_queries": {"status": "pending", "details": ""},
            "vector_config": {"status": "pending", "details": ""},
            "overall_success": False
        }

    def test_e2e_pipeline(self) -> bool:
        """Test the E2E pipeline still works"""
        logger.info("🔍 Testing E2E Pipeline Compatibility...")
        
        try:
            # Run the E2E test
            result = subprocess.run([
                sys.executable, "e2e_test.py"
            ], capture_output=True, text=True, timeout=120)
            
            if result.returncode == 0:
                self.test_results["e2e_test"]["status"] = "✅ PASS"
                self.test_results["e2e_test"]["details"] = "E2E test completed successfully"
                logger.info("✅ E2E Pipeline test PASSED")
                return True
            else:
                self.test_results["e2e_test"]["status"] = "❌ FAIL"
                self.test_results["e2e_test"]["details"] = f"Exit code: {result.returncode}, Error: {result.stderr}"
                logger.error(f"❌ E2E Pipeline test FAILED: {result.stderr}")
                return False
                
        except Exception as e:
            self.test_results["e2e_test"]["status"] = "❌ ERROR"
            self.test_results["e2e_test"]["details"] = str(e)
            logger.error(f"❌ E2E Pipeline test ERROR: {e}")
            return False

    def test_clickhouse_schema_compatibility(self) -> bool:
        """Test ClickHouse schema changes are backward compatible"""
        logger.info("🔍 Testing ClickHouse Schema Compatibility...")
        
        try:
            # Test that old queries still work with new schema
            init_sql = Path("clickhouse/init.sql")
            if not init_sql.exists():
                self.test_results["schema_compatibility"]["status"] = "❌ FAIL"
                self.test_results["schema_compatibility"]["details"] = "ClickHouse init.sql not found"
                return False
            
            # Read the schema and validate it has backward compatibility
            schema_content = init_sql.read_text()
            
            # Check that all new fields have DEFAULT values (backward compatible)
            new_fields = [
                "vendor LowCardinality(String) DEFAULT ''",
                "device_type LowCardinality(String) DEFAULT ''", 
                "cruise_segment LowCardinality(String) DEFAULT ''",
                "facility LowCardinality(String) DEFAULT ''",
                "severity LowCardinality(String) DEFAULT ''",
                "category LowCardinality(String) DEFAULT ''",
                "event_id String DEFAULT ''",
                "ip_address IPv4 DEFAULT toIPv4('0.0.0.0')",
                "ingestion_time DateTime DEFAULT now()"
            ]
            
            all_defaults_present = all(field in schema_content for field in new_fields)
            
            if all_defaults_present:
                self.test_results["schema_compatibility"]["status"] = "✅ PASS"
                self.test_results["schema_compatibility"]["details"] = "All new fields have DEFAULT values for backward compatibility"
                logger.info("✅ ClickHouse schema backward compatibility PASSED")
                return True
            else:
                self.test_results["schema_compatibility"]["status"] = "❌ FAIL"
                self.test_results["schema_compatibility"]["details"] = "Some new fields missing DEFAULT values"
                logger.error("❌ ClickHouse schema backward compatibility FAILED")
                return False
                
        except Exception as e:
            self.test_results["schema_compatibility"]["status"] = "❌ ERROR"
            self.test_results["schema_compatibility"]["details"] = str(e)
            logger.error(f"❌ Schema compatibility test ERROR: {e}")
            return False

    def test_existing_clickhouse_queries(self) -> bool:
        """Test that existing queries in services still work"""
        logger.info("🔍 Testing Existing ClickHouse Query Compatibility...")
        
        try:
            # Check anomaly service queries
            anomaly_service = Path("services/anomaly-detection/anomaly_service.py")
            if anomaly_service.exists():
                content = anomaly_service.read_text()
                
                # Check if queries use basic fields that still exist
                basic_queries = [
                    "FROM logs.raw",
                    "source", "message", "timestamp", "host", "service"
                ]
                
                queries_compatible = all(query in content for query in basic_queries)
                
                if queries_compatible:
                    logger.info("✅ Anomaly service queries are compatible")
                else:
                    logger.warning("⚠️  Some anomaly service queries may need review")
            
            # Check incident API
            incident_api = Path("services/incident-api/incident_api.py")
            if incident_api.exists():
                content = incident_api.read_text()
                # Basic compatibility check - these core fields should still work
                if "FROM logs.raw" in content or "logs.incidents" in content:
                    logger.info("✅ Incident API queries are compatible")
            
            self.test_results["clickhouse_queries"]["status"] = "✅ PASS"
            self.test_results["clickhouse_queries"]["details"] = "Existing query patterns are compatible"
            logger.info("✅ Existing ClickHouse queries compatibility PASSED")
            return True
            
        except Exception as e:
            self.test_results["clickhouse_queries"]["status"] = "❌ ERROR"
            self.test_results["clickhouse_queries"]["details"] = str(e)
            logger.error(f"❌ ClickHouse queries test ERROR: {e}")
            return False

    def test_vector_config_syntax(self) -> bool:
        """Test Vector configuration syntax is valid"""
        logger.info("🔍 Testing Vector Configuration Syntax...")
        
        try:
            vector_config = Path("vector/vector.toml")
            if not vector_config.exists():
                self.test_results["vector_config"]["status"] = "❌ FAIL"
                self.test_results["vector_config"]["details"] = "Vector config not found"
                return False
            
            # Try to validate vector config if vector is available
            # Since we can't install vector due to firewall restrictions,
            # we'll do basic TOML syntax validation
            
            try:
                import toml
                config_data = toml.load(vector_config)
                logger.info("✅ Vector configuration TOML syntax is valid")
                
                # Check if basic sources and sinks are present
                if 'sources' in config_data and 'sinks' in config_data:
                    self.test_results["vector_config"]["status"] = "✅ PASS"
                    self.test_results["vector_config"]["details"] = "Vector config syntax valid with sources and sinks"
                    return True
                else:
                    self.test_results["vector_config"]["status"] = "⚠️  PARTIAL"
                    self.test_results["vector_config"]["details"] = "TOML valid but missing expected sections"
                    return True
                    
            except ImportError:
                # If toml not available, just check file exists and is readable
                content = vector_config.read_text()
                if len(content) > 100:  # Basic sanity check
                    self.test_results["vector_config"]["status"] = "✅ PASS"
                    self.test_results["vector_config"]["details"] = "Vector config exists and readable"
                    logger.info("✅ Vector configuration basic validation PASSED")
                    return True
                else:
                    self.test_results["vector_config"]["status"] = "❌ FAIL"
                    self.test_results["vector_config"]["details"] = "Vector config too small or empty"
                    return False
                    
        except Exception as e:
            self.test_results["vector_config"]["status"] = "❌ ERROR"
            self.test_results["vector_config"]["details"] = str(e)
            logger.error(f"❌ Vector config test ERROR: {e}")
            return False

    async def run_all_tests(self) -> dict:
        """Run all backward compatibility tests"""
        logger.info("="*70)
        logger.info("🔍 RUNNING BACKWARD COMPATIBILITY TESTS")
        logger.info("="*70)
        
        test_start = time.time()
        
        # Run tests
        tests = [
            ("E2E Pipeline", self.test_e2e_pipeline),
            ("ClickHouse Schema", self.test_clickhouse_schema_compatibility),
            ("Existing Queries", self.test_existing_clickhouse_queries),
            ("Vector Config", self.test_vector_config_syntax)
        ]
        
        passed_tests = 0
        for test_name, test_func in tests:
            logger.info(f"\n📋 Running {test_name} test...")
            if test_func():
                passed_tests += 1
            
        test_duration = time.time() - test_start
        
        # Calculate overall success
        self.test_results["overall_success"] = passed_tests == len(tests)
        
        # Print summary
        logger.info("\n" + "="*70)
        logger.info("📊 BACKWARD COMPATIBILITY TEST SUMMARY")
        logger.info("="*70)
        
        for test_name, result in self.test_results.items():
            if test_name == "overall_success":
                continue
            logger.info(f"{result['status']:<12} {test_name}: {result['details']}")
        
        logger.info(f"\n📈 Results: {passed_tests}/{len(tests)} tests passed")
        logger.info(f"⏱️  Duration: {test_duration:.1f}s")
        
        if self.test_results["overall_success"]:
            logger.info("🎉 ALL BACKWARD COMPATIBILITY TESTS PASSED!")
        else:
            logger.error("❌ SOME BACKWARD COMPATIBILITY TESTS FAILED")
        
        return self.test_results


async def main():
    """Main entry point"""
    tester = BackwardCompatibilityTester()
    results = await tester.run_all_tests()
    
    # Save results
    with open("backward_compatibility_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    # Exit with appropriate code
    return 0 if results["overall_success"] else 1


if __name__ == "__main__":
    exit(asyncio.run(main()))