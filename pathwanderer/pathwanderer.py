import json
import math
import random
import re

import aiohttp
import discord
from redbot.core import Config, commands

HTTP_ROOT = "https://"
PATHBUILDER_URL_BASE = "https://pathbuilder2e.com/json.php?id="
JUST_DIGITS = r"\d+$"
PATHBUILDER_URL_TEMPLATE = r"https://pathbuilder2e.com/json.php\?id=\d+$"

# TODO: shouldn't there be a better way to store this somewhere?
TYPE = 0
ABILITY = 1
SKILL_DATA = {
    'acrobatics': ("check", "dex"),
    'arcana': ("check", "int"),
    'athletics': ("check", "str"),
    'charisma': ("ability", "cha"),
    'constitution': ("ability", "con"),
    'crafting': ("check", "int"),
    'deception': ("check", "cha"),
    'dexterity': ("ability", "dex"),
    'diplomacy': ("check", "cha"),
    'fortitude': ("save", "con"),
    'intelligence': ("ability", "int"),
    'intimidation': ("check", "cha"),
    'medicine': ("check", "wis"),
    'nature': ("check", "wis"),
    'occultism': ("check", "int"),
    'perception': ("check", "wis"),
    'performance': ("check", "cha"),
    'reflex': ("save", "dex"),
    'religion': ("check", "wis"),
    'society': ("check", "int"),
    'stealth': ("check", "dex"),
    'strength': ("ability", "str"),
    'survival': ("check", "wis"),
    'thievery': ("check", "dex"),
    'will': ("save", "wis"),
    'wisdom': ("ability", "wis")
}


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

    @commands.command(aliases=['import', 'mmimport', 'pfimport'])
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
        async with self.config.user(ctx.author).characters() as characters:
            if json_id in characters:
                await ctx.send("This character has already been imported, use `update` instead.")
                return

        async with aiohttp.ClientSession() as session:
            async with session.get(char_url) as response:
                response_text = await response.text()
                char_data = json.loads(response_text)

        if not char_data['success']:
            await ctx.send("The build was unsuccessful. Aborting import.\n" + \
                "This is not a problem with the command; please check in Pathbuilder 2e.")
            return

        async with self.config.user(ctx.author).characters() as characters:
            characters[json_id] = char_data

        await self.config.user(ctx.author).active_char.set(json_id)

        await ctx.send(f"Imported data for character with name {char_data['build']['name']} " + \
            f"and JSON ID {json_id}.")

    @commands.command(aliases=['pfupdate'])
    async def update(self, ctx):
        """Update data for the active character."""
        json_id = await self.config.user(ctx.author).active_char()
        if json_id is None:
            await ctx.send("Set an active character first with `character setactive`.")
            return

        char_url = PATHBUILDER_URL_BASE + json_id

        async with aiohttp.ClientSession() as session:
            async with session.get(char_url) as response:
                response_text = await response.text()
                char_data = json.loads(response_text)

        if not char_data['success']:
            await ctx.send("The build was unsuccessful. Aborting update.\n" + \
                "This is not a problem with the command; please check in Pathbuilder 2e.")
            return

        async with self.config.user(ctx.author).characters() as characters:
            characters[json_id] = char_data

        await ctx.send(f"Updated data for character with name {char_data['build']['name']} " + \
            f"and JSON ID {json_id}. (Note that changes cannot be pulled until Export JSON " + \
            "is selected again.)")

    @commands.group(aliases=['char', 'pfchar'])
    async def character(self, ctx):
        """Commands for character management."""

    @character.command(name="list")
    async def character_list(self, ctx):
        """Show all characters that the user has imported."""
        characters = await self.config.user(ctx.author).characters()
        if not characters:
            await ctx.send("You have no characters.")
            return

        active_id = await self.config.user(ctx.author).active_char()

        lines = []
        for json_id in characters:
            line = f"{characters[json_id]['build']['name']} (ID {json_id})"
            line += " (**active**)" if json_id == active_id else ""
            lines.append(line)

        await ctx.send("Your characters:\n" + "\n".join(sorted(lines)))

    @character.command(name="setactive", aliases=['set', 'switch'])
    async def character_set(self, ctx, *, query: str):
        """Set the active character."""
        characters = await self.config.user(ctx.author).characters()

        character_id = await self.json_id_from_query(ctx, query)

        if not character_id:
            await ctx.send(f"Could not find a character to match `{query}`.")
            return

        await self.config.user(ctx.author).active_char.set(character_id)
        await ctx.send(f"{characters[character_id]['build']['name']} made active.")

    @character.command(name="remove", aliases=['delete'])
    async def character_remove(self, ctx, *, query: str):
        """Remove a character from the list."""
        async with self.config.user(ctx.author).characters() as characters:
            character_id = await self.json_id_from_query(ctx, query)

            if not character_id:
                await ctx.send(f"Could not find a character to match `{query}`.")
                return

            name = characters[character_id]['build']['name']
            characters.pop(character_id)
            if await self.config.user(ctx.author).active_char() == character_id:
                await self.config.user(ctx.author).active_char.set(None)

            await ctx.send(f"{name} (ID {character_id}) has been removed from your characters.")

    async def json_id_from_query(self, ctx, query: str):
        query = query.lower()
        characters = await self.config.user(ctx.author).characters()

        for json_id in characters:
            # either match to json id or partial match to a character name
            if query == json_id or query in characters[json_id]['build']['name'].lower():
                return json_id

        return None

    @commands.command(aliases=['c', 'pfc', 'pfcheck'])
    async def check(self, ctx, check_name: str):
        """Make a skill check as the active character."""
        json_id = await self.config.user(ctx.author).active_char()
        if json_id is None:
            await ctx.send("Set an active character first with `character setactive`.")
            return

        data = await self.config.user(ctx.author).characters()
        char_data = data[json_id]['build']

        check_name = check_name.lower()

        if check_name in "lore":
            await ctx.send("Please use a specific lore skill. Your options are: " + \
                ", ".join([lore[0] for lore in char_data['lores']]))
            return

        skill_type, skill = self.find_skill_type(check_name, char_data)
        if not skill_type:
            await ctx.send(f"Could not interpret `{check_name}` as a check.")
            return
        if skill_type == "save":
            await ctx.send(f"`{skill}` is a saving throw.")
            return

        lore_indicator = ""
        if skill_type == "check":
            mod = self._get_skill_mod(skill, char_data)
        elif skill_type == "ability":
            mod = self._get_ability_mod(char_data['abilities'][SKILL_DATA[skill][ABILITY]])
        elif skill_type == "lore":
            mod = self._get_lore_mod(skill, char_data)
            lore_indicator = "Lore: "
        # catchall error, but shouldn't be able to get here
        else:
            await ctx.send(f"Could not understand `{check_name}`.")
            return

        name = char_data['name']
        article = "an" if skill[0] in ["a", "e", "i", "o", "u"] else "a"

        embed = discord.Embed()
        embed.title = f"{name} makes {article} {lore_indicator}{skill.capitalize()} check!"
        embed.description = self._get_roll_string(self.roll_d20(), mod)

        await ctx.send(embed=embed)

    @commands.command(aliases=['s', 'pfs', 'pfsave'])
    async def save(self, ctx, save_name: str):
        """Make a saving throw as the active character."""
        json_id = await self.config.user(ctx.author).active_char()
        if json_id is None:
            await ctx.send("Set an active character first with `character setactive`.")
            return

        data = await self.config.user(ctx.author).characters()
        char_data = data[json_id]['build']

        save_name = save_name.lower()

        skill_type, skill = self.find_skill_type(save_name, char_data)
        if not skill_type:
            await ctx.send(f"Could not interpret `{save_name}` as a save.")
            return
        if skill_type != "save":
            await ctx.send(f"`{skill}` is a check.")
            return

        mod = self._get_skill_mod(skill, char_data)

        name = char_data['name']

        embed = discord.Embed()
        embed.title = f"{name} makes a {skill.capitalize()} save!"
        embed.description = self._get_roll_string(self.roll_d20(), mod)

        await ctx.send(embed=embed)

    def roll_d20(self):
        return math.ceil(random.random() * 20)

    def find_skill_type(self, check_name: str, char_data: dict):
        # check predefined data
        for skill in SKILL_DATA:
            # note that "int" will always go to intelligence instead of intimidation
            if check_name in skill:
                return (SKILL_DATA[skill][TYPE], skill)

        # check lore skills
        lores = char_data['lores']
        for i in range(len(lores)):
            if lores[i][0] == check_name.capitalize():
                return ("lore", lores[i][0].lower())

        return None, None

    def _get_ability_mod(self, score: int):
        return math.floor((score - 10) / 2)

    def _get_skill_mod(self, skill: str, char_data: dict):
        abilities = char_data['abilities']
        level = char_data['level']
        profs = char_data['proficiencies']

        ability_mod = self._get_ability_mod(abilities[SKILL_DATA[skill][ABILITY]])
        prof_bonus = profs[skill] + (0 if profs[skill] == 0 else level)

        return ability_mod + prof_bonus

    def _get_lore_mod(self, lore_name: str, char_data: dict):
        abilities = char_data['abilities']
        level = char_data['level']
        # list of lists of size 2 where [0] is the Name and [1] is the bonus
        lores = char_data['lores']

        ability_mod = self._get_ability_mod(abilities['int'])

        prof_bonus = 0
        for i in range(len(lores)):
            if lores[i][0] == lore_name.capitalize():
                prof_bonus = lores[i][1] + (0 if lores[i][1] == 0 else level)

        return ability_mod + prof_bonus

    def _get_roll_string(self, die_roll: int, mod: int):
        op = "-" if mod < 0 else "+"
        die_display = f"**{die_roll}**" if die_roll in [1, 20] else die_roll
        return f"1d20 ({die_display}) {op} {mod} = `{die_roll + mod}`"
