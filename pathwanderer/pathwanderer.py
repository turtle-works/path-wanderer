import discord

from redbot.core import commands


class PathWanderer(commands.Cog):
	"""Cog that lets users do simple things for Pathfinder 2e."""

	def __init__(self, bot, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.bot = bot

	async def red_get_data_for_user(self, *, user_id):
		"""Get a user's personal data."""
		data = "No data is stored for user with ID {}.\n".format(user_id)
		return {"user_data.txt": BytesIO(data.encode())}

	async def red_delete_data_for_user(self, *, requester, user_id):
		"""Delete a user's personal data.

		No personal data is stored in this cog.
		"""
		return

	@commands.command()
	async def pathtester(self, ctx):
		"""Test if bot will respond."""
		await ctx.send('hello world')
