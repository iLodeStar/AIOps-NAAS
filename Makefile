.PHONY: up up-all up-service status logs down collect-logs fix creds simulate up-keycloak debug-incident diagnose compatibility-monitor

up:
	bash scripts/aiops.sh

up-all:
	bash scripts/aiops.sh up --all

up-service:
	@if [ -z "$$SERVICE" ]; then echo "Usage: make up-service SERVICE=<name>"; exit 1; fi
	bash scripts/aiops.sh up --service "$$SERVICE"

up-keycloak:
	bash scripts/aiops.sh up --with-keycloak

status:
	bash scripts/aiops.sh status

logs:
	@if [ -z "$$SERVICE" ]; then echo "Usage: make logs SERVICE=<name>"; exit 1; fi
	bash scripts/aiops.sh logs "$$SERVICE"

down:
	bash scripts/aiops.sh down

collect-logs:
	bash scripts/aiops.sh collect-logs

fix:
	bash scripts/aiops.sh fix

creds:
	bash scripts/aiops.sh up --ask-creds

simulate:
	bash scripts/simulate_data.sh

debug-incident:
	@echo "🚀 Starting One-Click Incident Debugging Tool..."
	bash scripts/one_click_debug.sh

diagnose:
	@echo "🩺 Starting User-Friendly Diagnostic Tool..."
	@echo "Available modes: sanity, regression, surveillance, automation"
	@if [ -z "$$MODE" ]; then \
		echo "Usage: make diagnose MODE=<mode>"; \
		echo "Example: make diagnose MODE=sanity"; \
		exit 1; \
	fi
	python3 scripts/user_friendly_diagnostics.py --mode "$$MODE"

compatibility-monitor:
	@echo "🔍 Starting System Compatibility Monitor..."
	python3 services/system-compatibility-monitor/compatibility_monitor.py

help:
	@echo "AIOps-NAAS Makefile targets:"
	@echo "  up              - Interactive wizard (default)"
	@echo "  up-all          - Start all services"
	@echo "  up-service      - Start single service (set SERVICE=name)"
	@echo "  up-keycloak     - Start with Keycloak SSO"
	@echo "  status          - Show service status"
	@echo "  logs            - View service logs (set SERVICE=name)"
	@echo "  down            - Stop all services"
	@echo "  collect-logs    - Collect logs for all services"
	@echo "  fix             - Run auto-fixes"
	@echo "  creds           - Set credentials interactively"
	@echo "  simulate        - Run data simulation"
	@echo "  debug-incident  - One-click incident data debugging 🔍"
	@echo "  diagnose        - User-friendly diagnostic tool (set MODE=sanity|regression|surveillance|automation) 🩺"
	@echo "  compatibility-monitor - Start system compatibility monitoring 🔍"