from .rtl import rtl


async def setup(bot):
    await bot.add_cog(rtl(bot))