#!/usr/bin/env python3
"""
Comprehensive E2E Test Suite Runner
Runs both remediation pipeline tests and vendor log parsing tests

This script orchestrates:
1. Original E2E test (Alert -> Policy -> Approval -> Execution -> Audit pipeline)  
2. New vendor log parsing E2E test (Network Devices -> Vector -> ClickHouse)
3. Backward compatibility validation
"""

import asyncio
import json
import logging
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ComprehensiveE2ETestSuite:
    """Orchestrates complete end-to-end testing for AIOps NAAS"""
    
    def __init__(self):
        self.test_results = {
            "suite_run_id": f"comprehensive_e2e_{int(time.time())}",
            "started_at": datetime.now().isoformat(),
            "test_components": {
                "remediation_pipeline": {"status": "pending", "details": "", "duration_s": 0},
                "vendor_log_parsing": {"status": "pending", "details": "", "duration_s": 0},
                "backward_compatibility": {"status": "pending", "details": "", "duration_s": 0}
            },
            "overall_success": False,
            "success_rate": 0.0,
            "total_duration_s": 0
        }
    
    async def run_remediation_pipeline_test(self) -> bool:
        """Run the original E2E remediation pipeline test"""
        logger.info("🔄 Running Remediation Pipeline E2E Test...")
        logger.info("-" * 50)
        
        start_time = time.time()
        
        try:
            # Run the existing E2E test
            result = subprocess.run([
                sys.executable, "e2e_test.py"
            ], capture_output=True, text=True, timeout=180)
            
            duration = time.time() - start_time
            self.test_results["test_components"]["remediation_pipeline"]["duration_s"] = duration
            
            if result.returncode == 0:
                self.test_results["test_components"]["remediation_pipeline"]["status"] = "✅ PASSED"
                self.test_results["test_components"]["remediation_pipeline"]["details"] = "Alert->Policy->Approval->Execution->Audit pipeline working correctly"
                logger.info("✅ Remediation Pipeline E2E test PASSED")
                return True
            else:
                self.test_results["test_components"]["remediation_pipeline"]["status"] = "❌ FAILED"
                self.test_results["test_components"]["remediation_pipeline"]["details"] = f"Exit code: {result.returncode}"
                logger.error(f"❌ Remediation Pipeline E2E test FAILED: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            self.test_results["test_components"]["remediation_pipeline"]["status"] = "❌ TIMEOUT"
            self.test_results["test_components"]["remediation_pipeline"]["details"] = "Test timed out after 180 seconds"
            logger.error("❌ Remediation Pipeline E2E test TIMED OUT")
            return False
        except Exception as e:
            duration = time.time() - start_time
            self.test_results["test_components"]["remediation_pipeline"]["duration_s"] = duration
            self.test_results["test_components"]["remediation_pipeline"]["status"] = "❌ ERROR"
            self.test_results["test_components"]["remediation_pipeline"]["details"] = str(e)
            logger.error(f"❌ Remediation Pipeline E2E test ERROR: {e}")
            return False
    
    async def run_vendor_log_parsing_test(self) -> bool:
        """Run the vendor log parsing E2E test"""
        logger.info("\n🌐 Running Vendor Log Parsing E2E Test...")
        logger.info("-" * 50)
        
        start_time = time.time()
        
        try:
            # Run the vendor log parsing E2E test
            result = subprocess.run([
                sys.executable, "test_e2e_vendor_log_parsing.py"
            ], capture_output=True, text=True, timeout=120)
            
            duration = time.time() - start_time
            self.test_results["test_components"]["vendor_log_parsing"]["duration_s"] = duration
            
            if result.returncode == 0:
                self.test_results["test_components"]["vendor_log_parsing"]["status"] = "✅ PASSED"
                self.test_results["test_components"]["vendor_log_parsing"]["details"] = "Multi-vendor log parsing and normalization working correctly"
                logger.info("✅ Vendor Log Parsing E2E test PASSED")
                return True
            else:
                self.test_results["test_components"]["vendor_log_parsing"]["status"] = "❌ FAILED"
                self.test_results["test_components"]["vendor_log_parsing"]["details"] = f"Exit code: {result.returncode}"
                logger.error(f"❌ Vendor Log Parsing E2E test FAILED: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            self.test_results["test_components"]["vendor_log_parsing"]["status"] = "❌ TIMEOUT"
            self.test_results["test_components"]["vendor_log_parsing"]["details"] = "Test timed out after 120 seconds"
            logger.error("❌ Vendor Log Parsing E2E test TIMED OUT")
            return False
        except Exception as e:
            duration = time.time() - start_time
            self.test_results["test_components"]["vendor_log_parsing"]["duration_s"] = duration
            self.test_results["test_components"]["vendor_log_parsing"]["status"] = "❌ ERROR"
            self.test_results["test_components"]["vendor_log_parsing"]["details"] = str(e)
            logger.error(f"❌ Vendor Log Parsing E2E test ERROR: {e}")
            return False
    
    async def run_backward_compatibility_test(self) -> bool:
        """Run the backward compatibility validation test"""
        logger.info("\n🔄 Running Backward Compatibility Test...")
        logger.info("-" * 50)
        
        start_time = time.time()
        
        try:
            # Run the backward compatibility test
            result = subprocess.run([
                sys.executable, "test_e2e_backward_compatibility.py"
            ], capture_output=True, text=True, timeout=60)
            
            duration = time.time() - start_time
            self.test_results["test_components"]["backward_compatibility"]["duration_s"] = duration
            
            if result.returncode == 0:
                self.test_results["test_components"]["backward_compatibility"]["status"] = "✅ PASSED"
                self.test_results["test_components"]["backward_compatibility"]["details"] = "All changes are backward compatible with existing systems"
                logger.info("✅ Backward Compatibility test PASSED")
                return True
            else:
                self.test_results["test_components"]["backward_compatibility"]["status"] = "❌ FAILED"
                self.test_results["test_components"]["backward_compatibility"]["details"] = f"Exit code: {result.returncode}"
                logger.error(f"❌ Backward Compatibility test FAILED: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            self.test_results["test_components"]["backward_compatibility"]["status"] = "❌ TIMEOUT"
            self.test_results["test_components"]["backward_compatibility"]["details"] = "Test timed out after 60 seconds"
            logger.error("❌ Backward Compatibility test TIMED OUT")
            return False
        except Exception as e:
            duration = time.time() - start_time
            self.test_results["test_components"]["backward_compatibility"]["duration_s"] = duration
            self.test_results["test_components"]["backward_compatibility"]["status"] = "❌ ERROR"
            self.test_results["test_components"]["backward_compatibility"]["details"] = str(e)
            logger.error(f"❌ Backward Compatibility test ERROR: {e}")
            return False
    
    def print_comprehensive_summary(self, test_results: List[bool]):
        """Print comprehensive test suite summary"""
        passed_tests = sum(test_results)
        total_tests = len(test_results)
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        logger.info("\n" + "="*80)
        logger.info("📊 COMPREHENSIVE E2E TEST SUITE SUMMARY")  
        logger.info("="*80)
        
        logger.info(f"Suite Run ID: {self.test_results['suite_run_id']}")
        logger.info(f"Total Duration: {self.test_results['total_duration_s']:.1f}s")
        logger.info(f"Overall Success Rate: {success_rate:.1f}%")
        logger.info(f"Tests Passed: {passed_tests}/{total_tests}")
        
        logger.info(f"\n📋 Test Component Results:")
        for component, details in self.test_results["test_components"].items():
            status = details["status"]
            duration = details["duration_s"]
            description = details["details"]
            
            component_name = component.replace("_", " ").title()
            logger.info(f"   {status:<12} {component_name} ({duration:.1f}s)")
            logger.info(f"                {description}")
        
        logger.info(f"\n🎯 Test Coverage:")
        logger.info(f"   ✅ Remediation Pipeline (Alert->Policy->Approval->Execution->Audit)")
        logger.info(f"   ✅ Multi-Vendor Log Parsing (Cisco, Juniper, Fortinet, Aruba, Microsoft)")
        logger.info(f"   ✅ Device Classification & Cruise Segment Mapping")
        logger.info(f"   ✅ ClickHouse Schema Backward Compatibility")
        logger.info(f"   ✅ Vector Configuration Validation")
        logger.info(f"   ✅ End-to-End Data Flow (Network -> Vector -> ClickHouse)")
        
        # Recommendations based on results
        if success_rate >= 95:
            logger.info(f"\n🎉 EXCELLENT! All systems working optimally.")
            logger.info(f"   ✅ Ready for production deployment")
        elif success_rate >= 80:
            logger.info(f"\n✅ GOOD! Most systems working correctly.")
            logger.info(f"   ⚠️  Review failed tests before production deployment")
        else:
            logger.error(f"\n❌ CRITICAL! Multiple system failures detected.")
            logger.error(f"   🚫 DO NOT deploy to production until issues are resolved")
        
        # Print next steps
        failed_components = [name for name, details in self.test_results["test_components"].items() 
                           if not details["status"].startswith("✅")]
        
        if failed_components:
            logger.info(f"\n🔧 Next Steps:")
            logger.info(f"   1. Review failed component logs: {', '.join(failed_components)}")
            logger.info(f"   2. Run individual tests for debugging: python test_<component>.py")
            logger.info(f"   3. Check Vector/ClickHouse service health")
            logger.info(f"   4. Validate network connectivity and firewall settings")
    
    async def run_comprehensive_tests(self) -> Dict[str, Any]:
        """Run all E2E tests and return comprehensive results"""
        logger.info("🚀 STARTING COMPREHENSIVE E2E TEST SUITE")
        logger.info("="*80)
        logger.info("Testing complete AIOps NAAS unified network log normalization system")
        logger.info("Covering remediation pipeline + vendor log parsing + backward compatibility")
        logger.info("="*80)
        
        suite_start_time = time.time()
        
        # Run all test components
        test_results = []
        
        # Test 1: Remediation Pipeline (existing functionality)
        remediation_passed = await self.run_remediation_pipeline_test()
        test_results.append(remediation_passed)
        
        # Test 2: Vendor Log Parsing (new functionality)
        vendor_parsing_passed = await self.run_vendor_log_parsing_test()
        test_results.append(vendor_parsing_passed)
        
        # Test 3: Backward Compatibility (integration validation)
        backward_compat_passed = await self.run_backward_compatibility_test()
        test_results.append(backward_compat_passed)
        
        # Calculate final metrics
        self.test_results["total_duration_s"] = time.time() - suite_start_time
        self.test_results["completed_at"] = datetime.now().isoformat()
        
        passed_tests = sum(test_results)
        total_tests = len(test_results)
        self.test_results["success_rate"] = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        self.test_results["overall_success"] = passed_tests == total_tests
        
        # Print comprehensive summary
        self.print_comprehensive_summary(test_results)
        
        return self.test_results


async def main():
    """Main entry point for comprehensive E2E test suite"""
    suite = ComprehensiveE2ETestSuite()
    
    try:
        results = await suite.run_comprehensive_tests()
        
        # Save detailed results
        with open("comprehensive_e2e_results.json", "w") as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"\n📄 Detailed results saved to: comprehensive_e2e_results.json")
        
        # Return appropriate exit code based on success rate
        if results["success_rate"] >= 80:  # 80% threshold for overall pass
            logger.info("✅ COMPREHENSIVE E2E TEST SUITE PASSED")
            return 0
        else:
            logger.error("❌ COMPREHENSIVE E2E TEST SUITE FAILED")
            return 1
            
    except KeyboardInterrupt:
        logger.warning("⚠️  Test suite interrupted by user")
        return 130  # Standard exit code for Ctrl+C
    except Exception as e:
        logger.error(f"💥 Test suite crashed: {e}")
        return 1


if __name__ == "__main__":
    exit(asyncio.run(main()))