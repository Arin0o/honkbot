from .ampapi import AMPAPI

async def setup(bot):
    await bot.add_cog(AMPAPI(bot))