import os
import discord
import requests
import pytz
from discord.ext import commands, tasks
from mcstatus import JavaServer
from datetime import datetime

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ==========================
# CONFIGURACIÓN
# ==========================

SERVER_ADDRESS = "CochinitosLand4.exaroton.me:61042"
CANAL_ID = 1499557785363550228

MAX_FALLOS = 5

# ==========================
# VARIABLES
# ==========================

estado_anterior = None
fallos_consecutivos = 0

# ==========================
# ESTADOS ROTATIVOS
# ==========================

estados = [
    ("Esta pescando UwU 🐟", discord.ActivityType.playing),
    ("Escuchando tus mentiras 🎧", discord.ActivityType.listening),
    ("Viendo las olas 🌊", discord.ActivityType.watching)
]

# ==========================
# READY
# ==========================

@bot.event
async def on_ready():
    synced = await bot.tree.sync()

    print(f"Bot conectado como {bot.user}")
    print(f"Comandos sincronizados: {[cmd.name for cmd in synced]}")

    cambiar_estado.start()
    check_server.start()

# ==========================
# ESTADO DEL BOT
# ==========================

@tasks.loop(hours=1)
async def cambiar_estado():
    texto, tipo = estados[cambiar_estado.current_loop % len(estados)]

    await bot.change_presence(
        activity=discord.Activity(
            type=tipo,
            name=texto
        ),
        status=discord.Status.online
    )

# ==========================
# MONITOR MINECRAFT
# ==========================

@tasks.loop(minutes=1)
async def check_server():
    global estado_anterior
    global fallos_consecutivos

    canal = bot.get_channel(CANAL_ID)

    try:

        server = JavaServer.lookup(SERVER_ADDRESS)

        status = server.status()

        print("\n" + "=" * 60)
        print("RESPUESTA DEL SERVIDOR")
        print(f"Latencia: {status.latency:.0f} ms")
        print(status.raw)
        print("=" * 60)

        protocol = (
            status.raw
            .get("version", {})
            .get("protocol")
        )

        version_name = str(
            status.raw
            .get("version", {})
            .get("name", "")
        ).lower()

        # Exaroton responde aunque esté apagado
        if protocol == -1:
            raise Exception(
                "Exaroton reporta servidor OFFLINE"
            )

        if "offline" in version_name:
            raise Exception(
                f"Version reporta OFFLINE: {version_name}"
            )

        fallos_consecutivos = 0

        if estado_anterior != "online":

            jugadores = status.players.sample

            if jugadores:

                lista = "\n".join(
                    f"• {j.name}"
                    for j in jugadores
                )

                descripcion = (
                    f"🟢 El servidor está **ONLINE**\n\n"
                    f"👥 Jugadores conectados: "
                    f"**{status.players.online}**\n\n"
                    f"{lista}"
                )

            else:

                descripcion = (
                    f"🟢 El servidor está **ONLINE**\n\n"
                    f"👥 Jugadores conectados: "
                    f"**{status.players.online}**"
                )

            embed = discord.Embed(
                title="💎⚔️ POWERLAND ⛏️💎",
                description=descripcion,
                color=discord.Color.green()
            )

            embed.set_thumbnail(
                url="https://i.imgur.com/rqFaiGG.jpeg"
            )

            embed.set_footer(
                text=f"Detectado a las {datetime.now().strftime('%H:%M:%S')}"
            )

            await canal.send(embed=embed)

            print("🟢 CAMBIO A ONLINE")

        estado_anterior = "online"

    except Exception as e:

        fallos_consecutivos += 1

        print(
            f"\n❌ Error consultando servidor "
            f"({fallos_consecutivos}/{MAX_FALLOS})"
        )

        print(e)

        if fallos_consecutivos >= MAX_FALLOS:

            if estado_anterior != "offline":

                embed = discord.Embed(
                    title="💎⚔️ POWERLAND ⛏️💎",
                    description="🔴 El servidor está **OFFLINE**.",
                    color=discord.Color.red()
                )

                embed.set_thumbnail(
                    url="https://i.imgur.com/rqFaiGG.jpeg"
                )

                embed.set_footer(
                    text=f"Detectado a las {datetime.now().strftime('%H:%M:%S')}"
                )

                await canal.send(embed=embed)

                print("🔴 CAMBIO A OFFLINE")

            estado_anterior = "offline"

# ==========================
# COMANDO HILOS
# ==========================

@bot.tree.command(
    name="hilos",
    description="Crear un hilo con título, mensaje y archivo"
)
async def hilos(
    interaction: discord.Interaction,
    titulo: str,
    mensaje: str,
    archivo: discord.Attachment = None
):

    contenido = mensaje

    if archivo:
        contenido += f"\n{archivo.url}"

    await interaction.response.send_message(contenido)

    msg = await interaction.original_response()

    await msg.create_thread(name=titulo)

# ==========================
# COMANDO STATUS POWERLAND
# ==========================

@bot.tree.command(
    name="statuspowerland",
    description="Estado actual de Powerland"
)
async def statuspowerland(interaction: discord.Interaction):

    print("COMANDO /statuspowerland EJECUTADO")

    try:
        server = JavaServer.lookup(SERVER_ADDRESS)

        try:
            status = server.status()
        except Exception as e:
            print(f"Primer intento falló: {e}, reintentando...")
            # Reintento inmediato
            server = JavaServer.lookup(SERVER_ADDRESS)
            status = server.status()

        protocol = status.raw.get("version", {}).get("protocol")
        version_name = str(status.raw.get("version", {}).get("name", "")).lower()

        if protocol == -1 or "offline" in version_name:
            raise Exception("Servidor reportado como OFFLINE")

        jugadores = status.players.sample
        lista = "\n".join(f"🟢 {j.name}" for j in jugadores) if jugadores else "🌙 No hay jugadores conectados"

        embed = discord.Embed(
            title="⚔️ Estado de Powerland ⚔️",
            description="🟢 **Servidor ONLINE**",
            color=discord.Color.green(),
            timestamp=datetime.now()
        )
        embed.set_thumbnail(url="https://i.imgur.com/rqFaiGG.jpeg")
        embed.add_field(name="👥 Jugadores", value=f"{status.players.online}/{status.players.max}", inline=True)
        embed.add_field(name="📡 Ping", value=f"{status.latency:.0f} ms", inline=True)
        embed.add_field(name="🕒 Consulta", value=datetime.now().strftime("%H:%M:%S"), inline=True)
        embed.add_field(name="🌐 Dirección", value=SERVER_ADDRESS, inline=False)
        embed.add_field(name="🎮 Conectados", value=lista, inline=False)
        embed.set_footer(text="Consultado desde FraeltasBot")

        await interaction.response.send_message(embed=embed)

    except Exception as e:
        print(f"Error en /statuspowerland: {e}")
        embed = discord.Embed(
            title="⚔️ Estado de Powerland ⚔️",
            description="🔴 **Servidor OFFLINE**",
            color=discord.Color.red(),
            timestamp=datetime.now()
        )
        embed.set_thumbnail(url="https://i.imgur.com/rqFaiGG.jpeg")
        embed.add_field(name="🌐 Dirección", value=SERVER_ADDRESS, inline=False)
        embed.add_field(name="🕒 Consulta", value=datetime.now().strftime("%H:%M:%S"), inline=True)
        embed.set_footer(text="Consultado desde FraeltasBot")
        await interaction.response.send_message(embed=embed)

# ==========================
# MUNDIAL26 COMANDO PARTIDOS HOY
# ==========================

@bot.tree.command(
    name="partidoshoy",
    description="Muestra los partidos del Mundial 2026 para hoy en hora de Lima"
)
async def partidoshoy(interaction: discord.Interaction):
    try:
        response = requests.get("https://worldcup26.ir/get/games")
        print(response.text)
        data = response.json()

        tz_local = pytz.timezone("America/Lima")
        hoy = datetime.now(tz_local).date()

        descripcion = ""
        for match in data:
            # La API devuelve local_date como string tipo "06/11/2026 13:00"
            fecha_str = match.get("local_date")
            if not fecha_str:
                continue

            # Parsear la fecha (formato: mm/dd/yyyy HH:MM)
            fecha_local = datetime.strptime(fecha_str, "%m/%d/%Y %H:%M")
            fecha_local = tz_local.localize(fecha_local)

            if fecha_local.date() == hoy:
                home = match.get("home_team_name_en", "???")
                away = match.get("away_team_name_en", "???")
                descripcion += f"⚽ {home} vs {away} ({fecha_local.strftime('%H:%M')})\n"

        if not descripcion:
            descripcion = "🌙 No hay partidos programados para hoy"

        embed = discord.Embed(
            title="📅 Partidos de Hoy - Mundial 2026",
            description=descripcion,
            color=discord.Color.gold()
        )
        embed.set_footer(text=f"Hora local: {tz_local.zone}")

        await interaction.response.send_message(embed=embed)

    except Exception as e:
        await interaction.response.send_message(
            f"❌ Error obteniendo partidos: {e}",
            ephemeral=True
        )



# ==========================
# INICIO
# ==========================

bot.run(os.getenv("DISCORD_TOKEN"))