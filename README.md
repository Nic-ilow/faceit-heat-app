# Faceit Django Webserver


Minimal, production-ready Django app for interacting with the Faceit API, containerized and deployable via Helm.

## 🚀 Features

- **Faceit API Integration**: Fetch player stats, match data, and generate performance insights.
- **Dockerized**: Single `Dockerfile` + `entrypoint.sh` for uniform builds.
- **Kubernetes-Ready**: Helm chart with Secret management and configurable values.
- **Secure by Design**: Environment-driven secrets, CSRF enabled, HTTPS redirect middleware.

## 🛠️ Tech Stack

- Python 3.11 • Django 4.x • Gunicorn
- Docker • Kubernetes • Helm
- Nginx (reverse proxy)

## ⚡ Quick Start

```bash
# Clone
git clone git@github.com:nic-ilow/faceit-heat-check.git && cd faceit

# Local development (SQLite)
cp .env.example .env
# fill .env with FACEIT_API_KEY & DJANGO_SECRET_KEY
python manage.py migrate
python manage.py runserver
```

In DEBUG mode, the app uses SQLite (`db.sqlite3`). For production, configure a PostgreSQL database via environment variables or Kubernetes secrets.## 📦 Deployment

Production deployment via Helm chart (in progress). The app expects an external PostgreSQL instance. Configure database connection parameters, FACEIT_API_KEY, and DJANGO_SECRET_KEY through Helm values or environment variables.

```bash
# Build & push image
docker build -t registry/faceit:latest .
docker push registry/faceit:latest

# Deploy via Helm (chart pending)
helm upgrade --install faceit charts/faceit \
  --namespace faceit \
  --set faceitApiKey="$FACEIT_API_KEY" \
  --set djangoSecretKey="$DJANGO_SECRET_KEY" \
  --set database.host="your-db-host" \
  --set database.user="your-db-user" \
  --set database.password="$DB_PASSWORD" \
  --set database.name="faceit_db"
```## 📄 License

MIT © Nicholas Ilow


