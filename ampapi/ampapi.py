import discord
import aiohttp
from redbot.core import commands, Config, tasks

class AMPAPI(commands.Cog):
    """AMP API Integration für RedBot"""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1234567892)
        self.config.register_guild(
            amp_url="",
            username="",
            password="",
            channel_id=None,
            servers={},
            embeds={
                "online": None,
                "offline": None,
                "maintenance": None
            },
            alerts={}
        )
        
        self.update_status.start()  # Startet die Status-Überwachung

    def cog_unload(self):
        """Stellt sicher, dass die Loop gestoppt wird, wenn das Cog entladen wird"""
        self.update_status.cancel()

    @tasks.loop(minutes=2)
    async def update_status(self):
        """Diese Methode ruft alle 2 Minuten die AMP API ab und aktualisiert den Status"""
        guilds = await self.config.all_guilds()

        async with aiohttp.ClientSession() as session:
            for guild_id, settings in guilds.items():
                amp_url = settings.get("amp_url")
                channel_id = settings.get("channel_id")
                servers = settings.get("servers", {})

                if not amp_url or not channel_id:
                    continue  # Überspringen, falls nicht konfiguriert

                channel = self.bot.get_channel(channel_id)
                if not channel:
                    continue

                for server_name, server_data in servers.items():
                    try:
                        async with session.get(f"{amp_url}/status/{server_name}") as response:
                            if response.status == 200:
                                data = await response.json()
                                status = data.get("status", "Unknown")

                                embed_data = settings["embeds"].get(status.lower())
                                embed = discord.Embed(
                                    title=f"📡 {server_name} Status",
                                    description=f"Server ist **{status}**",
                                    color=discord.Color.green() if status == "Online" else discord.Color.red()
                                )
                                if embed_data:
                                    embed.description = embed_data.get("description", embed.description)
                                    embed.color = embed_data.get("color", embed.color)
                                
                                await channel.send(embed=embed)
                            else:
                                print(f"❌ Fehler beim Abrufen der API für {server_name} ({response.status})")
                    except Exception as e:
                        print(f"❌ Fehler bei der API-Anfrage für {server_name}: {e}")

    ### 📌 Befehle zur Konfiguration der AMP-API

    @commands.command()
    async def setamp(self, ctx, amp_url: str, username: str, password: str):
        """Setzt die AMP API Zugangsdaten"""
        await self.config.guild(ctx.guild).amp_url.set(amp_url)
        await ctx.send(f"✅ AMP API URL wurde auf `{amp_url}` gesetzt.")

    @commands.command()
    async def setchannel(self, ctx, channel: discord.TextChannel):
        """Setzt den Kanal für Status-Updates"""
        await self.config.guild(ctx.guild).channel_id.set(channel.id)
        await ctx.send(f"✅ Status-Updates werden in {channel.mention} gepostet.")

    ### 📌 Befehle zur Verwaltung von Servern

    @commands.command()
    async def addserver(self, ctx, server_name: str):
        """Fügt einen Server zur Überwachung hinzu"""
        async with self.config.guild(ctx.guild).servers() as servers:
            servers[server_name] = {}
        await ctx.send(f"✅ Server `{server_name}` wurde zur Überwachung hinzugefügt.")

    @commands.command()
    async def removeserver(self, ctx, server_name: str):
        """Entfernt einen Server aus der Überwachung"""
        async with self.config.guild(ctx.guild).servers() as servers:
            if server_name in servers:
                del servers[server_name]
                await ctx.send(f"✅ Server `{server_name}` wurde entfernt.")
            else:
                await ctx.send(f"❌ Server `{server_name}` ist nicht registriert.")

    ### 📌 Befehle zur Anpassung der Status-Embeds

    @commands.command()
    async def setembed(self, ctx, status: str, *, embed_text: str):
        """Setzt das Embed für Online, Offline oder Wartung"""
        status = status.lower()
        if status not in ["online", "offline", "maintenance"]:
            await ctx.send("❌ Ungültiger Status. Verwende: `online`, `offline` oder `maintenance`.")
            return

        async with self.config.guild(ctx.guild).embeds() as embeds:
            embeds[status] = {"description": embed_text}

        await ctx.send(f"✅ Das Embed für `{status}` wurde aktualisiert.")

    @commands.command()
    async def getembed(self, ctx, status: str):
        """Zeigt das aktuelle Embed für einen Status"""
        status = status.lower()
        if status not in ["online", "offline", "maintenance"]:
            await ctx.send("❌ Ungültiger Status. Verwende: `online`, `offline` oder `maintenance`.")
            return

        embeds = await self.config.guild(ctx.guild).embeds()
        embed_data = embeds.get(status)

        if embed_data:
            embed = discord.Embed(
                title=f"Embed für {status.capitalize()}",
                description=embed_data.get("description", "Keine Beschreibung gesetzt."),
                color=discord.Color.blue()
            )
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"❌ Kein Embed für `{status}` gesetzt.")

    ### 📌 Befehle zur Verwaltung von Alerts

    @commands.command()
    async def setalert(self, ctx, alert_type: str, state: str):
        """Aktiviert oder deaktiviert Alerts für Offline oder volle Server"""
        alert_type = alert_type.lower()
        if alert_type not in ["offline", "maxplayers"]:
            await ctx.send("❌ Ungültiger Alert-Typ. Verwende: `offline` oder `maxplayers`.")
            return

        state = state.lower() in ["on", "true", "yes"]
        async with self.config.guild(ctx.guild).alerts() as alerts:
            alerts[alert_type] = state

        await ctx.send(f"✅ Alert `{alert_type}` wurde {'aktiviert' if state else 'deaktiviert'}.")

    @commands.command()
    async def alertstatus(self, ctx):
        """Zeigt die aktuelle Alert-Konfiguration"""
        alerts = await self.config.guild(ctx.guild).alerts()
        status_text = "\n".join([f"🔔 `{alert}`: {'🟢 AN' if state else '🔴 AUS'}" for alert, state in alerts.items()])
        embed = discord.Embed(
            title="📢 Alert-Status",
            description=status_text or "Keine Alerts aktiviert.",
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed)
