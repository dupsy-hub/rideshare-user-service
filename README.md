# RideShare User Management Service

FastAPI-based microservice for handling user registration, authentication, and profile management in the RideShare Pro platform.

## 🚀 Features

- **User Registration & Authentication**: JWT-based secure authentication
- **Profile Management**: User profiles with driver-specific details
- **Session Management**: Redis-based session storage
- **Security**: Password hashing, token validation, rate limiting
- **Health Checks**: Kubernetes-ready liveness and readiness probes
- **Structured Logging**: JSON-formatted logs with correlation IDs
- **Production Ready**: Multi-stage Docker build, non-root user, health checks

## 📋 API Endpoints

### Authentication

- `POST /api/users/register` - Register new user
- `POST /api/users/login` - User login
- `POST /api/users/logout` - User logout
- `POST /api/users/verify-token` - Verify JWT token

### User Management

- `GET /api/users/profile` - Get user profile
- `PUT /api/users/profile` - Update user profile
- `POST /api/users/driver-details` - Add driver details (drivers only)
- `GET /api/users/driver-details` - Get driver details

### Health Checks

- `GET /api/users/health` - Service health check
- `GET /api/users/ready` - Readiness check
- `GET /api/users/metrics` - Basic metrics

### Documentation

- `GET /api/users/docs` - Swagger UI
- `GET /api/users/redoc` - ReDoc documentation

## 🛠️ Setup & Development

### Prerequisites

- Python 3.11+
- PostgreSQL 13+
- Redis 6+
- Docker (optional)

### Local Development

1. **Clone the repository**

```bash
git clone <repository-url>
cd rideshare-user-service
```

2. **Create virtual environment**

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**

```bash
pip install -r requirements.txt
```

4. **Set up environment variables**

```bash
cp .env.example .env
# Edit .env with your database and Redis configurations
```

5. **Set up database**

```bash
# Create PostgreSQL database
createdb rideshare_db

# The application will create tables automatically on startup
```

6. **Run the service**

```bash
# Development mode with auto-reload
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Or run directly
python src/main.py
```

7. **Access the service**

- API Documentation: http://localhost:8000/api/users/docs
- Health Check: http://localhost:8000/api/users/health

### Docker Development

1. **Build the image**

```bash
docker build -t rideshare-user-service .
```

2. **Run with Docker Compose**

```bash
# Create docker-compose.yml with PostgreSQL and Redis
docker-compose up -d
```

## 🔧 Configuration

### Environment Variables

| Variable              | Description                  | Default  |
| --------------------- | ---------------------------- | -------- |
| `DEBUG`               | Enable debug mode            | `false`  |
| `DATABASE_URL`        | PostgreSQL connection string | Required |
| `REDIS_URL`           | Redis connection string      | Required |
| `JWT_SECRET_KEY`      | JWT signing secret           | Required |
| `JWT_EXPIRE_HOURS`    | Token expiration time        | `24`     |
| `BCRYPT_ROUNDS`       | Password hashing rounds      | `12`     |
| `RATE_LIMIT_REQUESTS` | Requests per minute limit    | `100`    |

### Database Schema

The service automatically creates these tables:

- `users` - Basic user information
- `user_profiles` - Extended user profiles
- `driver_details` - Driver-specific information

## 🧪 Testing

### Run Tests

```bash
# Unit tests
pytest tests/unit/ -v

# Integration tests
pytest tests/integration/ -v

# All tests with coverage
pytest tests/ --cov=src --cov-report=html
```

### API Testing

```bash
# Register a new user
curl -X POST "http://localhost:8000/api/users/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "SecurePass123!",
    "first_name": "John",
    "last_name": "Doe",
    "phone": "+1234567890",
    "role": "rider"
  }'

# Login
curl -X POST "http://localhost:8000/api/users/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "SecurePass123!"
  }'
```

## 🔒 Security

### Password Requirements

- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one digit
- At least one special character

### JWT Tokens

- 24-hour expiration by default
- Stored in Redis for session management
- Blacklisted on logout

### Security Headers

- X-Content-Type-Options: nosniff
- X-Frame-Options: DENY
- X-XSS-Protection: 1; mode=block
- Strict-Transport-Security: max-age=31536000

## 📊 Monitoring

### Health Checks

- **Liveness**: `/api/users/health` - Basic service health
- **Readiness**: `/api/users/ready` - Dependency health + resource checks

### Logs

Structured JSON logs with correlation IDs for request tracing:

```json
{
  "timestamp": "2025-01-01T12:00:00Z",
  "level": "info",
  "service": "user-management",
  "correlation_id": "uuid",
  "user_id": "uuid",
  "endpoint": "POST /api/users/login",
  "duration_ms": 120,
  "status_code": 200
}
```

### Metrics

Basic metrics available at `/api/users/metrics`:

- Memory usage
- Disk usage
- Service uptime

## 🚀 Deployment

### Kubernetes Deployment

1. **Build and push Docker image**

```bash
# Build image
docker build -t your-registry/rideshare-user-service:v1.0 .

# Push to registry
docker push your-registry/rideshare-user-service:v1.0
```

2. **Deploy to Kubernetes**

```bash
# Apply manifests
kubectl apply -f k8s/
```

### Environment Configuration

For Kubernetes deployment, use ConfigMaps and Secrets:

```yaml
# ConfigMap for non-sensitive config
apiVersion: v1
kind: ConfigMap
metadata:
  name: user-service-config
data:
  DEBUG: "false"
  JWT_EXPIRE_HOURS: "24"
  RATE_LIMIT_REQUESTS: "100"

---
# Secret for sensitive data
apiVersion: v1
kind: Secret
metadata:
  name: user-service-secrets
type: Opaque
stringData:
  DATABASE_URL: "postgresql+asyncpg://user:pass@postgres:5432/rideshare"
  REDIS_URL: "redis://redis:6379/0"
  JWT_SECRET_KEY: "your-secret-key"
```

## 🤝 Integration with Other Services

### Service Communication

This service provides authentication for other services:

```python
# Other services can verify tokens
headers = {"Authorization": f"Bearer {token}"}
response = requests.post(
    "http://user-service:8000/api/users/verify-token",
    headers=headers
)
```

### Event Publishing

The service publishes events to Redis:

- `user-events` channel for user registration/updates
- Session management in Redis

## 🐛 Troubleshooting

### Common Issues

1. **Database Connection Errors**

```bash
# Check database connectivity
pg_isready -h localhost -p 5432

# Verify database exists
psql -h localhost -U postgres -l
```

2. **Redis Connection Errors**

```bash
# Test Redis connection
redis-cli ping
```

3. **Token Validation Issues**

```bash
# Check JWT secret configuration
echo $JWT_SECRET_KEY

# Verify token format
jwt decode <token>
```

### Debug Mode

Enable debug logging:

```bash
export DEBUG=true
```

### Health Check Debug

```bash
# Check service health
curl http://localhost:8000/api/users/health

# Check readiness
curl http://localhost:8000/api/users/ready
```

## 📝 API Schema

Full API documentation is available at `/api/users/docs` when running the service.

### Example Request/Response

**Register User:**

```json
// Request
POST /api/users/register
{
  "email": "john@example.com",
  "password": "SecurePass123!",
  "first_name": "John",
  "last_name": "Doe",
  "phone": "+1234567890",
  "role": "rider"
}

// Response
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "user": {
    "id": "uuid",
    "email": "john@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "role": "rider",
    "is_active": true,
    "created_at": "2025-01-01T12:00:00Z"
  }
}
```

## 📄 License

This project is part of the RideShare Pro platform.

## 🔗 Related Services

- [Payment Service](../rideshare-payment-service) - Handle payments and billing
- [Ride Matching Service](../rideshare-ride-matching-service) - Ride requests and matching
- [Notification Service](../rideshare-notification-service) - SMS, email, push notifications
- [Infrastructure](../rideshare-infrastructure) - Shared Kubernetes resources
