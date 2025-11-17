# Progress
- Implemented: deck decoding via Hoyolab, resonance calculation, PIL-based deck image generation, deck/user/activity persistence, and aiogram handlers for private/group chats with batching up to 20 codes.
- Data lifecycle: card DB sync + image download from Hakushin (`populate_db`), optional deck seeding from `data/decks.csv`, local image overrides applied post-sync.
- Admin UX: card search with tag support, image preview/upload, background sync trigger; user/deck/activity views with inline details; idempotent superuser creation.
- Deployment: Docker Compose for web+bot+DB; env-driven configuration; media directory mounted for card assets.
- Open ends: no explicit outstanding tasks from user; verify requirements with stakeholder before new work. Maintain Memory Bank on changes.
