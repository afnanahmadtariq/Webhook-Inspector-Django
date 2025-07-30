# startup.py - Azure App Service startup script
import os
import subprocess
import sys

def install_dependencies():
    """Install Python dependencies"""
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])

def collect_static():
    """Collect static files"""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'webhook_inspector.production_settings')
    subprocess.check_call([sys.executable, "manage.py", "collectstatic", "--noinput"])

def run_migrations():
    """Run database migrations"""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'webhook_inspector.production_settings')
    subprocess.check_call([sys.executable, "manage.py", "migrate", "--noinput"])

def create_superuser():
    """Create superuser if it doesn't exist"""
    try:
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'webhook_inspector.production_settings')
        subprocess.check_call([
            sys.executable, "manage.py", "shell", "-c",
            "from django.contrib.auth.models import User; "
            "User.objects.filter(username='admin').exists() or "
            "User.objects.create_superuser('admin', 'admin@example.com', 'admin123')"
        ])
    except Exception as e:
        print(f"Could not create superuser: {e}")

if __name__ == "__main__":
    print("Starting Azure deployment setup...")
    
    # Set production settings
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'webhook_inspector.production_settings')
    
    try:
        print("Installing dependencies...")
        install_dependencies()
        
        print("Running migrations...")
        run_migrations()
        
        print("Collecting static files...")
        collect_static()
        
        print("Creating superuser...")
        create_superuser()
        
        print("Setup completed successfully!")
        
    except Exception as e:
        print(f"Setup failed: {e}")
        sys.exit(1)
