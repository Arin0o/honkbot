import discord
from redbot.core import commands, Config
from datetime import datetime
import asyncio
import logging

log = logging.getLogger("red.birthdaycog")

class BirthdayCog(commands.Cog):
    """Ein Geburtstags-Cog für RedBot"""
    
    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1234567890, force_registration=True)
        
        default_guild = {
            "birthdays": {},  # Speichert Geburtstage {user_id: "DD.MM"}
            "bday_channel": None,  # Speichert den Kanal für Geburtstagsnachrichten
            "last_sent": ""  # Speichert das letzte gesendete Datum, um doppelte Nachrichten zu vermeiden
        }
        self.config.register_guild(**default_guild)
        self.bot.loop.create_task(self.birthday_check_loop())

    async def birthday_check_loop(self):
        """Prüft einmal um 0 Uhr auf Geburtstage und wartet dann bis zum nächsten Tag."""
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            now = datetime.now()

            # Falls es exakt 00:00 Uhr ist, Geburtstage prüfen
            if now.hour == 0 and now.minute == 0:
                await self.check_and_send_birthdays()
                log.info("✅ Geburtstagsprüfung abgeschlossen.")

                # Warte 60 Sekunden, um mehrfaches Senden zu verhindern
                await asyncio.sleep(60)

            # Berechne die Zeit bis Mitternacht (nächster Tag)
            now = datetime.now()
            seconds_until_midnight = (
                (24 - now.hour - 1) * 3600 + (60 - now.minute - 1) * 60 + (60 - now.second)
            )
            log.info(f"⏳ Warte {seconds_until_midnight} Sekunden bis zur nächsten Geburtstagsprüfung.")
            
            # Warte, bis der nächste Tag beginnt
            await asyncio.sleep(seconds_until_midnight)
    async def check_and_send_birthdays(self, force=False):
        """Sendet Geburtstagsnachrichten oder gibt eine Nachricht aus, falls keiner Geburtstag hat (nur bei force)."""
        for guild in self.bot.guilds:
            birthdays = await self.config.guild(guild).birthdays()
            bday_channel_id = await self.config.guild(guild).bday_channel()
            last_sent = await self.config.guild(guild).last_sent()
            today = datetime.now().strftime("%d.%m")

            if last_sent == today and not force:
                log.info(f"🎂 Geburtstagsnachrichten wurden heute bereits gesendet. (force={force})")
                return  # Keine doppelte Nachricht senden
            
            if not bday_channel_id:
                log.warning(f"⚠ Kein Geburtstagskanal für {guild.name} gesetzt.")
                continue  # Kein Kanal gesetzt
                    
            channel = guild.get_channel(bday_channel_id)
            if not channel:
                log.warning(f"⚠ Der Kanal mit der ID {bday_channel_id} existiert nicht mehr.")
                continue  # Kanal existiert nicht mehr
            
            log.info(f"✅ Geburtstagskanal gefunden: {channel.name} ({channel.id})")

            sent_messages = 0
            for user_id, bday in birthdays.items():
                if bday == today:
                    user = guild.get_member(int(user_id))
                    if user:
                        try:
                            await channel.send(f"🎉 Herzlichen Glückwunsch zum Geburtstag, {user.mention}! 🎂")
                            log.info(f"🎉 Nachricht für {user.display_name} gesendet!")
                            sent_messages += 1
                        except discord.Forbidden:
                            log.error(f"❌ Fehler: Keine Berechtigung, in {channel.name} ({channel.id}) zu schreiben!")
                        except discord.HTTPException as e:
                            log.error(f"❌ Fehler beim Senden der Nachricht: {e}")

            # Falls keine Nachrichten gesendet wurden und force aktiv ist, sendet der Bot eine Nachricht
            if sent_messages == 0 and force:
                await channel.send("ℹ️ **Heute hat leider niemand Geburtstag.** 🎂😢")

            # Speichert das Datum nur, wenn es keine erzwungene Nachricht ist
            if not force:
                await self.config.guild(guild).last_sent.set(today)


    @commands.command()
    @commands.guild_only()
    async def checkbday(self, ctx):
        """Manuelle Überprüfung der heutigen Geburtstage"""
        await ctx.send("🔄 Prüfe Geburtstage...")
        await self.check_and_send_birthdays()
        await ctx.send("✅ Geburtstagsprüfung abgeschlossen.")

    @commands.command()
    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    async def forcebday(self, ctx):
        """Erzwingt die Geburtstagsnachricht, unabhängig vom letzten gesendeten Datum"""
        await ctx.send("🔄 Erzwinge Geburtstagsprüfung...")
        await self.check_and_send_birthdays(force=True)
        await ctx.send("✅ Geburtstagsnachricht wurde erzwungen!")

    @commands.command()
    @commands.guild_only()
    async def setbday(self, ctx, user: discord.Member, date: str):
        """Setzt den Geburtstag eines Nutzers (Format: TT.MM)"""
        try:
            datetime.strptime(date, "%d.%m")  # Prüfen, ob das Datum gültig ist
        except ValueError:
            return await ctx.send("⚠ Ungültiges Datum! Bitte verwende das Format TT.MM (z. B. 24.09).")
        
        await self.config.guild(ctx.guild).birthdays.set_raw(str(user.id), value=date)
        await ctx.send(f"✅ Der Geburtstag von {user.mention} wurde auf **{date}** gesetzt!")

    @commands.command()
    @commands.guild_only()
    async def delbday(self, ctx, user: discord.Member):
        """Löscht den Geburtstag eines Nutzers"""
        birthdays = await self.config.guild(ctx.guild).birthdays()
        
        if str(user.id) not in birthdays:
            return await ctx.send(f"⚠ {user.mention} hat keinen eingetragenen Geburtstag.")
        
        await self.config.guild(ctx.guild).birthdays.clear_raw(str(user.id))
        await ctx.send(f"🗑 Der Geburtstag von {user.mention} wurde gelöscht.")

    @commands.command()
    @commands.guild_only()
    async def listbday(self, ctx):
        """Listet alle Geburtstage auf"""
        birthdays = await self.config.guild(ctx.guild).birthdays()
        if not birthdays:
            return await ctx.send("📅 Es sind noch keine Geburtstage gespeichert.")
        
        msg = "**🎂 Geburtstagsliste:**\n"
        for user_id, date in sorted(birthdays.items(), key=lambda x: x[1]):  # Sortiert nach Datum
            user = ctx.guild.get_member(int(user_id))
            msg += f"• {user.display_name if user else f'User {user_id} (verlassen)'} → **{date}**\n"
        
        await ctx.send(msg)

    @commands.command()
    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    async def setbdaychannel(self, ctx, channel: discord.TextChannel):
        """Setzt den Kanal für Geburtstagsnachrichten"""
        await self.config.guild(ctx.guild).bday_channel.set(channel.id)
        await ctx.send(f"✅ Geburtstagsnachrichten werden nun in {channel.mention} gesendet!")

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        """Löscht den Geburtstag eines Nutzers, wenn er den Server verlässt"""
        birthdays = await self.config.guild(member.guild).birthdays()
        if str(member.id) in birthdays:
            await self.config.guild(member.guild).birthdays.clear_raw(str(member.id))
            log.info(f"🗑 Geburtstag von {member} automatisch entfernt (Server verlassen).")

    @commands.command()
    async def bday(self, ctx, subcommand: str = None):
        """Zeigt eine Liste aller Geburtstagsbefehle oder eine Beschreibung für einen bestimmten Befehl."""
        help_text = {
            "setbday": "`!setbday @User TT.MM` - Setzt den Geburtstag eines Nutzers im Format `TT.MM` (z. B. `!setbday @Max 24.09`).",
            "delbday": "`!delbday @User` - Löscht den Geburtstag eines Nutzers.",
            "listbday": "`!listbday` - Zeigt alle gespeicherten Geburtstage an.",
            "setbdaychannel": "`!setbdaychannel #channel` - Setzt den Channel, in dem die Geburtstagsnachrichten gesendet werden.",
            "checkbday": "`!checkbday` - Prüft manuell, ob heute jemand Geburtstag hat, und sendet eine Nachricht, falls ja.",
            "forcebday": "`!forcebday` - Erzwingt die Geburtstagsprüfung. Falls niemand Geburtstag hat, gibt es eine entsprechende Nachricht.",
            "bday": "`!bday help` - Zeigt diese Hilfe an."
        }

        if subcommand and subcommand.lower() in help_text:
            await ctx.send(f"ℹ️ **Hilfe für `{subcommand}`:**\n{help_text[subcommand.lower()]}")
        else:
            help_message = "**🎂 Geburtstagsbefehle:**\n"
            for cmd, desc in help_text.items():
                help_message += f"• {desc}\n"
            help_message += "\nVerwende `!bday help <befehl>` für genauere Infos."
            await ctx.send(help_message)
