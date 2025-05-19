import discord
from discord import app_commands
import aiohttp
import json
from datetime import datetime

GUILD_ID = ''
TEBEX_SECRET = ''
DISCORD_TOKEN = ''

# initialize the bot
class TebexBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        guild = discord.Object(id=GUILD_ID)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)
        print(f"slash commands synced to server - {GUILD_ID}")

bot = TebexBot()

# ==================== transaction command ====================

@bot.tree.command(name="transaction", description="Check Tebex transaction details by Transaction ID")
@app_commands.describe(transaction_id="Transaction ID to look up")
async def transaction(interaction: discord.Interaction, transaction_id: str):
    await interaction.response.defer()

    headers = {
        'X-Tebex-Secret': TEBEX_SECRET,
        'Content-Type': 'application/json'
    }

    async with aiohttp.ClientSession() as session:
        try:
            url = f'https://plugin.tebex.io/payments/{transaction_id}'
            async with session.get(url, headers=headers) as resp:
                raw_data = await resp.text()
                
                if resp.status != 200:
                    await interaction.followup.send(f"[ERROR] Failed to fetch transaction. Status: {resp.status}")
                    print("Raw response:", raw_data)
                    return

                try:
                    data = await resp.json()
                except Exception:
                    await interaction.followup.send("[ERROR] Failed to parse Tebex response as JSON.")
                    print("Raw response (unparsable):", raw_data)
                    return

        except Exception as e:
            await interaction.followup.send(f"[ERROR] Error fetching transaction: {str(e)}")
            return

    # format the response
    player_name = data.get("player", {}).get("name", "Unknown Player")
    player_uuid = data.get("player", {}).get("uuid", "Unknown UUID")
    amount = data.get("amount", "0.00")
    status = data.get("status", "N/A")
    date = data.get("date", "N/A")
    currency = data.get("currency", {}).get("symbol", "$")
    notes = data.get("notes", [])
    
    # list of packages
    package_details = "\n".join([f"- {pkg.get('name', 'Unknown Package')}" for pkg in data.get("packages", [])])

    # notes
    note_details = "\n".join([f"- {n['note']}" for n in notes]) if notes else "No notes available."

    # output message
    response = (
        f"**Transaction Details for ID `{transaction_id}`**\n"
        f"🧑 **Player**: {player_name} (`{player_uuid}`)\n"
        f"💰 **Amount**: {currency}{amount}\n"
        f"📅 **Date**: {date}\n"
        f"📌 **Status**: {status}\n\n"
        f"🎁 **Packages Purchased:**\n{package_details if package_details else 'No packages found.'}\n\n"
        f"📝 **Notes:**\n{note_details}"
    )

    await interaction.followup.send(response)

# ==================== purchase history command ====================

@bot.tree.command(name="purchasehistory", description="Check Tebex purchase history by SteamID64")
@app_commands.describe(uuid="The SteamID64 of the player to look up")
async def purchasehistory(interaction: discord.Interaction, uuid: str):
    await interaction.response.defer()

    headers = {
        'X-Tebex-Secret': TEBEX_SECRET,
        'Content-Type': 'application/json'
    }

    async with aiohttp.ClientSession() as session:
        try:
            url = f'https://plugin.tebex.io/user/{uuid}'
            async with session.get(url, headers=headers) as resp:
                raw_data = await resp.text()
                
                if resp.status != 200:
                    await interaction.followup.send(f"[ERROR] Failed to fetch purchase history. Status: {resp.status}")
                    print("Raw response:", raw_data)
                    return

                try:
                    data = await resp.json()
                except Exception:
                    await interaction.followup.send("[ERROR] Failed to parse Tebex response as JSON.")
                    print("Raw response (unparsable):", raw_data)
                    return

        except Exception as e:
            await interaction.followup.send(f"[ERROR] Error fetching purchase history: {str(e)}")
            return

    # format the response
    username = data.get("player", {}).get("username", "Unknown Username")
    total_spent = data.get("purchaseTotals", {}).get("USD", "0.00")
    ban_count = data.get("banCount", 0)
    chargeback_rate = data.get("chargebackRate", 0)

    # list of payments
    payments = data.get("payments", [])
    payment_details = "\n".join([
        f"- `{datetime.utcfromtimestamp(payment['time']).strftime('%Y-%m-%d %H:%M:%S')}` | ${payment['price']} {payment['currency']} | Status: {'Complete' if payment['status'] == 1 else 'Pending'} | ID: `{payment['txn_id']}`"
        for payment in payments
    ])

    # output message
    response = (
        f"**Purchase History for `{username}`**\n"
        f"💰 **Total Spent (USD):** ${total_spent}\n"
        f"🚫 **Ban Count:** {ban_count}\n"
        f"💳 **Chargeback Rate:** {chargeback_rate}%\n\n"
        f"🎁 **Payments:**\n{payment_details if payment_details else 'No payments found.'}"
    )

    await interaction.followup.send(response[:2000])

bot.run(DISCORD_TOKEN)

