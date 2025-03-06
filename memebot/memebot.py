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
        """Findet das Bild mit den meisten Netto-Upvotes (Upvotes - Downvotes)"""
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

    @commands.command()
    async def mdma(self, ctx, time_filter: str = "month"):
        """Zeigt das meistgeupvotete Meme nach Zeitraum (day, week, month, year, all)"""
        if time_filter == "help":
            return await self.mdma_help(ctx)
        await self.get_top_meme(ctx, time_filter)

    @commands.command()
    async def mdma_help(self, ctx):
        """Zeigt eine Liste aller Befehle und deren Erklärungen"""
        help_text = (
            "📜 **MemeBot Hilfe** 📜\n\n"
            "📌 **Einstellungen:**\n"
            "- `!mdma setmemechannel <kanal>` → Legt den Kanal für Memes fest.\n"
            "- `!mdma setpositiv <emoji>` → Setzt das Emoji für positive Reaktionen.\n"
            "- `!mdma setnegativ <emoji>` → Setzt das Emoji für negative Reaktionen.\n\n"
            "📊 **Statistiken:**\n"
            "- `!mdma day` → Zeigt das Meme mit den meisten Upvotes des Tages.\n"
            "- `!mdma week` → Zeigt das Meme mit den meisten Upvotes der Woche.\n"
            "- `!mdma` → Zeigt das beste Meme des Monats.\n"
            "- `!mdma year` → Zeigt das meistgeupvotete Meme des aktuellen Jahres.\n"
            "- `!mdma all` → Zeigt das meistgeupvotete Meme aller Zeiten.\n\n"
            "🏆 **Leaderboards:**\n"
            "- `!mdma leaderboard` → Zeigt die Top 5 Nutzer mit den meisten Netto-Upvotes.\n"
            "- `!mdma leaderboard all` → Zeigt alle Nutzer und ihre Netto-Upvotes.\n\n"
            "🛠️ **Moderation:**\n"
            "- `!mdma delete <message_id>` → Entfernt einen Meme-Eintrag aus der Statistik.\n\n"
            "ℹ️ **Hilfe:**\n"
            "- `!mdma help` → Zeigt diese Hilfe an."
        )
        await ctx.send(help_text)

    @commands.command()
    async def mdma_leaderboard(self, ctx, mode: str = "top"):
        """Zeigt die Top 5 Nutzer oder eine vollständige Liste aller Nutzer mit ihren Netto-Upvotes"""
        guild = ctx.guild
        data = await self.config.guild(guild).memes()

        user_scores = {}

        for meme in data.values():
            user_id = meme.get("author_id")
            if not user_id:
                continue
            netto_score = meme["upvotes"] - meme["downvotes"]
            user_scores[user_id] = user_scores.get(user_id, 0) + netto_score

        if not user_scores:
            return await ctx.send("❌ Keine Memes in der Datenbank gefunden.")

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
