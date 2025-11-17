# System Patterns
- **Architecture**: Django 5 project with apps `cards` (Card/Tag models, admin, Hakushin sync), `users` (TelegramUser/Deck/UserActivity + admin), and `bot` (aiogram 3 handlers and services). Postgres stores cards, decks, users, and activity; media files live under `media/`.
- **Bot flow** (`apps/bot/handlers/deck_codes.py`): parse up to 20 codes from messages or `/kk` command → fetch/create `Deck` (decode via Hoyolab, verify cards exist, cache IDs) → load cards with prefetch → compute resonances → generate deck image → reply with media group + captions; errors logged via UserActivity.
- **Data sync** (`apps/cards/services/db_updater.py`): orchestrated in a transaction; fetch full card list + new card IDs from Hakushin; upsert cards (two-pass for FKs), upsert tags, delete stale cards, then download missing images. Local overrides live in `data/card_image_overrides`, applied after DB sync.
- **Admin patterns**: Card admin uses select2 for tags, image preview/upload, and a custom action to trigger background card sync. Users admin inlines decks and activity; Deck/UserActivity are read-only aside from viewing. Superuser auto-creation is idempotent (`create_superuser` command).
- **Management commands**: `populate_db` wraps card sync; `import_decks` seeds cached decks from CSV; `startbot` boots aiogram; `create_superuser` seeds admin credentials.
- **Imaging** (`apps/bot/services/image_generator.py`): PIL-based composition with configurable card sizes, resonance badges, and local asset paths; safe fallbacks if base assets are missing.
- **Caching**: `Deck` stores lists of card IDs to preserve duplicates; `get_or_create_deck` avoids repeat API calls and logs missing cards for transparency.

