import discord
import aiohttp
import os
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
API_URL = os.getenv("API_URL")

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

VALID_JOBS = [
    "knight", "crusader", "wizard", "sage",
    "hunter", "bard", "dancer",
    "assassin", "rogue", "priest", "monk",
    "blacksmith", "alchemist", "super novice"
]

HELP_MSG = """
**คำสั่งกิลด์ ROOC** 🛡️

`!update <UID> <ชื่อ IGN> <อาชีพ>`
อัปเดตชื่อตัวละครหรืออาชีพของตัวเอง

**ตัวอย่าง:**
`!update 1234567 MindKnight Knight`

**อาชีพที่ใช้ได้:**
Knight, Crusader, Wizard, Sage, Hunter,
Bard, Dancer, Assassin, Rogue, Priest,
Monk, Blacksmith, Alchemist, Super Novice

`!roster` — ดูรายชื่อสมาชิกทั้งหมด
`!guildhelp` — แสดงคำสั่งทั้งหมด
"""

@client.event
async def on_ready():
    print(f"✅ Bot พร้อมใช้งาน: {client.user}")

@client.event
async def on_message(message):
    if message.author.bot:
        return

    content = message.content.strip()

    # คำสั่ง !guildhelp
    if content == "!guildhelp":
        await message.channel.send(HELP_MSG)
        return

    # คำสั่ง !update
    if content.lower().startswith("!update"):
        # รองรับอาชีพที่มีเว้นวรรค เช่น "super novice"
        parts = content.split(maxsplit=3)

        if len(parts) < 4:
            await message.reply(
                "❌ รูปแบบไม่ถูกต้อง\n"
                "ใช้: `!update <UID> <ชื่อ IGN> <อาชีพ>`\n"
                "ตัวอย่าง: `!update 1234567 MindKnight Knight`\n"
                "พิมพ์ `!guildhelp` เพื่อดูคำสั่งทั้งหมด"
            )
            return

        _, uid, ign, job = parts

        if job.lower() not in VALID_JOBS:
            await message.reply(
                f"❌ อาชีพ `{job}` ไม่ถูกต้อง\n"
                f"พิมพ์ `!guildhelp` เพื่อดูรายการอาชีพที่ใช้ได้"
            )
            return

        async with aiohttp.ClientSession() as session:
            try:
                payload = {
                    "action": "upsert",
                    "uid": uid,
                    "ign": ign,
                    "class": job.title()
                }
                async with session.post(API_URL, json=payload) as resp:
                    data = await resp.json(content_type=None)

                if data.get("error"):
                    await message.reply(f"❌ {data['error']}")
                else:
                    await message.reply(data.get("message", "✅ บันทึกสำเร็จ"))

            except Exception as e:
                await message.reply(f"❌ เชื่อมต่อ API ไม่ได้: {e}")
        return

    # คำสั่ง !roster
    if content == "!roster":
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(f"{API_URL}?action=getAll") as resp:
                    data = await resp.json(content_type=None)

                members = data.get("members", [])
                if not members:
                    await message.channel.send("📋 ยังไม่มีสมาชิกในระบบ")
                    return

                lines = ["**📋 รายชื่อสมาชิกกิลด์**\n```"]
                lines.append(f"{'#':<4} {'IGN':<20} {'อาชีพ':<15}")
                lines.append("-" * 40)
                for i, m in enumerate(members, 1):
                    lines.append(f"{i:<4} {m.get('ign','?'):<20} {m.get('class','?'):<15}")
                lines.append(f"\nสมาชิกทั้งหมด: {len(members)} คน```")

                await message.channel.send("\n".join(lines))

            except Exception as e:
                await message.reply(f"❌ โหลดข้อมูลไม่ได้: {e}")

client.run(TOKEN)