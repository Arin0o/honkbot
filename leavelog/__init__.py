from .leavelog import LeaveLog

async def setup(bot):
    await bot.add_cog(LeaveLog(bot))