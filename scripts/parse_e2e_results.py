#!/usr/bin/env python3
"""
Parse E2E test results and generate markdown summary
"""

import json
import sys

def parse_e2e_results():
    """Parse E2E results file and print markdown summary"""
    try:
        with open('e2e_results.json', 'r') as f:
            results = json.load(f)
        
        print(f"- **Success Rate**: {results.get('success_rate', 0):.1f}%")
        print(f"- **Total Scenarios**: {results.get('scenarios_run', 0)}")
        print(f"- **Successful Scenarios**: {results.get('scenarios_passed', 0)}")
        print(f"- **Alerts Generated**: {results.get('alerts_generated', 0)}")
        print(f"- **Policy Evaluations**: {results.get('policy_evaluations', 0)}")
        print(f"- **Executions Attempted**: {results.get('executions_attempted', 0)}")
        print(f"- **Audit Entries**: {results.get('audit_entries', 0)}")
        print()
        print('## Test Status')
        if results.get('success_rate', 0) >= 80:
            print('✅ **PASSED** - E2E tests meet 80%+ success rate threshold')
        else:
            print('❌ **FAILED** - E2E tests below 80% success rate threshold')
    except Exception as e:
        print('⚠️ **WARNING** - Could not parse E2E results file')
        print(f'Error: {e}')

if __name__ == '__main__':
    parse_e2e_results()