import discord
from discord import app_commands
import aiosqlite
import random
from datetime import datetime

import os
TOKEN = os.getenv('DISCORD_TOKEN')  # 从环境变量中读取

DB = "game.db"

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)


# ---------------- 数据库 ----------------

async def init_db():

    async with aiosqlite.connect(DB) as db:

        await db.execute("""
        CREATE TABLE IF NOT EXISTS users(
        user_id TEXT,
        guild_id TEXT,
        coins INTEGER,
        PRIMARY KEY(user_id,guild_id))
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS sign(
        user_id TEXT,
        guild_id TEXT,
        date TEXT,
        PRIMARY KEY(user_id,guild_id))
        """)

        await db.commit()


async def add_coins(user,guild,amount):

    async with aiosqlite.connect(DB) as db:

        await db.execute("""
        INSERT INTO users(user_id,guild_id,coins)
        VALUES(?,?,?)
        ON CONFLICT(user_id,guild_id)
        DO UPDATE SET coins=coins+?
        """,(user,guild,amount,amount))

        await db.commit()


async def get_coins(user,guild):

    async with aiosqlite.connect(DB) as db:

        async with db.execute(
        "SELECT coins FROM users WHERE user_id=? AND guild_id=?",
        (user,guild)) as cursor:

            row=await cursor.fetchone()

            return row[0] if row else 0


async def leaderboard(guild):

    async with aiosqlite.connect(DB) as db:

        async with db.execute("""
        SELECT user_id,coins
        FROM users
        WHERE guild_id=?
        ORDER BY coins DESC
        LIMIT 10
        """,(guild,)) as cursor:

            return await cursor.fetchall()


# ---------------- BOT 启动 ----------------

@client.event
async def on_ready():

    await init_db()

    await tree.sync()

    print(f"Bot 已上线 {client.user}")


# ---------------- 签到 ----------------

@tree.command(name="签到",description="每日签到")
async def sign(interaction:discord.Interaction):

    user=str(interaction.user.id)
    guild=str(interaction.guild.id)

    today=datetime.now().strftime("%Y-%m-%d")

    async with aiosqlite.connect(DB) as db:

        async with db.execute(
        "SELECT date FROM sign WHERE user_id=? AND guild_id=?",
        (user,guild)) as cursor:

            row=await cursor.fetchone()

        if row and row[0]==today:

            await interaction.response.send_message("今天已经签到过了")
            return

        reward=100

        await add_coins(user,guild,reward)

        await db.execute("""
        INSERT OR REPLACE INTO sign(user_id,guild_id,date)
        VALUES(?,?,?)
        """,(user,guild,today))

        await db.commit()

    await interaction.response.send_message(
        f"签到成功 🎉 获得 {reward} 金币"
    )


# ---------------- 积分 ----------------

@tree.command(name="积分",description="查看金币")
async def coins(interaction:discord.Interaction):

    user=str(interaction.user.id)
    guild=str(interaction.guild.id)

    money=await get_coins(user,guild)

    await interaction.response.send_message(
        f"💰 你的金币: {money}"
    )


# ---------------- 排行榜 ----------------

@tree.command(name="排行榜",description="服务器排行榜")
async def rank(interaction:discord.Interaction):

    guild=str(interaction.guild.id)

    data=await leaderboard(guild)

    embed=discord.Embed(
        title="🏆 金币排行榜",
        color=discord.Color.gold()
    )

    for i,(uid,coins) in enumerate(data,1):

        member=interaction.guild.get_member(int(uid))

        name=member.display_name if member else uid

        embed.add_field(
        name=f"{i}. {name}",
        value=f"{coins} 金币",
        inline=False)

    await interaction.response.send_message(embed=embed)


# ---------------- 猜数字 ----------------

@tree.command(name="猜数字",description="猜1-10")
@app_commands.describe(number="输入1-10")
async def guess(interaction:discord.Interaction,number:int):

    if number<1 or number>10:

        await interaction.response.send_message("请输入1-10")
        return

    secret=random.randint(1,10)

    user=str(interaction.user.id)
    guild=str(interaction.guild.id)

    if number==secret:

        reward=200

        await add_coins(user,guild,reward)

        await interaction.response.send_message(
        f"🎉 猜对了！数字是 {secret}\n+{reward} 金币")

    else:

        await interaction.response.send_message(
        f"❌ 猜错了，答案是 {secret}")


# ---------------- 掷骰子 ----------------

@tree.command(name="掷骰子",description="随机获得或失去金币")
async def dice(interaction:discord.Interaction):

    outcomes=[-50,-20,-10,10,20,50,100]

    result=random.choice(outcomes)

    user=str(interaction.user.id)
    guild=str(interaction.guild.id)

    await add_coins(user,guild,result)

    if result>0:

        msg=f"🎲 你赢了 {result} 金币"

    else:

        msg=f"💀 你输了 {-result} 金币"

    await interaction.response.send_message(msg)


# ---------------- 老虎机 ----------------

@tree.command(name="老虎机",description="赌博小游戏")
async def slot(interaction:discord.Interaction):

    user=str(interaction.user.id)
    guild=str(interaction.guild.id)

    symbols=["🍒","🍋","💎","⭐"]

    result=[random.choice(symbols) for _ in range(3)]

    text=" | ".join(result)

    if result[0]==result[1]==result[2]:

        reward=500

        await add_coins(user,guild,reward)

        msg=f"{text}\n🎉 JACKPOT +{reward}"

    else:

        msg=f"{text}\n再试一次"

    await interaction.response.send_message(msg)


# ---------------- 每日奖励 ----------------

@tree.command(name="daily",description="每日金币")
async def daily(interaction:discord.Interaction):

    user=str(interaction.user.id)
    guild=str(interaction.guild.id)

    reward=random.randint(50,150)

    await add_coins(user,guild,reward)

    await interaction.response.send_message(
    f"🎁 每日奖励 {reward} 金币")


client.run(TOKEN)