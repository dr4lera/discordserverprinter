import discord
from discord.ext import commands
from discord import app_commands
from openai import OpenAI
import os
from dotenv import load_dotenv
from PIL import Image
from io import BytesIO
import aiohttp

load_dotenv()

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

async def generate_server_icon(theme):
    response = client.images.generate(
        model="dall-e-3",
        prompt=f"Discord server logo for a theme about '{theme}', simple and bold icon style",
        size="1024x1024",
        n=1
    )
    image_url = response.data[0].url

    async with aiohttp.ClientSession() as session:
        async with session.get(image_url) as resp:
            if resp.status != 200:
                raise Exception("Failed to download image.")
            data = await resp.read()

    img = Image.open(BytesIO(data)).convert("RGBA")
    img = img.resize((512, 512))
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    try:
        await tree.sync()
    except Exception as e:
        print(f"❌ Sync error: {e}")

@tree.command(name="generateicon", description="Generate a Discord server icon based on a theme")
@app_commands.describe(theme="Theme for the server icon")
async def generateicon(interaction: discord.Interaction, theme: str):
    await interaction.response.defer(thinking=True)
    try:
        buffer = await generate_server_icon(theme)
        await interaction.followup.send(file=discord.File(buffer, filename="server_icon.png"))
    except Exception as e:
        await interaction.followup.send(f"❌ Failed to generate icon: {e}")

bot.run("set a 2nd bot token here or setup a second token in ur env im lazy so i just did mine here ;-; ")
