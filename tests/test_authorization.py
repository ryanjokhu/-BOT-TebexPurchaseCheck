"""Authorization regression tests for Tebex receipt lookups (offline, no Discord API calls)."""

import os
from dataclasses import replace
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

with patch.dict(os.environ, {
    "GUILD_ID": "123456789012345678",
    "TEBEX_SECRET": "unit-test-secret",
    "DISCORD_TOKEN": "unit-test-token",
}):
    import tebextransactioncheck as bot


def interaction(user_id, role_ids=(), *, admin=False, manage_guild=False):
    return SimpleNamespace(user=SimpleNamespace(
        id=user_id,
        roles=[SimpleNamespace(id=value) for value in role_ids],
        guild_permissions=SimpleNamespace(administrator=admin, manage_guild=manage_guild),
    ))


class AuthorizationTests(TestCase):
    def setUp(self):
        self.previous = bot.settings
        bot.settings = replace(bot.settings, staff_role_ids={10}, purchase_history_user_ids={23})

    def tearDown(self):
        bot.settings = self.previous

    def test_explicitly_authorized_member_can_view_history(self):
        user = interaction(23)
        self.assertFalse(bot.is_staff(user))
        self.assertTrue(bot.can_view_purchase_history(user))
        self.assertTrue(bot.purchase_history_response_is_private(user, private=False))

    def test_regular_member_still_denied(self):
        self.assertFalse(bot.can_view_purchase_history(interaction(24)))
        self.assertFalse(bot.can_view_purchase_history(interaction(24, role_ids=[99])))

    def test_staff_role_retains_access_and_optional_public_reply(self):
        user = interaction(24, role_ids=[10])
        self.assertTrue(bot.is_staff(user))
        self.assertTrue(bot.can_view_purchase_history(user))
        self.assertFalse(bot.purchase_history_response_is_private(user, private=False))

    def test_manage_server_retains_access(self):
        self.assertTrue(bot.can_view_purchase_history(interaction(24, manage_guild=True)))

    def test_admin_retains_access(self):
        self.assertTrue(bot.can_view_purchase_history(interaction(24, admin=True)))

    def test_delegated_access_does_not_grant_transaction_privileges(self):
        self.assertFalse(bot.is_staff(interaction(23)))

    def test_allows_private_staff_reply(self):
        self.assertTrue(bot.purchase_history_response_is_private(interaction(24, role_ids=[10]), private=True))
