from .rtl import RTL


async def setup(bot):
    await bot.add_cog(RTL(bot))