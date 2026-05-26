import os
import discord
from discord.ext import commands
import aiohttp
from bs4 import BeautifulSoup
import asyncio
import re
import urllib.parse

# ─── CONFIG ───────────────────────────────────────────────────────────────────
TOKEN = os.environ.get("TOKEN")   # <-- remplace ici

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "fr-FR,fr;q=0.9",
}

# ─── SCRAPERS ─────────────────────────────────────────────────────────────────

async def scrape_amazon(session, query):
    url = f"https://www.amazon.fr/s?k={urllib.parse.quote(query)}"
    try:
        async with session.get(url, headers=HEADERS, timeout=10) as r:
            soup = BeautifulSoup(await r.text(), "html.parser")
        results = []
        for item in soup.select('[data-component-type="s-search-result"]')[:3]:
            title_el = item.select_one("h2 a span")
            price_el = item.select_one(".a-price .a-offscreen")
            link_el  = item.select_one("h2 a")
            if title_el and price_el:
                results.append({
                    "title": title_el.text.strip()[:60],
                    "price": price_el.text.strip(),
                    "url":   "https://www.amazon.fr" + link_el["href"] if link_el else url,
                })
        return results
    except Exception:
        return []


async def scrape_ldlc(session, query):
    url = f"https://www.ldlc.com/recherche/{urllib.parse.quote(query)}/"
    try:
        async with session.get(url, headers=HEADERS, timeout=10) as r:
            soup = BeautifulSoup(await r.text(), "html.parser")
        results = []
        for item in soup.select(".listing-product li.pdt-item")[:3]:
            title_el = item.select_one(".title-3")
            price_el = item.select_one(".price")
            link_el  = item.select_one("a.pdt-item")
            if title_el and price_el:
                price_text = price_el.text.strip().split("\n")[0]
                results.append({
                    "title": title_el.text.strip()[:60],
                    "price": price_text,
                    "url":   "https://www.ldlc.com" + link_el["href"] if link_el else url,
                })
        return results
    except Exception:
        return []


async def scrape_materiel(session, query):
    url = f"https://www.materiel.net/recherche/{urllib.parse.quote(query)}/"
    try:
        async with session.get(url, headers=HEADERS, timeout=10) as r:
            soup = BeautifulSoup(await r.text(), "html.parser")
        results = []
        for item in soup.select(".listing-product li.pdt-item")[:3]:
            title_el = item.select_one(".title-3")
            price_el = item.select_one(".price")
            link_el  = item.select_one("a.pdt-item")
            if title_el and price_el:
                price_text = price_el.text.strip().split("\n")[0]
                results.append({
                    "title": title_el.text.strip()[:60],
                    "price": price_text,
                    "url":   "https://www.materiel.net" + link_el["href"] if link_el else url,
                })
        return results
    except Exception:
        return []


async def scrape_ebay(session, query):
    url = f"https://www.ebay.fr/sch/i.html?_nkw={urllib.parse.quote(query)}&_sop=15"
    try:
        async with session.get(url, headers=HEADERS, timeout=10) as r:
            soup = BeautifulSoup(await r.text(), "html.parser")
        results = []
        for item in soup.select(".s-item")[:4]:
            title_el = item.select_one(".s-item__title")
            price_el = item.select_one(".s-item__price")
            link_el  = item.select_one("a.s-item__link")
            if title_el and price_el and title_el.text.strip() != "Shop on eBay":
                results.append({
                    "title": title_el.text.strip()[:60],
                    "price": price_el.text.strip(),
                    "url":   link_el["href"] if link_el else url,
                })
        return results[:3]
    except Exception:
        return []


async def scrape_leboncoin(session, query):
    url = f"https://www.leboncoin.fr/recherche?text={urllib.parse.quote(query)}&category=15"
    try:
        async with session.get(url, headers=HEADERS, timeout=10) as r:
            soup = BeautifulSoup(await r.text(), "html.parser")
        results = []
        for item in soup.select("a[data-qa-id='aditem_container']")[:3]:
            title_el = item.select_one("p[data-qa-id='aditem_title']")
            price_el = item.select_one("span[data-qa-id='aditem_price']")
            if title_el and price_el:
                results.append({
                    "title": title_el.text.strip()[:60],
                    "price": price_el.text.strip(),
                    "url":   "https://www.leboncoin.fr" + item["href"],
                })
        return results
    except Exception:
        return []


# ─── COMMANDES ────────────────────────────────────────────────────────────────

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Activity(
        type=discord.ActivityType.watching,
        name="les prix PC 💻"
    ))
    print(f"✅ Bot connecté : {bot.user}")


@bot.command(name="prix")
async def prix(ctx, *, composant: str = None):
    if not composant:
        await ctx.send("❌ Usage : `!prix <composant>`\nEx: `!prix RTX 4070`")
        return

    # Message de chargement
    msg = await ctx.send(f"🔍 Recherche de **{composant}** en cours...")

    async with aiohttp.ClientSession() as session:
        tasks = [
            scrape_amazon(session, composant),
            scrape_ldlc(session, composant),
            scrape_materiel(session, composant),
            scrape_ebay(session, composant),
            scrape_leboncoin(session, composant),
        ]
        amazon, ldlc, materiel, ebay, leboncoin = await asyncio.gather(*tasks)

    stores = {
        "🛒 Amazon":        amazon,
        "💻 LDLC":          ldlc,
        "🖥️ Materiel.net": materiel,
        "🔄 eBay":          ebay,
        "🤝 Leboncoin":     leboncoin,
    }

    embed = discord.Embed(
        title=f"💰 Prix pour : {composant}",
        color=0x5865F2,
    )
    embed.set_footer(text="TechPriceBot • Prix en temps réel")

    found_any = False
    for store_name, results in stores.items():
        if results:
            found_any = True
            lines = []
            for r in results:
                lines.append(f"[{r['title']}]({r['url']}) — **{r['price']}**")
            embed.add_field(
                name=store_name,
                value="\n".join(lines),
                inline=False,
            )
        else:
            embed.add_field(name=store_name, value="*Aucun résultat*", inline=False)

    if not found_any:
        embed.description = "😕 Aucun résultat trouvé. Vérifie le nom du composant."

    await msg.edit(content=None, embed=embed)


@bot.command(name="aide")
async def aide(ctx):
    embed = discord.Embed(
        title="📖 Aide — TechPriceBot",
        description="Bot de comparaison de prix pour composants PC",
        color=0x5865F2,
    )
    embed.add_field(
        name="Commandes",
        value=(
            "`!prix <composant>` — Cherche le prix sur toutes les boutiques\n"
            "`!aide` — Affiche ce message"
        ),
        inline=False,
    )
    embed.add_field(
        name="Exemples",
        value=(
            "`!prix RTX 4070`\n"
            "`!prix Ryzen 5 7600X`\n"
            "`!prix SSD Samsung 1To`\n"
            "`!prix RAM DDR5 32GB`"
        ),
        inline=False,
    )
    embed.add_field(
        name="Boutiques",
        value="Amazon 🛒 • LDLC 💻 • Materiel.net 🖥️ • eBay 🔄 • Leboncoin 🤝",
        inline=False,
    )
    await ctx.send(embed=embed)


# ─── LANCEMENT ────────────────────────────────────────────────────────────────
bot.run(TOKEN)
