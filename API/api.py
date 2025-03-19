from redbot.core import commands, Config
from discord.ext import tasks
import aiohttp
import discord

class API(commands.Cog):
    """Cog zur Abfrage mehrerer AMP-Instanzen und Ausgabe in Discord."""


    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1234567890)
        default_global = {"instances": {}, "channel_id": 0}
        self.config.register_global(**default_global)
        self.ensure_config_initialized()
        self.status_updater.start()

    def ensure_config_initialized(self):
        """Stellt sicher, dass alle Konfigurationswerte existieren."""
        if not self.config.instances():
            self.config.instances.set({})
        if not self.config.channel_id():
            self.config.channel_id.set(0)

    def cog_unload(self):
        self.status_updater.cancel()

 
    @commands.command(name="apihelp")
    async def api_help(self, ctx):
        """Zeigt alle verfügbaren API-Befehle und deren Nutzung."""
        embed = discord.Embed(title="📖 API Befehlsübersicht", color=0x3498db)

        embed.add_field(
            name="!addinstance",
            value="`!addinstance [instance_id] [name] [api_url] [username] [password] [ip] [steamlink] [description]`\nFügt eine neue Instanz hinzu.",
            inline=False
        )

        embed.add_field(name="!editinstance [instance_id] [feld] [wert]",
                        value="Bearbeitet ein bestimmtes Feld einer bestehenden Instanz.",
                        inline=False)

        embed.add_field(name="!updateinstances",
                        value="Aktualisiert manuell alle Instanzenachrichten.",
                        inline=False)

        embed.add_field(name="!setstatuschannel [#channel]",
                        value="Setzt den Discord-Kanal, in dem Statusupdates angezeigt werden.",
                        inline=False)

        await ctx.send(embed=embed)
    @commands.command()
    async def addinstance(self, ctx, instance_id: str, name: str, api_url: str, username: str, password: str, ip: str, steamlink: str = "", *, description: str = "Keine Beschreibung"):
        instances = await self.config.instances()
        instances[instance_id] = {
            "name": name,
            "api_url": api_url,
            "username": username,
            "password": password,
            "ip": ip,
            "steamlink": steamlink,
            "description": description,
            "message_id": 0
        }
        await self.config.instances.set(instances)
        await ctx.send(f"Instanz '{name}' hinzugefügt.")

    @commands.command()
    async def updateinstances(self, ctx):
            """Aktualisiert manuell alle Instanzen."""
            await ctx.send("🔄 Aktualisiere alle Instanzen...")
            await self.status_updater()
            await ctx.send("✅ Instanzen wurden aktualisiert!")

    @commands.command()
    async def editinstance(self, ctx, instance_id: str, field: str, *, value: str):
        instances = await self.config.instances()
        if instance_id not in instances:
            await ctx.send("Instanz-ID nicht gefunden.")
            return
        if field in instances[instance_id]:
            instances[instance_id][field] = value
            await self.config.instances.set(instances)
            await ctx.send(f"{field} aktualisiert für Instanz '{instance_id}'.")
        else:
            await ctx.send("Ungültiges Feld.")

    async def fetch_amp_instance_status(self, instance_id: str, instance_info: dict):
        """Holt eine neue Session-ID vor jeder Anfrage und ruft dann den Status ab."""
        session_id, error = await self.login_amp(instance_info["api_url"], instance_info["username"], instance_info["password"])
        if error:
            return None, error

        status_endpoint = f"{instance_info['api_url']}API/ADSModule/GetInstance"
        payload = {"SESSIONID": session_id, "InstanceId": instance_id}
        headers = {'Accept': 'application/json'}

        #print(f"[DEBUG] Sende Anfrage an {status_endpoint} mit Payload: {payload}")

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(status_endpoint, json=payload, headers=headers, timeout=10) as response:
                    response_text = await response.text()
                    #print(f"[DEBUG] API Antwort ({instance_id}): {response_text}")
                    if "text/html" in response.headers.get("Content-Type", ""):
                        return None, "Fehler: API hat HTML statt JSON zurückgegeben. Prüfe die API-URL!"
                    response_text = await response.text()
                   # print(f"[DEBUG] API Antwort ({instance_id}): {response_text}")
                    
                    if response.status != 200:
                        return None, f"API-Fehler {response.status}: {response_text}"
                    
                    try:
                        data = await response.json()
                        if not data or "Running" not in data or data.get("AppState", 0) != 20:
                            return None, "Fehler: Keine 'Running'-Information in API-Antwort. Server möglicherweise offline."
                        return data, None
                    except Exception as e:
                        return None, f"Fehler beim Parsen der API-Antwort: {e}"
            except Exception as e:
                return None, f"Fehler beim Abrufen des Status: {e}"

    async def login_amp(self, api_url: str, username: str, password: str):
        """Holt eine neue Session-ID von der AMP-API."""
        login_endpoint = f"{api_url}API/Core/Login"
        login_data = {"username": username, "password": password, "token": "", "rememberMe": False}
        headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(login_endpoint, json=login_data, headers=headers, timeout=10) as response:
                    data = await response.json()
                    if data.get("success"):
                        session_id = data.get("sessionID")
                        #print(f"[DEBUG] Neue Session-ID erhalten: {session_id}")
                        return session_id, None
                    return None, f"Login fehlgeschlagen: {data.get('message', 'Unbekannter Fehler')}"
            except Exception as e:
                return None, f"Fehler bei der Anmeldung: {e}"

    @tasks.loop(minutes=2)
    async def status_updater(self):
        print("[DEBUG] Starte Status-Update...")
        instances = await self.config.instances()
        channel_id = await self.config.channel_id()

        channel = self.bot.get_channel(channel_id)
        if not channel:
            print("[ERROR] Kanal nicht gefunden!")
            return

        for instance_id, info in instances.items():
            #print(f"[DEBUG] Verarbeite Instanz {instance_id}...")
            status, error = await self.fetch_amp_instance_status(instance_id, info)
            if error or not status:
                print(f"[ERROR] Fehler bei Instanz {instance_id}: {error}")
                status_text = f"❌ läuft nicht (Fehler: {error})"
                embed_color = 0xff0000  # Rot für Fehler oder Offline
                player_count = "N/A"
            else:
                running = status.get("Running", False)
                player_count = status.get("Metrics", {}).get("Active Users", {}).get("RawValue", "0")
                if running:
                    status_text = "✅ läuft"
                    embed_color = 0x00ff00  # Grün für Online
                else:
                    status_text = "❌ läuft nicht"
                    embed_color = 0xff0000  # Rot für Offline

            embed = discord.Embed(title=info["name"], description=info["description"], color=embed_color)
            embed.add_field(name="IP", value=info["ip"], inline=True)
            embed.add_field(name="Steam Joinlink", value=info["steamlink"] or "Kein Link", inline=False)
            embed.add_field(name="Status", value=status_text, inline=True)
            embed.add_field(name="Spielerzahl", value=player_count, inline=True)

            try:
                message = await channel.fetch_message(info["message_id"])
                await message.edit(embed=embed)
            except discord.NotFound:
                msg = await channel.send(embed=embed)
                instances[instance_id]["message_id"] = msg.id
                await self.config.instances.set(instances)
            except discord.HTTPException as e:
                print(f"[ERROR] Fehler beim Aktualisieren der Nachricht: {e}")
                msg = await channel.send(embed=embed)
                instances[instance_id]["message_id"] = msg.id
                await self.config.instances.set(instances)

    @commands.command()
    async def setstatuschannel(self, ctx, channel: discord.TextChannel):
        await self.config.channel_id.set(channel.id)
        await ctx.send(f"Kanal für Statusupdates gesetzt: {channel.mention}")

    @status_updater.before_loop
    async def before_status_updater(self):
        await self.bot.wait_until_ready()