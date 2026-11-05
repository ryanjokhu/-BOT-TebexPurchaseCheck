"""Offline tests for verified legacy kits and player-scoped purchase receipts."""

import os
from dataclasses import replace
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase, TestCase
from unittest.mock import AsyncMock, patch

with patch.dict(os.environ, {
    "GUILD_ID": "123456789012345678",
    "TEBEX_SECRET": "unit-test-secret",
    "DISCORD_TOKEN": "unit-test-token",
}):
    import tebextransactioncheck as bot

STEAM = "76561198856040209"
OTHER = "76561198000000000"


def interaction(*, user_id=23, staff=False):
    user = SimpleNamespace(
        id=user_id,
        roles=[SimpleNamespace(id=10)] if staff else [],
        guild_permissions=SimpleNamespace(administrator=False, manage_guild=False),
    )
    return SimpleNamespace(
        user=user,
        response=SimpleNamespace(defer=AsyncMock(), is_done=lambda: True, send_message=AsyncMock()),
        followup=SimpleNamespace(send=AsyncMock()),
        command=SimpleNamespace(name="purchasehistory"),
    )


class VerifiedExistingManifestTests(TestCase):
    def test_manifest_is_only_for_one_steam_account(self):
        record = bot.read_verified_existing_kits(STEAM)
        self.assertIsNotNone(record)
        self.assertEqual(record["existingKits"], ["egg", "egg2", "fear", "eggie"])
        self.assertIsNone(bot.read_verified_existing_kits(OTHER))


class VerifiedExistingLookupTests(IsolatedAsyncioTestCase):
    def setUp(self):
        self.old = bot.settings
        bot.settings = replace(bot.settings, staff_role_ids={10}, purchase_history_user_ids={23})

    def tearDown(self):
        bot.settings = self.old

    async def test_delegate_only_sees_mapped_steam_account(self):
        user = interaction()
        with patch.dict(os.environ, {"PURCHASE_HISTORY_USER_SCOPE": f"23:{STEAM}"}):
            self.assertTrue(bot.can_query_purchase_history_target(user, STEAM))
            self.assertFalse(bot.can_query_purchase_history_target(user, OTHER))
            self.assertFalse(bot.can_query_purchase_history_target(interaction(user_id=24), STEAM))

    async def test_staff_remains_unrestricted(self):
        user = interaction(user_id=24, staff=True)
        self.assertTrue(bot.can_query_purchase_history_target(user, OTHER))

    async def test_unmapped_delegate_is_rejected(self):
        with patch.dict(os.environ, {"PURCHASE_HISTORY_USER_SCOPE": ""}):
            self.assertFalse(bot.can_query_purchase_history_target(interaction(), STEAM))

    async def test_legacy_receipt_does_not_inflate_payments_or_money(self):
        user = interaction()
        data = {
            "player": {"username": "Amethyst"},
            "purchaseTotals": {"USD": "12.71"},
            "payments": [{"time": 1767406110, "price": 12.71, "currency": "USD", "status": 1,
                          "txn_id": "test-reference", "name": "OP Custom Kit"}],
            "banCount": 0,
            "chargebackRate": 0,
        }
        with (
            patch.dict(os.environ, {"PURCHASE_HISTORY_USER_SCOPE": f"23:{STEAM}"}),
            patch.object(bot.tebex, "get_user", new_callable=AsyncMock, return_value=data) as fetch,
            patch.object(bot, "enrich_payment_product_names", new_callable=AsyncMock),
        ):
            await bot.purchasehistory.callback(user, STEAM, private=False)
        fetch.assert_awaited_once_with(STEAM)
        user.response.defer.assert_awaited_once_with(ephemeral=True, thinking=True)
        kwargs = user.followup.send.await_args.kwargs
        fields = {field.name: field.value for field in kwargs["embed"].fields}
        self.assertEqual(fields["Payments"], "1")
        self.assertEqual(fields["Direct Tebex spend (USD)"], "$12.71")
        self.assertIn("egg2", fields["Existing server kits (4 verified)"])
        self.assertNotIn("view", kwargs)
        receipt = kwargs["file"].fp.getvalue().decode("utf-8")
        self.assertIn("Payment count shown by Tebex response: 1", receipt)
        self.assertIn("Total spent USD: $12.71", receipt)
        self.assertIn("eggie", receipt)
        self.assertIn("not additional payments", receipt)

    async def test_denied_other_account_does_not_contact_tebex(self):
        user = interaction()
        with (
            patch.dict(os.environ, {"PURCHASE_HISTORY_USER_SCOPE": f"23:{STEAM}"}),
            patch.object(bot.tebex, "get_user", new_callable=AsyncMock) as fetch,
        ):
            await bot.purchasehistory.callback(user, OTHER, private=False)
        fetch.assert_not_awaited()
        self.assertTrue(user.followup.send.await_args.kwargs["ephemeral"])
