# Green Tasty

## Run locally without AWS

Requirements: Python 3 and Node.js 24.16+ in the 24.x line. Node.js 26 is not
supported. The frontend's `.nvmrc` pins Node.js 24.16.0; with `nvm`, run
`nvm install` and `nvm use` from the frontend directory before installing
dependencies.

1. From the repository root, start the local API:

   ```bash
   python3 backend/local-api/server.py
   ```

2. In a second terminal, install frontend dependencies and start Angular:

   ```bash
   cd frontend/restaurant-frontend-app
   npm ci
   npm start
   ```

3. Open [http://localhost:4200](http://localhost:4200), register an account,
   and sign in. The local API seeds locations and popular dishes and stores
   accounts and application data in a local SQLite database. No AWS account
   or credentials are needed.

See [`backend/local-api/README.md`](backend/local-api/README.md) for API details,
admin setup, and tests.

For the original AWS deployment instructions, see
[`README-AWS.md`](README-AWS.md).
