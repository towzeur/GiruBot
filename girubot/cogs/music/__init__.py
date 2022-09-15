from .music import Music


async def setup(bot):
	# https://gist.github.com/Rapptz/6706e1c8f23ac27c98cee4dd985c8120
	print('PIGI POP 2')
	await bot.add_cog(Music(bot))
