# PosFrontend

This project uses Angular CLI 22.0.4.

## Development server

Start Django first:

```bash
cd backend
.venv/bin/python manage.py migrate
.venv/bin/python manage.py runserver 0.0.0.0:8000
```

Then start Angular:

```bash
cd frontend
npm ci
npm start
```

The application uses same-origin API paths. `proxy.conf.json` forwards the API module paths to Django during development, so the browser never calls `localhost` and remote previews work correctly. Open `http://localhost:4200/` after the server starts.

For production, serve the Angular build and Django API behind one HTTPS origin, or provide a build-time API URL, and configure the reverse proxy to forward the API module paths to Django.

## Building

```bash
npm run build
```

The production build is self-contained: Chart.js is bundled and external font downloads are not required during compilation.

## Running unit tests

```bash
npm test -- --watch=false
```
