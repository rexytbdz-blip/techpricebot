import os
import json
import discord
from discord.ext import commands
import aiohttp
from bs4 import BeautifulSoup
import asyncio
import urllib.parse
from groq import Groq

# ─── CONFIG ───────────────────────────────────────────────────────────────────
TOKEN = os.environ.get("TOKEN")
groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

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

# Taux de conversion approximatifs
EUR_TO_USD = 1.08
EUR_TO_DZD = 145.0

# ─── LANGUES ──────────────────────────────────────────────────────────────────
LANG_FILE = "user_langs.json"

def load_langs():
    try:
        with open(LANG_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}

def save_langs(data):
    with open(LANG_FILE, "w") as f:
        json.dump(data, f)

def get_lang(user_id):
    return load_langs().get(str(user_id), "fr")

def set_lang(user_id, lang):
    langs = load_langs()
    langs[str(user_id)] = lang
    save_langs(langs)

STRINGS = {
    "fr": {
        "lang_set": "✅ Langue définie sur **Français** !",
        "lang_invalid": "❌ Langue invalide. Choix : `fr`, `en`, `ar`",
        "prix_search": "🔍 Recherche de **{composant}** en cours...",
        "prix_title": "💰 Prix pour : {composant}",
        "prix_footer": "RexyBot • Prix temps réel + Analyse IA",
        "prix_none": "😕 Aucun résultat trouvé. Essaie un nom plus précis.",
        "prix_no_result": "*Aucun résultat*",
        "prix_usage": "❌ Usage : `!prix <composant>`\nEx: `!prix RTX 4070`",
        "prix_ai_label": "🤖 Avis IA",
        "prix_ai_system": "Tu es un expert en composants PC. Réponds en français, très brièvement (2-3 lignes max).",
        "prix_ai_prompt": "Donne un avis rapide sur le rapport qualité/prix de : {composant}. Sois très concis.",
        "prix_occasion_label": "🛒 Occasions",
        "bn_usage": "❌ Usage : `!bottleneck <CPU> / <GPU>`\nEx: `!bottleneck Ryzen 5 7600X / RTX 4070`",
        "bn_searching": "🤖 Analyse IA du bottleneck : **{cpu}** + **{gpu}**...",
        "bn_title": "🔬 Bottleneck — {cpu} + {gpu}",
        "bn_footer": "RexyBot • Analyse IA powered by Groq",
        "bn_error": "❌ Erreur IA : {e}",
        "bn_system": "Tu es un expert en hardware PC. Réponds UNIQUEMENT en français, de façon concise.",
        "bn_prompt": "Analyse le bottleneck entre :\n- CPU : {cpu}\n- GPU : {gpu}\n\nFormat exact :\n**Résultat :** [✅ Équilibré / ⚠️ Bottleneck léger / 🔴 Bottleneck sévère]\n**Bottleneck estimé :** X% (côté CPU ou GPU)\n**Impact gaming :** 1080p / 1440p / 4K\n**Conseil :** upgrade recommandé ou confirmation",
        "build_usage": "❌ Usage : `!build <budget>`\nEx: `!build 800`",
        "build_invalid": "❌ Le budget doit être un nombre.",
        "build_min": "❌ Budget minimum : **100€**",
        "build_max": "❌ Budget maximum : **10 000€**",
        "build_searching": "🤖 L'IA prépare ta config pour **{budget}€**...",
        "build_prices": "🔍 Recherche des prix pour ta config **{budget}€**...",
        "build_title": "🖥️ Config PC {budget}€",
        "build_footer": "RexyBot • Config IA + Prix temps réel",
        "build_error": "❌ Erreur IA : {e}",
        "build_json_error": "❌ Erreur config. Réessaie.",
        "build_no_price": "*Prix non disponible*",
        "build_occasion_label": "🛒 Alternatives occasion",
        "build_system": "Tu es un expert en config PC pour le marché français. Réponds UNIQUEMENT avec un JSON valide, sans markdown.",
        "cpu_label": "⚙️ CPU", "gpu_label": "🎮 GPU", "ram_label": "🧠 RAM",
        "ssd_label": "💾 SSD", "mobo_label": "🔌 Carte mère",
        "psu_label": "⚡ Alimentation", "case_label": "📦 Boîtier",
        "aide_title": "📖 Aide — RexyBot",
        "aide_desc": "Bot IA spécialisé en composants PC 🤖",
        "aide_cmds": "`!prix <composant>` — Prix sur 6 sites + avis IA\n`!bottleneck <CPU> / <GPU>` — Analyse IA du bottleneck\n`!build <budget>` — Config PC complète (100€ → 10 000€)\n`!lang <fr|en|ar>` — Changer la langue\n`!aide` — Affiche ce message",
        "aide_examples": "`!prix RTX 4070`\n`!bottleneck Ryzen 5 7600X / RTX 4070`\n`!build 1000`",
        "aide_shops": "LDLC 💻 • Materiel.net 🖥️ • LeBonCoin • Facebook • eBay • Ouedkniss",
        "aide_cmds_label": "Commandes", "aide_ex_label": "Exemples", "aide_shops_label": "Boutiques",
    },
    "en": {
        "lang_set": "✅ Language set to **English**!",
        "lang_invalid": "❌ Invalid language. Choices: `fr`, `en`, `ar`",
        "prix_search": "🔍 Searching for **{composant}**...",
        "prix_title": "💰 Price for: {composant}",
        "prix_footer": "RexyBot • Real-time prices + AI Analysis",
        "prix_none": "😕 No results found. Try a more specific name.",
        "prix_no_result": "*No results*",
        "prix_usage": "❌ Usage: `!prix <component>`\nEx: `!prix RTX 4070`",
        "prix_ai_label": "🤖 AI Review",
        "prix_ai_system": "You are a PC hardware expert. Reply in English, very briefly (2-3 lines max).",
        "prix_ai_prompt": "Give a quick value-for-money opinion on: {composant}. Be very concise.",
        "prix_occasion_label": "🛒 Second-hand",
        "bn_usage": "❌ Usage: `!bottleneck <CPU> / <GPU>`\nEx: `!bottleneck Ryzen 5 7600X / RTX 4070`",
        "bn_searching": "🤖 AI bottleneck analysis: **{cpu}** + **{gpu}**...",
        "bn_title": "🔬 Bottleneck — {cpu} + {gpu}",
        "bn_footer": "RexyBot • AI Analysis powered by Groq",
        "bn_error": "❌ AI Error: {e}",
        "bn_system": "You are a PC hardware expert. Reply ONLY in English, concisely.",
        "bn_prompt": "Analyze the bottleneck between:\n- CPU: {cpu}\n- GPU: {gpu}\n\nExact format:\n**Result:** [✅ Balanced / ⚠️ Light bottleneck / 🔴 Severe bottleneck]\n**Estimated bottleneck:** X% (CPU or GPU side)\n**Gaming impact:** 1080p / 1440p / 4K\n**Advice:** recommended upgrade or confirmation",
        "build_usage": "❌ Usage: `!build <budget>`\nEx: `!build 800`",
        "build_invalid": "❌ Budget must be a number.",
        "build_min": "❌ Minimum budget: **100€**",
        "build_max": "❌ Maximum budget: **10,000€**",
        "build_searching": "🤖 AI is preparing your build for **{budget}€**...",
        "build_prices": "🔍 Searching prices for your **{budget}€** build...",
        "build_title": "🖥️ PC Build {budget}€",
        "build_footer": "RexyBot • AI Build + Real-time prices",
        "build_error": "❌ AI Error: {e}",
        "build_json_error": "❌ Config error. Try again.",
        "build_no_price": "*Price unavailable*",
        "build_occasion_label": "🛒 Second-hand alternatives",
        "build_system": "You are a PC build expert for the French market. Reply ONLY with valid JSON, no markdown.",
        "cpu_label": "⚙️ CPU", "gpu_label": "🎮 GPU", "ram_label": "🧠 RAM",
        "ssd_label": "💾 SSD", "mobo_label": "🔌 Motherboard",
        "psu_label": "⚡ Power Supply", "case_label": "📦 Case",
        "aide_title": "📖 Help — RexyBot",
        "aide_desc": "AI bot specialized in PC components 🤖",
        "aide_cmds": "`!prix <component>` — Prices on 6 sites + AI review\n`!bottleneck <CPU> / <GPU>` — AI bottleneck analysis\n`!build <budget>` — Full AI PC build (100€ → 10,000€)\n`!lang <fr|en|ar>` — Change language\n`!aide` — Show this message",
        "aide_examples": "`!prix RTX 4070`\n`!bottleneck Ryzen 5 7600X / RTX 4070`\n`!build 1000`",
        "aide_shops": "LDLC 💻 • Materiel.net 🖥️ • LeBonCoin • Facebook • eBay • Ouedkniss",
        "aide_cmds_label": "Commands", "aide_ex_label": "Examples", "aide_shops_label": "Stores",
    },
    "ar": {
        "lang_set": "✅ تم تعيين اللغة على **العربية**!",
        "lang_invalid": "❌ لغة غير صالحة. الخيارات: `fr`, `en`, `ar`",
        "prix_search": "🔍 جارٍ البحث عن **{composant}**...",
        "prix_title": "💰 سعر: {composant}",
        "prix_footer": "RexyBot • أسعار مباشرة + تحليل ذكاء اصطناعي",
        "prix_none": "😕 لا توجد نتائج. جرّب اسماً أكثر دقة.",
        "prix_no_result": "*لا توجد نتائج*",
        "prix_usage": "❌ الاستخدام: `!prix <المكوّن>`\nمثال: `!prix RTX 4070`",
        "prix_ai_label": "🤖 رأي الذكاء الاصطناعي",
        "prix_ai_system": "أنت خبير في مكونات الحاسوب. أجب باللغة العربية، بإيجاز شديد (2-3 أسطر فقط).",
        "prix_ai_prompt": "أعطِ رأياً سريعاً عن جودة/سعر: {composant}. كن موجزاً جداً.",
        "prix_occasion_label": "🛒 المستعمل",
        "bn_usage": "❌ الاستخدام: `!bottleneck <CPU> / <GPU>`\nمثال: `!bottleneck Ryzen 5 7600X / RTX 4070`",
        "bn_searching": "🤖 تحليل الاختناق: **{cpu}** + **{gpu}**...",
        "bn_title": "🔬 اختناق — {cpu} + {gpu}",
        "bn_footer": "RexyBot • تحليل ذكاء اصطناعي",
        "bn_error": "❌ خطأ: {e}",
        "bn_system": "أنت خبير في أجهزة الحاسوب. أجب فقط باللغة العربية، بإيجاز.",
        "bn_prompt": "حلّل الاختناق بين:\n- المعالج: {cpu}\n- بطاقة الرسومات: {gpu}\n\nالتنسيق:\n**النتيجة:** [✅ متوازن / ⚠️ اختناق خفيف / 🔴 اختناق شديد]\n**الاختناق المقدّر:** X%\n**تأثير الألعاب:** 1080p / 1440p / 4K\n**النصيحة:** ترقية أو تأكيد",
        "build_usage": "❌ الاستخدام: `!build <الميزانية>`\nمثال: `!build 800`",
        "build_invalid": "❌ يجب أن تكون الميزانية رقماً.",
        "build_min": "❌ الحد الأدنى: **100€**",
        "build_max": "❌ الحد الأقصى: **10 000€**",
        "build_searching": "🤖 الذكاء الاصطناعي يجهّز تكوينك لـ **{budget}€**...",
        "build_prices": "🔍 جارٍ البحث عن الأسعار لـ **{budget}€**...",
        "build_title": "🖥️ تكوين PC بـ {budget}€",
        "build_footer": "RexyBot • تكوين ذكاء اصطناعي + أسعار مباشرة",
        "build_error": "❌ خطأ: {e}",
        "build_json_error": "❌ خطأ في التكوين. أعد المحاولة.",
        "build_no_price": "*السعر غير متاح*",
        "build_occasion_label": "🛒 بدائل مستعملة",
        "build_system": "أنت خبير في تكوينات الحاسوب للسوق الفرنسي. أجب فقط بـ JSON صالح، بدون markdown.",
        "cpu_label": "⚙️ المعالج", "gpu_label": "🎮 بطاقة الرسومات", "ram_label": "🧠 الذاكرة",
        "ssd_label": "💾 التخزين", "mobo_label": "🔌 اللوحة الأم",
        "psu_label": "⚡ مصدر الطاقة", "case_label": "📦 الهيكل",
        "aide_title": "📖 مساعدة — RexyBot",
        "aide_desc": "بوت ذكاء اصطناعي متخصص في مكونات الحاسوب 🤖",
        "aide_cmds": "`!prix <المكوّن>` — أسعار على 6 مواقع + رأي ذكاء اصطناعي\n`!bottleneck <CPU> / <GPU>` — تحليل الاختناق\n`!build <الميزانية>` — تكوين كامل (100€ → 10 000€)\n`!lang <fr|en|ar>` — تغيير اللغة\n`!aide` — عرض هذه الرسالة",
        "aide_examples": "`!prix RTX 4070`\n`!bottleneck Ryzen 5 7600X / RTX 4070`\n`!build 1000`",
        "aide_shops": "LDLC 💻 • Materiel.net 🖥️ • LeBonCoin • Facebook • eBay • Ouedkniss",
        "aide_cmds_label": "الأوامر", "aide_ex_label": "أمثلة", "aide_shops_label": "المتاجر",
    }
}

def t(user_id, key, **kwargs):
    lang = get_lang(user_id)
    text = STRINGS.get(lang, STRINGS["fr"]).get(key, STRINGS["fr"].get(key, key))
    return text.format(**kwargs) if kwargs else text

# ─── HELPER IA ────────────────────────────────────────────────────────────────
def ask_groq(system: str, prompt: str, max_tokens: int = 900) -> str:
    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content

# ─── CONVERTISSEUR PRIX ───────────────────────────────────────────────────────
def convert_price(price_str: str) -> str:
    try:
        clean = price_str.replace("€", "").replace(",", ".").replace("\xa0", "").strip()
        eur = float(clean)
        usd = eur * EUR_TO_USD
        dzd = eur * EUR_TO_DZD
        return f"**{eur:.2f}€** • ${usd:.2f} • {dzd:,.0f} DZD"
    except Exception:
        return price_str

# ─── LIENS OCCASION ───────────────────────────────────────────────────────────
def occasion_links(composant: str) -> str:
    q = urllib.parse.quote(composant)
    lines = [
        f"[LeBonCoin](https://www.leboncoin.fr/recherche?text={q})",
        f"[Facebook Marketplace](https://www.facebook.com/marketplace/search/?query={q})",
        f"[eBay](https://www.ebay.fr/sch/i.html?_nkw={q})",
        f"[Ouedkniss](https://www.ouedkniss.com/recherche?q={q})",
    ]
    return " • ".join(lines)

# ─── SCRAPERS ─────────────────────────────────────────────────────────────────
async def scrape_ldlc(session, query):
    url = f"https://www.ldlc.com/recherche/{urllib.parse.quote(query)}/"
    try:
        async with session.get(url, headers=HEADERS, timeout=10) as r:
            soup = BeautifulSoup(await r.text(), "html.parser")
        results = []
        for item in soup.select(".listing-product li.pdt-item")[:2]:
            title_el = item.select_one(".title-3")
            price_el = item.select_one(".price .price") or item.select_one(".price")
            link_el  = item.select_one("a.pdt-item")
            if title_el and price_el:
                price_raw = price_el.text.strip().split()[0].replace(",", ".")
                results.append({
                    "title": title_el.text.strip()[:55],
                    "price_raw": price_raw,
                    "url": "https://www.ldlc.com" + link_el["href"] if link_el else url,
                    "store": "💻 LDLC",
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
        for item in soup.select(".listing-product li.pdt-item")[:2]:
            title_el = item.select_one(".title-3")
            price_el = item.select_one(".price .price") or item.select_one(".price")
            link_el  = item.select_one("a.pdt-item")
            if title_el and price_el:
                price_raw = price_el.text.strip().split()[0].replace(",", ".")
                results.append({
                    "title": title_el.text.strip()[:55],
                    "price_raw": price_raw,
                    "url": "https://www.materiel.net" + link_el["href"] if link_el else url,
                    "store": "🖥️ Materiel.net",
                })
        return results
    except Exception:
        return []

# ─── EVENTS ───────────────────────────────────────────────────────────────────
@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Activity(
        type=discord.ActivityType.watching, name="les prix PC 💻"
    ))
    print(f"✅ Bot connecté : {bot.user}")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        pass
    else:
        await ctx.send(f"❌ Erreur : {error}")

# ─── COMMANDES ────────────────────────────────────────────────────────────────

# ── !lang ─────────────────────────────────────────────────────────────────────
@bot.command(name="lang")
async def lang(ctx, langue: str = None):
    if langue not in ["fr", "en", "ar"]:
        await ctx.send(t(ctx.author.id, "lang_invalid"))
        return
    set_lang(ctx.author.id, langue)
    await ctx.send(t(ctx.author.id, "lang_set"))

# ── !prix ─────────────────────────────────────────────────────────────────────
@bot.command(name="prix")
async def prix(ctx, *, composant: str = None):
    uid = ctx.author.id
    if not composant:
        await ctx.send(t(uid, "prix_usage"))
        return

    msg = await ctx.send(t(uid, "prix_search", composant=composant))

    async with aiohttp.ClientSession() as session:
        ldlc, materiel = await asyncio.gather(
            scrape_ldlc(session, composant),
            scrape_materiel(session, composant),
        )

    all_results = ldlc + materiel
    embed = discord.Embed(title=t(uid, "prix_title", composant=composant), color=0x5865F2)
    embed.set_footer(text=t(uid, "prix_footer"))

    if not all_results:
        embed.description = t(uid, "prix_none")
        await msg.edit(content=None, embed=embed)
        return

    # Afficher les résultats avec prix convertis
    for store_name, results in [("💻 LDLC", ldlc), ("🖥️ Materiel.net", materiel)]:
        if results:
            lines = []
            for r in results:
                prix_affiche = convert_price(r["price_raw"])
                lines.append(f"[{r['title']}]({r['url']})\n{prix_affiche}")
            embed.add_field(name=store_name, value="\n\n".join(lines), inline=False)
        else:
            embed.add_field(name=store_name, value=t(uid, "prix_no_result"), inline=False)

    # Liens occasion
    embed.add_field(
        name=t(uid, "prix_occasion_label"),
        value=occasion_links(composant),
        inline=False
    )

    # Avis IA
    try:
        avis = await asyncio.to_thread(
            ask_groq,
            t(uid, "prix_ai_system"),
            t(uid, "prix_ai_prompt", composant=composant),
            250,
        )
        embed.add_field(name=t(uid, "prix_ai_label"), value=avis, inline=False)
    except Exception:
        pass

    await msg.edit(content=None, embed=embed)

# ── !bottleneck ───────────────────────────────────────────────────────────────
@bot.command(name="bottleneck")
async def bottleneck(ctx, *, args: str = None):
    uid = ctx.author.id
    if not args or "/" not in args:
        await ctx.send(t(uid, "bn_usage"))
        return

    parts = args.split("/", 1)
    cpu = parts[0].strip()
    gpu = parts[1].strip()

    msg = await ctx.send(t(uid, "bn_searching", cpu=cpu, gpu=gpu))

    try:
        reponse = await asyncio.to_thread(
            ask_groq,
            t(uid, "bn_system"),
            t(uid, "bn_prompt", cpu=cpu, gpu=gpu),
            800,
        )
    except Exception as e:
        await msg.edit(content=t(uid, "bn_error", e=e))
        return

    embed = discord.Embed(
        title=t(uid, "bn_title", cpu=cpu, gpu=gpu),
        description=reponse,
        color=0xFEE75C,
    )
    embed.set_footer(text=t(uid, "bn_footer"))
    await msg.edit(content=None, embed=embed)

# ── !build ────────────────────────────────────────────────────────────────────
@bot.command(name="build")
async def build(ctx, *, args: str = None):
    uid = ctx.author.id
    if not args:
        await ctx.send(t(uid, "build_usage"))
        return

    budget_str = args.replace("€", "").replace(" ", "").replace(",", "")
    try:
        budget = int(budget_str)
    except ValueError:
        await ctx.send(t(uid, "build_invalid"))
        return

    if budget < 100:
        await ctx.send(t(uid, "build_min"))
        return
    if budget > 10000:
        await ctx.send(t(uid, "build_max"))
        return

    msg = await ctx.send(t(uid, "build_searching", budget=budget))

    # Décider si GPU selon budget
    has_gpu = budget >= 400
    lang = get_lang(uid)

    if has_gpu:
        build_prompt = (
            f"Config PC gaming optimisée pour {budget}€ marché français. "
            f"JSON uniquement, sans markdown :\n"
            f'{{"cpu":"modèle complet","gpu":"modèle complet","ram":"modèle complet","ssd":"modèle complet","mobo":"modèle complet","psu":"modèle complet","case":"modèle complet","description":"phrase courte","occasion_gpu":"nom GPU occasion recommandé pour ce budget"}}'
        )
    else:
        build_prompt = (
            f"Config PC bureautique/légère pour {budget}€ marché français, SANS carte graphique dédiée (GPU intégré). "
            f"JSON uniquement, sans markdown :\n"
            f'{{"cpu":"modèle complet avec GPU intégré ex: Intel Core i3-12100","gpu":"Intégré (iGPU)","ram":"modèle complet","ssd":"modèle complet","mobo":"modèle complet","psu":"modèle complet","case":"modèle complet","description":"phrase courte","occasion_gpu":"GPU occasion recommandé si upgrade futur ex: RX 580 occasion"}}'
        )

    try:
        json_brut = await asyncio.to_thread(
            ask_groq,
            t(uid, "build_system"),
            build_prompt,
            500,
        )
    except Exception as e:
        await msg.edit(content=t(uid, "build_error", e=e))
        return

    try:
        json_propre = json_brut.strip().strip("```json").strip("```").strip()
        config = json.loads(json_propre)
    except json.JSONDecodeError:
        await msg.edit(content=t(uid, "build_json_error"))
        return

    await msg.edit(content=t(uid, "build_prices", budget=budget))

    # Scraping selon si GPU ou non
    if has_gpu:
        async with aiohttp.ClientSession() as session:
            (cpu_ldlc, cpu_mat, gpu_ldlc, gpu_mat,
             ram_ldlc, ssd_ldlc, mobo_ldlc, psu_ldlc, case_ldlc) = await asyncio.gather(
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
    else:
        async with aiohttp.ClientSession() as session:
            (cpu_ldlc, cpu_mat,
             ram_ldlc, ssd_ldlc, mobo_ldlc, psu_ldlc, case_ldlc) = await asyncio.gather(
                scrape_ldlc(session, config["cpu"]),
                scrape_materiel(session, config["cpu"]),
                scrape_ldlc(session, config["ram"]),
                scrape_ldlc(session, config["ssd"]),
                scrape_ldlc(session, config["mobo"]),
                scrape_ldlc(session, config["psu"]),
                scrape_ldlc(session, config["case"]),
            )
        gpu_ldlc, gpu_mat = [], []

    embed = discord.Embed(
        title=t(uid, "build_title", budget=budget),
        description=f"*{config.get('description', '')}*",
        color=0x5865F2,
    )

    def champ(ldlc_res, mat_res=None):
        lines = []
        if ldlc_res:
            p = convert_price(ldlc_res[0]["price_raw"])
            lines.append(f"💻 LDLC : [{ldlc_res[0]['title'][:38]}]({ldlc_res[0]['url']})\n{p}")
        if mat_res:
            p = convert_price(mat_res[0]["price_raw"])
            lines.append(f"🖥️ Materiel.net : [{mat_res[0]['title'][:38]}]({mat_res[0]['url']})\n{p}")
        return "\n\n".join(lines) if lines else t(uid, "build_no_price")

    embed.add_field(name=f"{t(uid,'cpu_label')} — {config['cpu']}", value=champ(cpu_ldlc, cpu_mat), inline=False)

    if has_gpu:
        embed.add_field(name=f"{t(uid,'gpu_label')} — {config['gpu']}", value=champ(gpu_ldlc, gpu_mat), inline=False)
    else:
        embed.add_field(name=f"{t(uid,'gpu_label')}", value="🔧 iGPU intégré au CPU", inline=False)

    embed.add_field(name=f"{t(uid,'ram_label')} — {config['ram']}", value=champ(ram_ldlc), inline=False)
    embed.add_field(name=f"{t(uid,'ssd_label')} — {config['ssd']}", value=champ(ssd_ldlc), inline=False)
    embed.add_field(name=f"{t(uid,'mobo_label')} — {config['mobo']}", value=champ(mobo_ldlc), inline=False)
    embed.add_field(name=f"{t(uid,'psu_label')} — {config['psu']}", value=champ(psu_ldlc), inline=False)
    embed.add_field(name=f"{t(uid,'case_label')} — {config['case']}", value=champ(case_ldlc), inline=False)

    # Alternatives occasion
    occasion_gpu = config.get("occasion_gpu", config.get("gpu", "GPU"))
    embed.add_field(
        name=t(uid, "build_occasion_label"),
        value=occasion_links(occasion_gpu),
        inline=False
    )

    embed.set_footer(text=t(uid, "build_footer"))
    await msg.edit(content=None, embed=embed)

# ── !aide ─────────────────────────────────────────────────────────────────────
@bot.command(name="aide")
async def aide(ctx):
    uid = ctx.author.id
    embed = discord.Embed(
        title=t(uid, "aide_title"),
        description=t(uid, "aide_desc"),
        color=0x5865F2,
    )
    embed.add_field(name=t(uid, "aide_cmds_label"), value=t(uid, "aide_cmds"), inline=False)
    embed.add_field(name=t(uid, "aide_ex_label"), value=t(uid, "aide_examples"), inline=False)
    embed.add_field(name=t(uid, "aide_shops_label"), value=t(uid, "aide_shops"), inline=False)
    await ctx.send(embed=embed)

# ─── LANCEMENT ────────────────────────────────────────────────────────────────
bot.run(TOKEN)
