# Local development API

This API runs the frontend-facing restaurant features without AWS: persistent
registration/sign-in, locations and menus, tables and reservations, pre-orders,
feedback, guest/group orders, waiter notifications, and reports. It uses only
Python's standard library and SQLite; no demo account is created. Register
through the frontend before signing in.

From the repository root, start the API:

```bash
python3 backend/local-api/server.py
```

In a second terminal, start the Angular app:

```bash
cd frontend/restaurant-frontend-app
npm start
```

Open [http://localhost:4200](http://localhost:4200). The development frontend
uses `http://127.0.0.1:8000`; production configuration remains unchanged.

The local API seeds three locations, four popular dishes, and tables for each
location on first startup. Accounts and application data are stored under
`backend/local-api/data/`.
Passwords are salted and hashed with PBKDF2-HMAC-SHA256. The API binds to
localhost by default and issues signed, expiring JWTs for registered users.
Keep this development server on localhost; it is not a production deployment.

All new accounts are customers unless you set `LOCAL_API_ADMIN_EMAIL` before
starting the server and register that exact email. That account receives the
local `Admin` role and can manage menu/location/table data, assign registered
users as waiters, and generate reports. To make a waiter, first register their
account, then add their email from the local admin workflow.

For example, on macOS/Linux start the API with:

```bash
LOCAL_API_ADMIN_EMAIL=admin@example.test python3 backend/local-api/server.py
```

Then register `admin@example.test` through the frontend. The email is an
example; choose an address you control.

To run its tests:

```bash
python3 -m unittest discover -s backend/local-api/tests -v
```

Set `LOCAL_API_PORT` to change the port, `GREEN_TASTY_DATA_DIR` to change the
database/secret location, `LOCAL_API_ADMIN_EMAIL` to designate a local admin,
or `LOCAL_API_SECRET` to supply a stable secret of at least 32 characters. Do
not commit the database or secret.

This is a local development replacement for the API contracts used by the
Angular app, not an AWS deployment. AWS infrastructure and the original Lambda
backend remain unchanged. Production hosting, email delivery, S3-compatible
public image hosting, scheduled report jobs, and multi-instance operation
require separate infrastructure and are not provided here.
