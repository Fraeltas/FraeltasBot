import os
import discord
import requests
import pytz
import asyncio
from discord.ext import commands, tasks
from mcstatus import JavaServer
from datetime import datetime, timedelta
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

# ==========================
# SESIÓN HTTP CON REINTENTOS
# ==========================

session = requests.Session()
retry = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
adapter = HTTPAdapter(max_retries=retry)
session.mount("https://", adapter)

# ==========================
# CACHE DIARIO DE PARTIDOS
# ==========================

cache_games = None
cache_fecha = None

async def fetch_games():
    """Petición asíncrona para no bloquear el loop"""
    def _fetch():
        response = session.get("https://worldcup26.ir/get/games", timeout=10)
        return response.json()
    return await asyncio.to_thread(_fetch)

async def get_games():
    """Devuelve partidos cacheados o refresca si cambió el día"""
    global cache_games, cache_fecha
    tz_lima = pytz.timezone("America/Lima")
    hoy = datetime.now(tz_lima).date()

    if cache_games and cache_fecha == hoy:
        return cache_games

    try:
        data = await fetch_games()
        cache_games = data.get("games", [])
        cache_fecha = hoy
        return cache_games
    except Exception as e:
        print(f"Error conectando a API: {e}")
        return cache_games if cache_games else []

# ==========================
# CONFIGURACIÓN DISCORD BOT
# ==========================

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

SERVER_ADDRESS = "CochinitosLand4.exaroton.me:61042"
CANAL_ID = 1499557785363550228
MAX_FALLOS = 5

estado_anterior = None
fallos_consecutivos = 0

# ==========================
# ESTADOS ROTATIVOS DEL BOT
# ==========================

estados = [
    ("Esta pescando UwU 🐟", discord.ActivityType.playing),
    ("Escuchando tus mentiras 🎧", discord.ActivityType.listening),
    ("Viendo las olas 🌊", discord.ActivityType.watching)
]

@bot.event
async def on_ready():
    synced = await bot.tree.sync()
    print(f"Bot conectado como {bot.user}")
    print(f"Comandos sincronizados: {[cmd.name for cmd in synced]}")
    cambiar_estado.start()
    check_server.start()

@tasks.loop(hours=1)
async def cambiar_estado():
    texto, tipo = estados[cambiar_estado.current_loop % len(estados)]
    await bot.change_presence(activity=discord.Activity(type=tipo, name=texto), status=discord.Status.online)

# ==========================
# MONITOR MINECRAFT
# ==========================

@tasks.loop(minutes=1)
async def check_server():
    global estado_anterior, fallos_consecutivos
    canal = bot.get_channel(CANAL_ID)

    try:
        server = JavaServer.lookup(SERVER_ADDRESS)
        status = server.status()
        protocol = status.raw.get("version", {}).get("protocol")
        version_name = str(status.raw.get("version", {}).get("name", "")).lower()

        if protocol == -1 or "offline" in version_name:
            raise Exception("Servidor OFFLINE")

        fallos_consecutivos = 0

        if estado_anterior != "online":
            jugadores = status.players.sample
            lista = "\n".join(f"• {j.name}" for j in jugadores) if jugadores else ""
            descripcion = f"🟢 ONLINE\n👥 {status.players.online}\n{lista}"

            embed = discord.Embed(title="💎⚔️ POWERLAND ⛏️💎", description=descripcion, color=discord.Color.green())
            embed.set_footer(text=f"Detectado a las {datetime.now().strftime('%H:%M:%S')}")
            await canal.send(embed=embed)
            print("🟢 CAMBIO A ONLINE")

        estado_anterior = "online"

    except Exception as e:
        fallos_consecutivos += 1
        print(f"❌ Error consultando servidor ({fallos_consecutivos}/{MAX_FALLOS})")
        print(e)

        if fallos_consecutivos >= MAX_FALLOS and estado_anterior != "offline":
            embed = discord.Embed(title="💎⚔️ POWERLAND ⛏️💎", description="🔴 OFFLINE", color=discord.Color.red())
            embed.set_footer(text=f"Detectado a las {datetime.now().strftime('%H:%M:%S')}")
            await canal.send(embed=embed)
            print("🔴 CAMBIO A OFFLINE")
            estado_anterior = "offline"

# ==========================
# COMANDO HILOS
# ==========================

@bot.tree.command(name="hilos", description="Crear un hilo con título, mensaje y archivo")
async def hilos(interaction: discord.Interaction, titulo: str, mensaje: str, archivo: discord.Attachment = None):
    contenido = mensaje
    if archivo:
        contenido += f"\n{archivo.url}"
    await interaction.response.send_message(contenido)
    msg = await interaction.original_response()
    await msg.create_thread(name=titulo)

# ==========================
# COMANDO STATUS POWERLAND
# ==========================

@bot.tree.command(name="statuspowerland", description="Estado actual de Powerland")
async def statuspowerland(interaction: discord.Interaction):
    try:
        server = JavaServer.lookup(SERVER_ADDRESS)
        status = server.status()
        jugadores = status.players.sample
        lista = "\n".join(f"🟢 {j.name}" for j in jugadores) if jugadores else "🌙 No hay jugadores"

        embed = discord.Embed(title="⚔️ Estado de Powerland ⚔️", description="🟢 ONLINE", color=discord.Color.green(), timestamp=datetime.now())
        embed.add_field(name="👥 Jugadores", value=f"{status.players.online}/{status.players.max}", inline=True)
        embed.add_field(name="📡 Ping", value=f"{status.latency:.0f} ms", inline=True)
        embed.add_field(name="🕒 Consulta", value=datetime.now().strftime("%H:%M:%S"), inline=True)
        embed.add_field(name="🌐 Dirección", value=SERVER_ADDRESS, inline=False)
        embed.add_field(name="🎮 Conectados", value=lista, inline=False)
        await interaction.response.send_message(embed=embed)

    except Exception:
        embed = discord.Embed(title="⚔️ Estado de Powerland ⚔️", description="🔴 OFFLINE", color=discord.Color.red(), timestamp=datetime.now())
        embed.add_field(name="🌐 Dirección", value=SERVER_ADDRESS, inline=False)
        embed.add_field(name="🕒 Consulta", value=datetime.now().strftime("%H:%M:%S"), inline=True)
        await interaction.response.send_message(embed=embed)

# ==========================
# MUNDIAL 2026 COMANDOS
# ==========================

stadium_timezones = {
    # Estados Unidos
    "atlanta": "America/New_York",
    "boston": "America/New_York",
    "dallas": "America/Chicago",
    "houston": "America/Chicago",
    "kansas_city": "America/Chicago",
    "los_angeles": "America/Los_Angeles",
    "miami": "America/New_York",
    "new_york_new_jersey": "America/New_York",
    "orlando": "America/New_York",   # Orlando usa la misma zona que NY
    "philadelphia": "America/New_York",
    "san_francisco": "America/Los_Angeles",
    "seattle": "America/Los_Angeles",

    # México
    "guadalajara": "America/Mexico_City",
    "mexico_city": "America/Mexico_City",
    "monterrey": "America/Monterrey",

    # Canadá
    "toronto": "America/Toronto",
    "vancouver": "America/Vancouver",
}

    # agrega más stadium_id según la lista oficial


# Diccionario de banderas (ejemplo con algunos equipos)
flags = {
    "Mexico": "🇲🇽",
    "South Africa": "🇿🇦",
    "South Korea": "🇰🇷",
    "Czech Republic": "🇨🇿",
    "Canada": "🇨🇦",
    "Bosnia and Herzegovina": "🇧🇦",
    "United States": "🇺🇸",
    "Paraguay": "🇵🇾",
    "Brazil": "🇧🇷",
    "Morocco": "🇲🇦",
    "Argentina": "🇦🇷",
    "Germany": "🇩🇪",
    "Japan": "🇯🇵",
    "Spain": "🇪🇸",
    "Uruguay": "🇺🇾",
    "England": "🇬🇧",
    "France": "🇫🇷",
    "Italy": "🇮🇹",
    "Portugal": "🇵🇹",
    "Netherlands": "🇳🇱",
    "Belgium": "🇧🇪",
    "Sweden": "🇸🇪",
    "Norway": "🇳🇴",
    "Denmark": "🇩🇰",
    "Switzerland": "🇨🇭",
    "Poland": "🇵🇱",
    "Turkey": "🇹🇷",
    "Egypt": "🇪🇬",
    "Ivory Coast": "🇨🇮",
    "Ecuador": "🇪🇨",
    "Japan": "🇯🇵",
    "Saudi Arabia": "🇸🇦",
    "Iran": "🇮🇷",
    "Qatar": "🇶🇦",
    "Australia": "🇦🇺",
    "New Zealand": "🇳🇿",
    "South Korea": "🇰🇷",
    "China": "🇨🇳",
    "Russia": "🇷🇺",
    "Ukraine": "🇺🇦",
    "Scotland": "🏴",
    "Ireland": "🇮🇪",
    "Tunisia": "🇹🇳",
    "Algeria": "🇩🇿",
    "Senegal": "🇸🇳",
    "Ghana": "🇬🇭",
    "Panama": "🇵🇦",
    "Japan": "🇯🇵",
    "Cape Verde": "🇨🇻",
    "Jordan": "🇯🇴",
    "Croatia": "🇭🇷",
    "Colombia": "🇨🇴",
    "Chile": "🇨🇱",
    "Peru": "🇵🇪",
}

# ==========================
# COMANDOS MUNDIAL 2026
# ==========================

@bot.tree.command(name="partidoshoy", description="Partidos del Mundial 2026 para hoy en hora Lima")
async def partidoshoy(interaction: discord.Interaction):
    await interaction.response.defer()
    games = await get_games()
    tz_lima = pytz.timezone("America/Lima")
    hoy = datetime.now(tz_lima).date()

    descripcion = ""
    for match in games:
        fecha_str = match.get("local_date")
        stadium_id = match.get("stadium_id")
        if not fecha_str or not stadium_id:
            continue
        try:
            fecha_local_sede = datetime.strptime(fecha_str, "%m/%d/%Y %H:%M")
            tz_sede = pytz.timezone(stadium_timezones.get(stadium_id, "America/New_York"))
            fecha_local_sede = tz_sede.localize(fecha_local_sede)
            fecha_lima = fecha_local_sede.astimezone(tz_lima)
        except:
            continue
        if fecha_lima.date() == hoy:
            home = match.get("home_team_name_en", "???")
            away = match.get("away_team_name_en", "???")
            descripcion += f"{flags.get(home,'')} {home} vs {away} {flags.get(away,'')} ({fecha_lima.strftime('%H:%M')})\n"

    if not descripcion:
        descripcion = "🌙 No hay partidos programados para hoy"

    embed = discord.Embed(title="📅 Partidos de Hoy - Mundial 2026", description=descripcion, color=discord.Color.gold())
    embed.set_footer(text=f"Hora local: {tz_lima.zone}")
    await interaction.followup.send(embed=embed)


@bot.tree.command(name="partidosmañana", description="Partidos del Mundial 2026 para mañana en hora Lima")
async def partidosmañana(interaction: discord.Interaction):
    await interaction.response.defer()
    games = await get_games()
    tz_lima = pytz.timezone("America/Lima")
    manana = datetime.now(tz_lima).date() + timedelta(days=1)

    descripcion = ""
    for match in games:
        fecha_str = match.get("local_date")
        stadium_id = match.get("stadium_id")
        if not fecha_str or not stadium_id:
            continue
        try:
            fecha_local_sede = datetime.strptime(fecha_str, "%m/%d/%Y %H:%M")
            tz_sede = pytz.timezone(stadium_timezones.get(stadium_id, "America/New_York"))
            fecha_local_sede = tz_sede.localize(fecha_local_sede)
            fecha_lima = fecha_local_sede.astimezone(tz_lima)
        except:
            continue
        if fecha_lima.date() == manana:
            home = match.get("home_team_name_en", "???")
            away = match.get("away_team_name_en", "???")
            descripcion += f"{flags.get(home,'')} {home} vs {away} {flags.get(away,'')} ({fecha_lima.strftime('%H:%M')})\n"

    if not descripcion:
        descripcion = "🌙 No hay partidos programados para mañana"

    embed = discord.Embed(title="📅 Partidos de Mañana - Mundial 2026", description=descripcion, color=discord.Color.green())
    embed.set_footer(text=f"Hora local: {tz_lima.zone}")
    await interaction.followup.send(embed=embed)


@bot.tree.command(name="resultadosayer", description="Resultados del Mundial 2026 de ayer en hora Lima")
async def resultadosayer(interaction: discord.Interaction):
    await interaction.response.defer()
    games = await get_games()
    tz_lima = pytz.timezone("America/Lima")
    ayer = datetime.now(tz_lima).date() - timedelta(days=1)

    descripcion = ""
    for match in games:
        fecha_str = match.get("local_date")
        stadium_id = match.get("stadium_id")
        if not fecha_str or not stadium_id:
            continue
        try:
            fecha_local_sede = datetime.strptime(fecha_str, "%m/%d/%Y %H:%M")
            tz_sede = pytz.timezone(stadium_timezones.get(stadium_id, "America/New_York"))
            fecha_local_sede = tz_sede.localize(fecha_local_sede)
            fecha_lima = fecha_local_sede.astimezone(tz_lima)
        except:
            continue
        if fecha_lima.date() == ayer:
            home = match.get("home_team_name_en", "???")
            away = match.get("away_team_name_en", "???")
            score_home = match.get("home_score", "-")
            score_away = match.get("away_score", "-")
            descripcion += f"{flags.get(home,'')} {home} {score_home} - {score_away} {away} {flags.get(away,'')}\n"

    if not descripcion:
        descripcion = "🌙 No hubo partidos ayer"

    embed = discord.Embed(title="📊 Resultados de Ayer - Mundial 2026", description=descripcion, color=discord.Color.blue())
    embed.set_footer(text=f"Hora local: {tz_lima.zone}")
    await interaction.followup.send(embed=embed)


@bot.tree.command(name="cr7", description="Próximo partido de Cristiano Ronaldo (Portugal)")
async def cr7(interaction: discord.Interaction):
    await interaction.response.defer()
    games = await get_games()
    tz_lima = pytz.timezone("America/Lima")
    ahora = datetime.now(tz_lima)

    proximo = None
    for match in games:
        fecha_str = match.get("local_date")
        stadium_id = match.get("stadium_id")
        if not fecha_str or not stadium_id:
            continue
        try:
            fecha_local_sede = datetime.strptime(fecha_str, "%m/%d/%Y %H:%M")
            tz_sede = pytz.timezone(stadium_timezones.get(stadium_id, "America/New_York"))
            fecha_local_sede = tz_sede.localize(fecha_local_sede)
            fecha_lima = fecha_local_sede.astimezone(tz_lima)
        except:
            continue

        home = match.get("home_team_name_en", "???")
        away = match.get("away_team_name_en", "???")

        if home == "Portugal" or away == "Portugal":
            if fecha_lima > ahora:
                if not proximo or fecha_lima < proximo["fecha"]:
                    proximo = {"home": home, "away": away, "fecha": fecha_lima}

    if not proximo:
        descripcion = "❌ No hay partidos próximos de Portugal en el calendario."
    else:
        descripcion = (
            f"{flags.get(proximo['home'],'')} {proximo['home']} vs {proximo['away']} {flags.get(proximo['away'],'')}\n"
            f"📅 {proximo['fecha'].strftime('%d/%m/%Y %H:%M')} (hora Lima)"
        )

    embed = discord.Embed(title="🇵🇹 Próximo Partido de Cristiano Ronaldo", description=descripcion, color=discord.Color.red())
    embed.set_footer(text=f"Hora local: {tz_lima.zone}")
    await interaction.followup.send(embed=embed)

# ==========================
# KEY
# ==========================

bot.run(os.getenv("DISCORD_TOKEN"))
