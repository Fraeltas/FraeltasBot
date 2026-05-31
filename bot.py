import os
import discord
from discord import app_commands
from discord.ext import commands, tasks

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Lista de estados que rotan cada hora
estados = [
    ("Esta pescando UwU 🐟", discord.ActivityType.playing),
    ("Escuchando tus mentiras", discord.ActivityType.listening),
    ("Viendo las olas 🌊", discord.ActivityType.watching)
]


@bot.event
async def on_ready():
    synced = await bot.tree.sync()
    print(f"Bot conectado como {bot.user}")
    print(f"Comandos slash sincronizados: {[cmd.name for cmd in synced]}")
    print(f"Bot conectado como {bot.user}")
    # Inicia el loop que cambia el estado
    cambiar_estado.start()

# Loop que se ejecuta cada 1 hora
@tasks.loop(hours=1)
async def cambiar_estado():
    texto, tipo = estados[cambiar_estado.current_loop % len(estados)]
    await bot.change_presence(
        activity=discord.Activity(type=tipo, name=texto),
        status=discord.Status.online
    )

# Comando /hilos
@bot.tree.command(name="hilos", description="Crear un hilo con título, mensaje y archivo")
async def hilos(interaction: discord.Interaction, titulo: str, mensaje: str, archivo: discord.Attachment = None):
    content = mensaje
    if archivo:
        content += f"\nArchivo: {archivo.url}"

    msg = await interaction.channel.send(content)
    await msg.create_thread(name=titulo)
    await interaction.response.send_message(f"Hilo **{titulo}** creado ✅", ephemeral=True)
# Ejecutar bot
bot.run(os.getenv("DISCORD_TOKEN"))