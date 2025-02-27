import discord
from redbot.core import commands, Config

class MTM(commands.Cog):
    """Move To Me - Verschiebe Nutzer in deinen Voice-Channel"""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1234567890, force_registration=True)
        default_guild = {"command_channel_id": 0}
        self.config.register_guild(**default_guild)

    @commands.command()
    async def setmtm(self, ctx):
        """Setzt den aktuellen Kanal als den einzigen erlaubten Befehlskanal"""
        await self.config.guild(ctx.guild).command_channel_id.set(ctx.channel.id)
        await ctx.send(f"✅ Der Kanal `{ctx.channel.name}` wurde als Befehlskanal für MTM festgelegt.")

    @commands.command()
    async def mtm(self, ctx, member: discord.Member):
        """Verschiebt den angegebenen Nutzer in den Voice-Channel des Befehlsgebers"""
        command_channel_id = await self.config.guild(ctx.guild).command_channel_id()
        if ctx.channel.id != command_channel_id:
            return await ctx.send("❌ Du kannst diesen Befehl nur im festgelegten Kanal nutzen.")

        if ctx.author.voice is None or ctx.author.voice.channel is None:
            return await ctx.send("❌ Du bist in keinem Voice-Channel.")

        if member.voice is None or member.voice.channel is None:
            return await ctx.send(f"❌ {member.mention} ist in keinem Voice-Channel.")

        try:
            await member.move_to(ctx.author.voice.channel)
            await ctx.send(f"✅ {member.mention} wurde in {ctx.author.voice.channel.name} verschoben.")
        except discord.Forbidden:
            await ctx.send("❌ Ich habe keine Berechtigung, diesen Nutzer zu verschieben.")
        except discord.HTTPException:
            await ctx.send("❌ Es gab einen Fehler beim Verschieben des Nutzers.")
