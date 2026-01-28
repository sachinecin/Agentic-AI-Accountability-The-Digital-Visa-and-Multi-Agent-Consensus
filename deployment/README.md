# Digital Visa Protocol - Deployment

## Quick Start with Docker Compose

### Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- 4GB RAM minimum
- 10GB disk space

### Running the Full Stack

```bash
# From the deployment/docker directory
cd deployment/docker

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Check service status
docker-compose ps

# Stop all services
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

### Service Endpoints

Once running, the following services will be available:

- **PDP (Policy Decision Point)**: http://localhost:8080
- **PEP (Policy Enforcement Point)**: http://localhost:8081
- **Agent Registry**: http://localhost:8082
- **Trace Store**: http://localhost:8083
- **Consensus Engine**: http://localhost:8084
- **Billing Service (Example)**: http://localhost:5001
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379

### Health Checks

Check if all services are healthy:

```bash
curl http://localhost:8080/health  # PDP
curl http://localhost:8081/health  # PEP
curl http://localhost:8082/health  # Agent Registry
curl http://localhost:8083/health  # Trace Store
curl http://localhost:8084/health  # Consensus Engine
curl http://localhost:5001/health  # Billing Service
```

## Kubernetes Deployment

### Prerequisites

- Kubernetes 1.24+
- kubectl configured
- Helm 3.0+ (optional)

### Deploy to Kubernetes

```bash
# From the deployment/kubernetes directory
cd deployment/kubernetes

# Create namespace
kubectl create namespace digital-visa

# Deploy all components
kubectl apply -f configmap.yaml
kubectl apply -f secrets.yaml
kubectl apply -f pdp-deployment.yaml
kubectl apply -f pep-deployment.yaml
kubectl apply -f registry-deployment.yaml
kubectl apply -f trace-store-deployment.yaml
kubectl apply -f consensus-deployment.yaml

# Check deployment status
kubectl get pods -n digital-visa
kubectl get services -n digital-visa

# View logs
kubectl logs -f deployment/pdp-service -n digital-visa
```

### Access Services

```bash
# Port forward to access services locally
kubectl port-forward service/pdp-service 8080:8080 -n digital-visa
kubectl port-forward service/pep-service 8081:8081 -n digital-visa
```

## Production Considerations

### Security

1. **Key Management**
   - Use HSM or cloud KMS for signing keys
   - Rotate keys every 90 days
   - Store keys encrypted at rest

2. **Network Security**
   - Enable mTLS between all services
   - Use network policies to restrict traffic
   - Deploy behind API gateway with rate limiting

3. **Secrets Management**
   - Use Kubernetes secrets or Vault
   - Never commit secrets to git
   - Rotate database credentials regularly

### High Availability

1. **Service Replication**
   - Run at least 3 replicas of each service
   - Use pod anti-affinity for distribution
   - Configure horizontal pod autoscaling

2. **Database**
   - Use PostgreSQL with streaming replication
   - Configure automated backups
   - Set up point-in-time recovery

3. **Load Balancing**
   - Deploy behind load balancer
   - Configure health checks
   - Set up circuit breakers

### Monitoring

1. **Metrics**
   - Prometheus for metrics collection
   - Grafana for visualization
   - Alert on key SLIs

2. **Logging**
   - Centralized logging (ELK/EFK)
   - Structured JSON logs
   - Log retention policies

3. **Tracing**
   - Distributed tracing with Jaeger
   - OpenTelemetry instrumentation
   - Trace sampling configuration

### Scaling

**Horizontal Scaling Targets:**
- PDP: Auto-scale on CPU > 70%
- PEP: Auto-scale on requests/sec > 1000
- Consensus Engine: Fixed 3 replicas
- Trace Store: Auto-scale on memory > 80%

**Resource Requests/Limits:**
```yaml
resources:
  requests:
    memory: "512Mi"
    cpu: "250m"
  limits:
    memory: "1Gi"
    cpu: "500m"
```

## Configuration

### Environment Variables

**Common:**
- `LOG_LEVEL`: DEBUG, INFO, WARNING, ERROR (default: INFO)
- `SERVICE_NAME`: Service identifier
- `METRICS_PORT`: Prometheus metrics port (default: 9090)

**PDP:**
- `POLICY_REFRESH_INTERVAL`: Seconds between policy reloads (default: 60)
- `JWT_SIGNING_KEY_PATH`: Path to RSA private key
- `TOKEN_TTL_SECONDS`: Default token TTL (default: 60)

**PEP:**
- `PDP_URL`: Policy Decision Point endpoint
- `VERIFY_REASONING_HASH`: Enable hash verification (default: true)
- `REPLAY_PROTECTION_TTL`: Transaction cache TTL (default: 300)

**Consensus Engine:**
- `DEFAULT_THRESHOLD`: Default consensus ratio (default: 0.67)
- `MAX_TIMEOUT_SECONDS`: Maximum consensus timeout (default: 60)

### Database Configuration

**PostgreSQL:**
```yaml
DATABASE_URL: postgresql://user:pass@host:5432/digital_visa
CONNECTION_POOL_SIZE: 20
MAX_OVERFLOW: 10
```

**Redis:**
```yaml
REDIS_URL: redis://host:6379/0
REDIS_MAX_CONNECTIONS: 50
```

## Troubleshooting

### Common Issues

**Service won't start:**
```bash
# Check logs
docker-compose logs service-name

# Check for port conflicts
netstat -tuln | grep 8080

# Verify environment variables
docker-compose config
```

**Token verification fails:**
```bash
# Check PEP can reach PDP
docker-compose exec pep-service curl http://pdp-service:8080/health

# Verify JWT signing keys match
docker-compose exec pdp-service cat /keys/private.pem
docker-compose exec pep-service cat /keys/public.pem
```

**Database connection issues:**
```bash
# Check PostgreSQL is running
docker-compose ps postgres

# Test connection
docker-compose exec postgres psql -U digital_visa_user -d digital_visa -c "SELECT 1;"
```

### Debug Mode

Enable debug logging:
```bash
docker-compose up -d
docker-compose exec pdp-service export LOG_LEVEL=DEBUG
docker-compose restart pdp-service
```

## Backup and Recovery

### Database Backup

```bash
# Backup PostgreSQL
docker-compose exec postgres pg_dump -U digital_visa_user digital_visa > backup.sql

# Restore
docker-compose exec -T postgres psql -U digital_visa_user digital_visa < backup.sql
```

### Configuration Backup

```bash
# Export agent registry
curl http://localhost:8082/api/v1/export > agent-registry-backup.json

# Import
curl -X POST http://localhost:8082/api/v1/import -d @agent-registry-backup.json
```

## Performance Tuning

### Optimization Tips

1. **Database**
   - Add indexes on frequently queried columns
   - Configure connection pooling
   - Enable query caching

2. **Caching**
   - Cache policy decisions for identical requests
   - Use Redis for transaction tracking
   - Set appropriate TTLs

3. **Network**
   - Enable HTTP/2
   - Use connection keep-alive
   - Configure request timeouts

4. **Resource Limits**
   - Right-size container resources
   - Monitor memory usage
   - Adjust based on load testing
