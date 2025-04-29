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
```

## Kubernetes Deployment

### 1. PostgreSQL Setup

1. **Create test namespace**  
   ```bash
   kubectl create namespace faceit-test
   ```

2. **Create a pvc for postgres**
    ```
    apiVersion: v1
    kind: PersistentVolumeClaim
    metadata:
      name: faceit-postgres-pvc
      namespace: faceit-test
    spec:
      accessModes:
        - ReadWriteOnce
      resources:
        requests:
          storage: 10Gi
    ```

3. **Create your db secret**
    ```
    export TEST_DB_PASSWORD=$(openssl rand -base64 16)
    kubectl create secret generic faceit-postgres-secret \
      --namespace faceit-test \
      --from-literal=password="$TEST_DB_PASSWORD"
    ```


4. **Deploy StatefulSet**
    ```
    apiVersion: apps/v1
    kind: StatefulSet
    metadata:
      name: faceit-postgres
      namespace: faceit-test
    spec:
      serviceName: faceit-postgres
      replicas: 1
      selector:
        matchLabels:
          app: faceit-postgres
      template:
        metadata:
          labels:
            app: faceit-postgres
        spec:
          containers:
          - name: postgres
            image: postgres:15
            env:
            - name: POSTGRES_DB
              value: faceit_test_db
            - name: POSTGRES_USER
              value: faceit
            - name: POSTGRES_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: faceit-postgres-secret
                  key: password
            ports:
            - containerPort: 5432
            volumeMounts:
            - name: data
              mountPath: /var/lib/postgresql/data
      volumeClaimTemplates:
      - metadata:
          name: data
        spec:
          accessModes: [ReadWriteOnce]
          resources:
            requests:
              storage: 10Gi
    ```

5. **Export Postgres**
    ```
    apiVersion: v1
    kind: Service
    metadata:
      name: faceit-postgres
      namespace: faceit-test
    spec:
      ports:
        - port: 5432
          targetPort: 5432
      selector:
        app: faceit-postgres
    ```

# Deploy via Helm

```
helm upgrade --install faceit charts/faceit \
  --namespace faceit-test \
  --create-namespace \
  --set image.repository="your_repo" \
  --set image.tag="latest" \
  --set service.port=8001 \
  --set service.targetPort=8001 \
  --set faceitApiKey="${FACEIT_API_KEY}" \
  --set djangoSecretKey="${DJANGO_SECRET_KEY}" \
  --set database.host="faceit-postgres.faceit-test.svc.cluster.local" \
  --set database.user="faceit" \
  --set database.password="${TEST_DB_PASSWORD}" \
  --set database.name="faceit_test_db"
```

## Note
We can also edit the values.yaml file for some of these things (port/targetPort/repository/tag)

```## 📄 License

MIT © Nicholas Ilow


