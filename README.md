# Databoard

## Development

Clone:

```sh
git clone https://www.github.com/ChrisDonovan307/databoard.git
cd databoard
```

Set up backend environment:

```sh
cd backend && uv sync && cd ..
```

Set up frontend environment

```sh
cd frontend && npm install && cd ..
```

To run development, there is a `run.sh` script that will launch front and back ends.

```sh
chmod +x run.sh
./run.sh
```

Defaults to `localhost:5173/databoard`

## Project Structure

Apart from main front end and back end directories, `.dev` has works in progress and the remains of the program that pulls data using the Dataverse APIs. This needs to be worked into the backend and wired up again. Also re-written because it's a mess.

### Frontend
```
frontend
├── eslint.config.js
├── package.json
├── package-lock.json
├── playwright.config.ts
├── src
│   ├── app.css
│   ├── app.d.ts
│   ├── app.html
│   ├── lib
│   │   ├── assets
│   │   ├── index.ts
│   │   ├── theme.svelte.ts
│   │   └── vitest-examples
│   └── routes
│       ├── BarChart.svelte
│       ├── demo
│       ├── detail
│       ├── +layout.svelte
│       ├── Map.svelte
│       ├── Navbar.svelte
│       ├── +page.server.ts
│       ├── +page.svelte
│       └── +page.ts
├── static
│   └── robots.txt
├── svelte.config.js
├── tsconfig.json
└── vite.config.ts
```

### Backend

```bash
backend
├── api.py
├── data
│   ├── dataverses.csv
│   └── installations
│       ├── installations.csv
│       ├── installations.geojson
│       └── response.json
├── dev
│   ├── get_installations.py
│   ├── http_cache.sqlite
│   ├── sandbox.py
│   └── script.py
├── examples
│   ├── example.py
│   └── minimal.py
├── http_cache.sqlite
├── __init__.py
├── pages
│   ├── graphs.py
│   ├── home.py
│   ├── map.py
│   └── tables.py
├── pyproject.toml
├── ref
│   ├── app.py
│   └── wsgi.py
├── requirements.txt
├── routes
│   ├── data.py
│   └── __init__.py
├── uv.lock
└── wsgi.py
```