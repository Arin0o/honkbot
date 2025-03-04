from .birthdaycog import BirthdayCog

async def setup(bot):
    await bot.add_cog(BirthdayCog(bot))
