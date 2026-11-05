from __future__ import annotations

import asyncio
import io
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable

import aiohttp
try:
    from dotenv import load_dotenv
except ImportError:  # python-dotenv is optional but recommended for local installs.
    load_dotenv = None

if load_dotenv:
    load_dotenv()

import discord
from discord import app_commands


LOGGER = logging.getLogger("tebex_purchase_check")
TEBEX_API_BASE = "https://plugin.tebex.io"
DISCORD_EMBED_DESCRIPTION_LIMIT = 4096
SAFE_DESCRIPTION_LIMIT = 3600
DEFAULT_HISTORY_ITEMS_PER_PAGE = 8
PRODUCT_FETCH_CONCURRENCY = 4

PRODUCT_NAME_KEYS = (
    "name",
    "package_name",
    "packageName",
    "display_name",
    "displayName",
    "title",
    "product_name",
    "productName",
)
PRODUCT_CONTAINER_KEYS = (
    "package",
    "packages",
    "item",
    "items",
    "product",
    "products",
    "contents",
    "content",
)


def _env_required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name, "").strip()
    if not value:
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise RuntimeError(f"Environment variable {name} must be an integer") from exc


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name, "").strip().lower()
    if not value:
        return default
    if value in {"1", "true", "yes", "y", "on"}:
        return True
    if value in {"0", "false", "no", "n", "off"}:
        return False
    raise RuntimeError(f"Environment variable {name} must be true or false")


def _env_int_set(name: str) -> set[int]:
    raw = os.getenv(name, "").strip()
    if not raw:
        return set()

    values: set[int] = set()
    for part in raw.replace(";", ",").split(","):
        part = part.strip()
        if not part:
            continue
        try:
            values.add(int(part))
        except ValueError as exc:
            raise RuntimeError(f"Environment variable {name} contains a non-integer role id: {part}") from exc
    return values


@dataclass(frozen=True)
class Settings:
    guild_id: int
    tebex_secret: str
    discord_token: str
    staff_role_ids: set[int]
    purchase_history_user_ids: set[int]
    history_items_per_page: int
    show_total_spent_in_embed: bool

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            guild_id=int(_env_required("GUILD_ID")),
            tebex_secret=_env_required("TEBEX_SECRET"),
            discord_token=_env_required("DISCORD_TOKEN"),
            staff_role_ids=_env_int_set("STAFF_ROLE_IDS"),
            purchase_history_user_ids=_env_int_set("PURCHASE_HISTORY_USER_IDS"),
            history_items_per_page=max(1, min(15, _env_int("HISTORY_ITEMS_PER_PAGE", DEFAULT_HISTORY_ITEMS_PER_PAGE))),
            show_total_spent_in_embed=_env_bool("SHOW_TOTAL_SPENT_IN_EMBED", False),
        )


settings = Settings.from_env()


class TebexError(RuntimeError):
    pass


class TebexNotFound(TebexError):
    pass


class TebexClient:
    def __init__(self, secret: str):
        self._headers = {
            "X-Tebex-Secret": secret,
            "Content-Type": "application/json",
        }

    async def get_json(self, session: aiohttp.ClientSession, path: str) -> dict[str, Any]:
        url = f"{TEBEX_API_BASE}{path}"
        async with session.get(url, headers=self._headers, timeout=aiohttp.ClientTimeout(total=20)) as response:
            body = await response.text()

            if response.status == 404:
                raise TebexNotFound("Tebex record was not found.")

            if response.status == 401 or response.status == 403:
                raise TebexError("Tebex rejected the configured secret. Check TEBEX_SECRET.")

            if response.status == 429:
                raise TebexError("Tebex rate limited this request. Try again shortly.")

            if response.status < 200 or response.status >= 300:
                LOGGER.warning("Tebex request failed: status=%s body=%s", response.status, body[:1000])
                raise TebexError(f"Tebex request failed with status {response.status}.")

            try:
                payload = await response.json()
            except Exception as exc:
                LOGGER.exception("Tebex returned non-JSON response: %s", body[:1000])
                raise TebexError("Tebex returned an invalid response.") from exc

            if not isinstance(payload, dict):
                raise TebexError("Tebex returned an unexpected response shape.")

            return payload

    async def get_transaction(self, transaction_id: str) -> dict[str, Any]:
        async with aiohttp.ClientSession() as session:
            return await self.get_json(session, f"/payments/{transaction_id}")

    async def get_user(self, uuid: str) -> dict[str, Any]:
        async with aiohttp.ClientSession() as session:
            return await self.get_json(session, f"/user/{uuid}")


tebex = TebexClient(settings.tebex_secret)


class TebexBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        guild = discord.Object(id=settings.guild_id)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)
        LOGGER.info("Slash commands synced to server %s", settings.guild_id)


bot = TebexBot()


def is_staff(interaction: discord.Interaction) -> bool:
    permissions = getattr(interaction.user, "guild_permissions", None)
    if permissions and (permissions.administrator or permissions.manage_guild):
        return True

    if not settings.staff_role_ids:
        return False

    roles = getattr(interaction.user, "roles", [])
    return any(getattr(role, "id", None) in settings.staff_role_ids for role in roles)


def can_view_purchase_history(interaction: discord.Interaction) -> bool:
    """Grant complete receipts only to staff or explicitly allowlisted users."""
    return is_staff(interaction) or getattr(interaction.user, "id", None) in settings.purchase_history_user_ids


def purchase_history_response_is_private(interaction: discord.Interaction, private: bool) -> bool:
    """Non-staff delegates cannot post financial records to public channels."""
    return private or not is_staff(interaction)


def as_text(value: Any, fallback: str = "N/A") -> str:
    if value is None:
        return fallback
    text = str(value).strip()
    return text if text else fallback


def truncate_text(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    return value[: max(0, limit - 1)].rstrip() + "…"


def money(value: Any, currency: str | None = None, symbol: str | None = None) -> str:
    text = as_text(value, "0.00")
    try:
        amount = Decimal(text)
        text = f"{amount:,.2f}"
    except (InvalidOperation, ValueError):
        pass

    if symbol:
        return f"{symbol}{text}"
    if currency:
        return f"{text} {currency}"
    return text


def format_timestamp(value: Any) -> str:
    if value is None:
        return "Unknown date"

    try:
        timestamp = int(value)
        return datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    except (TypeError, ValueError, OSError):
        pass

    text = as_text(value, "Unknown date")
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    except ValueError:
        return text


def status_label(value: Any) -> str:
    status_map = {
        1: "Complete",
        2: "Refunded",
        3: "Chargeback",
        4: "Declined",
        5: "Pending",
    }
    try:
        numeric = int(value)
        return status_map.get(numeric, f"Unknown ({numeric})")
    except (TypeError, ValueError):
        return as_text(value, "Unknown")


def unique_text(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = as_text(value, "").strip()
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(text)
    return result


def _collect_product_names(value: Any, *, allow_plain_string: bool = False) -> list[str]:
    if value is None:
        return []

    if isinstance(value, str):
        return [value] if allow_plain_string and value.strip() else []

    if isinstance(value, list):
        names: list[str] = []
        for item in value:
            names.extend(_collect_product_names(item, allow_plain_string=True))
        return unique_text(names)

    if not isinstance(value, dict):
        return []

    names: list[str] = []
    for key in PRODUCT_NAME_KEYS:
        candidate = value.get(key)
        if isinstance(candidate, str) and candidate.strip():
            names.append(candidate)
            break

    for key in PRODUCT_CONTAINER_KEYS:
        if key in value:
            names.extend(_collect_product_names(value.get(key), allow_plain_string=True))

    return unique_text(names)


def package_names(packages: Iterable[Any]) -> list[str]:
    return _collect_product_names(list(packages), allow_plain_string=True)


def transaction_id_from_payment(payment: dict[str, Any]) -> str:
    return as_text(payment.get("txn_id") or payment.get("transaction_id") or payment.get("id"), "")


def product_names_from_payment(payment: dict[str, Any]) -> list[str]:
    names: list[str] = []

    enriched = payment.get("_product_names")
    if isinstance(enriched, list):
        names.extend(as_text(name, "") for name in enriched)

    for key in PRODUCT_CONTAINER_KEYS:
        if key in payment:
            names.extend(_collect_product_names(payment.get(key), allow_plain_string=True))

    # Some Tebex responses use one direct product/package name instead of a nested package object.
    for key in PRODUCT_NAME_KEYS:
        candidate = payment.get(key)
        if isinstance(candidate, str) and candidate.strip():
            names.append(candidate)

    return unique_text(names)


async def enrich_payment_product_names(payments: list[dict[str, Any]]) -> None:
    """Fetch transaction details for rows that do not include package names in the user-history response."""

    missing = [payment for payment in payments if not product_names_from_payment(payment) and transaction_id_from_payment(payment)]
    if not missing:
        return

    semaphore = asyncio.Semaphore(PRODUCT_FETCH_CONCURRENCY)

    async with aiohttp.ClientSession() as session:
        async def enrich_one(payment: dict[str, Any]) -> None:
            txn_id = transaction_id_from_payment(payment)
            if not txn_id:
                return

            async with semaphore:
                try:
                    transaction = await tebex.get_json(session, f"/payments/{txn_id}")
                except Exception as exc:
                    LOGGER.warning("Could not enrich Tebex transaction %s with package names: %s", txn_id, exc)
                    return

            names = product_names_from_payment(transaction)
            if names:
                payment["_product_names"] = names

        await asyncio.gather(*(enrich_one(payment) for payment in missing))


def normalize_payments(data: dict[str, Any]) -> list[dict[str, Any]]:
    payments = data.get("payments", [])
    if not isinstance(payments, list):
        return []

    normalized = [payment.copy() for payment in payments if isinstance(payment, dict)]
    normalized.sort(key=lambda payment: int(payment.get("time") or 0), reverse=True)
    return normalized


def player_name_from_user_payload(data: dict[str, Any]) -> str:
    player = data.get("player", {})
    if isinstance(player, dict):
        return as_text(player.get("username") or player.get("name"), "Unknown player")
    return "Unknown player"


def build_payment_line(index: int, payment: dict[str, Any], *, markdown: bool = True) -> str:
    txn_id = transaction_id_from_payment(payment) or "Unknown transaction"
    price = money(payment.get("price") or payment.get("amount"), currency=as_text(payment.get("currency"), ""))
    status = status_label(payment.get("status"))
    date = format_timestamp(payment.get("time") or payment.get("date"))
    products = product_names_from_payment(payment)
    product_text = truncate_text(", ".join(products), 140) if products else "Product unavailable"

    if markdown:
        return f"{index}. **{product_text}**\n   `{date}` | {price} | {status} | Txn: `{txn_id}`"

    return f"{index}. Product: {product_text} | Date: {date} | Amount: {price} | Status: {status} | Transaction: {txn_id}"


def build_history_pages(payments: list[dict[str, Any]], items_per_page: int) -> list[str]:
    if not payments:
        return ["No payments found."]

    pages: list[str] = []
    current_lines: list[str] = []

    for index, payment in enumerate(payments, start=1):
        line = build_payment_line(index, payment)
        candidate = "\n".join([*current_lines, line])

        if current_lines and (len(current_lines) >= items_per_page or len(candidate) > SAFE_DESCRIPTION_LIMIT):
            pages.append("\n".join(current_lines))
            current_lines = [line]
        else:
            current_lines.append(line)

    if current_lines:
        pages.append("\n".join(current_lines))

    return pages


def build_history_text_file(uuid: str, data: dict[str, Any], payments: list[dict[str, Any]]) -> discord.File:
    username = player_name_from_user_payload(data)
    totals = data.get("purchaseTotals", {}) if isinstance(data.get("purchaseTotals"), dict) else {}
    lines = [
        f"Purchase history for: {username}",
        f"Lookup UUID/SteamID64: {uuid}",
        f"Total spent USD: ${as_text(totals.get('USD'), '0.00')}",
        f"Ban count: {as_text(data.get('banCount'), '0')}",
        f"Chargeback rate: {as_text(data.get('chargebackRate'), '0')}%",
        f"Payment count shown by Tebex response: {len(payments)}",
        "",
        "Payments:",
    ]

    if payments:
        lines.extend(build_payment_line(index, payment, markdown=False) for index, payment in enumerate(payments, start=1))
    else:
        lines.append("No payments found.")

    buffer = io.BytesIO("\n".join(lines).encode("utf-8"))
    safe_uuid = "".join(char for char in uuid if char.isalnum() or char in ("-", "_"))[:64] or "player"
    return discord.File(buffer, filename=f"tebex_purchase_history_{safe_uuid}.txt")


class PurchaseHistoryView(discord.ui.View):
    def __init__(self, *, pages: list[str], embeds: list[discord.Embed], owner_id: int):
        super().__init__(timeout=300)
        self.pages = pages
        self.embeds = embeds
        self.owner_id = owner_id
        self.index = 0
        self._sync_buttons()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id == self.owner_id or is_staff(interaction):
            return True
        await interaction.response.send_message("Only staff can page through this purchase history.", ephemeral=True)
        return False

    def _sync_buttons(self) -> None:
        self.previous_page.disabled = self.index <= 0
        self.next_page.disabled = self.index >= len(self.embeds) - 1

    async def _update(self, interaction: discord.Interaction) -> None:
        self._sync_buttons()
        await interaction.response.edit_message(embed=self.embeds[self.index], view=self)

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.secondary)
    async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.index = max(0, self.index - 1)
        await self._update(interaction)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.secondary)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.index = min(len(self.embeds) - 1, self.index + 1)
        await self._update(interaction)


async def send_error(interaction: discord.Interaction, message: str) -> None:
    await interaction.followup.send(f"[ERROR] {message}", ephemeral=True)


async def send_unauthorized(interaction: discord.Interaction) -> None:
    await interaction.followup.send("You do not have permission to use this command.", ephemeral=True)


@bot.tree.command(name="transaction", description="Check Tebex transaction details by transaction ID")
@app_commands.describe(transaction_id="Transaction ID to look up")
async def transaction(interaction: discord.Interaction, transaction_id: str):
    await interaction.response.defer(ephemeral=True, thinking=True)
    if not is_staff(interaction):
        await send_unauthorized(interaction)
        return

    try:
        data = await tebex.get_transaction(transaction_id.strip())
    except TebexNotFound:
        await send_error(interaction, "No transaction was found for that ID.")
        return
    except TebexError as exc:
        await send_error(interaction, str(exc))
        return
    except asyncio.TimeoutError:
        await send_error(interaction, "Tebex did not respond in time.")
        return

    player = data.get("player", {}) if isinstance(data.get("player"), dict) else {}
    currency = data.get("currency", {}) if isinstance(data.get("currency"), dict) else {}
    products = product_names_from_payment(data)
    notes = data.get("notes", []) if isinstance(data.get("notes", []), list) else []

    embed = discord.Embed(
        title=f"Transaction {transaction_id}",
        color=discord.Color.green() if str(data.get("status", "")).lower() in {"complete", "completed", "paid", "1"} else discord.Color.orange(),
    )
    embed.add_field(name="Player", value=f"{as_text(player.get('name'), 'Unknown player')} (`{as_text(player.get('uuid'), 'Unknown UUID')}`)", inline=False)
    embed.add_field(name="Amount", value=money(data.get("amount"), symbol=currency.get("symbol")), inline=True)
    embed.add_field(name="Status", value=as_text(data.get("status")), inline=True)
    embed.add_field(name="Date", value=format_timestamp(data.get("date")), inline=False)
    embed.add_field(name="Products", value="\n".join(f"- {name}" for name in products)[:1024] if products else "No products found.", inline=False)

    note_lines = []
    for note in notes:
        if isinstance(note, dict):
            note_lines.append(f"- {as_text(note.get('note'))}")
        else:
            note_lines.append(f"- {as_text(note)}")
    embed.add_field(name="Notes", value="\n".join(note_lines)[:1024] if note_lines else "No notes available.", inline=False)

    await interaction.followup.send(embed=embed, ephemeral=True)


@bot.tree.command(name="purchasehistory", description="Check full Tebex purchase history by SteamID64/UUID")
@app_commands.describe(
    uuid="SteamID64/UUID of the player to look up",
    private="Keep the receipt visible only to you. Disable only when staff intentionally need it posted in-channel.",
)
async def purchasehistory(interaction: discord.Interaction, uuid: str, private: bool = True):
    is_authorized = can_view_purchase_history(interaction)
    response_is_private = purchase_history_response_is_private(interaction, private)
    await interaction.response.defer(ephemeral=response_is_private, thinking=True)
    if not is_authorized:
        await send_unauthorized(interaction)
        return

    uuid = uuid.strip()

    try:
        data = await tebex.get_user(uuid)
    except TebexNotFound:
        await send_error(interaction, "No Tebex user was found for that SteamID64/UUID.")
        return
    except TebexError as exc:
        await send_error(interaction, str(exc))
        return
    except asyncio.TimeoutError:
        await send_error(interaction, "Tebex did not respond in time.")
        return

    username = player_name_from_user_payload(data)
    totals = data.get("purchaseTotals", {}) if isinstance(data.get("purchaseTotals"), dict) else {}
    payments = normalize_payments(data)
    await enrich_payment_product_names(payments)
    pages = build_history_pages(payments, settings.history_items_per_page)

    embeds: list[discord.Embed] = []
    for page_index, page in enumerate(pages, start=1):
        embed = discord.Embed(
            title=f"Purchase History: {username}",
            description=page[:DISCORD_EMBED_DESCRIPTION_LIMIT],
            color=discord.Color.blurple(),
        )
        if settings.show_total_spent_in_embed:
            embed.add_field(name="Total Spent (USD)", value=f"${as_text(totals.get('USD'), '0.00')}", inline=True)
        embed.add_field(name="Payments", value=str(len(payments)), inline=True)
        embed.add_field(name="Ban Count", value=as_text(data.get("banCount"), "0"), inline=True)
        embed.add_field(name="Chargeback Rate", value=f"{as_text(data.get('chargebackRate'), '0')}%", inline=True)
        embed.set_footer(text=f"Page {page_index}/{len(pages)} • Full receipt attached as .txt")
        embeds.append(embed)

    attachment = build_history_text_file(uuid, data, payments)
    view = PurchaseHistoryView(pages=pages, embeds=embeds, owner_id=interaction.user.id) if len(embeds) > 1 else None
    await interaction.followup.send(embed=embeds[0], view=view, file=attachment, ephemeral=response_is_private)


if __name__ == "__main__":
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    bot.run(settings.discord_token)
