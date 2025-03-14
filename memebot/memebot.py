import discord
from redbot.core import commands, Config
from datetime import datetime, timedelta

class MemeBot(commands.Cog):
    """Ein Meme-Voting-Cog für RedBot"""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1234567890, force_registration=True)
        default_guild = {
            "meme_channel": None,
            "positive_emoji": "⬆️",
            "negative_emoji": "⬇️",
            "memes": {}
        }
        self.config.register_guild(**default_guild)

    async def get_top_meme(self, ctx, time_filter):
        """Findet das Bild mit den meisten Netto-Upvotes"""
        await self.update_reaction_counts(ctx)  # FIX: Jetzt mit self aufgerufen

        guild = ctx.guild
        data = await self.config.guild(guild).memes()

        now = datetime.utcnow()
        time_threshold = {
            "day": now - timedelta(days=1),
            "week": now - timedelta(weeks=1),
            "month": now.replace(day=1),
            "year": now.replace(month=1, day=1),
            "all": None
        }.get(time_filter, now.replace(day=1))

        filtered_memes = {
            msg_id: meme for msg_id, meme in data.items()
            if time_threshold is None or datetime.utcfromtimestamp(meme["timestamp"]) >= time_threshold
        }

        if not filtered_memes:
            return await ctx.send("❌ Keine Memes gefunden für diesen Zeitraum.")

        best_meme = max(filtered_memes.values(), key=lambda x: x["upvotes"] - x["downvotes"], default=None)

        if not best_meme:
            return await ctx.send("❌ Kein Meme gefunden.")

        netto_score = best_meme["upvotes"] - best_meme["downvotes"]
        message_link = f"https://discord.com/channels/{guild.id}/{best_meme['channel_id']}/{best_meme['message_id']}"

        await ctx.send(
            f"📸 **Meistgeupvotetes Meme für {time_filter}:**\n"
            f"👍 **Upvotes:** {best_meme['upvotes']} | 👎 **Downvotes:** {best_meme['downvotes']}\n"
            f"📊 **Netto-Wertung:** {netto_score}\n"
            f"🔗 [Hier klicken, um das Bild zu sehen]({message_link})"
        )

    async def update_reaction_counts(self, ctx):
        """Zählt alle Reaktionen auf gespeicherte Memes neu"""
        guild = ctx.guild
        meme_channel_id = await self.config.guild(guild).meme_channel()

        if not meme_channel_id:
            return await ctx.send("❌ Es wurde noch kein Meme-Kanal festgelegt.")

        meme_channel = guild.get_channel(meme_channel_id)
        if not meme_channel:
            return await ctx.send("⚠️ Der gespeicherte Kanal existiert nicht mehr.")

        async with self.config.guild(guild).memes() as memes:
            updated = 0
            for message_id, meme in memes.items():
                try:
                    message = await meme_channel.fetch_message(int(message_id))
                    pos_emoji = await self.config.guild(ctx.guild).positive_emoji()
                    neg_emoji = await self.config.guild(ctx.guild).negative_emoji()

                    upvotes = 0
                    downvotes = 0

                    for reaction in message.reactions:
                        if str(reaction.emoji) == pos_emoji:
                            upvotes = reaction.count - 1  # 🛠️ -1, da der Bot selbst reagiert!
                        elif str(reaction.emoji) == neg_emoji:
                            downvotes = reaction.count - 1  # 🛠️ -1, falls der Bot reagiert hat

                    meme["upvotes"] = upvotes
                    meme["downvotes"] = downvotes
                    updated += 1
                except discord.NotFound:
                    print(f"[MemeBot] ❌ Nachricht {message_id} nicht gefunden, wird ignoriert.")

            await ctx.send(f"✅ Reaktionen für {updated} Memes aktualisiert.")


    @commands.group(name="mdma", invoke_without_command=True)
    async def mdma(self, ctx):
        """Zeigt eine Übersicht aller verfügbaren Befehle"""
        await self.mdma_help(ctx)

    @mdma.command(name="mdma")
    async def mdma_mdma(self, ctx):
        """Zeigt das meistgeupvotete Meme des Monats"""
        await self.get_top_meme(ctx, "month")

    @mdma.command(name="updatecounts")
    async def mdma_updatecounts(self, ctx):
        """Aktualisiert die Upvote- und Downvote-Zahlen aller Memes"""
        await self.update_reaction_counts(ctx)
        await ctx.send("✅ Alle Upvotes und Downvotes wurden aktualisiert!")

    @mdma.command(name="setmemechannel")
    @commands.admin()
    async def mdma_setmemechannel(self, ctx, channel: discord.TextChannel):
        """Setzt den Meme-Kanal"""
        await self.config.guild(ctx.guild).meme_channel.set(channel.id)
        await ctx.send(f"✅ Meme-Channel wurde auf {channel.mention} gesetzt!")

    @mdma.command(name="listchannel")
    async def mdma_listchannel(self, ctx):
        """Zeigt den aktuell eingestellten Meme-Kanal an"""
        meme_channel_id = await self.config.guild(ctx.guild).meme_channel()

        if not meme_channel_id:
            return await ctx.send("❌ Es wurde noch kein Meme-Kanal festgelegt.")

        meme_channel = ctx.guild.get_channel(meme_channel_id)
        if meme_channel:
            await ctx.send(f"📌 Der aktuell eingestellte Meme-Kanal ist: {meme_channel.mention}")
        else:
            await ctx.send("⚠️ Der gespeicherte Kanal existiert nicht mehr.")
    @mdma.command(name="leaderboard")
    async def mdma_leaderboard(self, ctx, mode: str = "top"):
        """Zeigt die Top 5 Nutzer oder eine vollständige Liste aller Nutzer mit ihren Netto-Upvotes"""
        guild = ctx.guild
        data = await self.config.guild(guild).memes()  # 🔥 KEIN Update der Reaktionen → sofortige Anzeige!

        user_scores = {}

        # 🔍 Jetzt prüfen wir ALLE gespeicherten Werte, OHNE neue Anfragen an Discord
        for meme in data.values():
            user_id = meme["author_id"]
            netto_score = meme["upvotes"] - meme["downvotes"]

            if user_id not in user_scores:
                user_scores[user_id] = 0
            user_scores[user_id] += netto_score

        if not user_scores:
            return await ctx.send("❌ Keine Memes in der Datenbank gefunden.")

        # 🔥 Nutzer nach Netto-Upvotes sortieren
        sorted_users = sorted(user_scores.items(), key=lambda x: x[1], reverse=True)

        if mode.lower() == "top":
            top_5 = sorted_users[:5]
            leaderboard_text = "🏆 **Top 5 Meme-Künstler:**\n"
            for i, (user_id, score) in enumerate(top_5, 1):
                user = guild.get_member(user_id)
                username = user.display_name if user else f"Unbekannt ({user_id})"
                leaderboard_text += f"**{i}. {username}** – {score} Netto-Upvotes\n"
            return await ctx.send(leaderboard_text)

        elif mode.lower() == "all":
            leaderboard_text = "📜 **Gesamtes Meme-Scoreboard:**\n"
            for user_id, score in sorted_users:
                user = guild.get_member(user_id)
                username = user.display_name if user else f"Unbekannt ({user_id})"
                leaderboard_text += f"**{username}** – {score} Netto-Upvotes\n"
            return await ctx.send(leaderboard_text)

        else:
            return await ctx.send("❌ Ungültiger Modus! Nutze `!mdma leaderboard` oder `!mdma leaderboard all`.")

    async def mdma_help(self, ctx):
        """Zeigt eine Liste aller Befehle und deren Erklärungen"""
        help_text = (
            "📜 **MemeBot Hilfe** 📜\n\n"
            "📌 **Meme-Statistiken:**\n"
            "- `!mdma mdma` → Zeigt das Meme des Monats.\n"
            "- `!mdma day` → Zeigt das meistgeupvotete Meme des Tages.\n"
            "- `!mdma week` → Zeigt das meistgeupvotete Meme der Woche.\n"
            "- `!mdma year` → Zeigt das meistgeupvotete Meme des Jahres.\n"
            "- `!mdma all` → Zeigt das meistgeupvotete Meme aller Zeiten.\n\n"
            "🏆 **Leaderboard & Updates:**\n"
            "- `!mdma leaderboard` → Zeigt die Top 5 Nutzer mit den meisten Netto-Upvotes.\n"
            "- `!mdma leaderboard all` → Zeigt alle Nutzer und ihre Netto-Upvotes.\n"
            "- `!mdma updatecounts` → Aktualisiert alle Upvote- und Downvote-Zahlen.\n\n"
            "🛠️ **Einstellungen:**\n"
            "- `!mdma setmemechannel <#kanal>` → Legt den Meme-Kanal fest.\n"
            "- `!mdma listchannel` → Zeigt, welcher Meme-Kanal aktuell eingestellt ist.\n\n"
            "ℹ️ **Hilfe:**\n"
            "- `!mdma help` → Zeigt diese Hilfe an."
        )
        await ctx.send(help_text)

    @commands.Cog.listener()
    async def on_message(self, message):
        """Reagiert automatisch auf jede Nachricht im festgelegten Meme-Kanal"""
        if not message.guild:
            return  

        guild_config = await self.config.guild(message.guild).all()
        meme_channel = guild_config.get("meme_channel")

        if not meme_channel or message.channel.id != meme_channel:
            return  # ⏩ Ignoriert Nachrichten außerhalb des Meme-Kanals

        pos_emoji = guild_config["positive_emoji"]
        neg_emoji = guild_config["negative_emoji"]

        try:
            await message.add_reaction(pos_emoji)
            await message.add_reaction(neg_emoji)
            print(f"[MemeBot] ✅ Reaktionen hinzugefügt ({pos_emoji}, {neg_emoji}) für Nachricht {message.id}")
        except discord.Forbidden:
            print(f"[MemeBot] ❌ Fehlende Berechtigungen, um Reaktionen hinzuzufügen.")

        async with self.config.guild(message.guild).memes() as memes:
            memes[str(message.id)] = {
                "message_id": message.id,
                "channel_id": message.channel.id,
                "author_id": message.author.id,
                "timestamp": message.created_at.timestamp(),
                "upvotes": 0,
                "downvotes": 0
            }
            print(f"[MemeBot] ✅ Nachricht {message.id} wurde als Meme gespeichert.")
