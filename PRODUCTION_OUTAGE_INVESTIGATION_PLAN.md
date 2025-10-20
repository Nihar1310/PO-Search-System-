# Production Service Outage Investigation Plan

## Overview
This document provides a systematic approach to diagnosing and resolving production backend service outages. Follow this plan sequentially to minimize downtime and identify root causes efficiently.

---

## Phase 1: Initial Information Gathering (5-10 minutes)

### Critical Questions to Ask

Before beginning technical investigation, gather context:

1. **Stack Information**
   - What is the technology stack? (Language, framework, runtime version)
   - What are the service dependencies? (Databases, caches, message queues, external APIs)
   - What is the deployment architecture? (Containers, VMs, serverless, orchestration platform)

2. **Recent Changes**
   - When did the issue start? (Exact timestamp if available)
   - Were there any deployments in the last 24-48 hours?
   - Were there any configuration changes (environment variables, feature flags)?
   - Were there any infrastructure changes (scaling, migrations, network updates)?

3. **Traffic Patterns**
   - What is the current traffic volume vs. normal baseline?
   - Are there any traffic spikes or anomalies?
   - Which endpoints/operations are affected (all or specific ones)?
   - What is the geographic distribution of affected users?

4. **Error Symptoms**
   - What are users experiencing? (Timeouts, 5xx errors, 4xx errors, slow responses)
   - What error messages appear in logs?
   - What is the error rate percentage?
   - Are there any patterns (intermittent, consistent, progressive degradation)?

---

## Phase 2: Hypothesis Formation (5-7 Possible Root Causes)

Based on common production issues, consider these potential sources:

### 1. **Resource Exhaustion**
- CPU, memory, or disk space maxed out
- Connection pool exhaustion
- File descriptor limits reached

### 2. **Database Issues**
- Database connection failures
- Long-running queries blocking operations
- Database replication lag
- Database server down or unreachable

### 3. **Dependency Failures**
- External API timeouts or errors
- Cache server (Redis/Memcached) unavailable
- Message queue backlog or failure
- DNS resolution failures

### 4. **Network/Infrastructure Problems**
- Load balancer misconfiguration or failure
- Network partitioning or routing issues
- SSL/TLS certificate expiration
- Firewall rules blocking traffic

### 5. **Code/Deployment Issues**
- Bugs introduced in recent deployment
- Memory leaks or resource leaks
- Unhandled exceptions crashing the service
- Configuration errors in new release

### 6. **Traffic Anomalies**
- DDoS attack or traffic spike
- Specific client overwhelming the system
- Retry storms from clients

### 7. **Cascading Failures**
- Circuit breakers triggered incorrectly
- Upstream service failures propagating
- Health check endpoints failing causing load balancer to mark instances unhealthy

---

## Phase 3: Narrowing Down to Most Likely Causes (1-2)

### Priority 1: Application Layer Issues
**Most common in production outages (60-70% of cases)**

**Rationale:** Recent deployments, code bugs, or configuration errors are the most frequent causes when a service "stops responding." Look for:
- Recent changes in last 24-48 hours
- Error patterns in application logs
- Process crashes or restarts

### Priority 2: Resource Exhaustion
**Second most common (20-30% of cases)**

**Rationale:** Services that were working fine suddenly stop due to gradual resource depletion (memory leaks, disk filling up, connection pools exhausted).

---

## Phase 4: Sequential Investigation Steps

### Step 1: Verify Service Status and Basic Health

#### Commands:
```bash
# Check if service process is running
ps aux | grep <service_name>
systemctl status <service_name>  # For systemd services
docker ps | grep <container_name>  # For containerized services
kubectl get pods -n <namespace>  # For Kubernetes

# Check service uptime
uptime

# Check recent system reboots
last reboot | head -5
```

#### Expected Signals:
- ✅ **PASS:** Process is running, uptime is recent, no crashes
- ❌ **FAIL:** Process not found, frequent restarts, or recent system reboot → Investigate crash logs

---

### Step 2: Check Application Logs

#### Commands:
```bash
# Application logs (adjust paths based on your setup)
tail -n 500 /var/log/<app>/application.log
journalctl -u <service_name> --since "1 hour ago" --no-pager | tail -100

# Docker container logs
docker logs --tail=500 <container_name>

# Kubernetes pod logs
kubectl logs -n <namespace> <pod_name> --tail=500

# Search for errors
grep -i "error\|exception\|fatal\|panic\|failed" /var/log/<app>/application.log | tail -50

# Check for out of memory errors
dmesg | grep -i "out of memory\|oom\|killed process"
```

#### Expected Signals:
- ✅ **PASS:** Normal log entries, no error spikes
- ❌ **FAIL:** Frequent errors, stack traces, OOM kills → Application-level issue confirmed

**Validation Question:** Are there any ERROR, EXCEPTION, or FATAL log entries? If yes, what are the stack traces showing?

---

### Step 3: Verify Resource Availability

#### Commands:
```bash
# CPU usage
top -bn1 | head -20
mpstat 1 5  # 5 samples, 1 second apart

# Memory usage
free -h
vmstat 1 5

# Disk usage
df -h
du -sh /var/log/* | sort -h | tail -10  # Check log sizes

# I/O wait
iostat -x 1 5

# Network connections and states
netstat -an | grep ESTABLISHED | wc -l  # Active connections
ss -s  # Socket statistics
netstat -tunlp | grep <port>  # Check if service is listening

# File descriptors
lsof | wc -l  # Total open file descriptors
lsof -p <pid> | wc -l  # FDs for specific process
ulimit -n  # FD limit

# Process-specific resource usage
top -p <pid>
ps -p <pid> -o %cpu,%mem,vsz,rss,cmd
```

#### Expected Signals:
- ✅ **PASS:** CPU < 80%, Memory available > 20%, Disk < 90%, I/O wait < 30%
- ❌ **FAIL:** Any resource > threshold → Resource exhaustion confirmed

**Validation Question:** Are CPU, memory, or disk resources critically low? Is I/O wait high?

---

### Step 4: Test Service Connectivity

#### Commands:
```bash
# Local connectivity test
curl -v http://localhost:<port>/health
curl -v -m 5 http://localhost:<port>/api/endpoint  # 5 second timeout

# Check if port is listening
netstat -tulnp | grep <port>
ss -tulnp | grep <port>

# Test from external perspective
curl -v http://<public_ip>:<port>/health
wget --timeout=5 --tries=1 http://<public_ip>:<port>/health

# DNS resolution
nslookup <service_domain>
dig <service_domain>

# Network path trace
traceroute <service_domain>
mtr -r -c 10 <service_domain>  # Better than traceroute
```

#### Expected Signals:
- ✅ **PASS:** Service responds to localhost, port is listening
- ❌ **FAIL:** Connection refused, timeout → Network or binding issue

**Validation Question:** Does the service respond to localhost requests? Can external requests reach it?

---

### Step 5: Database Layer Verification

#### Commands:
```bash
# Test database connectivity
# PostgreSQL
psql -h <host> -U <user> -d <database> -c "SELECT 1;"

# MySQL (password will be prompted interactively for security)
mysql -h <host> -u <user> -p -e "SELECT 1;"
# Alternative secure methods:
# 1. Use mysql_config_editor for encrypted login paths: mysql_config_editor set --login-path=prod --host=<host> --user=<user> --password
#    Then connect with: mysql --login-path=prod -e "SELECT 1;"
# 2. Store credentials in ~/.my.cnf with restricted permissions (chmod 600)
# Note: Using MYSQL_PWD environment variable or inline passwords (-p<password>) is discouraged in production

# Check database server status
systemctl status postgresql  # or mysql, mariadb
docker ps | grep postgres  # For containerized DB

# Check active connections
# PostgreSQL
psql -h <host> -U <user> -d <database> -c "SELECT count(*) FROM pg_stat_activity;"
psql -h <host> -U <user> -d <database> -c "SELECT * FROM pg_stat_activity WHERE state = 'active';"

# MySQL (password will be prompted interactively for security)
mysql -h <host> -u <user> -p -e "SHOW PROCESSLIST;"
# For non-interactive environments, export MYSQL_PWD='<password>' in a secure session before running:
# export MYSQL_PWD='<password>' && mysql -h <host> -u <user> -e "SHOW PROCESSLIST;" && unset MYSQL_PWD
# Or use mysql_config_editor for encrypted credentials (recommended for production)

# Check for long-running queries
# PostgreSQL
psql -h <host> -U <user> -d <database> -c "SELECT pid, now() - pg_stat_activity.query_start AS duration, query FROM pg_stat_activity WHERE state = 'active' AND now() - pg_stat_activity.query_start > interval '30 seconds' ORDER BY duration DESC;"

# Check for locks
# PostgreSQL
psql -h <host> -U <user> -d <database> -c "SELECT * FROM pg_locks WHERE NOT granted;"

# Check replication lag
# PostgreSQL
psql -h <replica_host> -U <user> -d <database> -c "SELECT EXTRACT(EPOCH FROM (now() - pg_last_xact_replay_timestamp())) AS lag_seconds;"
```

#### Expected Signals:
- ✅ **PASS:** Database responds, connections < max_connections, no long-running queries
- ❌ **FAIL:** Connection failures, connection pool exhausted, query timeouts → Database issue

**Validation Question:** Can the application connect to the database? Are there any blocking queries?

---

### Step 6: Dependency Health Checks

#### Commands:
```bash
# Cache services (Redis example)
redis-cli ping
redis-cli info stats
redis-cli --stat  # Real-time stats

# Message queues (RabbitMQ example)
rabbitmqctl status
rabbitmqctl list_queues

# External API health (adjust URL)
curl -v -m 10 https://api.external-service.com/health

# Check DNS resolution for dependencies
dig api.external-service.com
nslookup cache.internal.com

# Network connectivity to dependencies
telnet <dependency_host> <port>
nc -zv <dependency_host> <port>  # Better than telnet

# SSL certificate validation
echo | openssl s_client -connect <host>:443 -servername <host> 2>/dev/null | openssl x509 -noout -dates
```

#### Expected Signals:
- ✅ **PASS:** All dependencies respond within acceptable timeouts
- ❌ **FAIL:** Timeouts, connection failures, certificate issues → Dependency failure

**Validation Question:** Are all external dependencies (cache, message queue, APIs) healthy and responding?

---

### Step 7: Load Balancer and Proxy Verification

#### Commands:
```bash
# NGINX logs and status
tail -f /var/log/nginx/error.log
tail -f /var/log/nginx/access.log
nginx -t  # Test configuration
systemctl status nginx

# HAProxy status
echo "show stat" | socat stdio /var/run/haproxy.sock
tail -f /var/log/haproxy.log

# Check backend health from load balancer
curl http://localhost:<admin_port>/health  # Load balancer health endpoint

# AWS ELB/ALB (if using AWS CLI)
aws elbv2 describe-target-health --target-group-arn <arn>

# Check for SSL issues
openssl s_client -connect <domain>:443 -servername <domain>
```

#### Expected Signals:
- ✅ **PASS:** Load balancer healthy, backends marked as healthy
- ❌ **FAIL:** Backends marked unhealthy, configuration errors → LB issue

---

### Step 8: Configuration Validation

#### Commands:
```bash
# Check environment variables
env | grep -i <app_prefix>
cat /proc/<pid>/environ | tr '\0' '\n'  # For running process

# Compare configuration with last known good state
diff <(cat current-config.yml) <(cat previous-config.yml)

# Verify configuration file syntax
python -m json.tool config.json  # For JSON
yamllint config.yml  # For YAML

# Check for recent configuration changes
git log --since="2 days ago" -- config/

# Feature flags (if using a feature flag system)
curl http://feature-flag-service/api/flags
```

#### Expected Signals:
- ✅ **PASS:** Configuration matches expected values, no syntax errors
- ❌ **FAIL:** Configuration mismatches, missing values → Config issue

---

### Step 9: Metrics and Monitoring Analysis

#### Commands:
```bash
# System metrics (if using Prometheus)
curl http://localhost:9090/api/v1/query?query=up{job="<service>"}

# Application metrics
curl http://localhost:<metrics_port>/metrics

# Key metrics to check:
# - Request rate: rate(http_requests_total[5m])
# - Error rate: rate(http_requests_total{status=~"5.."}[5m])
# - Latency: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))
# - Active connections: http_connections_active
# - Database connection pool: db_connections{state="active"}

# CloudWatch metrics (AWS)
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApplicationELB \
  --metric-name TargetResponseTime \
  --dimensions Name=LoadBalancer,Value=<lb_name> \
  --statistics Average \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300
```

#### Expected Signals:
- ✅ **PASS:** Metrics within normal ranges, no anomalies
- ❌ **FAIL:** Spike in errors, latency, or unusual patterns → Confirms issue scope

---

### Step 10: Recent Deployment Verification

#### Commands:
```bash
# Check deployment history
git log --oneline --since="2 days ago"
git diff HEAD~1 HEAD  # Compare with previous commit

# Docker image verification
docker images | grep <service>
docker inspect <image_id> | grep -i "created\|version"

# Kubernetes deployment history
kubectl rollout history deployment/<deployment_name> -n <namespace>
kubectl describe deployment/<deployment_name> -n <namespace>

# Check for any feature flags that were toggled recently
curl http://feature-service/api/recent-changes
```

#### Expected Signals:
- ✅ **PASS:** No recent deployments or changes
- ❌ **FAIL:** Recent deployment coincides with outage start → Deployment issue highly likely

---

## Phase 5: Diagnostic Logging Enhancement

If the root cause is still unclear, add temporary logging:

### Application Layer Logging:
```bash
# Increase log level (method depends on framework)
# Example for environment variable
export LOG_LEVEL=DEBUG
systemctl restart <service>

# Add request tracing
# Example headers to log: X-Request-ID, User-Agent, Client-IP
```

### Database Query Logging:
```bash
# PostgreSQL - Enable slow query logging
ALTER SYSTEM SET log_min_duration_statement = 1000;  # Log queries > 1s
SELECT pg_reload_conf();

# MySQL - Enable slow query log
SET GLOBAL slow_query_log = 'ON';
SET GLOBAL long_query_time = 1;
```

### Network Traffic Analysis:
```bash
# Capture traffic for analysis
tcpdump -i any -w /tmp/capture.pcap port <service_port>
tcpdump -i any -nn -A port <service_port> | tee /tmp/traffic.log

# Analyze captured traffic
tcpdump -r /tmp/capture.pcap -nn
```

**⚠️ SECURITY WARNING - Packet Capture Best Practices:**
- **Apply strict capture filters:** Limit by specific ports, IPs, and protocols to minimize sensitive data collection (e.g., `tcpdump -i any 'port 80 and host 10.0.1.5'`)
- **Avoid full payload capture when possible:** Use `-s 96` to capture only headers, not full packet contents
- **Secure storage:** Store capture files in a secure location with restricted permissions (`chmod 600 /tmp/capture.pcap`)
- **Encrypt at rest:** Consider encrypting capture files, especially if they contain authentication tokens or PII
- **Limit access:** Only grant access to named investigators; maintain an access log
- **Retention policy:** Define and enforce a retention period (e.g., 7 days); securely delete captures after analysis
- **Secure deletion:** Use `shred -vfz -n 3 /tmp/capture.pcap` instead of `rm` to overwrite data
- **Redaction before sharing:** Use approved tooling to redact sensitive data before sharing captures with third parties

---

## Phase 6: Immediate Mitigation Actions (While Investigating)

### Priority-Based Mitigation Strategy:

#### 1. **If Application Layer Issue (Code Bug/Config)**
```bash
# Rollback to last known good version
# Docker
docker pull <image>:<previous_tag>
docker stop <container_name>
docker run -d --name <container_name> <image>:<previous_tag>

# Kubernetes
kubectl rollout undo deployment/<deployment_name> -n <namespace>
kubectl rollout status deployment/<deployment_name> -n <namespace>

# Git-based deployment
git checkout <previous_commit>
./deploy.sh
```

#### 2. **If Resource Exhaustion**
```bash
# Horizontal scaling (add more instances)
# Kubernetes
kubectl scale deployment/<deployment_name> --replicas=<new_count> -n <namespace>

# AWS Auto Scaling
aws autoscaling set-desired-capacity \
  --auto-scaling-group-name <asg_name> \
  --desired-capacity <new_count>

# Vertical scaling (increase resources)
# Restart with more memory (Docker)
docker stop <container>
docker run -d --name <container> -m 4g <image>

# Clear caches if memory exhaustion
redis-cli FLUSHALL  # Use with caution
```

#### 3. **If Database Issues**
```bash
# Kill long-running queries (use targeted, coordinated approach)
# PostgreSQL - STEP 1: Identify candidate sessions for termination
# Query to find problematic sessions (customize filters for your use case):
SELECT pid, usename, datname, application_name, state, query_start, now() - query_start AS duration, query
FROM pg_stat_activity
WHERE state = 'active'
  AND query_start < now() - interval '5 minutes'
  AND datname = '<target_database>'  -- Filter by database
  AND usename = '<target_user>'      -- Filter by user (optional)
  AND application_name LIKE '%<pattern>%'  -- Filter by application (optional)
  AND query NOT LIKE '%pg_stat_activity%'  -- Exclude monitoring queries
ORDER BY duration DESC;

# STEP 2: Attempt graceful cancellation first (allows transactions to rollback cleanly)
SELECT pg_cancel_backend(pid) FROM pg_stat_activity WHERE pid IN (<pid1>, <pid2>, ...);
-- Wait 10-30 seconds and re-check if queries have stopped

# STEP 3: Only if graceful cancellation fails, terminate forcefully (kills connection immediately)
-- ⚠️ CONFIRM WITH STAKEHOLDERS BEFORE EXECUTING
SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE pid IN (<pid1>, <pid2>, ...);

# CHECKLIST before terminating:
# [ ] Validated PIDs belong to the problematic queries (not critical batch jobs)
# [ ] Notified application owners/operations team
# [ ] Documented filters used (database, user, application_name, query pattern)
# [ ] Recorded terminated PIDs and reasons in incident log
# [ ] Tested in staging environment if time permits

# Add read replicas for read-heavy workloads
# (Depends on cloud provider or setup)

# Connection pool tuning
# Temporarily increase max_connections (PostgreSQL)
ALTER SYSTEM SET max_connections = 500;
SELECT pg_reload_conf();
```

#### 4. **If Dependency Failure**
```bash
# Enable circuit breakers in application
# Update configuration to skip non-critical dependencies

# Add fallback/cached responses
# Modify code to return cached data when dependency fails

# Increase timeouts temporarily (if dependency is slow)
# Update application timeout configuration
```

#### 5. **If Traffic Spike/DDoS**
```bash
# Enable rate limiting at load balancer
# NGINX example:
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;

# Block specific IPs - REQUIRES VALIDATION AND SAFEGUARDS
# ⚠️ WARNING: Blocking IPs without proper validation can disrupt legitimate traffic from CDNs, proxies, or entire user segments

# VALIDATION CHECKLIST (complete BEFORE blocking):
# [ ] Checked request logs to confirm malicious activity from this IP
# [ ] Verified geolocation and ASN (Autonomous System Number) of the IP
# [ ] Performed reverse DNS lookup: `dig -x <malicious_ip>`
# [ ] Cross-referenced against known CDN/proxy/hosting provider IP ranges (CloudFlare, AWS, Akamai, etc.)
# [ ] Checked internal whitelist for legitimate infrastructure IPs
# [ ] Confirmed with security team or senior engineer
# [ ] Documented justification and approval in incident log

# RECOMMENDED: Use time-limited blocking with fail2ban or custom scripts
# fail2ban automatically removes blocks after a timeout:
# fail2ban-client set <jail_name> banip <malicious_ip>

# TEMPORARY BLOCK (manual, with timestamp for removal):
iptables -A INPUT -s <malicious_ip> -j DROP -m comment --comment "Blocked $(date +%Y-%m-%d_%H:%M) - Ticket #1234 - Approved by: <name>"
# Document removal time and set reminder to review

# TEST IN STAGING FIRST (if possible):
# Apply the rule in a test environment to verify no collateral impact

# MONITORING & ROLLBACK:
# Monitor for collateral impact on legitimate users:
# - Watch error rates, successful auth attempts, traffic patterns
# - Set alerts for sudden drops in legitimate traffic
# If legitimate traffic is blocked, immediately remove the rule:
iptables -D INPUT -s <malicious_ip> -j DROP

# AUDIT LOGGING:
# Log all block actions with justification:
echo "$(date +%Y-%m-%d_%H:%M:%S) - Blocked IP: <malicious_ip> - Reason: <reason> - Approved by: <name> - Ticket: #1234" >> /var/log/ip_blocks.log

# Enable CloudFlare DDoS protection (if using)
# Or enable AWS Shield, etc.

# Scale up urgently
kubectl scale deployment/<deployment_name> --replicas=20 -n <namespace>
```

---

## Phase 7: Root Cause Confirmation Checklist

Before declaring root cause found, confirm:

- [ ] Can you reproduce the issue in a test environment?
- [ ] Does the timeline match (issue appeared after the suspected change)?
- [ ] Do the logs/metrics confirm the hypothesis?
- [ ] Does the fix resolve the issue completely?
- [ ] Are there any other lingering symptoms?

---

## Phase 8: Communication Protocol

### Initial Communication (Within 5 minutes of outage detection)

**To:** Engineering team, On-call manager, Product/Business stakeholders

**Subject:** [URGENT] Production Service Outage - <Service Name>

**Template:**
```
INCIDENT REPORT - INITIAL

Status: INVESTIGATING
Severity: P1/P2/P3
Start Time: [YYYY-MM-DD HH:MM UTC]
Impact: [% of users affected / specific features down]

Current Symptoms:
- [Describe what users are experiencing]
- [Error rates, timeout percentages]

Actions Taken:
- [List immediate actions]

Next Steps:
- [What's being investigated next]

ETA for Update: [15-30 minutes]

Incident Commander: [Name]
```

### Status Updates (Every 15-30 minutes)

**Template:**
```
INCIDENT UPDATE #[N]

Status: INVESTIGATING / MITIGATING / RESOLVED
Time: [YYYY-MM-DD HH:MM UTC]

Progress:
- [What was discovered]
- [What was tried]
- [Current hypothesis]

Current Impact:
- [Updated metrics]

Next Steps:
- [Next 1-2 actions]

ETA for Next Update: [Time]
```

### Resolution Communication

**Template:**
```
INCIDENT RESOLVED

Status: RESOLVED
Resolution Time: [YYYY-MM-DD HH:MM UTC]
Total Duration: [HH:MM]

Root Cause:
[Detailed explanation of what caused the outage]

Timeline:
- [HH:MM] Issue detected
- [HH:MM] Investigation started
- [HH:MM] Root cause identified
- [HH:MM] Mitigation applied
- [HH:MM] Service restored

Impact Summary:
- [Number/percentage of affected users]
- [Duration of impact]
- [Business metrics affected]

Resolution:
[What was done to fix it]

Prevention Measures:
- [Immediate action 1]
- [Immediate action 2]
- [Follow-up actions]

Post-Incident Review Scheduled:
[Date and time for postmortem]
```

---

## Phase 9: Post-Resolution Actions

### Immediate (Within 1 hour):
1. Verify all systems are fully operational
2. Monitor for any regression or recurring issues
3. Document all findings in incident log
4. Remove any temporary fixes/workarounds

### Short-term (Within 24 hours):
1. Schedule post-mortem meeting
2. Create tickets for identified improvements
3. Update runbooks based on learnings
4. Share incident report with stakeholders

### Post-Mortem Agenda:
- Timeline reconstruction
- Root cause analysis (5 Whys)
- What went well / What didn't
- Action items to prevent recurrence
- Monitoring/alerting improvements needed
- Documentation updates required

---

## Quick Reference: Command Cheat Sheet

```bash
# Service Status
systemctl status <service>
ps aux | grep <service>

# Logs (last 100 lines)
journalctl -u <service> -n 100
docker logs --tail=100 <container>
kubectl logs <pod> --tail=100

# Resource Check
free -h && df -h && top -bn1 | head -20

# Network Test
curl -v http://localhost:<port>/health
netstat -tunlp | grep <port>

# Database Quick Check
psql -h <host> -U <user> -d <db> -c "SELECT 1;"

# Process Restart
systemctl restart <service>
docker restart <container>
kubectl rollout restart deployment/<name>
```

---

## Appendix: Tool Installation (If Missing)

```bash
# Essential debugging tools
sudo apt-get update
sudo apt-get install -y \
  curl wget \
  net-tools iproute2 \
  tcpdump nmap netcat \
  htop iotop iftop \
  sysstat dstat \
  strace lsof \
  jq \
  postgresql-client mysql-client redis-tools

# For RHEL/CentOS
sudo yum install -y \
  curl wget \
  net-tools iproute \
  tcpdump nmap nmap-ncat \
  htop iotop iftop \
  sysstat dstat \
  strace lsof \
  jq \
  postgresql mysql redis
```

---

## Summary

This investigation plan provides a systematic approach to diagnosing production outages:

1. **Gather Context First** - Understand the stack, recent changes, and symptoms
2. **Form Hypotheses** - Consider 5-7 possibilities, narrow to 1-2 most likely
3. **Investigate Systematically** - Follow layers: Infrastructure → Application → Database → Dependencies
4. **Validate Each Step** - Use specific commands and look for expected signals
5. **Mitigate Immediately** - Apply fixes while investigating if possible
6. **Communicate Continuously** - Keep stakeholders informed every 15-30 minutes
7. **Document and Learn** - Post-mortem to prevent future occurrences

**Key Success Factors:**
- Follow the plan sequentially but be ready to adapt
- Always confirm assumptions with data (logs, metrics, commands)
- Mitigate impact while investigating (don't wait for perfect understanding)
- Communicate proactively and frequently
- Document everything for future reference and learning