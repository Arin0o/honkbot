import discord
import json
import os
import datetime
import matplotlib.pyplot as plt
import numpy as np
from redbot.core import commands, checks, Config
from redbot.core.bot import Red
from discord.ext import tasks

class VoiceHeatmap(commands.Cog):
    """
    Erstellt eine Heatmap der Voice-Chat-Aktivität über 24 Stunden und 7 Wochentage
    auf Basis der letzten 90 Tage.
    """

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1234567890, force_registration=True)
        self.config.register_guild(
            voice_data=[],
            ignored_channels=[],
            darkmode=False
        )
        self.collect_voice_data.start()

    def cog_unload(self):
        self.collect_voice_data.cancel()

    @tasks.loop(minutes=1)
    async def collect_voice_data(self):
        for guild in self.bot.guilds:
            ignored = await self.config.guild(guild).ignored_channels()
            count = sum(len(vc.members) for vc in guild.voice_channels if vc.id not in ignored)
            timestamp = datetime.datetime.utcnow().replace(second=0, microsecond=0).isoformat()
            data = await self.config.guild(guild).voice_data()
            data.append({"timestamp": timestamp, "voice_count": count})
            MAX_ENTRIES = 129600
            if len(data) > MAX_ENTRIES:
                data = data[-MAX_ENTRIES:]
            cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=90)
            data = [entry for entry in data if datetime.datetime.fromisoformat(entry["timestamp"]) > cutoff]
            await self.config.guild(guild).voice_data.set(data)

    @collect_voice_data.before_loop
    async def before_collect(self):
        await self.bot.wait_until_ready()

    @commands.command(name="voiceheat")
    @checks.admin()
    async def voiceheat(self, ctx, subcommand: str = None, *, argument: str = None):
        """Steuert die VoiceHeatmap-Funktionen."""
        if subcommand is None or subcommand.lower() == "help":
            text = (
                "**VoiceHeatmap – Hilfe**\n"
                "`!voiceheat map` – Zeigt die aktuelle Heatmap an.\n"
                "`!voiceheat dark` – Schaltet den Darkmode ein oder aus.\n"
                "`!voiceheat ignore <#VoiceChannel>` – Ignoriert einen Voicechannel bei der Analyse.\n"
                "`!voiceheat unignore <#VoiceChannel>` – Entfernt einen Channel aus der Ignorierliste.\n"
                "`!voiceheat help` – Zeigt diese Hilfe an.\n"
                "`!voiceheat status` – Zeigt den aktuellen Status (Darkmode, Datenpunkte etc.)."
            )
            return await ctx.send(text)

        if subcommand.lower() == "dark":
            current = await self.config.guild(ctx.guild).darkmode()
            await self.config.guild(ctx.guild).darkmode.set(not current)
            status = "aktiviert" if not current else "deaktiviert"
            return await ctx.send(f"Darkmode ist jetzt {status}.")

        if subcommand.lower() == "ignore" and argument:
            try:
                channel_id = int(argument.strip("<#>"))
                channel = ctx.guild.get_channel(channel_id)
                if isinstance(channel, discord.VoiceChannel):
                    ignored = await self.config.guild(ctx.guild).ignored_channels()
                    if channel.id not in ignored:
                        ignored.append(channel.id)
                        await self.config.guild(ctx.guild).ignored_channels.set(ignored)
                    return await ctx.send(f"Kanal {channel.mention} wird nun ignoriert.")
                else:
                    return await ctx.send("Das ist kein gültiger Voicechannel.")
            except Exception:
                return await ctx.send("Fehler beim Verarbeiten des Channels. Bitte verwende einen gültigen Link oder eine Channel-ID.")

        if subcommand.lower() == "unignore" and argument:
            try:
                channel_id = int(argument.strip("<#>"))
                channel = ctx.guild.get_channel(channel_id)
                if isinstance(channel, discord.VoiceChannel):
                    ignored = await self.config.guild(ctx.guild).ignored_channels()
                    if channel.id in ignored:
                        ignored.remove(channel.id)
                        await self.config.guild(ctx.guild).ignored_channels.set(ignored)
                        return await ctx.send(f"Kanal {channel.mention} wird nicht mehr ignoriert.")
                    else:
                        return await ctx.send("Dieser Kanal wird aktuell nicht ignoriert.")
                else:
                    return await ctx.send("Das ist kein gültiger Voicechannel.")
            except Exception:
                return await ctx.send("Fehler beim Verarbeiten des Channels. Bitte verwende einen gültigen Link oder eine Channel-ID.")

        if subcommand.lower() == "status":
            dark = await self.config.guild(ctx.guild).darkmode()
            ignored = await self.config.guild(ctx.guild).ignored_channels()
            data = await self.config.guild(ctx.guild).voice_data()
            count = len(data)
            return await ctx.send(
                f"📊 **Status der VoiceHeatmap:**\n"
                f"- Darkmode: {'aktiviert' if dark else 'deaktiviert'}\n"
                f"- Ignorierte Channels: {len(ignored)}\n"
                f"- Gespeicherte Datenpunkte: {count}"
            )

        if subcommand.lower() == "map":
            data = await self.config.guild(ctx.guild).voice_data()
            if not data:
                return await ctx.send("Keine Voice-Daten vorhanden.")

            heatmap = [[[] for _ in range(24)] for _ in range(7)]
            for entry in data:
                dt = datetime.datetime.fromisoformat(entry["timestamp"])
                weekday = dt.weekday()
                hour = dt.hour
                heatmap[weekday][hour].append(entry["voice_count"])

            avg_data = [[np.mean(hour) if hour else 0 for hour in day] for day in heatmap]
            heatmap_array = np.array(avg_data)

            dark = await self.config.guild(ctx.guild).darkmode()
            if dark:
                plt.style.use('dark_background')
                cmap = 'plasma'
            else:
                plt.style.use('default')
                cmap = 'hot'

            fig, ax = plt.subplots(figsize=(18, 6))
            cax = ax.imshow(heatmap_array, cmap=cmap, aspect='auto', origin='upper')
            plt.colorbar(cax, ax=ax, label='Durchschnittliche Nutzerzahl')

            gesamt_anzahl = sum([sum(stunde) for tag in heatmap for stunde in tag if stunde])
            durchschn_pro_stunde = gesamt_anzahl / 24 if gesamt_anzahl else 0
            durchschn_pro_tag = gesamt_anzahl / 7 if gesamt_anzahl else 0
            max_wert = np.max(heatmap_array)

            stat_text = f"Ø/h: {durchschn_pro_stunde:.1f} | Ø/Tag: {durchschn_pro_tag:.1f} | Max: {max_wert:.0f}"
            ax.text(1.02, -0.1, stat_text, transform=ax.transAxes, fontsize=10, ha='left', va='top')
            ax.set_title('Voice-Aktivität Heatmap (letzte 90 Tage)')
            ax.set_xlabel('Stunde des Tages')
            ax.set_ylabel('Wochentag')
            ax.set_xticks(np.arange(0, 24, 1))
            ax.set_xticklabels([str(h + 1) for h in range(24)])
            ax.set_yticks(np.arange(0, 7, 1))
            ax.set_yticklabels(["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"])

            file_path = os.path.join(os.path.dirname(__file__), "heatmap.png")
            plt.tight_layout(rect=[0, 0, 0.97, 1])
            plt.savefig(file_path)
            plt.close()

            return await ctx.send(file=discord.File(file_path))

        return await ctx.send("Unbekannter Unterbefehl. Nutze `!voiceheat help` für eine Übersicht.")
