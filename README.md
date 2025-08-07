# Webhook Inspector Django

A micro web application for receiving, logging, and inspecting incoming webhooks. This project provides business logic for developers who need to test and debug webhook integrations.

## Core Features

### 🔗 Temporary Webhook URLs
- Generate unique URLs (e.g., `/hooks/<uuid>/`)
- Automatic expiration after X minutes or requests
- Secure and isolated webhook endpoints

### 📝 Webhook Logging
- Store complete request data:
  - Full request body
  - Headers
  - Timestamp
  - IP address
- Simple admin dashboard for log viewing

### ⚡ Real-time Updates
- Live-refresh incoming webhook data using:
  - Django Channels, or
  - HTMX for dynamic UI updates

### 🔍 Search & Filter
- Filter requests by:
  - Date range
  - HTTP method
  - Content type
- Advanced search capabilities

### 🚀 Async Processing
- Offload request logging to Celery + Redis
- Process webhook data for later use
- JSON schema validation support

## Tech Stack & Concepts Covered

- **Django** + Django REST Framework (optional for API-style logs)
- **Django UUID routing** for unique webhook endpoints
- **Django Channels** or **HTMX** for real-time UI updates
- **Celery + Redis** for async task processing
- **SQLite** or **PostgreSQL** for data storage
- **Logging** with model-level TTL (auto-delete expired logs)

## Why It's Technical & Valuable

- ✅ Covers UUID routing, middleware, and raw request handling
- ✅ Implements async queues and background processing
- ✅ Mimics popular tools like Webhook.site or RequestBin
- ✅ Extremely useful for API developers and webhook testing
- ✅ Production-ready patterns for webhook processing

