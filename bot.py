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

# ---------------------------------------------------------
# ฟังก์ชันเช็คสิทธิ์ผู้ดูแล/ผู้จัดการกิลด์
# เช็คทั้ง Discord Permission (Administrator / Manage Server)
# และ Role ชื่อ "Guild Manager" (ถ้ามี)
# ---------------------------------------------------------
def is_guild_manager():
    async def predicate(interaction: discord.Interaction) -> bool:
        perms = interaction.user.guild_permissions
        if perms.administrator or perms.manage_guild:
            return True
        role_names = [r.name for r in interaction.user.roles]
        return "Guild officer" in role_names
    return app_commands.check(predicate)


@client.event
async def on_ready():
    await tree.sync()
    print(f"✅ Bot พร้อมใช้งาน: {client.user}")


# ---------------------------------------------------------
# /update — อัปเดตชื่อตัวละครและอาชีพของตัวเอง (ใช้ได้ทุกคน)
# ---------------------------------------------------------
@tree.command(name="update", description="อัปเดตชื่อตัวละครและอาชีพของคุณ")
@app_commands.describe(
    uid="UID ในเกม (ตัวเลข 6 หลัก)",
    charname="ชื่อตัวละคร",
    job="อาชีพของตัวละคร"
)
@app_commands.choices(job=JOB_CHOICES)
async def update(interaction: discord.Interaction, uid: str, charname: str, job: app_commands.Choice[str]):
    if not uid.isdigit():
        await interaction.response.send_message("❌ UID ต้องเป็นตัวเลขเท่านั้น", ephemeral=True)
        return
    if len(uid) != 6:
        await interaction.response.send_message("❌ UID ต้องเป็นตัวเลข 6 หลัก", ephemeral=True)
        return

    await interaction.response.defer()
    async with aiohttp.ClientSession() as session:
        try:
            payload = {
                "action": "upsert",
                "uid": uid,
                "ign": charname,
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


# ---------------------------------------------------------
# /roster — ดูรายชื่อสมาชิกทั้งหมด (ใช้ได้ทุกคน)
# ---------------------------------------------------------
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


# ---------------------------------------------------------
# Autocomplete สำหรับช่อง uid ในคำสั่ง /delete
# พิมพ์บางส่วนของ UID หรือชื่อตัวละคร จะขึ้นลิสต์สมาชิกให้เลือก
# ---------------------------------------------------------
async def member_autocomplete(interaction: discord.Interaction, current: str):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{API_URL}?action=getAll") as resp:
                data = await resp.json(content_type=None)
        members = data.get("members", [])
    except Exception:
        return []

    current_lower = current.lower()
    matches = [
        m for m in members
        if current_lower in str(m.get("uid", "")).zfill(6).lower()
        or current_lower in str(m.get("ign", "")).lower()
    ]

    return [
        app_commands.Choice(
            name=f"{m.get('ign','?')} ({m.get('class','?')}) — UID {str(m.get('uid','')).zfill(6)}",
            value=str(m.get("uid", "")).zfill(6)  # ← padStart ให้ครบ 6 หลักก่อนส่งค่า
        )
        for m in matches[:25]
    ]


# ---------------------------------------------------------
# /delete — ลบสมาชิกออกจากกิลด์ (สำหรับผู้ดูแล/ผู้จัดการกิลด์เท่านั้น)
# ---------------------------------------------------------
@tree.command(name="delete", description="ลบสมาชิกออกจากกิลด์ (สำหรับผู้ดูแลเท่านั้น)")
@app_commands.describe(uid="เลือกสมาชิกที่ต้องการลบ (พิมพ์ชื่อหรือ UID เพื่อค้นหา)")
@app_commands.autocomplete(uid=member_autocomplete)
@is_guild_manager()
async def delete(interaction: discord.Interaction, uid: str):
    if not uid.isdigit() or len(uid) != 6:
        await interaction.response.send_message("❌ UID ต้องเป็นตัวเลข 6 หลัก", ephemeral=True)
        return

    await interaction.response.defer()
    async with aiohttp.ClientSession() as session:
        try:
            payload = {"action": "delete", "uid": uid}
            async with session.post(API_URL, json=payload) as resp:
                data = await resp.json(content_type=None)
            if data.get("error"):
                await interaction.followup.send(f"❌ {data['error']}")
            else:
                await interaction.followup.send(data.get("message", "🗑️ ลบสำเร็จ"))
        except Exception as e:
            await interaction.followup.send(f"❌ เชื่อมต่อ API ไม่ได้: {e}")


@delete.error
async def delete_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.CheckFailure):
        await interaction.response.send_message(
            "❌ คำสั่งนี้สำหรับผู้ดูแลเซิร์ฟเวอร์หรือ Role 'Guild officer' เท่านั้น",
            ephemeral=True
        )
    else:
        await interaction.response.send_message(f"❌ เกิดข้อผิดพลาด: {error}", ephemeral=True)


client.run(TOKEN)
