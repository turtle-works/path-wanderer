import aiohttp
import discord
import json
import re

from redbot.core import Config, commands

HTTP_ROOT = "https://"
PATHBUILDER_URL_BASE = "https://pathbuilder2e.com/json.php?id="
JUST_DIGITS = r"\d+$"
PATHBUILDER_URL_TEMPLATE = r"https://pathbuilder2e.com/json.php\?id=\d+$"


class PathWanderer(commands.Cog):
	"""Cog that lets users do simple things for Pathfinder 2e."""

	def __init__(self, bot, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.bot = bot

		self.config = Config.get_conf(self, identifier=34263737)
		self.config.register_user(active_char=None, characters={}, preferences={})

	async def red_get_data_for_user(self, *, user_id):
		"""Get a user's personal data."""
		characters = await self.config.user_from_id(user_id).characters()
		if characters:
			data = f"For user with ID {user_id}, data is stored for characters with " + \
				"Pathbuilder 2e JSON IDs:\n" + "\n".join([json_id for json_id in characters])
		else:
			data = f"No data is stored for user with ID {user_id}.\n"
		return {"user_data.txt": BytesIO(data.encode())}

	async def red_delete_data_for_user(self, *, requester, user_id):
		"""Delete a user's personal data.

		Imported Pathfinder 2e character data is stored by this cog.
		"""
		await self.config.user_from_id(user_id).clear()

	@commands.command(aliases=['import', 'mmimport'])
	async def loadchar(self, ctx, url: str):
		"""Import from a Pathbuilder 2e JSON."""
		if re.match(PATHBUILDER_URL_TEMPLATE, url):
			char_url = url
		elif re.match(PATHBUILDER_URL_TEMPLATE, HTTP_ROOT + url):
			char_url = HTTP_ROOT + url
		elif re.match(JUST_DIGITS, url):
			char_url = PATHBUILDER_URL_BASE + url
		else:
			await ctx.send("Couldn't parse that as a link to a Pathbuilder 2e JSON.")
			return

		json_id = char_url.split('=')[1]

		async with aiohttp.ClientSession() as session:
			async with session.get(char_url) as response:
				response_text = await response.text()
				char_data = json.loads(response_text)

		if not char_data['success']:
			await ctx.send("This character did not build successfully. Aborting import.\n" + \
				"This is not a problem with the command; please check in Pathbuilder 2e.")
			return

		async with self.config.user(ctx.author).characters() as characters:
			# TODO: after it's written, remind about [p]update instead of overriding each time
			characters[json_id] = char_data

		await self.config.user(ctx.author).active_char.set(json_id)

		await ctx.send(f"Imported data for character with name {char_data['build']['name']} " + \
			f"and JSON ID {json_id}.")
