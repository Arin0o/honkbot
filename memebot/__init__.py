from .memebot import MemeBot

async def setup(bot):
    await bot.add_cog(MemeBot(bot))
