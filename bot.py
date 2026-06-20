import os
import json
import discord
from discord.ext import commands
import aiohttp
from bs4 import BeautifulSoup
import asyncio
import urllib.parse
import google.generativeai as genai

# ─── CONFIG ───────────────────────────────────────────────────────────────────
TOKEN = os.environ.get("TOKEN")
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.0-flash")

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

# ─── HELPER IA ────────────────────────────────────────────────────────────────
def gemini(system: str, prompt: str) -> str:
    response = model.generate_content(f"{system}\n\n{prompt}")
    return response.text

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


# ── !prix ─────────────────────────────────────────────────────────────────────
@bot.command(name="prix")
async def prix(ctx, *, composant: str = None):
    if not composant:
        await ctx.send("❌ Usage : `!prix <composant>`\nEx: `!prix RTX 4070`")
        return

    msg = await ctx.send(f"🔍 Recherche de **{composant}** en cours...")

    async with aiohttp.ClientSession() as session:
        ldlc, materiel = await asyncio.gather(
            scrape_ldlc(session, composant),
            scrape_materiel(session, composant),
        )

    embed = discord.Embed(title=f"💰 Prix pour : {composant}", color=0x5865F2)
    embed.set_footer(text="RexyBot • Prix en temps réel")

    found_any = False
    for store_name, results in [("💻 LDLC", ldlc), ("🖥️ Materiel.net", materiel)]:
        if results:
            found_any = True
            lines = [f"[{r['title']}]({r['url']}) — **{r['price']}**" for r in results]
            embed.add_field(name=store_name, value="\n".join(lines), inline=False)
        else:
            embed.add_field(name=store_name, value="*Aucun résultat*", inline=False)

    if not found_any:
        embed.description = "😕 Aucun résultat trouvé. Vérifie le nom du composant."

    await msg.edit(content=None, embed=embed)


# ── !bottleneck ───────────────────────────────────────────────────────────────
@bot.command(name="bottleneck")
async def bottleneck(ctx, *, args: str = None):
    if not args or "/" not in args:
        await ctx.send(
            "❌ Usage : `!bottleneck <CPU> / <GPU>`\n"
            "Exemple : `!bottleneck Ryzen 5 7600X / RTX 4070`"
        )
        return

    parts = args.split("/", 1)
    cpu = parts[0].strip()
    gpu = parts[1].strip()

    msg = await ctx.send(f"🤖 Analyse IA du bottleneck : **{cpu}** + **{gpu}**...")

    try:
        reponse = await asyncio.to_thread(
            gemini,
            (
                "Tu es un expert en hardware PC. Tu analyses les bottlenecks entre CPU et GPU "
                "avec précision. Tu réponds UNIQUEMENT en français, de façon concise et structurée. "
                "Tu connais tous les composants AMD, Intel et NVIDIA sortis jusqu'en 2025. "
                "N'utilise pas de markdown avec des astérisques, utilise du texte simple."
            ),
            (
                f"Analyse le bottleneck entre :\n"
                f"- CPU : {cpu}\n"
                f"- GPU : {gpu}\n\n"
                f"Réponds avec exactement ce format :\n"
                f"**Résultat :** [✅ Équilibré / ⚠️ Bottleneck léger / 🔴 Bottleneck sévère]\n"
                f"**Bottleneck estimé :** X% (côté CPU ou GPU)\n"
                f"**Impact gaming :** 1080p / 1440p / 4K (une ligne par résolution)\n"
                f"**Conseil :** (upgrade recommandé si bottleneck > 15%, sinon confirme que c'est bon)"
            ),
        )
    except Exception as e:
        await msg.edit(content=f"❌ Erreur IA : {e}")
        return

    embed = discord.Embed(
        title=f"🔬 Bottleneck — {cpu} + {gpu}",
        description=reponse,
        color=0xFEE75C,
    )
    embed.set_footer(text="RexyBot • Analyse IA powered by Gemini")
    await msg.edit(content=None, embed=embed)


# ── !build ────────────────────────────────────────────────────────────────────
@bot.command(name="build")
async def build(ctx, *, args: str = None):
    if not args:
        await ctx.send(
            "❌ Usage : `!build <budget en euros>`\n"
            "Exemple : `!build 800`"
        )
        return

    budget_str = args.replace("€", "").replace(" ", "").replace(",", "")
    try:
        budget = int(budget_str)
    except ValueError:
        await ctx.send("❌ Le budget doit être un nombre.\nExemple : `!build 800`")
        return

    if budget < 300:
        await ctx.send("❌ Le budget minimum est de **300€** pour un PC gaming.")
        return

    msg = await ctx.send(f"🤖 L'IA prépare ta config pour **{budget}€**...")

    # Étape 1 : Gemini génère la config en JSON
    try:
        json_brut = await asyncio.to_thread(
            gemini,
            (
                "Tu es un expert en configuration PC gaming sur le marché français. "
                "Tu réponds UNIQUEMENT avec un objet JSON valide, sans texte avant ni après, "
                "sans balises markdown, sans backticks, sans ```json."
            ),
            (
                f"Génère une configuration PC gaming optimisée pour un budget de {budget}€ sur le marché français.\n"
                f"Réponds UNIQUEMENT avec ce JSON (noms courts et précis pour les recherches LDLC) :\n"
                f'{{"cpu":"<nom>","gpu":"<nom>","ram":"<nom>","ssd":"<nom>","mobo":"<nom>","psu":"<nom>","case":"<nom>","description":"<phrase courte>"}}'
            ),
        )
    except Exception as e:
        await msg.edit(content=f"❌ Erreur IA : {e}")
        return

    # Parser le JSON
    try:
        json_propre = json_brut.strip().strip("```json").strip("```").strip()
        config = json.loads(json_propre)
    except json.JSONDecodeError:
        await msg.edit(content="❌ Erreur lors de la génération de la config. Réessaie.")
        return

    await msg.edit(content=f"🔍 Recherche des prix pour ta config **{budget}€**...")

    # Étape 2 : scraping parallèle pour tous les composants
    async with aiohttp.ClientSession() as session:
        (
            cpu_ldlc, cpu_mat,
            gpu_ldlc, gpu_mat,
            ram_ldlc,
            ssd_ldlc,
            mobo_ldlc,
            psu_ldlc,
            case_ldlc,
        ) = await asyncio.gather(
            scrape_ldlc(session, config["cpu"]),
            scrape_materiel(session, config["cpu"]),
            scrape_ldlc(session, config["gpu"]),
            scrape_materiel(session, config["gpu"]),
            scrape_ldlc(session, config["ram"]),
            scrape_ldlc(session, config["ssd"]),
            scrape_ldlc(session, config["mobo"]),
            scrape_ldlc(session, config["psu"]),
            scrape_ldlc(session, config["case"]),
        )

    embed = discord.Embed(
        title=f"🖥️ Config PC {budget}€",
        description=f"*{config.get('description', '')}*",
        color=0x5865F2,
    )

    def champ(ldlc_res, mat_res=None):
        lines = []
        if ldlc_res:
            lines.append(f"💻 LDLC : [{ldlc_res[0]['title'][:40]}]({ldlc_res[0]['url']}) — **{ldlc_res[0]['price']}**")
        if mat_res:
            lines.append(f"🖥️ Materiel.net : [{mat_res[0]['title'][:40]}]({mat_res[0]['url']}) — **{mat_res[0]['price']}**")
        return "\n".join(lines) if lines else "*Prix non disponible*"

    embed.add_field(name=f"⚙️ CPU — {config['cpu']}",       value=champ(cpu_ldlc, cpu_mat), inline=False)
    embed.add_field(name=f"🎮 GPU — {config['gpu']}",       value=champ(gpu_ldlc, gpu_mat), inline=False)
    embed.add_field(name=f"🧠 RAM — {config['ram']}",       value=champ(ram_ldlc),          inline=False)
    embed.add_field(name=f"💾 SSD — {config['ssd']}",       value=champ(ssd_ldlc),          inline=False)
    embed.add_field(name=f"🔌 Carte mère — {config['mobo']}", value=champ(mobo_ldlc),       inline=False)
    embed.add_field(name=f"⚡ Alimentation — {config['psu']}", value=champ(psu_ldlc),       inline=False)
    embed.add_field(name=f"📦 Boîtier — {config['case']}",  value=champ(case_ldlc),         inline=False)

    embed.set_footer(text="RexyBot • Config IA + Prix temps réel LDLC & Materiel.net")
    await msg.edit(content=None, embed=embed)


# ── !aide ─────────────────────────────────────────────────────────────────────
@bot.command(name="aide")
async def aide(ctx):
    embed = discord.Embed(
        title="📖 Aide — RexyBot",
        description="Bot IA spécialisé en composants PC 🤖",
        color=0x5865F2,
    )
    embed.add_field(
        name="Commandes",
        value=(
            "`!prix <composant>` — Cherche le prix sur LDLC & Materiel.net\n"
            "`!bottleneck <CPU> / <GPU>` — Analyse IA du bottleneck\n"
            "`!build <budget>` — Config PC complète générée par l'IA\n"
            "`!aide` — Affiche ce message"
        ),
        inline=False,
    )
    embed.add_field(
        name="Exemples",
        value=(
            "`!prix RTX 4070`\n"
            "`!bottleneck Ryzen 5 7600X / RTX 4070`\n"
            "`!build 1000`"
        ),
        inline=False,
    )
    embed.add_field(name="Boutiques", value="LDLC 💻 • Materiel.net 🖥️", inline=False)
    await ctx.send(embed=embed)


# ─── LANCEMENT ────────────────────────────────────────────────────────────────
bot.run(TOKEN)
