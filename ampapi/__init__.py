from .ampapi import ampapi

async def setup(bot):
    await bot.add_cog(ampapi(bot))
