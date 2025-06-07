import discord
from redbot.core import commands, Config
from redbot.core.bot import Red
from datetime import datetime

class LeaveLog(commands.Cog):
    """Dokumentiert das Verlassen oder Bannen von Mitgliedern."""

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=9238123)
        self.config.register_guild(channel=None, enabled=True)
        self.recent_bans = {}

    @commands.guild_only()
    @commands.admin()
    @commands.group(name="leavelog", invoke_without_command=True)
    async def leavelog(self, ctx: commands.Context):
        """Verwalte das Leavelog-Modul."""
        await ctx.send("Nutze `!leavelog info`, um alle Befehle anzuzeigen.")

    @leavelog.command(name="channel")
    @commands.admin()
    async def set_channel(self, ctx: commands.Context, channel: discord.TextChannel):
        """Setzt den Kanal für das Log."""
        await self.config.guild(ctx.guild).channel.set(channel.id)
        await ctx.send(f"Log-Kanal wurde auf {channel.mention} gesetzt.")

    @leavelog.command(name="toggle")
    @commands.admin()
    async def toggle_logging(self, ctx: commands.Context):
        """Aktiviert oder deaktiviert das Logging."""
        current = await self.config.guild(ctx.guild).enabled()
        await self.config.guild(ctx.guild).enabled.set(not current)
        status = "aktiviert" if not current else "deaktiviert"
        await ctx.send(f"Leavelog wurde **{status}**.")

    @leavelog.command(name="info")
    @commands.admin()
    async def info(self, ctx: commands.Context):
        """Zeigt eine Übersicht der verfügbaren Befehle an."""
        enabled = await self.config.guild(ctx.guild).enabled()
        channel_id = await self.config.guild(ctx.guild).channel()
        status = "Aktiviert" if enabled else "Deaktiviert"
        channel = f"<#{channel_id}>" if channel_id else "Nicht gesetzt"

        await ctx.send(
            f"**Status:** {status}\n"
            f"**Kanal:** {channel}\n\n"
            "**Verfügbare Befehle:**\n"
            "`!leavelog channel #kanal` – Setzt den Zielkanal.\n"
            "`!leavelog toggle` – Aktiviert oder deaktiviert das Modul.\n"
            "`!leavelog info` – Zeigt diese Übersicht."
        )

    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User):
        """Speichert gebannte Nutzer temporär."""
        self.recent_bans[user.id] = datetime.utcnow()

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        guild = member.guild
        if not await self.config.guild(guild).enabled():
            return

        channel_id = await self.config.guild(guild).channel()
        if not channel_id:
            return
        channel = guild.get_channel(channel_id)
        if not channel:
            return

        banned = False
        if member.id in self.recent_bans:
            banned = True
            del self.recent_bans[member.id]

        joined_at = member.joined_at.strftime("%d.%m.%Y, %H:%M Uhr") if member.joined_at else "Unbekannt"
        roles = [r.mention for r in member.roles if r != guild.default_role]
        roles_display = ", ".join(roles) if roles else "Keine besonderen Rollen"

        embed = discord.Embed(
            title="Mitglied wurde gebannt" if banned else "Mitglied hat den Server verlassen",
            color=discord.Color.dark_red() if banned else discord.Color.orange(),
            timestamp=datetime.utcnow()
        )
        embed.set_author(name=str(member), icon_url=member.display_avatar.url)
        embed.add_field(name="Letzter Anzeigename", value=member.display_name, inline=False)
        embed.add_field(name="Beigetreten am", value=joined_at, inline=False)
        embed.add_field(name="Rollen", value=roles_display, inline=False)
        embed.set_footer(text=f"User-ID: {member.id}")

        await channel.send(embed=embed)
