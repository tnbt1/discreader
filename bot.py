import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import aiohttp
import json
import re
import os
from dotenv import load_dotenv
from collections import deque
import logging

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.voice_states = True

class VoiceBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='/', intents=intents)
        self.voice_channel = None
        self.text_channels = {}
        self.is_reading = {}
        self.message_queue = {}
        self.voicevox_url = os.getenv('VOICEVOX_URL', 'http://localhost:50021')
        
        self.speaker = int(os.getenv('SPEAKER_ID', '2'))
        self.speed = float(os.getenv('VOICE_SPEED', '1.0'))
        self.pitch = float(os.getenv('VOICE_PITCH', '0.0'))
        self.intonation = float(os.getenv('VOICE_INTONATION', '1.0'))
        self.volume = float(os.getenv('VOICE_VOLUME', '1.0'))

    async def setup_hook(self):
        await self.tree.sync()
        logger.info("スラッシュコマンドを同期しました")

    async def on_ready(self):
        logger.info(f'{self.user} としてログインしました')
        await self.change_presence(activity=discord.Activity(
            type=discord.ActivityType.listening,
            name="テキストチャンネル"
        ))

    def should_read_message(self, message):
        if message.author == self.user:
            return False
        
        if message.author.bot:
            return False
        
        if not message.content.strip():
            return False
        
        if message.content.startswith(('/', '!', '.')):
            return False
        
        url_pattern = r'^https?://\S+$'
        if re.match(url_pattern, message.content.strip()):
            return False
        
        custom_emoji_pattern = r'^(<:\w+:\d+>)+$'
        if re.match(custom_emoji_pattern, message.content.strip()):
            return False
        
        return True

    def clean_message(self, content):
        url_pattern = r'https?://\S+'
        content = re.sub(url_pattern, 'URL省略', content)
        
        custom_emoji_pattern = r'<:(\w+):\d+>'
        content = re.sub(custom_emoji_pattern, r'\1', content)
        
        mention_pattern = r'<@!?(\d+)>'
        def replace_mention(match):
            user_id = int(match.group(1))
            user = self.get_user(user_id)
            return f'@{user.display_name}' if user else '@メンバー'
        content = re.sub(mention_pattern, replace_mention, content)
        
        channel_pattern = r'<#(\d+)>'
        content = re.sub(channel_pattern, 'チャンネル', content)
        
        content = content.replace('\n', '、')
        
        max_length = int(os.getenv('MAX_MESSAGE_LENGTH', '100'))
        if len(content) > max_length:
            content = content[:max_length] + '、以下略'
        
        return content

    async def generate_voice(self, text):
        async with aiohttp.ClientSession() as session:
            params = {
                'text': text,
                'speaker': self.speaker
            }
            
            async with session.post(
                f'{self.voicevox_url}/audio_query',
                params=params
            ) as response:
                if response.status != 200:
                    logger.error(f"音声クエリ生成エラー: {response.status}")
                    return None
                query = await response.json()
            
            query['speedScale'] = self.speed
            query['pitchScale'] = self.pitch
            query['intonationScale'] = self.intonation
            query['volumeScale'] = self.volume
            
            headers = {'Content-Type': 'application/json'}
            params = {'speaker': self.speaker}
            
            async with session.post(
                f'{self.voicevox_url}/synthesis',
                json=query,
                params=params,
                headers=headers
            ) as response:
                if response.status != 200:
                    logger.error(f"音声合成エラー: {response.status}")
                    return None
                return await response.read()

    async def play_voice(self, voice_client, audio_data):
        temp_file = 'temp_voice.wav'
        with open(temp_file, 'wb') as f:
            f.write(audio_data)
        
        source = discord.FFmpegPCMAudio(temp_file)
        voice_client.play(source)
        
        while voice_client.is_playing():
            await asyncio.sleep(0.1)
        
        if os.path.exists(temp_file):
            os.remove(temp_file)

    async def process_message_queue(self, guild_id):
        if guild_id not in self.message_queue:
            self.message_queue[guild_id] = deque()
            
        while self.is_reading.get(guild_id, False):
            if not self.message_queue[guild_id]:
                await asyncio.sleep(0.5)
                continue
                
            message = self.message_queue[guild_id].popleft()
            voice_client = discord.utils.get(self.voice_clients, guild=message.guild)
            
            if not voice_client or not voice_client.is_connected():
                break
            
            cleaned_text = self.clean_message(message.content)
            
            audio_data = await self.generate_voice(cleaned_text)
            if audio_data:
                await self.play_voice(voice_client, audio_data)

    async def on_message(self, message):
        if not message.guild:
            return
        
        guild_id = message.guild.id
        
        logger.info(f"メッセージ受信: {message.content} from {message.author}")
        
        if guild_id not in self.text_channels:
            return
            
        if message.channel.id != self.text_channels[guild_id]:
            return
        
        if not self.is_reading.get(guild_id, False):
            return
        
        if not self.should_read_message(message):
            return
        
        logger.info(f"キューに追加: {message.content}")
        
        if guild_id not in self.message_queue:
            self.message_queue[guild_id] = deque()
        self.message_queue[guild_id].append(message)

bot = VoiceBot()

@bot.tree.command(name="join", description="ボットをボイスチャンネルに参加させます")
async def join(interaction: discord.Interaction):
    if not interaction.user.voice:
        await interaction.response.send_message(
            "❌ ボイスチャンネルに参加してから実行してください", 
            ephemeral=True
        )
        return
    
    voice_client = discord.utils.get(bot.voice_clients, guild=interaction.guild)
    if voice_client and voice_client.is_connected():
        await interaction.response.send_message(
            "⚠️ 既にボイスチャンネルに参加しています", 
            ephemeral=True
        )
        return
    
    channel = interaction.user.voice.channel
    voice_client = await channel.connect()
    
    guild_id = interaction.guild.id
    bot.is_reading[guild_id] = True
    
    asyncio.create_task(bot.process_message_queue(guild_id))
    
    await interaction.response.send_message(
        f"✅ {channel.name} に参加しました\n"
        f"読み上げを開始します"
    )

@bot.tree.command(name="leave", description="ボットをボイスチャンネルから退出させます")
async def leave(interaction: discord.Interaction):
    voice_client = discord.utils.get(bot.voice_clients, guild=interaction.guild)
    
    if not voice_client or not voice_client.is_connected():
        await interaction.response.send_message(
            "❌ ボイスチャンネルに参加していません", 
            ephemeral=True
        )
        return
    
    guild_id = interaction.guild.id
    bot.is_reading[guild_id] = False
    
    if guild_id in bot.message_queue:
        bot.message_queue[guild_id].clear()
    
    await voice_client.disconnect()
    
    await interaction.response.send_message("👋 ボイスチャンネルから退出しました")

@bot.tree.command(name="setchannel", description="読み上げるテキストチャンネルを設定します")
@app_commands.describe(channel="読み上げるテキストチャンネル")
async def setchannel(interaction: discord.Interaction, channel: discord.TextChannel):
    guild_id = interaction.guild.id
    bot.text_channels[guild_id] = channel.id
    
    await interaction.response.send_message(
        f"✅ 読み上げチャンネルを {channel.mention} に設定しました"
    )

@bot.tree.command(name="status", description="ボットの現在の状態を表示します")
async def status(interaction: discord.Interaction):
    guild_id = interaction.guild.id
    voice_client = discord.utils.get(bot.voice_clients, guild=interaction.guild)
    
    vc_status = "未接続"
    if voice_client and voice_client.is_connected():
        vc_status = f"接続中: {voice_client.channel.name}"
    
    reading_status = "停止中"
    if bot.is_reading.get(guild_id, False):
        reading_status = "読み上げ中"
    
    text_channel = "未設定"
    if guild_id in bot.text_channels:
        channel = interaction.guild.get_channel(bot.text_channels[guild_id])
        if channel:
            text_channel = channel.mention
    
    queue_size = 0
    if guild_id in bot.message_queue:
        queue_size = len(bot.message_queue[guild_id])
    
    embed = discord.Embed(
        title="📊 ボットステータス",
        color=discord.Color.blue()
    )
    embed.add_field(name="🎤 VC接続", value=vc_status, inline=False)
    embed.add_field(name="📖 読み上げ", value=reading_status, inline=False)
    embed.add_field(name="💬 対象チャンネル", value=text_channel, inline=False)
    embed.add_field(name="📝 キュー", value=f"{queue_size} 件", inline=False)
    embed.add_field(name="🔊 音声", value=f"四国めたん（速度: {bot.speed}）", inline=False)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="help", description="ヘルプを表示します")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📚 ヘルプ",
        description="VCで声を出せない方のための読み上げボット",
        color=discord.Color.green()
    )
    
    commands_text = """
    `/join` - ボイスチャンネルに参加して読み上げを開始
    `/leave` - ボイスチャンネルから退出して読み上げを停止
    `/setchannel` - 読み上げるテキストチャンネルを設定
    `/status` - 現在の状態を表示
    `/help` - このヘルプを表示
    """
    
    embed.add_field(name="コマンド一覧", value=commands_text, inline=False)
    
    usage_text = """
    1. `/setchannel` で読み上げ対象チャンネルを設定
    2. VCに参加してから `/join` を実行
    3. 設定したチャンネルのメッセージが自動で読み上げられます
    4. `/leave` で読み上げを停止
    """
    
    embed.add_field(name="使い方", value=usage_text, inline=False)
    
    await interaction.response.send_message(embed=embed)

if __name__ == "__main__":
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        logger.error("DISCORD_TOKEN が設定されていません")
        exit(1)
    
    bot.run(token)