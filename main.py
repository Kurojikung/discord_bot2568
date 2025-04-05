import os
import discord
from discord.ext import commands
import yt_dlp
import asyncio



intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)
TOKEN = 'MTM1NzYyMjc3MzU4OTA4NjI0OQ.GOFX8H.o9ivqToMOSWLRuk7Y-ZyweAAIKjZOqkuE9cIVM'
queue = []
previous_track = None  # ตัวแปรสำหรับเก็บเพลงก่อนหน้า

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

# !play [url]
@bot.command()
async def play(ctx, url):
    global previous_track  # ใช้ตัวแปร global
    if not ctx.author.voice:
        await ctx.send("❌ คุณต้องอยู่ในห้องเสียงก่อนใช้คำสั่งนี้!")
        return

    if not ctx.voice_client:
        await ctx.author.voice.channel.connect()

    if ctx.author.voice.channel != ctx.voice_client.channel:
        await ctx.send("❌ คุณต้องอยู่ในห้องเดียวกับบอทเพื่อใช้คำสั่งนี้!")
        return

    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'ignoreerrors': True,
        'retries': 5,
        'nocheckcertificate': True,
        'extract_flat': False  # ต้อง False เพื่อดึงเพลงเต็ม
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

        # ถ้าเป็น playlist
        if 'entries' in info:
            for entry in info['entries']:
                if not entry:
                    continue
                await add_track_to_queue(ctx, entry)
        else:
            await add_track_to_queue(ctx, info)

    if not ctx.voice_client.is_playing():
        await play_next(ctx)

# แยกออกมาเป็นฟังก์ชันเพื่อใช้กับ playlist หรือ single video
async def add_track_to_queue(ctx, info):
    global previous_track  # ใช้ตัวแปร global
    title = info['title']
    webpage_url = info['webpage_url']
    duration = info.get('duration', 0)
    audio_url = info['url']

    track = {
        'title': title,
        'url': webpage_url,
        'duration': duration,
        'audio_url': audio_url,
        'requester': ctx.author.display_name
    }

    queue.append(track)
    position = len(queue)

    embed = discord.Embed(title="🎵 Add Track", description=f"[{title}]({webpage_url})", color=0x1DB954)
    embed.add_field(name="⏱️ Track Length", value=f"{duration // 60}:{duration % 60:02d}")
    embed.add_field(name="📊 Position in queue", value=position)
    embed.set_footer(text=f"🎧 Requested by {ctx.author.display_name}")
    await ctx.send(embed=embed)

    # บันทึกเพลงก่อนหน้า
    if queue:
        previous_track = queue[-2] if len(queue) > 1 else None

    if not ctx.voice_client.is_playing():
        await play_next(ctx)

async def play_next(ctx):
    if queue:
        track = queue.pop(0)
        vc = ctx.voice_client

        source = discord.FFmpegPCMAudio(track['audio_url'])
        vc.play(source, after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop))

        embed = discord.Embed(title="🎶 Now Playing", description=f"[{track['title']}]({track['url']})", color=0x1DB954)
        embed.set_footer(text=f"🎧 Requested by {track['requester']}")
        await ctx.send(embed=embed)

        if not queue:
            asyncio.create_task(auto_disconnect_check(ctx))
            
# คำสั่ง !back สำหรับเล่นเพลงก่อนหน้า
@bot.command()
async def back(ctx):
    global previous_track  # ใช้ตัวแปร global
    if previous_track:
        # เพิ่มเพลงก่อนหน้าไปที่คิว
        queue.insert(0, previous_track)
        await play_next(ctx)
        await ctx.send(f"⏪ กลับไปเล่นเพลง: {previous_track['title']}")
    else:
        await ctx.send("❌ ไม่มีเพลงก่อนหน้านี้")

async def auto_disconnect_check(ctx):
    await asyncio.sleep(10)  # รอ 10 วินาที

    voice_client = ctx.voice_client
    if voice_client and voice_client.is_connected():
        channel = voice_client.channel
        if len(channel.members) == 1:  # มีแค่บอทอยู่
            await voice_client.disconnect()
            await ctx.send("👋 ไม่มีใครอยู่ในห้องแล้ว บอทออกจากห้องเสียงอัตโนมัติจ้า~")

@bot.command()
async def stop(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("⏹️ หยุดเล่นเพลงแล้ว")
    else:
        await ctx.send("❌ ไม่มีเพลงกำลังเล่น")

@bot.command()
async def leave(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("👋 บอทออกจากห้องเสียงแล้ว")
    else:
        await ctx.send("❌ บอทไม่ได้อยู่ในห้องเสียง")

@bot.command(name="commands")  # <== ตั้งชื่อใหม่
async def show_commands(ctx):
    embed = discord.Embed(title="📖 คำสั่งของบอทเพลง", color=0x3498db)
    embed.add_field(name="!play [ลิงก์ YouTube]", value="เล่นเพลงจาก YouTube (และเข้าห้องเสียงอัตโนมัติ)", inline=False)
    embed.add_field(name="!stop", value="หยุดเพลงที่กำลังเล่น", inline=False)
    embed.add_field(name="!leave", value="ให้บอทออกจากห้องเสียง", inline=False)
    embed.add_field(name="!back", value="เล่นเพลงก่อนหน้าที่เล่น", inline=False)  # เพิ่มคำอธิบายคำสั่ง
    embed.set_footer(text=" 😎")
    await ctx.send(embed=embed)



bot.run(TOKEN)