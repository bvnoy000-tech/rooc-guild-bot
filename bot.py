import discord
from discord import app_commands
import aiohttp
import os
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
API_URL = os.getenv("API_URL")

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# Choices สำหรับ dropdown อาชีพ
JOB_CHOICES = [
    app_commands.Choice(name="Knight",       value="Knight"),
    app_commands.Choice(name="Crusader",     value="Crusader"),
    app_commands.Choice(name="Wizard",       value="Wizard"),
    app_commands.Choice(name="Sage",         value="Sage"),
    app_commands.Choice(name="Hunter",       value="Hunter"),
    app_commands.Choice(name="Bard",         value="Bard"),
    app_commands.Choice(name="Dancer",       value="Dancer"),
    app_commands.Choice(name="Assassin",     value="Assassin"),
    app_commands.Choice(name="Rogue",        value="Rogue"),
    app_commands.Choice(name="Priest",       value="Priest"),
    app_commands.Choice(name="Monk",         value="Monk"),
    app_commands.Choice(name="Blacksmith",   value="Blacksmith"),
    app_commands.Choice(name="Alchemist",    value="Alchemist"),
    app_commands.Choice(name="Super Novice", value="Super Novice"),
]

@client.event
async def on_ready():
    await tree.sync()
    print(f"✅ Bot พร้อมใช้งาน: {client.user}")

@tree.command(name="update", description="อัปเดตชื่อตัวละครและอาชีพของคุณ")
@app_commands.describe(
    uid="UID ในเกม (ดูได้ที่ตัวละคร → ข้อมูล)",
    ign="ชื่อตัวละครในเกม",
    job="อาชีพของตัวละคร"
)
@app_commands.choices(job=JOB_CHOICES)
async def update(interaction: discord.Interaction, uid: str, ign: str, job: app_commands.Choice[str]):
    await interaction.response.defer()

    async with aiohttp.ClientSession() as session:
        try:
            payload = {
                "action": "upsert",
                "uid": uid,
                "ign": ign,
                "class": job.value
            }
            async with session.post(API_URL, json=payload) as resp:
                data = await resp.json(content_type=None)

            if data.get("error"):
                await interaction.followup.send(f"❌ {data['error']}")
            else:
                await interaction.followup.send(data.get("message", "✅ บันทึกสำเร็จ"))

        except Exception as e:
            await interaction.followup.send(f"❌ เชื่อมต่อ API ไม่ได้: {e}")

@tree.command(name="roster", description="ดูรายชื่อสมาชิกกิลด์ทั้งหมด")
async def roster(interaction: discord.Interaction):
    await interaction.response.defer()

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{API_URL}?action=getAll") as resp:
                data = await resp.json(content_type=None)

            members = data.get("members", [])
            if not members:
                await interaction.followup.send("📋 ยังไม่มีสมาชิกในระบบ")
                return

            lines = ["**📋 รายชื่อสมาชิกกิลด์**\n```"]
            lines.append(f"{'#':<4} {'IGN':<20} {'อาชีพ':<15}")
            lines.append("-" * 40)
            for i, m in enumerate(members, 1):
                lines.append(f"{i:<4} {m.get('ign','?'):<20} {m.get('class','?'):<15}")
            lines.append(f"\nสมาชิกทั้งหมด: {len(members)} คน```")

            await interaction.followup.send("\n".join(lines))

        except Exception as e:
            await interaction.followup.send(f"❌ โหลดข้อมูลไม่ได้: {e}")

client.run(TOKEN)
