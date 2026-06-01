import os
import discord
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
CANAL_ID = 1511035429623959706

# Estados rotativos
estados = [
    ("Esta pescando UwU 🐟", discord.ActivityType.playing),
    ("Escuchando tus mentiras 🎧", discord.ActivityType.listening),
    ("Viendo las olas 🌊", discord.ActivityType.watching)
]

# Variables globales
estado_anterior = None
fallos_consecutivos = 0

# Más tolerancia a microcortes
MAX_FALLOS = 5


# ==========================
# EVENTO READY
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
        activity=discord.Activity(type=tipo, name=texto),
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
        # Crear conexión nueva cada vez
        server = JavaServer.lookup(SERVER_ADDRESS)

        status = server.status()

        version_name = status.raw.get("version", {}).get("name","")

        if "offline" in version_name.lower():
            raise Exception("Exaroton reporta servidor OFFLINE")

        # LOGS DE DEPURACIÓN
        print("\n" + "=" * 60)
        print("RESPUESTA DEL SERVIDOR")
        print(f"Latencia: {status.latency:.0f} ms")
        print(status.raw)
        print("=" * 60)

        # Reiniciar contador porque respondió
        fallos_consecutivos = 0

        # Solo avisar si cambió a ONLINE
        if estado_anterior != "online":

            jugadores = status.players.sample

            if jugadores:
                lista = "\n".join(
                    f"• {jugador.name}"
                    for jugador in jugadores
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
                url="https://i.imgur.com/V1dm5U6.jpeg"
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

        # Solo marcar OFFLINE después de varios fallos seguidos
        if fallos_consecutivos >= MAX_FALLOS:

            if estado_anterior != "offline":

                embed = discord.Embed(
                    title="💎⚔️ POWERLAND ⛏️💎",
                    description="🔴 El servidor está **OFFLINE**.",
                    color=discord.Color.red()
                )

                embed.set_thumbnail(
                    url="https://i.imgur.com/V1dm5U6.jpeg"
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
# INICIO DEL BOT
# ==========================

bot.run(os.getenv("DISCORD_TOKEN"))