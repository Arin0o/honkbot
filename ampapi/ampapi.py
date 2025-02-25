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
