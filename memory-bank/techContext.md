# Tech Context
- **Runtime/deps**: Python 3.13; Django 5.2.3; aiogram 3.10; PostgreSQL 16; httpx for async HTTP; Pillow for image work; django-select2; whitenoise for static; dotenv for env loading.
- **Services**: Docker Compose runs `db` (Postgres), `web` (Django admin/site with migrations + superuser creation), and `bot` (aiogram worker). Media volume mounted for card images.
- **External APIs**: Hoyolab decode endpoint for deck codes; Hakushin (`gcg.json`, `new.json`, `UI/*`) for card metadata and images. Local overrides defined in `apps/cards/services/db_updater.py::IMAGE_OVERRIDES`.
- **Env config** (`.env`): SECRET_KEY/DEBUG; Postgres creds/host/port; admin credentials (ADMIN_USERNAME/PASSWORD/EMAIL); bot config BOT_TOKEN and ADMIN_ID.
- **Data**: Card images stored under `media/card_images`; static assets for deck images under `core/static/bot`; optional deck seeds in `data/decks.csv`.

