from .mtm import MTM

async def setup(bot):
    await bot.add_cog(MTM(bot))