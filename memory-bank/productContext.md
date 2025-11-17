# Product Context
- **Need**: Genshin TCG players share 68-char deck codes; they want immediate decoding, resonance checks, and a visual deck preview without leaving Telegram.
- **Audience**: End users interacting through Telegram (private or group chats) and administrators maintaining card data, decks cache, and user insights via Django admin.
- **Experience goals**: Low-latency replies, clear error messaging for invalid/missing cards, polished deck imagery, and the ability to batch-handle up to 20 codes per message.
- **Value**: Persistent deck cache avoids repeat API calls, admin UI supports card updates (incl. on-demand sync), and media assets live on disk for fast retrieval and easy overrides.

