from .api import API

async def setup(bot):
    await bot.add_cog(API(bot))