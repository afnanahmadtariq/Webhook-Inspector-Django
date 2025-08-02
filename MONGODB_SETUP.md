# MongoDB Setup Guide

This project uses MongoDB as the database through Djongo, which allows using Django ORM with MongoDB.

## Quick Setup Options

### Option 1: MongoDB Atlas (Recommended for Production)

1. Create a free account at [MongoDB Atlas](https://www.mongodb.com/atlas)
2. Create a new cluster
3. Create a database user
4. Whitelist your IP address (or use 0.0.0.0/0 for development)
5. Get your connection string, it will look like:
   ```
   mongodb+srv://username:password@cluster.mongodb.net/webhook_inspector?retryWrites=true&w=majority
   ```

### Option 2: Local MongoDB (Development)

1. Install MongoDB Community Edition
2. Start MongoDB service
3. Use connection string:
   ```
   mongodb://localhost:27017/webhook_inspector
   ```

### Option 3: Docker MongoDB

```bash
docker run -d --name webhook-mongo -p 27017:27017 -e MONGO_INITDB_DATABASE=webhook_inspector mongo:latest
```

## Environment Configuration

Update your `.env` file with your MongoDB URI:

```bash
# MongoDB Configuration
MONGO_URI=mongodb+srv://username:password@cluster.mongodb.net/webhook_inspector?retryWrites=true&w=majority
MONGO_DB=webhook_inspector
```

## Database Migration

Since we're using Djongo, Django migrations work normally:

```bash
python manage.py makemigrations
python manage.py migrate
```

## Important Notes

1. **Djongo Compatibility**: We're using Djongo v1.3.6 which works with Django 5.x
2. **No SQL Features**: MongoDB-specific features like aggregations can be used through raw queries
3. **Indexes**: Django model indexes are automatically created in MongoDB
4. **JSON Fields**: Django JSONField works seamlessly with MongoDB's document structure

## Production Considerations

- Use MongoDB Atlas or a managed MongoDB service
- Enable authentication and SSL/TLS
- Set up proper backup strategies
- Monitor performance with MongoDB Compass or Atlas monitoring
- Consider using connection pooling for high traffic

## Troubleshooting

If you encounter issues:

1. Ensure MongoDB is running and accessible
2. Check your connection string format
3. Verify network connectivity and firewall settings
4. Check Django logs for specific error messages
