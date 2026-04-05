#!/bin/bash

# For development

set -e

# Kill both processes together
trap 'kill 0' EXIT

# Make root the working dir regardless of where it is called from
cd "$(dirname "$0")"

# Launch flask and npm
(cd backend && source .venv/bin/activate && flask --app api run) &
(cd frontend && npm run dev) &

# Wait while background job runs
wait
