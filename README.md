# Django on Docker

A Django web application with file upload functionality, containerized with Docker and served with Nginx.

## Features

- 🐳 **Dockerized Django Application** - Complete containerization with Docker Compose
- 📁 **File Upload System** - Secure file upload with django-sendfile2
- 🗄️ **PostgreSQL Database** - Production-ready database setup
- 🌐 **Nginx Reverse Proxy** - High-performance web server
- 🔒 **Secure File Serving** - Files served through Django views with access control
- 📱 **Responsive UI** - Bootstrap-based responsive design
- 🛡️ **Production Ready** - Separate configurations for development and production

## Project Structure

```
django-on-docker/
├── app/                          # Django application
│   ├── hello_django/            # Main Django project
│   ├── myapp/                   # Sample Django app
│   ├── upload/                  # File upload app
│   ├── Dockerfile               # Development Dockerfile
│   ├── Dockerfile.prod          # Production Dockerfile
│   └── manage.py
├── nginx/                       # Nginx configuration
├── docker-compose.yml           # Development compose file
├── docker-compose.prod.yml      # Production compose file
└── README.md
```

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)

## Quick Start

### Development Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd django-on-docker
   ```

2. **Set up environment variables**
   ```bash
   cp .env.example .env.dev
   # Edit .env.dev with your configuration
   ```

3. **Build and run the development environment**
   ```bash
   docker-compose up --build
   ```

4. **Access the application**
   - Django app: http://localhost:1337
   - Upload interface: http://localhost:1337/upload/
   - Admin panel: http://localhost:1337/admin/

5. **Create a superuser (optional)**
   ```bash
   docker-compose exec web python manage.py createsuperuser
   ```

### Production Setup

1. **Set up production environment variables**
   ```bash
   cp .env.example .env.prod
   cp .env.example .env.db.prod
   # Edit both files with production values
   ```

2. **Build and run production environment**
   ```bash
   docker-compose -f docker-compose.prod.yml up --build
   ```

3. **Run initial setup commands**
   ```bash
   # Collect static files
   docker-compose -f docker-compose.prod.yml exec web python manage.py collectstatic --no-input
   
   # Run migrations
   docker-compose -f docker-compose.prod.yml exec web python manage.py migrate
   
   # Create superuser
   docker-compose -f docker-compose.prod.yml exec web python manage.py createsuperuser
   ```

## Environment Configuration

### Required Environment Variables

Create `.env.dev` for development or `.env.prod` for production:

```env
# Django Settings
DEBUG=True
SECRET_KEY=your-secret-key-here
DJANGO_ALLOWED_HOSTS=localhost 127.0.0.1 [::1]

# Database Settings
DB_ENGINE=django.db.backends.postgresql
DB_NAME=hello_django_dev
DB_USER=hello_django
DB_PASSWORD=hello_django
DB_HOST=db
DB_PORT=5432

# PostgreSQL Settings
POSTGRES_USER=hello_django
POSTGRES_PASSWORD=hello_django
POSTGRES_DB=hello_django_dev
```

## Available Services

### Development Services
- **web**: Django application (port 8000)
- **db**: PostgreSQL database (port 5432)
- **nginx**: Nginx reverse proxy (port 1337)

### Optional Development Services
Copy `docker-compose.override.yml.example` to `docker-compose.override.yml` to enable:
- **redis**: Redis cache (port 6379)
- **mailhog**: Email testing (SMTP: 1025, Web UI: 8025)
- **pgadmin**: Database admin (port 5050)

## File Upload System

The application includes a secure file upload system with the following features:

- **File Upload Form**: `/upload/`
- **File List**: `/upload/` (shows all uploaded files)
- **File Details**: `/upload/file/<id>/`
- **Secure Downloads**: Files served through Django views with access control
- **Admin Interface**: Manage uploads through Django admin

### Upload Features
- File size validation (10MB limit)
- File type validation
- Secure file serving with django-sendfile2
- Responsive Bootstrap UI
- Pagination for file lists

## Common Commands

### Development
```bash
# Start services
docker-compose up

# Start in background
docker-compose up -d

# Rebuild containers
docker-compose up --build

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Run Django commands
docker-compose exec web python manage.py <command>

# Access Django shell
docker-compose exec web python manage.py shell

# Run tests
docker-compose exec web python manage.py test
```

### Production
```bash
# Start production services
docker-compose -f docker-compose.prod.yml up -d

# View production logs
docker-compose -f docker-compose.prod.yml logs -f

# Stop production services
docker-compose -f docker-compose.prod.yml down
```

## Database Management

### Migrations
```bash
# Create migrations
docker-compose exec web python manage.py makemigrations

# Apply migrations
docker-compose exec web python manage.py migrate

# Show migration status
docker-compose exec web python manage.py showmigrations
```

### Database Access
```bash
# Access PostgreSQL directly
docker-compose exec db psql -U hello_django -d hello_django_dev

# Create database backup
docker-compose exec db pg_dump -U hello_django hello_django_dev > backup.sql

# Restore database backup
docker-compose exec -T db psql -U hello_django -d hello_django_dev < backup.sql
```

## Troubleshooting

### Common Issues

1. **Port already in use**
   ```bash
   # Check what's using the port
   netstat -tulpn | grep :1337
   
   # Change port in docker-compose.yml
   ```

2. **Permission denied errors**
   ```bash
   # Fix file permissions
   sudo chown -R $USER:$USER .
   ```

3. **Database connection errors**
   ```bash
   # Restart database service
   docker-compose restart db
   
   # Check database logs
   docker-compose logs db
   ```

4. **Static files not loading**
   ```bash
   # Collect static files
   docker-compose exec web python manage.py collectstatic --no-input
   ```

### Logs and Debugging
```bash
# View all logs
docker-compose logs

# View specific service logs
docker-compose logs web
docker-compose logs db
docker-compose logs nginx

# Follow logs in real-time
docker-compose logs -f web
```

## Security Considerations

- Change default passwords in production
- Use strong SECRET_KEY in production
- Configure proper ALLOWED_HOSTS
- Set up SSL/TLS certificates
- Regular security updates
- Monitor file upload sizes and types

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and questions:
- Check the troubleshooting section
- Review Docker and Django documentation
- Create an issue in the repository

---

**Happy coding! 🚀**
