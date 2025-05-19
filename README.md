🛡️ [BOT] TebexPurchaseCheck

A Discord bot built to easily check Tebex transactions and purchase history using the Tebex API. This bot allows server owners and administrators to quickly verify payments and view purchase history directly within Discord.

🚀 Features

Transaction Lookup: Fetches detailed information about specific transactions by Transaction ID.
Purchase History: Retrieves the full purchase history of a player using their SteamID64.
Real-Time Data: Displays live transaction and purchase information, including packages, amounts, status, and more.
Error Handling: Clear error messages if the transaction or player is not found.

⚙️ Setup Instructions

Clone the repository:
- git clone https://github.com/ryanjokhu/-BOT-TebexPurchaseCheck.git
- cd -BOT-TebexPurchaseCheck

Install dependencies:
- pip install discord aiohttp

Configure environment variables:
- Fill in your GUILD_ID, TEBEX_SECRET, and DISCORD_TOKEN in the script.

Run the bot:
- python tebextransactioncheck.py
