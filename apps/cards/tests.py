from django.test import TestCase

from apps.cards.services.db_updater import _normalize_card_name


class NormalizeCardNameTests(TestCase):
    def test_wanderer_name_normalized_by_id(self):
        self.assertEqual(_normalize_card_name(1506, "Anything"), "Wanderer")

    def test_wanderer_name_normalized_by_value(self):
        template_name = "#{REALNAME[ID(1)|DELAYHANDLE(true)]}"
        self.assertEqual(_normalize_card_name(9999, template_name), "Wanderer")

    def test_regular_name_remains_unchanged(self):
        self.assertEqual(_normalize_card_name(1, "Diluc"), "Diluc")
