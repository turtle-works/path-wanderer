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

# possible allowed options
FINESSE_WEAPONS = ["Claw Blade", "Dagger", "Dogslicer", "Dueling Sword", "Elven Curve Blade",
    "Filcher's Fork", "Fist", "Kukri", "Light Mace", "Main-gauche", "Rapier", "Sai",
    "Sawtooth Saber", "Shears", "Shortsword", "Sickle", "Spiked Chain", "Starknife",
    "Sword Cane", "Tengu Gale Blade", "Wakizashi", "Whip"]
PROPULSIVE_WEAPONS = ["Composite Longbow", "Composite Shortbow", "Daikyu", "Halfling Sling Staff",
    "Sling"]
RANGED_WEAPONS = ["Blowgun", "Bola", "Bomb", "Composite Longbow", "Composite Shortbow", "Daikyu",
    "Dart", "Halfling Sling Staff", "Hand Crossbow", "Heavy Crossbow", "Javelin", "Longbow",
    "Shortbow", "Shuriken", "Sling"]


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

    @commands.command(aliases=["import", "mmimport", "pfimport"])
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

        json_id = char_url.split("=")[1]
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

        await ctx.send(f"Imported data for {char_data['build']['name']}.")

    @commands.command(aliases=["pfupdate"])
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

        await ctx.send(f"Updated data for {char_data['build']['name']}. " + \
            f"(Note that changes cannot be pulled until Export JSON is selected again.)")

    @commands.group(aliases=["char", "pfchar"])
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
            line = f"{characters[json_id]['build']['name']}"
            line += " (**active**)" if json_id == active_id else ""
            lines.append(line)

        await ctx.send("Your characters:\n" + "\n".join(sorted(lines)))

    @character.command(name="setactive", aliases=["set", "switch"])
    async def character_set(self, ctx, *, query: str):
        """Set the active character."""
        characters = await self.config.user(ctx.author).characters()

        character_id = await self.json_id_from_query(ctx, query)

        if not character_id:
            await ctx.send(f"Could not find a character to match `{query}`.")
            return

        await self.config.user(ctx.author).active_char.set(character_id)
        await ctx.send(f"{characters[character_id]['build']['name']} made active.")

    @character.command(name="remove", aliases=["delete"])
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

            await ctx.send(f"{name} has been removed from your characters.")

    async def json_id_from_query(self, ctx, query: str):
        query = query.lower()
        characters = await self.config.user(ctx.author).characters()

        for json_id in characters:
            # either match to json id or partial match to a character name
            if query == json_id or query in characters[json_id]['build']['name'].lower():
                return json_id

        return None

    @commands.command(aliases=["c", "pfc", "pfcheck"])
    async def check(self, ctx, *, check_name: str):
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
        embed.description = self._get_roll_string(self.roll_die(), mod)

        await ctx.send(embed=embed)

    @commands.command(aliases=["s", "pfs", "pfsave"])
    async def save(self, ctx, *, save_name: str):
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
        embed.description = self._get_roll_string(self.roll_die(), mod)

        await ctx.send(embed=embed)

    def roll_die(self, die_size: int=20):
        return math.ceil(random.random() * die_size)

    # starting to understand why one imports d20
    def roll_xdy(self, dice: str):
        num_dice, die_size = dice.split("d")
        num_dice = 1 if not num_dice else int(num_dice)
        return [self.roll_die(die_size) for i in range(int(num_dice))]

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

    def _get_roll_string(self, die_roll: int, mod: int, die_size: int=20):
        op = "-" if mod < 0 else "+"
        die_display = f"**{die_roll}**" if die_roll in [1, die_size] else die_roll
        return f"1d{die_size} ({die_display}) {op} {mod} = `{die_roll + mod}`"

    @commands.command()
    async def attack(self, ctx, *, weapon_name: str):
        """Attack with a weapon."""
        json_id = await self.config.user(ctx.author).active_char()
        if json_id is None:
            await ctx.send("Set an active character first with `character setactive`.")
            return

        data = await self.config.user(ctx.author).characters()
        char_data = data[json_id]['build']

        weapon = None
        for weap in char_data['weapons']:
            if weapon_name.lower() in weap['display'].lower():
                weapon = weap
        if weapon is None:
            await ctx.send(f"Did not find `{weapon_name}` in available weapons.")
            return

        name = char_data['name']
        article = "an" if weapon['display'][0] in ["a", "e", "i", "o", "u"] else "a"

        to_hit, damage_bonus = self._get_weapon_mods(weapon, char_data)

        to_hit_roll = self.roll_die()
        to_hit_line = f"**To hit**: {self._get_roll_string(to_hit_roll, to_hit)}"

        die_size = int(weapon['die'].split("d")[1])
        damage_roll = self.roll_die(die_size)
        damage_line = f"**Damage**: {self._get_roll_string(damage_roll, damage_bonus, die_size)}"

        if to_hit_roll == 20:
            to_hit_line += " (**crit**)"
            damage_line += f" => `{(damage_roll + damage_bonus) * 2}`"

        embed = discord.Embed()
        embed.title = f"{name} attacks with {article} {weapon['display']}!"
        embed.description = f"{to_hit_line}\n{damage_line}"
        await ctx.send(embed=embed)

    def _get_weapon_mods(self, weapon: dict, char_data: dict):
        abilities = char_data['abilities']
        level = char_data['level']
        profs = char_data['proficiencies']

		# have to manually do all this stuff
        if weapon['name'] in FINESSE_WEAPONS:
            ability_mod = self._get_ability_mod(max(abilities['str'], abilities['dex']))
        elif weapon['name'] in RANGED_WEAPONS:
            ability_mod = self._get_ability_mod(abilities['dex'])
        else:
            ability_mod = self._get_ability_mod(abilities['str'])

        # TODO: how to establish when a weapon is being thrown?
        if weapon['name'] in PROPULSIVE_WEAPONS:
            str_mod = self._get_ability_mod(abilities['str'])
            damage_bonus = math.floor(str_mod / 2) if str_mod > 0 else str_mod
        elif weapon['name'] in RANGED_WEAPONS:
            damage_bonus = 0
        else:
            damage_bonus = self._get_ability_mod(abilities['str'])

        prof_bonus = profs[weapon['prof']] + (0 if profs[weapon['prof']] == 0 else level)

        return ability_mod + prof_bonus + weapon['pot'], damage_bonus

    @commands.command(aliases=["pfsheet"])
    async def sheet(self, ctx):
        """Show the active character's sheet."""
        json_id = await self.config.user(ctx.author).active_char()
        if json_id is None:
            await ctx.send("Set an active character first with `character setactive`.")
            return

        data = await self.config.user(ctx.author).characters()
        char_data = data[json_id]['build']

        embed = discord.Embed()
        embed.title = f"{char_data['name']}"
        embed.description = f"{char_data['class']} {char_data['level']}"

        ability_lines = []
        for ability in char_data['abilities']:
            mod = self._get_ability_mod(char_data['abilities'][ability])
            op = "-" if mod < 0 else "+"
            ability_lines.append(f"**{ability.upper()}**: ({op}{mod})")
        abilities_field = " ".join(ability_lines[:3]) + "\n" + " ".join(ability_lines[3:])
        embed.add_field(name="Ability Scores", value=abilities_field, inline=False)

        profs = char_data['proficiencies']
        save_lines = []
        skill_lines = []
        for skill in SKILL_DATA:
            if SKILL_DATA[skill][TYPE] == "ability":
                continue
            prof_label = self._get_prof_label(profs[skill])
            mod = self._get_skill_mod(skill, char_data)
            op = "-" if mod < 0 else "+"

            line = f"{prof_label}{skill.capitalize()}: ({op}{mod})"
            if SKILL_DATA[skill][TYPE] == "save":
                save_lines.append(line)
            else:
                skill_lines.append(line)

        save_field = "\n".join(save_lines)
        embed.add_field(name="Saving Throws", value=save_field, inline=True)
        skill_field = "\n".join(skill_lines)
        embed.add_field(name="Skills", value=skill_field, inline=True)

        lore_lines = []
        for skill in char_data['lores']:
            prof_label = self._get_prof_label(skill[1])
            mod = self._get_lore_mod(skill[0].lower(), char_data)
            op = "-" if mod < 0 else "+"
            lore_lines.append(f"{prof_label}{skill[0].capitalize()}: ({op}{mod})")
        lore_field = "\n".join(lore_lines)
        embed.add_field(name="Lores", value=lore_field, inline=True)

        weapon_lines = []
        for weapon in char_data['weapons']:
            to_hit, damage_bonus = self._get_weapon_mods(weapon, char_data)
            to_hit_op = "-" if to_hit < 0 else "+"
            damage_op = "-" if damage_bonus < 0 else "+"
            weapon_lines.append(f"**{weapon['display']}**: {to_hit_op}{to_hit} to hit, " + \
                f"1{weapon['die']} {damage_op} {damage_bonus} damage")
        weapon_field = "\n".join(weapon_lines)
        embed.add_field(name="Weapon Attacks", value=weapon_field, inline=False)

        await ctx.send(embed=embed)

    def _get_prof_label(self, prof_bonus: int):
        if prof_bonus == 8:
            label = "(**L**) "
        elif prof_bonus == 6:
            label = "(**M**) "
        elif prof_bonus == 4:
            label = "(**E**) "
        elif prof_bonus == 2:
            label = "(**T**) "
        else:
            label = ""

        return label
