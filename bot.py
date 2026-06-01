import os
import discord
from discord import app_commands
from discord.ext import commands, tasks
from mcstatus import JavaServer
from datetime import datetime

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Estados rotativos cada hora
estados = [
    ("Esta pescando UwU 🐟", discord.ActivityType.playing),
    ("Escuchando tus mentiras", discord.ActivityType.listening),
    ("Viendo las olas 🌊", discord.ActivityType.watching)
]

# Configuración del server
server = JavaServer.lookup("CochinitosLand4.exaroton.me:61042")
CANAL_ID = 1499557785363550228
estado_anterior = None

@bot.event
async def on_ready():
    synced = await bot.tree.sync()
    print(f"Bot conectado como {bot.user}")
    print(f"Comandos slash sincronizados: {[cmd.name for cmd in synced]}")
    cambiar_estado.start()
    check_server.start()

@tasks.loop(hours=1)
async def cambiar_estado():
    texto, tipo = estados[cambiar_estado.current_loop % len(estados)]
    await bot.change_presence(
        activity=discord.Activity(type=tipo, name=texto),
        status=discord.Status.online
    )

@tasks.loop(minutes=1)
async def check_server():
    global estado_anterior
    canal = bot.get_channel(CANAL_ID)
    try:
        status = server.status()
        jugadores = status.players.sample

        if estado_anterior != "online":
            if jugadores:
                lista = "\n".join([p.name for p in jugadores])
                descripcion = f"🟢 El server está **ONLINE** con {status.players.online} jugadores:\n{lista}"
            else:
                descripcion = f"🟢 El server está **ONLINE** con {status.players.online} jugadores."

            embed = discord.Embed(
                title="💎⚔️-𝐏𝐎𝐖𝐄𝐑𝐋𝐀𝐍𝐃-⛏️💎",
                description=descripcion,
                color=discord.Color.green()
            )
            embed.set_thumbnail(url="https://static.wikia.nocookie.net/minecraft_gamepedia/images/5/5e/Grass_Block_JE5_BE3.png")  # Logo Minecraft
            embed.set_footer(text=f"Detectado a las {datetime.now().strftime('%H:%M:%S')}")
            await canal.send(embed=embed)

        estado_anterior = "online"

    except:
        if estado_anterior != "offline":
            embed = discord.Embed(
                title="💎⚔️-𝐏𝐎𝐖𝐄𝐑𝐋𝐀𝐍𝐃-⛏️💎",
                description="🔴 El server está **OFFLINE**.",
                color=discord.Color.red()
            )
            embed.set_thumbnail(url="https://static.wikia.nocookie.net/minecraft_gamepedia/images/5/5e/Grass_Block_JE5_BE3.png")  # Logo Minecraft
            embed.set_footer(text=f"Detectado a las {datetime.now().strftime('%H:%M:%S')}")
            await canal.send(embed=embed)

        estado_anterior = "offline"

# Comando /hilos
@bot.tree.command(name="hilos", description="Crear un hilo con título, mensaje y archivo")
async def hilos(interaction: discord.Interaction, titulo: str, mensaje: str, archivo: discord.Attachment = None):
    content = mensaje
    if archivo:
        content += f"\nArchivo: {archivo.url}"
    await interaction.response.send_message(content)
    msg = await interaction.original_response()
    await msg.create_thread(name=titulo)

bot.run(os.getenv("DISCORD_TOKEN"))
