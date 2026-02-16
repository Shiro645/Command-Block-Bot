# 🧱 Command Block Bot

A modular Discord bot built for a Minecraft modded server community.

It provides server management tools, verification systems, ticket support, reaction roles, and a fully integrated Minecraft-themed economy system.

---

## 🚀 Features

### 🔐 Staff Commands

- `/add_whitelist <username>` — Add a player to `whitelist.json`
- `/remove_whitelist <username>` — Remove a player from whitelist
- `/check_whitelist <username>` — Check whitelist status
- `/add_block`
- `/add_emerald`
- `/add_item`
- `/add_gear`
- `/xp_add`
- `/xp_set`
- `/level_set`
- `/talent_add`
- `/talent_reset`

---

### 🌍 Minecraft Commands (@everyone)

- `/server_status` — Show server status (players & ping)
- `/ip` — Show join instructions
- `/modpacks` — Show modpack information

---

## ✅ Community Systems

- Verification message with **“Accept & Join”** button
- Automatic `@Player` role assignment
- Ticket system with private support channels
- Reaction role panel
- Welcome and leave messages

---

# 💎 Economy System

A Minecraft-inspired progression system integrated directly into Discord.

## 🪨 Passive Block Mining

Users receive **1–6 random blocks** when sending messages.

Block distribution:
- 6 → Cobblestone
- 4–5 → Cobblestone / Gravel
- 2–3 → Cobblestone / Gravel / Deepslate
- 1 → Cobblestone / Gravel / Deepslate / rare Bedrock

Cooldown configurable in `config.json`.

---

## 💰 Selling Blocks

`/sell`

Block values:
- Cobblestone → 1 emerald
- Gravel → 3 emeralds
- Deepslate → 5 emeralds
- Bedrock → 10 emeralds

---

## 🛒 Market System

`/market`

Buy:
- 4 sticks → 1 emerald
- Gold ingot → 5 emeralds
- Iron ingot → 10 emeralds
- Diamond ingot → 25 emeralds
- Netherite ingot → 100 emeralds

Interactive dropdown + quantity modal.

---

## 🛠 Crafting

`/craft <item> <material>`

Items:
- sword
- pickaxe
- axe
- shovel
- hoe
- helmet
- chestplate
- leggings
- boots

Materials:
- gold
- iron
- diamond
- netherite

Recipes follow Minecraft crafting logic.

---

## 🎒 Inventory

`/inventory`

Displays:
- Blocks
- Emerald balance
- Items
- Gear
- Estimated sell value

---

## ⭐ XP & Talents

Commands:
- `/xp`
- `/talents`
- `/talent_buy`

Users gain XP through activity.
Talent points are earned every 5 levels.

Talent branches:
- Miner
- Trader
- Lucky
- Efficiency

---

# ⚙️ Installation

```bash
git clone https://github.com/Shiro645/Command-Block-Bot.git
cd command-block-bot

python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file:

```
DISCORD_TOKEN=your_bot_token_here
```

Configure `config.json` with your server IDs.

Run:

```bash
python bot.py
```

---

# 🏗️ Project Structure

```
bot.py
database.py
config.json
whitelist.json
economy.db
cogs/
utils/
```

---

# 🔮 Roadmap

- Moderation commands (mute / ban)
- Daily mini-games
- Leaderboards
- Seasonal resets
- Extended progression systems

---

# 📜 License

MIT
