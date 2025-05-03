from redbot.core import commands, Config
from discord.ext import tasks
import aiohttp
import discord
import asyncio
import logging

log = logging.getLogger("red.api")  # Logging für Fehlerausgabe

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

    async def send_error_embed(self, ctx, description):
        embed = discord.Embed(
            title="⚠️ Fehler",
            description=description,
            color=0xFF0000
        )
        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        """Globale Fehlerbehandlung für Commands."""
        if isinstance(error, commands.CommandNotFound):
            return
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❗ Fehlendes Argument: `{error.param.name}`.\nBenutze `!apihelp` für Hilfe.")
            return
        if isinstance(error, commands.BadArgument):
            await ctx.send("❗ Ungültiges Argument. Bitte überprüfe deine Eingaben.")
            return
        if isinstance(error, commands.CommandInvokeError):
            log.error(f"Fehler in Command {ctx.command}: {error.original}")
            await self.send_error_embed(ctx, f"Fehler beim Ausführen des Befehls: {error.original}")
            return

        log.error(f"Unerwarteter Fehler: {error}")
        await self.send_error_embed(ctx, "Ein unerwarteter Fehler ist aufgetreten.")

    @commands.command(name="apihelp")
    async def api_help(self, ctx):
        """Zeigt alle verfügbaren API-Befehle und deren Nutzung."""
        embed = discord.Embed(title="📖 API Befehlsübersicht", color=0x3498db)

        embed.add_field(
            name="!addinstance",
            value="`!addinstance [instance_id] [name] [api_url] [username] [password] [ip] [steamlink] [description]`\nFügt eine neue Instanz hinzu.",
            inline=False
        )

        embed.add_field(
            name="!editinstance",
            value="`!editinstance [instance_id] [feld] [wert]`\nBearbeitet ein bestimmtes Feld einer bestehenden Instanz.",
            inline=False
        )

        embed.add_field(
            name="!removeinstance",
            value="`!removeinstance [instance_id]`\nEntfernt eine Instanz aus der Überwachung.",
            inline=False
        )

        embed.add_field(
            name="!listinstances",
            value="`!listinstances`\nListet alle aktuell überwachten Instanzen auf.",
            inline=False
        )

        embed.add_field(
            name="!updateinstances",
            value="`!updateinstances`\nAktualisiert manuell alle Instanzennachrichten.",
            inline=False
        )

        embed.add_field(
            name="!setstatuschannel",
            value="`!setstatuschannel [#channel]`\nSetzt den Discord-Kanal, in dem Statusupdates angezeigt werden.",
            inline=False
        )

        await ctx.send(embed=embed)

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def addinstance(self, ctx, instance_id: str, name: str, api_url: str, username: str, password: str, ip: str, steamlink: str = "", *, description: str = "Keine Beschreibung"):
        try:
            instances = await self.config.instances()
            if instance_id in instances:
                await ctx.send("❌ Diese Instanz-ID existiert bereits.")
                return

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
            await ctx.send(f"✅ Instanz '{name}' hinzugefügt.")
        except Exception as e:
            log.error(f"addinstance: {e}")
            await self.send_error_embed(ctx, f"Fehler beim Hinzufügen der Instanz: {e}")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def removeinstance(self, ctx, instance_id: str):
        """Entfernt eine Instanz aus der Überwachung."""
        try:
            instances = await self.config.instances()
            if instance_id not in instances:
                await ctx.send("❌ Instanz-ID nicht gefunden.")
                return

            channel_id = await self.config.channel_id()
            channel = self.bot.get_channel(channel_id)
            if channel:
                message_id = instances[instance_id].get("message_id")
                if message_id:
                    try:
                        message = await channel.fetch_message(message_id)
                        await message.delete()
                    except discord.NotFound:
                        pass
                    except discord.HTTPException as e:
                        log.error(f"Fehler beim Löschen der Statusnachricht: {e}")

            del instances[instance_id]
            await self.config.instances.set(instances)
            await ctx.send(f"✅ Instanz `{instance_id}` wurde entfernt.")
        except Exception as e:
            log.error(f"removeinstance: {e}")
            await self.send_error_embed(ctx, f"Fehler beim Entfernen der Instanz: {e}")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def listinstances(self, ctx):
        """Listet alle überwachten Instanzen auf."""
        try:
            instances = await self.config.instances()
            if not instances:
                await ctx.send("ℹ️ Keine Instanzen gefunden.")
                return

            embeds = []
            embed = discord.Embed(title="🖥️ Überwachte Instanzen", color=0x3498db)
            count = 0

            for instance_id, info in instances.items():
                embed.add_field(
                    name=f"{info['name']} ({instance_id})",
                    value=f"IP: {info['ip']}\nBeschreibung: {info['description']}",
                    inline=False
                )
                count += 1
                if count == 25:
                    embeds.append(embed)
                    embed = discord.Embed(title="🖥️ Weitere überwachte Instanzen", color=0x3498db)
                    count = 0

            embeds.append(embed)
            for e in embeds:
                await ctx.send(embed=e)
        except Exception as e:
            log.error(f"listinstances: {e}")
            await self.send_error_embed(ctx, f"Fehler beim Auflisten der Instanzen: {e}")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def editinstance(self, ctx, instance_id: str, field: str, *, value: str):
        try:
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
        except Exception as e:
            log.error(f"editinstance: {e}")
            await self.send_error_embed(ctx, f"Fehler beim Bearbeiten der Instanz: {e}")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def updateinstances(self, ctx):
        try:
            await ctx.send("🔄 Aktualisiere alle Instanzen...")
            await self.status_updater()
            await ctx.send("✅ Instanzen wurden aktualisiert!")
        except Exception as e:
            log.error(f"updateinstances: {e}")
            await self.send_error_embed(ctx, f"Fehler beim Aktualisieren: {e}")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def setstatuschannel(self, ctx, channel: discord.TextChannel):
        try:
            await self.config.channel_id.set(channel.id)
            await ctx.send(f"Kanal für Statusupdates gesetzt: {channel.mention}")
        except Exception as e:
            log.error(f"setstatuschannel: {e}")
            await self.send_error_embed(ctx, f"Fehler beim Setzen des Kanals: {e}")

    async def login_amp(self, api_url: str, username: str, password: str):
        login_endpoint = f"{api_url}API/Core/Login"
        login_data = {"username": username, "password": password, "token": "", "rememberMe": False}
        headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(login_endpoint, json=login_data, headers=headers, timeout=10) as response:
                    data = await response.json()
                    if data.get("success"):
                        return data.get("sessionID"), None
                    return None, f"Login fehlgeschlagen: {data.get('message', 'Unbekannter Fehler')}"
            except Exception as e:
                return None, f"Fehler bei der Anmeldung: {e}"

    async def fetch_amp_instance_status(self, instance_id: str, instance_info: dict):
        try:
            session_id, error = await self.login_amp(instance_info["api_url"], instance_info["username"], instance_info["password"])
            if error:
                return None, error

            status_endpoint = f"{instance_info['api_url']}API/ADSModule/GetInstance"
            payload = {"SESSIONID": session_id, "InstanceId": instance_id}
            headers = {'Accept': 'application/json'}

            async with aiohttp.ClientSession() as session:
                async with session.post(status_endpoint, json=payload, headers=headers, timeout=10) as response:
                    if "text/html" in response.headers.get("Content-Type", ""):
                        return None, "Fehler: API hat HTML statt JSON zurückgegeben."

                    if response.status != 200:
                        return None, f"API-Fehler {response.status}"

                    data = await response.json()
                    if not data or "Running" not in data or data.get("AppState", 0) != 20:
                        return None, "Keine gültige Antwort erhalten."
                    return data, None
        except asyncio.TimeoutError:
            return None, "Timeout bei der Anfrage."
        except Exception as e:
            return None, f"Fehler beim Abrufen des Status: {e}"

    @tasks.loop(minutes=2)
    async def status_updater(self):
        log.info("Starte Status-Update...")
        instances = await self.config.instances()
        channel_id = await self.config.channel_id()

        channel = self.bot.get_channel(channel_id)
        if not channel:
            log.error("Kanal nicht gefunden!")
            return

        for instance_id, info in instances.items():
            status, error = await self.fetch_amp_instance_status(instance_id, info)
            if error or not status:
                status_text = f"❌ läuft nicht (Fehler: {error})"
                embed_color = 0xff0000
                player_count = "N/A"
            else:
                running = status.get("Running", False)
                player_count = status.get("Metrics", {}).get("Active Users", {}).get("RawValue", "0")
                status_text = "✅ läuft" if running else "❌ läuft nicht"
                embed_color = 0x00ff00 if running else 0xff0000

            embed = discord.Embed(
            title=f"🎮 {info['name']}",
            color=embed_color
            )
            embed.add_field(name="📝 Beschreibung", value=info["description"], inline=False)
            embed.add_field(name="🌐 IP-Adresse", value=f"`{info['ip']}`", inline=False)

            steamlink = info["steamlink"] or None
            if steamlink:
                embed.add_field(name="🔗 Steam Joinlink", value=f"[Hier klicken]({steamlink})", inline=False)
            else:
                embed.add_field(name="🔗 Steam Joinlink", value="Kein Link angegeben", inline=False)

            embed.add_field(name="📡 Status", value=("🟢 läuft" if status_text.startswith("✅") else "🔴 offline"), inline=True)
            embed.add_field(name="👥 Spielerzahl", value=player_count, inline=True)

            embed.set_footer(text="Powered by Hossa INC")
            embed.timestamp = discord.utils.utcnow()

            try:
                message = await channel.fetch_message(info["message_id"])
                await message.edit(embed=embed)
            except discord.NotFound:
                msg = await channel.send(embed=embed)
                instances[instance_id]["message_id"] = msg.id
                await self.config.instances.set(instances)
            except discord.HTTPException as e:
                log.error(f"Fehler beim Aktualisieren der Nachricht: {e}")
                msg = await channel.send(embed=embed)
                instances[instance_id]["message_id"] = msg.id
                await self.config.instances.set(instances)

    @status_updater.before_loop
    async def before_status_updater(self):
        await self.bot.wait_until_ready()
