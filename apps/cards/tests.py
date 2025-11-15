import tempfile
from pathlib import Path

from django.test import TestCase, override_settings

from apps.cards.services import db_updater


class NormalizeCardNameTests(TestCase):
    def test_wanderer_name_normalized_by_id(self):
        self.assertEqual(db_updater._normalize_card_name(1506, "Anything"), "Wanderer")

    def test_wanderer_name_normalized_by_value(self):
        template_name = "#{REALNAME[ID(1)|DELAYHANDLE(true)]}"
        self.assertEqual(db_updater._normalize_card_name(9999, template_name), "Wanderer")

    def test_regular_name_remains_unchanged(self):
        self.assertEqual(db_updater._normalize_card_name(1, "Diluc"), "Diluc")


class ApplyImageOverridesTests(TestCase):
    def test_override_image_copied_into_media_root(self):
        with tempfile.TemporaryDirectory() as temp_media_root:
            temp_media_root_path = Path(temp_media_root)
            with override_settings(MEDIA_ROOT=temp_media_root_path):
                original_image_dir = db_updater.IMAGE_DIR
                override_file = db_updater.CARD_IMAGE_OVERRIDES_DIR / "312041.webp"
                override_file.parent.mkdir(parents=True, exist_ok=True)

                created_override = False
                if not override_file.exists():
                    override_file.write_bytes(b"test")
                    created_override = True

                try:
                    try:
                        # Обновляем путь к директории изображений на время теста.
                        db_updater.IMAGE_DIR = temp_media_root_path / "card_images"

                        db_updater._apply_image_overrides({312041})
                        self.assertTrue(
                            (db_updater.IMAGE_DIR / "312041.webp").exists()
                        )
                    finally:
                        db_updater.IMAGE_DIR = original_image_dir
                finally:
                    if created_override:
                        override_file.unlink()
