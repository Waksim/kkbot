from unittest.mock import patch, AsyncMock
from django.test import TransactionTestCase

from apps.bot.services.hoyolab import decode_deck_code
from apps.bot.tests.test_data import DECK_TEST_CASES


class HoyolabAPITest(TransactionTestCase):
    """
    Тестирует функцию `decode_deck_code` для взаимодействия с API Hoyolab.
    Использует моки для изоляции от реальных сетевых запросов.
    """

    @patch('apps.bot.services.hoyolab.httpx.AsyncClient.post', new_callable=AsyncMock)
    async def test_decode_valid_codes(self, mock_post: AsyncMock):
        """
        Проверяет успешное раскодирование валидных кодов колод.
        """
        for test_case in DECK_TEST_CASES:
            with self.subTest(deck_code=test_case.deck_code):
                # Настраиваем мок для возврата успешного ответа
                mock_response = AsyncMock()
                mock_response.json.return_value = test_case.mock_api_response
                mock_response.raise_for_status.return_value = None
                mock_post.return_value = mock_response

                # Вызываем тестируемую функцию
                decoded_deck, error_message = await decode_deck_code(test_case.deck_code)

                # Проверяем результат
                self.assertIsNone(error_message, "Ошибки быть не должно")
                self.assertIsNotNone(decoded_deck, "Результат не должен быть None")

                # Сравниваем списки ID карт
                self.assertListEqual(
                    sorted(decoded_deck.character_ids),
                    sorted(test_case.character_ids),
                    "Списки ID карт персонажей не совпадают"
                )
                self.assertListEqual(
                    sorted(decoded_deck.action_ids),
                    sorted(test_case.action_ids),
                    "Списки ID карт действий не совпадают"
                )

    @patch('apps.bot.services.hoyolab.httpx.AsyncClient.post', new_callable=AsyncMock)
    async def test_api_error_handling(self, mock_post: AsyncMock):
        """
        Проверяет обработку ошибки от API (неверный retcode).
        """
        # Настраиваем мок для возврата ответа с ошибкой
        mock_response = AsyncMock()
        mock_response.json.return_value = {"retcode": -100, "message": "Invalid code", "data": None}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        deck_code = "invalid_code"
        decoded_deck, error_message = await decode_deck_code(deck_code)

        self.assertIsNone(decoded_deck, "Результат должен быть None при ошибке")
        self.assertIsNotNone(error_message, "Сообщение об ошибке должно присутствовать")
        self.assertEqual(error_message, "Invalid code")