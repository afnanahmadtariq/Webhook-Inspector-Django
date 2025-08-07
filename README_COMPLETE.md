# Django Webhook Inspector

A comprehensive webhook inspection and testing tool built with Django, designed for monitoring, analyzing, and debugging webhook requests in real-time.

## 🚀 Quick Start

### Using Docker Compose (Recommended)

1. **Clone and Setup**
   ```bash
   git clone <repository-url>
   cd Webhook-Inspector-Django
   cp .env.example .env
   # Edit .env file with your configuration
   ```

2. **Start Services**
   ```bash
   docker-compose up -d
   ```

3. **Access the Application**
   - API: http://localhost:8000/api/v1/
   - Admin: http://localhost:8000/admin/
   - Health Check: http://localhost:8000/api/v1/webhooks/health/

### Manual Installation

1. **Prerequisites**
   - Python 3.12+
   - PostgreSQL or MongoDB
   - Redis
   - Node.js (for frontend)

2. **Backend Setup**
   ```bash
   # Create virtual environment
   python -m venv venv
   venv\Scripts\activate  # Windows
   # source venv/bin/activate  # Linux/Mac
   
   # Install dependencies
   pip install -r requirements.txt
   
   # Setup environment
   cp .env.example .env
   # Edit .env file
   
   # Run migrations
   python manage.py migrate
   
   # Create superuser
   python manage.py createsuperuser
   
   # Start development server
   python manage.py runserver
   ```

3. **Start Background Services**
   ```bash
   # Terminal 1: Celery Worker
   celery -A webhook_inspector worker --loglevel=info
   
   # Terminal 2: Celery Beat
   celery -A webhook_inspector beat --loglevel=info
   ```

## 📋 Features Implemented

### ✅ Core Webhook Features
- **Temporary Webhook URLs**: Generate unique, time-limited webhook endpoints
- **Complete Request Logging**: Capture headers, body, method, IP, and metadata
- **Real-time Updates**: WebSocket connections for live webhook monitoring
- **Advanced Search & Filtering**: Query by method, status, IP, headers, and more
- **Data Export**: Export webhook data in JSON, CSV, and XML formats

### ✅ Analytics & Monitoring
- **Request Analytics**: Detailed statistics and performance metrics
- **Geolocation Tracking**: IP-based location detection for requests
- **Alert System**: Configurable alerts for webhook patterns
- **Health Monitoring**: System health checks and status endpoints

### ✅ Security & Authentication
- **JWT Authentication**: Secure API access with token-based auth
- **API Key Management**: Generate and manage API keys for integration
- **Rate Limiting**: Prevent abuse with configurable rate limits
- **CORS Support**: Cross-origin resource sharing for frontend integration

### ✅ Advanced Features
- **Schema Validation**: Validate incoming webhooks against JSON schemas
- **Async Processing**: Background task processing with Celery
- **Multi-database Support**: PostgreSQL and MongoDB compatibility
- **WebSocket Support**: Real-time updates using Django Channels

### ✅ Deployment Ready
- **Docker Support**: Complete containerization with docker-compose
- **Azure Deployment**: Ready-to-deploy configuration for Azure App Service
- **Production Settings**: Optimized settings for production environments
- **Health Checks**: Comprehensive health monitoring endpoints

## 🏗️ Architecture

### Backend (Django REST API)
```
webhook_inspector/          # Main Django project
├── hooks/                  # Core webhook functionality
│   ├── models.py          # Database models
│   ├── views.py           # API endpoints
│   ├── serializers.py     # DRF serializers
│   ├── filters.py         # Query filtering
│   └── consumers.py       # WebSocket consumers
├── authentication/        # User management & API keys
├── analytics/             # Analytics and monitoring
└── webhook_inspector/     # Project settings
```

### Database Schema
- **WebhookEndpoint**: Temporary webhook URLs with TTL
- **WebhookRequest**: Complete request logging with metadata
- **WebhookAnalytics**: Performance metrics and statistics
- **WebhookSchema**: JSON schema validation rules
- **UserProfile**: Extended user data with API keys
- **AlertRule**: Configurable alert conditions

### API Endpoints

#### Webhook Management
- `POST /api/v1/webhooks/endpoints/` - Create webhook endpoint
- `GET /api/v1/webhooks/endpoints/` - List user's endpoints
- `DELETE /api/v1/webhooks/endpoints/{uuid}/` - Delete endpoint
- `ANY /api/v1/webhooks/capture/{uuid}/` - Capture webhook requests

#### Request Analysis
- `GET /api/v1/webhooks/requests/` - List webhook requests
- `GET /api/v1/webhooks/requests/{id}/` - Get request details
- `GET /api/v1/webhooks/requests/export/` - Export requests
- `GET /api/v1/webhooks/analytics/` - Get analytics data

#### Authentication
- `POST /api/v1/auth/register/` - User registration
- `POST /api/v1/auth/login/` - User login
- `POST /api/v1/auth/refresh/` - Refresh JWT token
- `GET /api/v1/auth/profile/` - User profile
- `POST /api/v1/auth/api-keys/` - Generate API key

## 🔧 Configuration

### Environment Variables

Key configuration options in `.env`:

```bash
# Database
DATABASE_ENGINE=postgresql  # or mongodb
POSTGRES_HOST=localhost
POSTGRES_DB=webhook_inspector

# Redis & Celery
REDIS_HOST=localhost
CELERY_BROKER_URL=redis://localhost:6379/0

# Security
SECRET_KEY=your-secret-key
JWT_SECRET_KEY=your-jwt-secret

# Features
ENABLE_WEBSOCKETS=True
ENABLE_GEOLOCATION=True
ANALYTICS_ENABLED=True

# Rate Limiting
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=3600
```

### Feature Flags

Control features via environment variables:
- `ENABLE_WEBSOCKETS`: Real-time updates
- `ENABLE_GEOLOCATION`: IP location tracking
- `ENABLE_SCHEMA_VALIDATION`: JSON schema validation
- `ANALYTICS_ENABLED`: Analytics collection
- `RATE_LIMIT_ENABLED`: API rate limiting

## 🚀 Azure Deployment

### Prerequisites
- Azure subscription
- Azure CLI installed
- Docker installed

### Deployment Steps

1. **Prepare Azure Resources**
   ```bash
   # Create resource group
   az group create --name webhook-inspector-rg --location eastus
   
   # Create App Service plan
   az appservice plan create --name webhook-inspector-plan --resource-group webhook-inspector-rg --sku B1 --is-linux
   
   # Create PostgreSQL server
   az postgres server create --name webhook-inspector-db --resource-group webhook-inspector-rg --admin-user webhook_admin --admin-password YourSecurePassword123
   
   # Create Redis cache
   az redis create --name webhook-inspector-cache --resource-group webhook-inspector-rg --location eastus --sku Basic --vm-size c0
   ```

2. **Deploy Application**
   ```bash
   # Create web app
   az webapp create --name webhook-inspector-app --resource-group webhook-inspector-rg --plan webhook-inspector-plan --deployment-container-image-name webhook-inspector:latest
   
   # Configure environment variables
   az webapp config appsettings set --name webhook-inspector-app --resource-group webhook-inspector-rg --settings @.env.azure
   ```

3. **Configure Deployment**
   - Copy `.env.azure` to configure production settings
   - Update `ALLOWED_HOSTS` with your Azure domain
   - Configure database connection strings
   - Set up Redis connection with SSL

### Production Checklist

- [ ] Update `SECRET_KEY` and `JWT_SECRET_KEY`
- [ ] Configure PostgreSQL database
- [ ] Set up Redis cache with SSL
- [ ] Configure email backend (SendGrid/Azure Communication Services)
- [ ] Set up Application Insights (optional)
- [ ] Configure custom domain and SSL
- [ ] Set up backup strategy
- [ ] Configure monitoring and alerts

## 🔍 API Usage Examples

### Create Webhook Endpoint
```bash
curl -X POST http://localhost:8000/api/v1/webhooks/endpoints/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Webhook",
    "description": "Testing webhook capture",
    "ttl_hours": 24
  }'
```

### Send Test Webhook
```bash
curl -X POST http://localhost:8000/api/v1/webhooks/capture/YOUR_UUID/ \
  -H "Content-Type: application/json" \
  -d '{
    "event": "test",
    "data": {
      "message": "Hello World"
    }
  }'
```

### Get Webhook Requests
```bash
curl -X GET "http://localhost:8000/api/v1/webhooks/requests/?endpoint_uuid=YOUR_UUID" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Export Data
```bash
curl -X GET "http://localhost:8000/api/v1/webhooks/requests/export/?format=csv&endpoint_uuid=YOUR_UUID" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## 🧪 Testing

### Run Tests
```bash
# All tests
python manage.py test

# Specific app
python manage.py test hooks

# With coverage
pip install coverage
coverage run --source='.' manage.py test
coverage report
```

### Health Check
```bash
curl http://localhost:8000/api/v1/webhooks/health/
```

## 📚 Frontend Integration

This backend is designed to work with a separate React frontend. Key integration points:

### WebSocket Connection
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/webhooks/YOUR_UUID/');
ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    // Handle real-time webhook updates
};
```

### API Client Example
```javascript
const api = axios.create({
    baseURL: 'http://localhost:8000/api/v1/',
    headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
    }
});

// Create webhook endpoint
const response = await api.post('/webhooks/endpoints/', {
    name: 'My Webhook',
    description: 'Test webhook',
    ttl_hours: 24
});
```

## 🔧 Development

### Adding New Features

1. **Models**: Add to `hooks/models.py`
2. **Serializers**: Add to `hooks/serializers.py`
3. **Views**: Add to `hooks/views.py`
4. **URLs**: Update `hooks/urls.py`
5. **Tests**: Add tests in `hooks/tests.py`

### Database Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### Static Files
```bash
python manage.py collectstatic
```

## 📖 Additional Resources

- [Django Documentation](https://docs.djangoproject.com/)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [Django Channels](https://channels.readthedocs.io/)
- [Celery Documentation](https://docs.celeryproject.org/)
- [Azure App Service](https://docs.microsoft.com/en-us/azure/app-service/)

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/new-feature`
3. Commit changes: `git commit -am 'Add new feature'`
4. Push to branch: `git push origin feature/new-feature`
5. Submit pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**Built with ❤️ using Django, designed for scalability and production deployment on Azure.**
