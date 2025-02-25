import discord
import requests
from redbot.core import commands, Config, tasks
from redbot.core.bot import Red

class AMPAPI(commands.Cog):
    """AMP Server Status Cog für RedBot"""

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1234567892)
        default_guild = {
            "amp_url": "",
            "username": "",
            "password": "",
            "channel_id": None,
            "server_instances": {},
            "session_id": None,
            "embed_online": None,
            "embed_offline": None,
            "embed_maintenance": None,
            "server_embeds": {},
            "alerts": {},
            "alert_channels": {}
        }
        self.config.register_guild(**default_guild)
        self.update_status.start()

    def cog_unload(self):
        self.update_status.cancel()

    @commands.group()
    async def ampapi(self, ctx):
        """Verwaltung der AMP API und Serverstatus-Überwachung."""
        if ctx.invoked_subcommand is None:
            help_text = (
                "**📌 1️⃣ Grundkonfiguration**\n"
                "`!ampapi setamp <API_URL> <Benutzer> <Passwort>` - **Setzt die AMP-Login-Daten**\n"
                "`!ampapi setchannel <#channel>` - **Legt den Discord-Channel für Status-Updates fest**\n\n"
                "**📌 2️⃣ Server hinzufügen & verwalten**\n"
                "`!ampapi addserver <Servername>` - **Fügt einen neuen Server zur Überwachung hinzu**\n"
                "`!ampapi removeserver <Servername>` - **Entfernt einen Server aus der Überwachung**\n"
                "`!ampapi rename <AlterName> <NeuerName>` - **Ändert den Namen eines überwachten Servers**\n"
                "`!ampapi listservers` - **Zeigt alle überwachten Server an**\n"
                "`!ampapi status <Server>` - **Zeigt den aktuellen Status eines einzelnen Servers**\n"
                "`!ampapi forceupdate` - **Erzwingt eine sofortige Aktualisierung aller Server**\n\n"
                "**📌 3️⃣ Embed-Nachrichten anpassen**\n"
                "`!ampapi setembed online/offline/maintenance {JSON}` - **Setzt das Standard-Embed für einen Status**\n"
                "`!ampapi setserverembed <Server> online/offline/maintenance {JSON}` - **Setzt ein individuelles Embed für einen Server**\n"
                "`!ampapi getembed online/offline/maintenance` - **Zeigt das aktuelle Standard-Embed für einen Status**\n"
                "`!ampapi getserverembed <Server> online/offline/maintenance` - **Zeigt das individuelle Server-Embed**\n\n"
                "**📌 4️⃣ Alerts & Warnungen konfigurieren**\n"
                "`!ampapi setalertchannel <Server> <#channel>` - **Setzt den Discord-Channel für Alerts eines Servers**\n"
                "`!ampapi togglealert <Server> offline/maxplayers on/off` - **Aktiviert/Deaktiviert spezifische Alerts**\n"
                "`!ampapi setalertmsg <Server> offline/maxplayers {JSON}` - **Ändert die Alert-Nachricht für verschiedene Events**\n"
            )
            embed = discord.Embed(title="📖 AMP API Hilfe", description=help_text, color=discord.Color.blue())
            await ctx.send(embed=embed)

    @ampapi.command()
    async def setamp(self, ctx, amp_url: str, username: str, password: str):
        """Setzt die AMP-API-Daten (Admin only)"""
        await self.config.guild(ctx.guild).amp_url.set(amp_url)
        await self.config.guild(ctx.guild).username.set(username)
        await self.config.guild(ctx.guild).password.set(password)
        await ctx.send("✅ AMP-API-Daten gespeichert.")

    @ampapi.command()
    async def setchannel(self, ctx, channel: discord.TextChannel):
        """Setzt den Status-Update-Channel"""
        await self.config.guild(ctx.guild).channel_id.set(channel.id)
        await ctx.send(f"✅ Updates werden nun in {channel.mention} gepostet.")

    @ampapi.command()
    async def addserver(self, ctx, instance_name: str):
        """Fügt einen neuen Server zur Überwachung hinzu"""
        servers = await self.config.guild(ctx.guild).server_instances()
        servers[instance_name] = None
        await self.config.guild(ctx.guild).server_instances.set(servers)
        await ctx.send(f"✅ Server `{instance_name}` hinzugefügt.")

    @ampapi.command()
    async def removeserver(self, ctx, instance_name: str):
        """Entfernt einen Server aus der Überwachung"""
        servers = await self.config.guild(ctx.guild).server_instances()
        if instance_name in servers:
            del servers[instance_name]
            await self.config.guild(ctx.guild).server_instances.set(servers)
            await ctx.send(f"✅ Server `{instance_name}` wurde entfernt.")
        else:
            await ctx.send("❌ Dieser Server ist nicht in der Liste.")

    @ampapi.command()
    async def status(self, ctx, instance_name: str):
        """Zeigt den aktuellen Status eines Servers"""
        status = await self.get_server_status(ctx.guild, instance_name)
        if status:
            embed = await self.get_embed(ctx.guild, instance_name, status)
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"❌ Server `{instance_name}` konnte nicht abgefragt werden.")

    async def update_status(self):
        """Holt den Status der Server und prüft auf Änderungen"""
        for guild in self.bot.guilds:
            alert_channels = await self.config.guild(guild).alert_channels()
            alerts = await self.config.guild(guild).alerts()
            server_instances = await self.config.guild(guild).server_instances()

            for instance in server_instances.keys():
                status = await self.get_server_status(guild, instance)
                embed = await self.get_embed(guild, instance, status)

                alert_channel_id = alert_channels.get(instance)
                alert_channel = self.bot.get_channel(alert_channel_id) if alert_channel_id else None

                if status:
                    if status["status"] == "Offline" and instance in alerts and alerts[instance].get("offline", False):
                        alert_msg = alerts[instance].get("offline_msg", f"⚠️ **{instance} ist OFFLINE! 🚨**")
                        if alert_channel:
                            await alert_channel.send(alert_msg)

                    if status["players"] >= status["max_players"] and instance in alerts and alerts[instance].get("maxplayers", False):
                        alert_msg = alerts[instance].get("maxplayers_msg", f"⚠️ **{instance} hat die maximale Spielerzahl erreicht!**")
                        if alert_channel:
                            await alert_channel.send(alert_msg)

    async def get_server_status(self, guild, instance_name):
        """Fragt den Status einer AMP-Instanz ab"""
        session_id = await self.config.guild(guild).session_id() or await self.login(guild)
        amp_url = await self.config.guild(guild).amp_url()

        if not session_id or not amp_url:
            return None

        url = f"{amp_url}/API/Core/GetStatus"
        headers = {"Authorization": f"Bearer {session_id}", "Content-Type": "application/json"}
        response = requests.post(url, headers=headers, json={"Instance": instance_name})

        return response.json() if response.status_code == 200 else None
