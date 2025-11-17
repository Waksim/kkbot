# Project Brief
- Build a Telegram bot that decodes Genshin Impact TCG deck codes, shows their composition, and computes elemental/region/faction resonances.
- Generate attractive shareable deck images from stored card assets and deck data.
- Cache decoded decks in PostgreSQL for instant future responses and keep card data/images in sync with the Hakushin API, with manual override support for specific assets.
- Provide a Django admin experience for cards, decks, user activity, and maintenance actions.
- Ship a reproducible deployment via Docker with separate services for the web/admin app, the bot process, and PostgreSQL.

