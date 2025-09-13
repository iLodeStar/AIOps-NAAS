# AIOps NAAS Diagnostic Tool - User Guide

This guide is written for **non-technical users** who need to validate that the AIOps NAAS system is working correctly. No technical background is required - everything is explained in simple terms.

## What is AIOps NAAS?

AIOps NAAS is a system that monitors your ship's or facility's computer systems and networks. It automatically detects problems, correlates different events, and can even fix some issues automatically. Think of it as a smart assistant that watches over your technology 24/7.

## What Are Diagnostic Tools?

Diagnostic tools are like health check-ups for your computer systems. Just like a doctor runs tests to make sure you're healthy, these tools test your monitoring system to make sure it's working correctly.

## Quick Start

### Prerequisites
Before running diagnostics, make sure:
1. You have access to the server/computer running AIOps NAAS
2. The system is powered on and connected to the network
3. You can open a command line (terminal) interface

### Running Your First Test

1. **Open Terminal/Command Line**
   - On Windows: Press `Win + R`, type `cmd`, press Enter
   - On Mac: Press `Cmd + Space`, type `Terminal`, press Enter  
   - On Linux: Press `Ctrl + Alt + T`

2. **Navigate to the AIOps Directory**
   ```bash
   cd /path/to/AIOps-NAAS
   ```

3. **Run a Quick Health Check**
   ```bash
   python3 scripts/user_friendly_diagnostics.py --mode sanity
   ```

## Diagnostic Modes Explained

### 🚀 Sanity Mode (Recommended for beginners)
**Duration:** 5 minutes  
**What it does:** Sends one normal message and one problem message to test basic system functionality.

```bash
python3 scripts/user_friendly_diagnostics.py --mode sanity
```

**When to use:**
- First time using the system
- After system updates or changes
- Quick daily health checks
- When something seems wrong

**What you'll see:**
- ✅ Green checkmarks = Everything is working
- ⚠️  Yellow warnings = Minor issues, system still works
- ❌ Red X marks = Problems that need attention

### 🔍 Regression Mode (For comprehensive testing)
**Duration:** 15 minutes  
**What it does:** Tests all different types of data and messages your system can handle.

```bash
python3 scripts/user_friendly_diagnostics.py --mode regression
```

**When to use:**
- After major system changes
- Before important voyages or events
- Monthly system validation
- When troubleshooting complex issues

**What gets tested:**
- System logs (normal operations)
- Error messages (when things go wrong)
- Network alerts (connectivity issues)
- Performance alerts (CPU, memory, disk space)
- Security events (unauthorized access attempts)

### 👁️ Surveillance Mode (Watch and learn)
**Duration:** 15 minutes  
**What it does:** Watches your system work with real data without interfering.

```bash
python3 scripts/user_friendly_diagnostics.py --mode surveillance
```

**When to use:**
- To understand normal system behavior
- To establish baseline performance
- When investigating intermittent issues
- To monitor system during specific operations

**What you'll learn:**
- How often incidents occur naturally
- System performance patterns
- Which services are most active
- Normal vs. abnormal behavior

### 🤖 Automation Mode (Full autonomous monitoring)
**Duration:** 1 hour  
**What it does:** Runs the system completely autonomously and provides detailed insights.

```bash
python3 scripts/user_friendly_diagnostics.py --mode automation
```

**When to use:**
- For comprehensive system evaluation
- Before certifying system readiness
- To understand long-term system behavior
- For compliance reporting

**What you'll get:**
- Total number of incidents created
- Expected vs. actual incident counts
- System accuracy metrics
- Performance insights

## Understanding Your Results

### What Do The Colors Mean?

- **🟢 Green (Success)**: Everything is working perfectly
- **🟡 Yellow (Warning)**: Minor issues that don't stop the system from working
- **🔴 Red (Error)**: Serious problems that need immediate attention
- **🔵 Blue (Information)**: Helpful information, not a problem

### Common Result Scenarios

#### ✅ Perfect Results
```
✅ All services are healthy!
✅ Normal message was successfully stored in database
✅ Anomaly message was stored in database
✅ Sanity test PASSED - Your system is working correctly!
```

**What this means:** Your system is working perfectly. It can:
- Receive and store normal operational messages
- Detect and process problem situations
- Create incidents when appropriate
- Store all data correctly

**Next steps:** Your system is ready for operational use.

#### ⚠️  Partial Success
```
⚠️  Only 4/5 services are healthy
✅ Normal message was successfully stored in database
✅ Anomaly message was stored in database
⚠️  Sanity test had some issues - see details above
```

**What this means:** Your system is mostly working, but one service might be having issues.

**Next steps:** 
- Check which service is down
- Try restarting that specific service
- The system can still work, but might have reduced functionality

#### ❌ Problems Detected
```
❌ Docker is not running or not installed
❌ Normal message was not found in database
❌ The anomaly detection pipeline may not be working correctly
```

**What this means:** There are serious issues preventing your system from working correctly.

**Next steps:** 
- Check that all services are started
- Review error messages for specific problems
- Contact technical support if needed

### Understanding Data Flow

Your diagnostic test follows this path:

1. **Test Message Sent** → System receives your test message
2. **Message Processing** → Vector processes and transforms the message
3. **Data Storage** → ClickHouse stores the processed message
4. **Anomaly Detection** → System checks if message indicates a problem
5. **Incident Creation** → If it's a problem, an incident is created
6. **Correlation** → System links related incidents together

Each step must work for the whole system to function correctly.

### What Are Anomalies vs Non-Anomalies?

**Non-Anomaly (Normal) Messages:**
- Regular system status updates
- Successful operations
- Routine maintenance activities
- Normal performance metrics

**Example:** "System startup completed successfully"
**Expected Result:** Message stored, but no incident created

**Anomaly Messages:**
- Error conditions
- Performance problems (high CPU, low disk space)
- Security alerts
- System failures

**Example:** "CRITICAL: CPU usage at 98% - system overloaded"
**Expected Result:** Message stored AND incident created

### Understanding Incident Windows

The system uses "incident windows" to prevent spam:

- **Single Incident Window:** If the same problem happens multiple times within a short period (usually 5-10 minutes), only ONE incident is created
- **Example:** If CPU is high for 30 minutes, you get one incident, not 30 separate incidents
- **Why this matters:** Prevents alert fatigue and focuses on real issues

## Troubleshooting Common Issues

### "Docker is not running"
**Problem:** The container system isn't started  
**Solution:** 
- Run `docker ps` to check
- Start Docker service on your system
- On Linux: `sudo systemctl start docker`

### "Service not responding"
**Problem:** One or more system components are down  
**Solution:**
- Check service status: `docker compose ps`
- Restart specific service: `docker compose restart [service-name]`
- Restart everything: `docker compose restart`

### "Message not found in database"
**Problem:** Data isn't flowing through the system properly  
**Solution:**
- Wait longer (sometimes processing takes time)
- Check Vector logs: `docker compose logs vector`
- Check ClickHouse connectivity: Visit http://localhost:8123/play

### "No incidents created"
**Problem:** Anomaly detection isn't working  
**Solution:**
- Check anomaly detection service logs
- Verify NATS message bus is running
- Confirm Benthos correlation service is active

## Saving and Sharing Results

To save your diagnostic results to a file:

```bash
python3 scripts/user_friendly_diagnostics.py --mode sanity --output my_results.json
```

This creates a detailed report that you can:
- Share with technical support
- Keep for compliance records
- Compare with previous tests
- Use for troubleshooting

## Best Practices

### Daily Operations
- Run sanity mode once per day
- Check that all services show green/healthy status
- Review any warnings and address them promptly

### Weekly Maintenance
- Run regression mode weekly
- Compare results with previous weeks
- Document any changes or issues

### Before Critical Operations
- Run surveillance mode to establish current baseline
- Ensure all systems show healthy status
- Have technical support contacts ready

### Monthly Reviews
- Run automation mode for comprehensive analysis
- Review incident creation patterns
- Update system configurations if needed

## Getting Help

If you encounter issues:

1. **Save your diagnostic output** with `--output results.json`
2. **Note the Session ID** shown at the start of each test
3. **Screenshot any error messages**
4. **Check the system logs** in `/tmp/aiops_diagnostics.log`

Contact technical support with this information for faster resolution.

## Glossary

**AIOps:** Artificial Intelligence for IT Operations - smart monitoring and automation  
**Anomaly:** Something unusual or wrong that needs attention  
**ClickHouse:** Database where all your log messages are stored  
**Correlation:** Linking related events together to understand the bigger picture  
**Docker:** Container system that runs all the software components  
**Incident:** A problem event that needs human attention or action  
**NATS:** Message bus that connects different system components  
**Regression:** Testing to make sure everything still works after changes  
**Syslog:** Standard format for system log messages  
**Vector:** Software that collects and processes log messages  

Remember: These tools are designed to be safe - they won't break your system or interfere with normal operations. When in doubt, start with sanity mode!