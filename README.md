# Faceit Heat

Django app for FACEIT CS2 stats — fetch player performance data, match history, and generate heat-check insights.

Live at [heat.nilow.space](https://heat.nilow.space)

## Features

- Faceit API integration for player stats and match data
- Performance calculations and session tracking
- Dockerized with Gunicorn + WhiteNoise
- Kubernetes-ready with plain manifests, Sealed Secrets, and cert-manager TLS
- CI/CD via GitHub Actions pushing to GHCR

## Tech Stack

- Python 3.12, Django 5.1, Gunicorn
- Docker, Kubernetes (k3s), Traefik
- PostgreSQL 15
- GitHub Actions, GHCR

## Local Development

```bash
git clone git@github.com:nic-ilow/faceit-heat-app.git && cd faceit-heat-app

cp .env.example .env
# fill .env with FACEIT_API_KEY & DJANGO_SECRET_KEY

python manage.py migrate
python manage.py runserver
```

In DEBUG mode the app uses SQLite. For production it connects to PostgreSQL via `DB_*` env vars.

## Deployment

CI/CD automatically builds and pushes the Docker image to GHCR on push to `main`. Kubernetes manifests live in `k8s/`.

### Prerequisites

- k3s cluster with Traefik, cert-manager, and Sealed Secrets controller
- `kubectl` and `kubeseal` CLI access

### 1. Create namespace and GHCR pull secret

```bash
kubectl apply -f k8s/namespace.yaml

kubectl create secret docker-registry ghcr-pull-secret \
  --namespace faceit \
  --docker-server=ghcr.io \
  --docker-username=nic-ilow \
  --docker-password=<GITHUB_PAT> \
  --docker-email=<email>
```

### 2. Deploy PostgreSQL

```bash
export DB_PASSWORD=$(openssl rand -base64 16)

kubectl create secret generic faceit-postgres-secret \
  --namespace faceit \
  --from-literal=password="$DB_PASSWORD"

kubectl apply -f k8s/postgres/
```

### 3. Generate Sealed Secret

```bash
kubectl create secret generic faceit-secrets \
  --namespace faceit \
  --from-literal=DJANGO_SECRET_KEY="$(openssl rand -base64 50)" \
  --from-literal=FACEIT_API_KEY="<your-api-key>" \
  --from-literal=DB_PASSWORD="$DB_PASSWORD" \
  --dry-run=client -o yaml | kubeseal --format yaml > k8s/sealed-secret.yaml
```

Commit the resulting `sealed-secret.yaml`.

### 4. Deploy the app

```bash
kubectl apply -f k8s/sealed-secret.yaml
kubectl apply -f k8s/deployment.yaml -f k8s/service.yaml -f k8s/ingress.yaml -f k8s/hpa.yaml
```

### 5. Post-deploy

- Grant Actions access to the GHCR package in GitHub package settings
- Verify TLS: `kubectl get certificate -n faceit`
- Check pods: `kubectl get pods -n faceit`

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DJANGO_SECRET_KEY` | Yes | — | Django secret key |
| `FACEIT_API_KEY` | Yes | — | FACEIT API key |
| `DJANGO_DEBUG` | No | `True` | Set `false` in production |
| `DJANGO_ALLOWED_HOSTS` | No | `*` | Comma-separated hostnames |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | No | — | Comma-separated origins (e.g. `https://heat.nilow.space`) |
| `DB_HOST` | No | `postgres-service` | PostgreSQL host |
| `DB_PORT` | No | `5432` | PostgreSQL port |
| `DB_NAME` | No | `postgres` | Database name |
| `DB_USER` | No | `postgres` | Database user |
| `DB_PASSWORD` | No | — | Database password (triggers PostgreSQL mode when set) |

## License

MIT © Nicholas Ilow
