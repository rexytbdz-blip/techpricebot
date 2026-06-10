import os
import discord
from discord.ext import commands
import aiohttp
from bs4 import BeautifulSoup
import asyncio
import urllib.parse

# ─── CONFIG ───────────────────────────────────────────────────────────────────
TOKEN = os.environ.get("TOKEN")

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

    msg = await ctx.send(f"🔍 Recherche de **{composant}** en cours...")

    async with aiohttp.ClientSession() as session:
        tasks = [
            scrape_ldlc(session, composant),
            scrape_materiel(session, composant),
        ]
        ldlc, materiel = await asyncio.gather(*tasks)

    stores = {
        "💻 LDLC":          ldlc,
        "🖥️ Materiel.net": materiel,
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

# ─── BASE DE DONNÉES BOTTLENECK (mise à jour technical.city) ──────────────────

CPU_SCORES = {
    # AMD Ryzen 9000
    "ryzen 9 9950x": 98, "ryzen 9 9900x": 90, "ryzen 7 9700x": 82,
    "ryzen 7 9800x3d": 88, "ryzen 5 9600x": 74, "ryzen 5 9600": 71,
    # AMD Ryzen 7000
    "ryzen 9 7950x": 95, "ryzen 9 7950x3d": 97, "ryzen 9 7900x": 88,
    "ryzen 9 7900x3d": 91, "ryzen 9 7900": 85, "ryzen 7 7700x": 78,
    "ryzen 7 7700": 74, "ryzen 7 7800x3d": 83, "ryzen 5 7600x": 68,
    "ryzen 5 7600": 65,
    # AMD Ryzen 5000
    "ryzen 9 5950x": 85, "ryzen 9 5900x": 80, "ryzen 7 5800x3d": 78,
    "ryzen 7 5800x": 72, "ryzen 7 5800": 69, "ryzen 5 5600x": 62,
    "ryzen 5 5600": 59, "ryzen 5 5500": 52,
    # AMD Ryzen 3000
    "ryzen 9 3900x": 68, "ryzen 9 3900xt": 70, "ryzen 7 3700x": 60,
    "ryzen 7 3800x": 62, "ryzen 7 3800xt": 63, "ryzen 5 3600x": 54,
    "ryzen 5 3600": 52, "ryzen 3 3300x": 40,
    # Intel Core 14ème gen
    "i9-14900k": 96, "i9-14900kf": 96, "i9-14900": 90, "i9-14900f": 90,
    "i7-14700k": 86, "i7-14700kf": 86, "i7-14700": 80, "i7-14700f": 80,
    "i5-14600k": 72, "i5-14600kf": 72, "i5-14500": 64, "i5-14400": 60,
    "i5-14400f": 60, "i3-14100": 42, "i3-14100f": 42,
    # Intel Core 13ème gen
    "i9-13900k": 94, "i9-13900kf": 94, "i9-13900": 88, "i9-13900f": 88,
    "i7-13700k": 84, "i7-13700kf": 84, "i7-13700": 78, "i7-13700f": 78,
    "i5-13600k": 70, "i5-13600kf": 70, "i5-13500": 62, "i5-13400": 58,
    "i5-13400f": 58, "i3-13100": 40, "i3-13100f": 40,
    # Intel Core 12ème gen
    "i9-12900k": 88, "i9-12900kf": 88, "i9-12900": 82, "i7-12700k": 78,
    "i7-12700kf": 78, "i7-12700": 72, "i5-12600k": 65, "i5-12600kf": 65,
    "i5-12400": 56, "i5-12400f": 56, "i3-12100": 38, "i3-12100f": 38,
    # Intel Core 11ème gen
    "i9-11900k": 72, "i7-11700k": 65, "i5-11600k": 56, "i5-11400": 50,
    "i5-11400f": 50, "i3-11100": 34,
    # Intel Core 10ème gen
    "i9-10900k": 65, "i7-10700k": 58, "i5-10600k": 50, "i5-10400": 44,
    "i5-10400f": 44, "i3-10100": 32,
}

GPU_SCORES = {
    # NVIDIA RTX 50xx
    "rtx 5090": 98, "rtx 5080": 88, "rtx 5070 ti": 80, "rtx 5070": 72,
    "rtx 5060 ti": 60, "rtx 5060": 50,
    # NVIDIA RTX 40xx
    "rtx 4090": 95, "rtx 4080 super": 84, "rtx 4080": 83,
    "rtx 4070 ti super": 78, "rtx 4070 ti": 76, "rtx 4070 super": 73,
    "rtx 4070": 66, "rtx 4060 ti": 56, "rtx 4060": 46,
    # NVIDIA RTX 30xx
    "rtx 3090 ti": 72, "rtx 3090": 65, "rtx 3080 ti": 64,
    "rtx 3080 12gb": 62, "rtx 3080": 60, "rtx 3070 ti": 55,
    "rtx 3070": 52, "rtx 3060 ti": 47, "rtx 3060": 40, "rtx 3050": 30,
    # NVIDIA RTX 20xx
    "rtx 2080 ti": 55, "rtx 2080 super": 48, "rtx 2080": 46,
    "rtx 2070 super": 43, "rtx 2070": 40, "rtx 2060 super": 37,
    "rtx 2060": 34,
    # NVIDIA GTX 16xx
    "gtx 1660 ti": 28, "gtx 1660 super": 27, "gtx 1660": 24,
    "gtx 1650 super": 21, "gtx 1650": 18,
    # AMD RX 9000
    "rx 9070 xt": 67, "rx 9070": 62,
    # AMD RX 7000
    "rx 7900 xtx": 78, "rx 7900 xt": 72, "rx 7900 gre": 65,
    "rx 7800 xt": 58, "rx 7700 xt": 52, "rx 7600 xt": 42, "rx 7600": 38,
    # AMD RX 6000
    "rx 6950 xt": 68, "rx 6900 xt": 65, "rx 6800 xt": 60, "rx 6800": 56,
    "rx 6750 xt": 50, "rx 6700 xt": 46, "rx 6700": 42, "rx 6650 xt": 40,
    "rx 6600 xt": 37, "rx 6600": 34, "rx 6500 xt": 20,
    # AMD RX 5000
    "rx 5700 xt": 32, "rx 5700": 29, "rx 5600 xt": 25,
}

CPU_RECOMMANDATIONS = {
    "bas":    ("Ryzen 5 5600", "Intel i5-12400F"),
    "moyen":  ("Ryzen 5 7600X", "Intel i5-13600K"),
    "haut":   ("Ryzen 7 7700X", "Intel i7-13700K"),
    "top":    ("Ryzen 9 7900X", "Intel i9-13900K"),
}

GPU_RECOMMANDATIONS = {
    "bas":    ("RTX 3060", "RX 6600"),
    "moyen":  ("RTX 3070", "RX 6700 XT"),
    "haut":   ("RTX 4070", "RX 7800 XT"),
    "top":    ("RTX 4080", "RX 7900 XT"),
}

def get_niveau(score):
    if score < 50:
        return "bas"
    elif score < 70:
        return "moyen"
    elif score < 85:
        return "haut"
    else:
        return "top"

def analyser_bottleneck(cpu_score, gpu_score):
    diff = abs(cpu_score - gpu_score)
    ratio = cpu_score / gpu_score if gpu_score > 0 else 1
    if diff <= 10:
        return diff, "aucun"
    elif cpu_score < gpu_score:
        return round((1 - ratio) * 100), "cpu"
    else:
        return round((ratio - 1) * 100), "gpu"


@bot.command(name="bottleneck")
async def bottleneck(ctx, *, args: str = None):
    if not args or "/" not in args:
        await ctx.send(
            "❌ Usage : `!bottleneck <CPU> / <GPU>`\n"
            "Exemple : `!bottleneck Ryzen 5 7600X / RTX 4070`"
        )
        return

    parts = args.split("/")
    if len(parts) != 2:
        await ctx.send("❌ Sépare bien le CPU et le GPU avec `/`\nExemple : `!bottleneck Ryzen 5 5600 / RTX 3070`")
        return

    cpu_input = parts[0].strip().lower()
    gpu_input = parts[1].strip().lower()

    cpu_score = None
    cpu_nom = None
    for key, score in CPU_SCORES.items():
        if key in cpu_input or cpu_input in key:
            cpu_score = score
            cpu_nom = key.upper()
            break

    gpu_score = None
    gpu_nom = None
    for key, score in GPU_SCORES.items():
        if key in gpu_input or gpu_input in key:
            gpu_score = score
            gpu_nom = key.upper()
            break

    if cpu_score is None:
        await ctx.send(f"❌ CPU **{parts[0].strip()}** non reconnu.\nEssaie avec le nom exact, ex: `Ryzen 5 7600X` ou `i5-13600K`")
        return

    if gpu_score is None:
        await ctx.send(f"❌ GPU **{parts[1].strip()}** non reconnu.\nEssaie avec le nom exact, ex: `RTX 4070` ou `RX 7800 XT`")
        return

    msg = await ctx.send("🔍 Analyse du bottleneck en cours...")

    pourcentage, type_bn = analyser_bottleneck(cpu_score, gpu_score)

    if type_bn == "aucun" or pourcentage <= 10:
        couleur = 0x00FF00
        statut = "✅ Aucun bottleneck"
        description = "Ton CPU et ton GPU sont parfaitement équilibrés ! Belle configuration 🎉"
    elif pourcentage <= 20:
        couleur = 0xFFA500
        statut = "⚠️ Bottleneck léger"
        description = "Il y a un petit déséquilibre mais ça reste jouable."
    else:
        couleur = 0xFF0000
        statut = "🔴 Bottleneck sévère"
        description = "Ton build est très déséquilibré, tu perds beaucoup de performances !"

    embed = discord.Embed(title="🔬 Analyse Bottleneck", color=couleur)
    embed.add_field(name="🖥️ CPU", value=f"`{cpu_nom}`", inline=True)
    embed.add_field(name="🎮 GPU", value=f"`{gpu_nom}`", inline=True)
    embed.add_field(name="📊 Résultat", value=f"**{statut}**\n{description}", inline=False)

    barre_pleine = min(round(pourcentage / 5), 20)
    barre_vide = 20 - barre_pleine
    barre = "🟥" * barre_pleine + "⬜" * barre_vide
    embed.add_field(name=f"Bottleneck : {pourcentage}%", value=barre, inline=False)

    if type_bn == "cpu":
        niveau_gpu = get_niveau(gpu_score)
        reco_cpu = CPU_RECOMMANDATIONS[niveau_gpu]
        embed.add_field(
            name="💡 Conseil",
            value=(
                f"Ton **CPU est trop faible** pour ta carte graphique.\n"
                f"**CPUs recommandés :**\n• {reco_cpu[0]}\n• {reco_cpu[1]}"
            ),
            inline=False,
        )
        async with aiohttp.ClientSession() as session:
            ldlc1, mat1 = await asyncio.gather(
                scrape_ldlc(session, reco_cpu[0]),
                scrape_materiel(session, reco_cpu[0]),
            )
        prix_lines = []
        if ldlc1:
            prix_lines.append(f"💻 LDLC : [{ldlc1[0]['title'][:40]}]({ldlc1[0]['url']}) — **{ldlc1[0]['price']}**")
        if mat1:
            prix_lines.append(f"🖥️ Materiel.net : [{mat1[0]['title'][:40]}]({mat1[0]['url']}) — **{mat1[0]['price']}**")
        if prix_lines:
            embed.add_field(name=f"🛒 Prix pour {reco_cpu[0]}", value="\n".join(prix_lines), inline=False)

    elif type_bn == "gpu":
        niveau_cpu = get_niveau(cpu_score)
        reco_gpu = GPU_RECOMMANDATIONS[niveau_cpu]
        embed.add_field(
            name="💡 Conseil",
            value=(
                f"Ta **GPU est trop faible** pour ton processeur.\n"
                f"**GPUs recommandés :**\n• {reco_gpu[0]}\n• {reco_gpu[1]}"
            ),
            inline=False,
        )
        async with aiohttp.ClientSession() as session:
            ldlc1, mat1 = await asyncio.gather(
                scrape_ldlc(session, reco_gpu[0]),
                scrape_materiel(session, reco_gpu[0]),
            )
        prix_lines = []
        if ldlc1:
            prix_lines.append(f"💻 LDLC : [{ldlc1[0]['title'][:40]}]({ldlc1[0]['url']}) — **{ldlc1[0]['price']}**")
        if mat1:
            prix_lines.append(f"🖥️ Materiel.net : [{mat1[0]['title'][:40]}]({mat1[0]['url']}) — **{mat1[0]['price']}**")
        if prix_lines:
            embed.add_field(name=f"🛒 Prix pour {reco_gpu[0]}", value="\n".join(prix_lines), inline=False)
    else:
        embed.add_field(name="💡 Conseil", value="Ton build est bien équilibré, profite de tes jeux ! 🎮", inline=False)

    embed.set_footer(text="TechPriceBot • Analyse Bottleneck")
    await msg.edit(content=None, embed=embed)
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
        value="LDLC 💻 • Materiel.net 🖥️",
        inline=False,
    )
    await ctx.send(embed=embed)


# ─── LANCEMENT ────────────────────────────────────────────────────────────────
bot.run(TOKEN)
