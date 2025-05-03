import discord
from redbot.core import commands, Config
from redbot.core.bot import Red
import asyncio

class MTM(commands.Cog):
    """Move To Me - Verschiebe Nutzer in deinen Voice-Channel."""

    def __init__(self, bot: Red) -> None:
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1234567891, force_registration=True)
        default_guild = {
            "command_channel_id": 0,
            "cooldown_seconds": 0,
            "max_users": 0,
            "blacklisted_users": [],
            "last_modified_by": None
        }
        self.config.register_guild(**default_guild)
        self.cooldown_buckets = {}

    async def update_cooldown(self, ctx: commands.Context) -> bool:
        """Prüft und aktualisiert den Cooldown."""
        cooldown = await self.config.guild(ctx.guild).cooldown_seconds()
        if cooldown <= 0:
            return False
        now = discord.utils.utcnow().timestamp()
        bucket_key = f"{ctx.guild.id}-{ctx.author.id}"
        last_used = self.cooldown_buckets.get(bucket_key, 0)
        if now - last_used < cooldown:
            seconds_left = round(cooldown - (now - last_used))
            try:
                await ctx.message.add_reaction("⏳")
            except discord.HTTPException:
                pass
            await ctx.reply(f"❌ Du musst noch {seconds_left} Sekunden warten.", mention_author=False)
            return True
        return False

    def set_cooldown(self, ctx: commands.Context) -> None:
        """Setzt den aktuellen Zeitpunkt als Cooldown."""
        now = discord.utils.utcnow().timestamp()
        bucket_key = f"{ctx.guild.id}-{ctx.author.id}"
        self.cooldown_buckets[bucket_key] = now

    @commands.group(name="mtm", invoke_without_command=True)
    async def mtm_group(self, ctx: commands.Context, members: commands.Greedy[discord.Member] = None) -> None:
        """Verschiebe einen oder mehrere Nutzer in deinen Voice-Channel."""
        if not members:
            return await ctx.reply("❌ Bitte gib mindestens einen Nutzer an.", mention_author=False)

        # Blacklist Check
        blacklisted = await self.config.guild(ctx.guild).blacklisted_users()
        if ctx.author.id in blacklisted:
            return await ctx.reply("❌ Du bist auf der Blacklist und darfst diesen Befehl nicht nutzen.", mention_author=False)

        # Cooldown Check
        if await self.update_cooldown(ctx):
            return

        command_channel_id = await self.config.guild(ctx.guild).command_channel_id()
        if command_channel_id and ctx.channel.id != command_channel_id:
            return await ctx.reply("❌ Du kannst diesen Befehl nur im festgelegten Befehlskanal nutzen.", mention_author=False)

        if not ctx.author.voice or not ctx.author.voice.channel:
            return await ctx.reply("❌ Du bist in keinem Voice-Channel.", mention_author=False)

        max_users = await self.config.guild(ctx.guild).max_users()
        if max_users > 0 and len(members) > max_users:
            return await ctx.reply(f"❌ Du kannst maximal {max_users} Nutzer gleichzeitig verschieben.", mention_author=False)

        successful_moves = []
        failed_moves = []

        for member in members:
            if not member.voice or not member.voice.channel:
                failed_moves.append(f"{member.mention} (nicht im Voice-Channel)")
                continue
            try:
                await member.move_to(ctx.author.voice.channel)
                successful_moves.append(member.mention)
            except discord.Forbidden:
                failed_moves.append(f"{member.mention} (keine Berechtigung)")
            except discord.HTTPException:
                failed_moves.append(f"{member.mention} (Fehler beim Verschieben)")

        messages = []
        if successful_moves:
            messages.append(f"✅ {ctx.author.mention} hat {', '.join(successful_moves)} in {ctx.author.voice.channel.mention} verschoben.")
        if failed_moves:
            messages.append(f"❌ Konnte folgende Nutzer nicht verschieben: {', '.join(failed_moves)}.")

        if successful_moves:
            self.set_cooldown(ctx)  # Cooldown nur setzen bei Erfolg

        await ctx.reply('\n'.join(messages), mention_author=False)

    @mtm_group.command(name="setchannel")
    @commands.admin_or_permissions(manage_guild=True)
    async def set_channel(self, ctx: commands.Context) -> None:
        """Setzt den aktuellen Kanal als erlaubten Befehlskanal."""
        await self.config.guild(ctx.guild).command_channel_id.set(ctx.channel.id)
        await self.config.guild(ctx.guild).last_modified_by.set(ctx.author.id)
        await ctx.reply(f"✅ Der Kanal `{ctx.channel.name}` wurde als Befehlskanal festgelegt.", mention_author=False)

    @mtm_group.command(name="setcooldown")
    @commands.admin_or_permissions(manage_guild=True)
    async def set_cooldown_time(self, ctx: commands.Context, sekunden: int) -> None:
        """Setzt den Cooldown in Sekunden."""
        if sekunden < 0:
            return await ctx.reply("❌ Der Cooldown muss 0 oder größer sein.", mention_author=False)
        await self.config.guild(ctx.guild).cooldown_seconds.set(sekunden)
        await self.config.guild(ctx.guild).last_modified_by.set(ctx.author.id)
        await ctx.reply(f"✅ Cooldown wurde auf {sekunden} Sekunden gesetzt.", mention_author=False)

    @mtm_group.command(name="setmaxusers")
    @commands.admin_or_permissions(manage_guild=True)
    async def set_max_users(self, ctx: commands.Context, anzahl: int) -> None:
        """Setzt die maximale Anzahl verschiebbarer Nutzer."""
        if anzahl < 1:
            return await ctx.reply("❌ Die Anzahl muss mindestens 1 sein.", mention_author=False)
        await self.config.guild(ctx.guild).max_users.set(anzahl)
        await self.config.guild(ctx.guild).last_modified_by.set(ctx.author.id)
        await ctx.reply(f"✅ Maximal {anzahl} Nutzer können jetzt gleichzeitig verschoben werden.", mention_author=False)

    @mtm_group.command(name="blacklist")
    @commands.admin_or_permissions(manage_guild=True)
    async def blacklist_user(self, ctx: commands.Context, member: discord.Member) -> None:
        """Fügt einen Nutzer zur Blacklist hinzu oder entfernt ihn."""
        blacklisted = await self.config.guild(ctx.guild).blacklisted_users()
        if member.id in blacklisted:
            blacklisted.remove(member.id)
            await ctx.reply(f"✅ {member.mention} wurde von der Blacklist entfernt.", mention_author=False)
        else:
            blacklisted.append(member.id)
            await ctx.reply(f"✅ {member.mention} wurde zur Blacklist hinzugefügt.", mention_author=False)
        await self.config.guild(ctx.guild).blacklisted_users.set(blacklisted)
        await self.config.guild(ctx.guild).last_modified_by.set(ctx.author.id)

    @mtm_group.command(name="info")
    async def info(self, ctx: commands.Context) -> None:
        """Zeigt aktuelle MTM-Einstellungen."""
        data = await self.config.guild(ctx.guild).all()
        channel = ctx.guild.get_channel(data["command_channel_id"])
        last_mod_user = ctx.guild.get_member(data["last_modified_by"]) if data["last_modified_by"] else None
        blacklisted = [ctx.guild.get_member(uid) for uid in data["blacklisted_users"]]
        blacklisted_mentions = [u.mention for u in blacklisted if u]

        embed = discord.Embed(
            title="MTM - Aktuelle Einstellungen",
            color=discord.Color.blurple()
        )
        embed.add_field(name="Befehlskanal", value=channel.mention if channel else "Nicht festgelegt", inline=False)
        embed.add_field(name="Cooldown", value=f"{data['cooldown_seconds']} Sekunden", inline=False)
        embed.add_field(name="Maximale Nutzer", value=f"{data['max_users'] if data['max_users'] else 'Unbegrenzt'}", inline=False)
        embed.add_field(name="Blacklist", value=', '.join(blacklisted_mentions) if blacklisted_mentions else "Keine", inline=False)
        embed.add_field(name="Zuletzt geändert von", value=last_mod_user.mention if last_mod_user else "Unbekannt", inline=False)
        await ctx.reply(embed=embed, mention_author=False)

    @mtm_group.command(name="help")
    async def mtm_help(self, ctx: commands.Context) -> None:
        """Zeigt eine Übersicht aller MTM-Befehle."""
        embed = discord.Embed(
            title="MTM - Hilfe",
            description="Verfügbare Befehle:",
            color=discord.Color.blurple()
        )
        embed.add_field(name="!mtm @User1 @User2", value="Verschiebe Nutzer zu deinem Voice-Channel.", inline=False)
        embed.add_field(name="!mtm setchannel", value="Setzt den erlaubten Befehlskanal.", inline=False)
        embed.add_field(name="!mtm setcooldown [Sekunden]", value="Setzt den Cooldown (0 = deaktiviert).", inline=False)
        embed.add_field(name="!mtm setmaxusers [Anzahl]", value="Maximale Nutzer pro Verschiebung.", inline=False)
        embed.add_field(name="!mtm blacklist @User", value="Fügt Nutzer zur Blacklist hinzu oder entfernt sie.", inline=False)
        embed.add_field(name="!mtm info", value="Zeigt aktuelle Einstellungen an.", inline=False)
        embed.add_field(name="!mtm help", value="Zeigt diese Hilfe an.", inline=False)
        await ctx.reply(embed=embed, mention_author=False)
