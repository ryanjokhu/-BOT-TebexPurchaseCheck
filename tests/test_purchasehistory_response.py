"""Regression tests: discord.py rejects view=None on single-page purchase receipts."""

import os
from dataclasses import replace
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, patch

with patch.dict(os.environ, {
    "GUILD_ID": "123456789012345678",
    "TEBEX_SECRET": "unit-test-secret",
    "DISCORD_TOKEN": "unit-test-token",
}):
    import tebextransactioncheck as bot


def make_interaction(*, user_id=23, staff=False, deferred=True):
    user = SimpleNamespace(
        id=user_id,
        roles=[SimpleNamespace(id=10)] if staff else [],
        guild_permissions=SimpleNamespace(administrator=False, manage_guild=False),
    )
    response = SimpleNamespace(
        defer=AsyncMock(),
        is_done=lambda: deferred,
        send_message=AsyncMock(),
    )
    return SimpleNamespace(
        user=user,
        response=response,
        followup=SimpleNamespace(send=AsyncMock()),
        command=SimpleNamespace(name="purchasehistory"),
    )


def payload(payment_count):
    return {
        "player": {"username": "FixturePlayer"},
        "banCount": 0,
        "chargebackRate": 0,
        "purchaseTotals": {"USD": "12.50"},
        "payments": [
            {
                "time": 1750000000 + i,
                "price": "12.50",
                "currency": "USD",
                "status": 1,
                "txn_id": f"tx-test-{i}",
                "name": "Fixture Package",
            }
            for i in range(payment_count)
        ],
    }


class PurchaseHistoryResponseTests(IsolatedAsyncioTestCase):
    def setUp(self):
        self.saved_settings = bot.settings
        bot.settings = replace(
            bot.settings,
            staff_role_ids={10},
            purchase_history_user_ids={23},
            history_items_per_page=1,
        )

    def tearDown(self):
        bot.settings = self.saved_settings

    async def run_history(self, user, payments):
        with (
            patch.object(bot.tebex, "get_user", new_callable=AsyncMock, return_value=payload(payments)) as lookup,
            patch.object(bot, "enrich_payment_product_names", new_callable=AsyncMock),
        ):
            await bot.purchasehistory.callback(user, "76561198000000000", private=False)
        lookup.assert_awaited_once()

    async def test_single_page_delegate_has_private_receipt_without_view_keyword(self):
        user = make_interaction()
        await self.run_history(user, 1)
        user.response.defer.assert_awaited_once_with(ephemeral=True, thinking=True)
        user.followup.send.assert_awaited_once()
        kwargs = user.followup.send.await_args.kwargs
        self.assertTrue(kwargs["ephemeral"])
        self.assertNotIn("view", kwargs)
        self.assertIn("file", kwargs)
        self.assertEqual(kwargs["embed"].footer.text, "Page 1/1 • Full receipt attached as .txt")

    async def test_empty_history_receives_single_page_without_view_keyword(self):
        user = make_interaction()
        await self.run_history(user, 0)
        kwargs = user.followup.send.await_args.kwargs
        self.assertNotIn("view", kwargs)
        self.assertIn("No payments found.", kwargs["embed"].description)

    async def test_multiple_pages_keep_paginator_for_staff(self):
        user = make_interaction(user_id=44, staff=True)
        await self.run_history(user, 2)
        user.response.defer.assert_awaited_once_with(ephemeral=False, thinking=True)
        kwargs = user.followup.send.await_args.kwargs
        self.assertFalse(kwargs["ephemeral"])
        self.assertIsInstance(kwargs["view"], bot.PurchaseHistoryView)
        self.assertEqual(len(kwargs["view"].embeds), 2)

    async def test_unexpected_error_after_defer_sends_private_feedback(self):
        user = make_interaction(deferred=True)
        await bot.on_app_command_error(user, RuntimeError("fixture"))
        user.followup.send.assert_awaited_once()
        self.assertTrue(user.followup.send.await_args.kwargs["ephemeral"])
        self.assertNotIn("fixture", user.followup.send.await_args.args[0])

    async def test_unexpected_error_before_defer_sends_private_feedback(self):
        user = make_interaction(deferred=False)
        await bot.on_app_command_error(user, RuntimeError("fixture"))
        user.response.send_message.assert_awaited_once()
        self.assertTrue(user.response.send_message.await_args.kwargs["ephemeral"])

    async def test_unlisted_user_is_denied_without_contacting_tebex(self):
        user = make_interaction(user_id=999)
        with patch.object(bot.tebex, "get_user", new_callable=AsyncMock) as lookup:
            await bot.purchasehistory.callback(user, "76561198000000000")
        lookup.assert_not_awaited()
        self.assertIn("permission", user.followup.send.await_args.args[0].lower())
