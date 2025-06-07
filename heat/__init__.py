from .heat import VoiceHeatmap

async def setup(bot):
    await bot.add_cog(VoiceHeatmap(bot))