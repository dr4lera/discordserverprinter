import discord
from discord.ext import commands
from discord import app_commands
from openai import OpenAI
import os
import json
from dotenv import load_dotenv

load_dotenv()

# Discord setup
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# OpenAI client setup
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    try:
        await tree.sync()
    except Exception as e:
        print(f"❌ Sync error: {e}")

@tree.command(name="setup", description="Set up your server based on a theme")
@app_commands.describe(theme="The theme to base the server setup on")
async def setup(interaction: discord.Interaction, theme: str):
    try:
        await interaction.response.defer(thinking=True)

        guild = interaction.guild
        interaction_channel = interaction.channel

        # Delete all channels except the one where the command was triggered
        for channel in guild.channels:
            if channel.id != interaction_channel.id:
                try:
                    await channel.delete()
                except Exception as e:
                    print(f"Failed to delete channel {channel.name}: {e}")

        # Delete all roles except @everyone
        for role in guild.roles:
            if role.name != "@everyone":
                try:
                    await role.delete()
                except Exception as e:
                    print(f"Failed to delete role {role.name}: {e}")

        # Prompt for OpenAI
        prompt = f"""
You are helping set up a Discord server based on the theme: "{theme}".
Return ONLY valid JSON with the following structure:
- server_name (string)
- server_description (string)
- description (string)
- roles (list of objects with 'name', 'color' (hex string), and 'permissions' (list of permission strings))
- categories (list of objects with 'name' and 'channels' list)
- welcome (object with 'channel' and 'message')

Requirements:
1. Include AT LEAST 5 roles.
2. Include AT LEAST 20 channels total across categories.
3. Add a mandatory category named "Info" with these text channels:
   - 📜rules
   - 📢announcements
   - ℹ️info
4. All channels must have emoji prefixes relevant to the theme (like 🎮 for gaming).
5. Channels can be "text" or "voice".
6. Ensure descriptions are lively and hook the user
7. Return no explanations, only well-formed JSON.

Example categories structure:

"categories": [
  {{
    "name": "Info",
    "channels": [
      {{"name": "📜rules", "type": "text"}},
      {{"name": "📢announcements", "type": "text"}},
      {{"name": "ℹ️info", "type": "text"}}
    ]
  }},
  ...
]
"""

        
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4
        )

        raw_content = response.choices[0].message.content.strip("```json").strip("```").strip()
        server_structure = json.loads(raw_content)

        
        new_name = server_structure.get("server_name")
        new_description = server_structure.get("server_description")

        if new_name:
            try:
                await guild.edit(name=new_name)
            except Exception as e:
                print(f"❌ Failed to change server name: {e}")

        if new_description:
            try:
                await guild.edit(description=new_description)
            except Exception as e:
                print(f"❌ Failed to change server description: {e}")

       
        role_objects = {}
        for role in server_structure.get("roles", []):
            perms = discord.Permissions()
            for perm in role.get("permissions", []):
                try:
                    setattr(perms, perm, True)
                except Exception as e:
                    print(f"Invalid permission: {perm}")

            color_hex = role.get("color", "#808080")
            new_role = await guild.create_role(
                name=role["name"],
                permissions=perms,
                colour=discord.Colour(int(color_hex.replace("#", ""), 16))
            )
            role_objects[role["name"]] = new_role

       
        for category in server_structure.get("categories", []):
            cat = await guild.create_category(category["name"])
            for ch in category.get("channels", []):
                if ch["type"] == "text":
                    await guild.create_text_channel(ch["name"], category=cat)
                elif ch["type"] == "voice":
                    await guild.create_voice_channel(ch["name"], category=cat)

        
        welcome_channel_name = server_structure.get("welcome", {}).get("channel")
        welcome_msg = server_structure.get("welcome", {}).get("message")
        if welcome_channel_name and welcome_msg:
            welcome_channel = discord.utils.get(guild.text_channels, name=welcome_channel_name)
            if welcome_channel:
                await welcome_channel.send(welcome_msg)

        await interaction.followup.send(
            f"✅ Server setup complete!\n**Server Name:** {new_name or guild.name}\n**Description:** {new_description or 'No description provided.'}"
        )

    except Exception as e:
        print(f"Exception in setup: {e}")
        try:
            await interaction.followup.send("❌ Error setting up server. Check logs.")
        except Exception:
            pass

bot.run(os.getenv("DISCORD_TOKEN"))
