import httpx
import json
from typing import NamedTuple, Optional, List, Tuple

class DecodedDeck(NamedTuple):
    """Структура для хранения раскодированных ID карт."""
    character_ids: List[int]
    action_ids: List[int]

HOYOLAB_API_URL = "https://sg-public-api.hoyolab.com/event/cardsquare/decode_card_code?lang=en-us"

async def decode_deck_code(code: str) -> Tuple[Optional[DecodedDeck], Optional[str]]:
    """
    Асинхронно отправляет запрос к API Hoyolab для раскодирования колоды.
    В случае успеха возвращает (DecodedDeck, None).
    В случае ошибки возвращает (None, "сообщение об ошибке").
    """
    payload_dict = {"code": code}
    payload_str = json.dumps(payload_dict)
    headers = {'Content-Type': 'application/json'}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                HOYOLAB_API_URL,
                content=payload_str,
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            # ИСПРАВЛЕНИЕ: Удаляем отладочный вывод
            # print(repr(data))

            if data.get("retcode") != 0 or not data.get("data"):
                error_message = data.get("message", "Неизвестная ошибка API.")
                return None, error_message

            api_data = data["data"]
            char_cards = api_data.get("role_cards", [])
            action_cards = api_data.get("action_cards", [])

            char_ids = [
                card['basic']['item_id']
                for card in char_cards if 'basic' in card and 'item_id' in card['basic']
            ]
            action_ids = [
                card['basic']['item_id']
                for card in action_cards if 'basic' in card and 'item_id' in card['basic']
            ]

            decoded_deck = DecodedDeck(character_ids=char_ids, action_ids=action_ids)
            return decoded_deck, None

        except (httpx.RequestError, httpx.HTTPStatusError):
            return None, "Не удалось связаться с сервером Hoyolab."
        except (KeyError, TypeError, json.JSONDecodeError):
            return None, "Получен некорректный ответ от сервера Hoyolab."