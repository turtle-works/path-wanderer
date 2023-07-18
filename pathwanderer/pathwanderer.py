import json
import math
import random
import re
import urllib

import aiohttp
import discord
import d20
from redbot.core import Config, commands

HTTP_ROOT = "https://"
PATHBUILDER_URL_BASE = "https://pathbuilder2e.com/json.php?id="
JUST_DIGITS = r"\d+$"
PATHBUILDER_URL_TEMPLATE = r"https://pathbuilder2e.com/json.php\?id=\d+$"
AON_SEARCH_BASE = "https://2e.aonprd.com/Search.aspx?q="

SPELL_SLOT_SYMBOL = "✦"

KNOWN_FLAGS = ["ac", "b", "d", "dc", "phrase", "rr"]
DOUBLE_QUOTES = ["\"", "“", "”"]

CRIT_SUCCESS = 2
SUCCESS = 1
FAILURE = 0
CRIT_FAILURE = -1

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
AGILE_WEAPONS = ["Blowgun", "Butterfly Sword", "Clan Dagger", "Claw Blade", "Corset Knife",
    "Dagger", "Dart", "Dogslicer", "Feng Huo Lun", "Fighting Fan", "Filcher's Fork", "Fist",
    "Flyssa", "Gauntlet", "Hatchet", "Kama", "Katar", "Kukri", "Light Hammer", "Light Mace",
    "Light Pick", "Main-gauche", "Orc Knuckle Dagger", "Sai", "Sap", "Sawtooth Saber",
    "Shortsword", "Shuriken", "Sickle", "Special Unarmed (1d4)", "Special Unarmed (1d6)",
    "Special Unarmed (1d8)", "Special Unarmed (1d10)", "Special Unarmed Cobra Fang",
    "Special Unarmed Crane Wing", "Special Unarmed Lashing Branch",
    "Special Unarmed Shadow Grasp", "Special Unarmed Stumbling Swing",
    "Special Unarmed Tiger Claw", "Special Unarmed Wind Crash", "Special Unarmed Wolf Jaw",
    "Spiked Gauntlet", "Starknife", "Sword Cane", "Tekko-Kagi", "Tengu Gale Blade",
    "Thunder Sling", "Wakizashi", "War Razor", "Whipstaff"]
FINESSE_WEAPONS = ["Bow Staff - Melee", "Butterfly Sword", "Claw Blade", "Combat Lure",
    "Corset Knife", "Dagger", "Dancer's Spear", "Dogslicer", "Dueling Sword", "Elven Curve Blade",
    "Feng Huo Lun", "Fighting Fan", "Filcher's Fork", "Fist", "Flyssa", "Karambit", "Kukri",
    "Light Mace", "Main-gauche", "Rapier", "Sai", "Sawtooth Saber", "Shears", "Shortsword",
    "Sickle", "Special Unarmed (1d4)", "Special Unarmed (1d6)", "Special Unarmed (1d8)",
    "Special Unarmed (1d10)", "Special Unarmed Cobra Fang", "Special Unarmed Crane Wing",
    "Special Unarmed Lashing Branch", "Special Unarmed Stumbling Swing",
    "Special Unarmed Tiger Claw", "Special Unarmed Wolf Jaw", "Spiked Chain", "Starknife",
    "Sword Cane", "Tekko-Kagi", "Tengu Gale Blade", "Wakizashi", "War Razor", "Whip", "Whipstaff"]
PROPULSIVE_WEAPONS = ["Composite Longbow", "Composite Shortbow", "Daikyu", "Gakgung",
    "Halfling Sling Staff", "Mikazuki - Ranged", "Phalanx Piercer", "Sling",
    "Special Unarmed Wind Crash", "Spraysling", "Thunder Sling"]
RANGED_WEAPONS = ["Blowgun", "Bola", "Bomb", "Bow Staff - Ranged", "Composite Longbow",
    "Composite Shortbow", "Crescent Cross - Ranged", "Crossbow", "Daikyu", "Dart", "Gakgung",
    "Gauntlet Bow", "Halfling Sling Staff", "Hand Crossbow", "Harpoon", "Heavy Crossbow",
    "Javelin", "Lancer - Ranged", "Longbow", "Mikazuki - Ranged", "Phalanx Piercer", "Rotary Bow",
    "Shield Bow", "Shortbow", "Shuriken", "Sling", "Special Unarmed Wind Crash", "Spraysling",
    "Sukgung", "Thunder Sling", "Wrecker - Ranged"]

STR_THRESH = 0
PENALTY = 1
ARMOR_DATA = {
    'Bastion Plate': (18, -3),
    'Breastplate': (16, -2),
    'Buckle Armor': (12, -1),
    'Ceramic Plate': (14, -2),
    'Chain Mail': (16, -2),
    'Chain Shirt': (12, -1),
    'Coral Armor': (14, -2),
    'Fortress Plate': (18, -3),
    'Full Plate': (18, -3),
    'Half Plate': (16, -3),
    'Hide Armor': (14, -2),
    'Lamellar Breastplate': (16, -2),
    'Lattice Armor': (16, -2),
    'Leaf Weave': (10, -1),
    'Leather Armor': (10, -1),
    'Leather Lamellar': (10, -1),
    'Niyah\u00e1at': (14, -2),
    'O-Yoroi': (18, -3),
    'Padded Armor': (10, 0),
    'Quilted Armor': (12, -1),
    'Sankeit': (12, -1),
    'Scale Mail': (14, -2),
    'Splint Mail': (16, -3),
    'Studded Leather Armor': (12, -1),
    'Wooden Breastplate': (14, -2)
}

WORK_DC = 0
TRAINED_PAY = 1
FAILURE_PAY = 5
WORK_DATA = {
    'legal': {
        3: [18, 40, 50, 60, 60, 7],
        4: [19, 50, 60, 80, 80, 8],
        5: [20, 60, 80, 100, 100, 9],
        6: [22, 70, 100, 150, 150, 10],
        7: [23, 80, 150, 200, 200, 15],
        8: [24, 100, 200, 280, 280, 20]
    },
    'criminal': {
        3: [18, 50, 60, 70, 70],
        4: [19, 60, 70, 90, 90],
        5: [20, 70, 90, 120, 120],
        6: [22, 80, 120, 180, 180],
        7: [23, 90, 180, 240, 240],
        8: [24, 120, 240, 320, 320]
    }
}


class PathWanderer(commands.Cog):
    """Cog that lets users do simple things for Pathfinder 2e."""

    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot

        self.config = Config.get_conf(self, identifier=34263737)
        self.config.register_user(active_char=None, characters={}, csettings={}, preferences={})

    async def red_get_data_for_user(self, *, user_id):
        """Get a user's personal data."""
        characters = await self.config.user_from_id(user_id).characters()
        if characters:
            data = f"For user with ID {user_id}, data is stored for characters with " + \
                "Pathbuilder 2e JSON IDs:\n" + \
                "\n".join([json_id for json_id in characters.keys()])
        else:
            data = f"No data is stored for user with ID {user_id}.\n"
        return {"user_data.txt": BytesIO(data.encode())}

    async def red_delete_data_for_user(self, *, requester, user_id):
        """Delete a user's personal data.

        Imported Pathfinder 2e character data is stored by this cog.
        """
        await self.config.user_from_id(user_id).clear()

    @commands.command(name="import", aliases=["loadchar", "mmimport", "pfimport"])
    async def import_char(self, ctx, url: str):
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
                active_char = await self.config.user(ctx.author).active_char()
                switch_msg = ""
                if json_id != active_char:
                    switch_msg = " switch to their sheet with `character setactive` and"

                await ctx.send(f"This character has already been imported,{switch_msg} use " + \
                    "`update` instead.")
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

        await ctx.send(f"Imported data for {char_data['build']['name']} " + \
            f"({char_data['build']['class']} {char_data['build']['level']}).")

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

        await ctx.send(f"Updated data for {char_data['build']['name']} " + \
            f"({char_data['build']['class']} {char_data['build']['level']}). " + \
            f"(Note that changes cannot be pulled until Export JSON is selected again.)")

    @commands.group(aliases=["char", "pfchar"])
    async def character(self, ctx):
        """Commands for character management."""

    @character.command(name="list")
    async def character_list(self, ctx):
        """List all characters that the user has imported."""
        await self._character_list(ctx, False)

    @character.command(name="ids")
    async def character_ids(self, ctx):
        """Receive a list of all the characters that the user has imported, with their JSON IDs."""
        await self._character_list(ctx, True)

    async def _character_list(self, ctx, show_ids: bool):
        characters = await self.config.user(ctx.author).characters()
        if not characters:
            await ctx.send("You have no characters.")
            return

        active_id = await self.config.user(ctx.author).active_char()

        lines = []
        for json_id in characters.keys():
            char_data = characters[json_id]['build']
            line = f"{char_data['name']}"
            line += f" ({char_data['class']} {char_data['level']})"
            if show_ids:
                line += f" (ID **{json_id}**)"
            line += " (**active**)" if json_id == active_id else ""
            lines.append(line)

        if not show_ids:
            await ctx.send("Your characters:\n" + "\n".join(sorted(lines)))
        else:
            await ctx.author.send("Your characters:\n" + "\n".join(sorted(lines)))
            await ctx.send("List has been sent to your DMs.")

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

    @character.command(name="setcolor")
    async def character_color(self, ctx, *, color: str):
        """Set the active character's embed color.

        Takes either a hex code or "random". Examples:
        `[p]character setcolor #FF8822`
        `[p]character setcolor random`
        """
        json_id = await self.config.user(ctx.author).active_char()
        if json_id is None:
            await ctx.send("Set an active character first with `character setactive`.")
            return

        data = await self.config.user(ctx.author).characters()
        name = data[json_id]['build']['name']

        if re.match(r"^#?[0-9a-fA-F]{6}$", color) or color.lower() == "random":
            async with self.config.user(ctx.author).csettings() as csettings:
                if json_id not in csettings:
                    csettings[json_id] = {}

                if color.lower() == "random":
                    csettings[json_id]['color'] = None
                else:
                    csettings[json_id]['color'] = int(color.lstrip("#"), 16)
            embed = await self._get_base_embed(ctx)
            embed.description = f"Embed color has been set for {name}."
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"Could not interpret `{color}` as a color.")

    @character.command(name="setimage")
    async def character_image(self, ctx, *, image: str=""):
        """Set the active character's image.
        
        Takes either an attached image, an image link, or "none" (to delete).
        """
        json_id = await self.config.user(ctx.author).active_char()
        if json_id is None:
            await ctx.send("Set an active character first with `character setactive`.")
            return

        data = await self.config.user(ctx.author).characters()
        name = data[json_id]['build']['name']
        if len(ctx.message.attachments):
            if not ctx.message.attachments[0].content_type.startswith("image"):
                await ctx.send("Could not interpret the attachment as an image.")
                return
            else:
                url = ctx.message.attachments[0].url
        else:
            if not image:
                await ctx.send("Could not interpret image link.")
                return
            elif image == "none":
                url = None
            else:
                if "pathbuilder2e.com" in image:
                    await ctx.send("Please don't use images hosted from Pathbuilder 2e, " + \
                        "I'm sure I'm putting too much stress on their server already.")
                    return
                url = image

        async with self.config.user(ctx.author).csettings() as csettings:
            if json_id not in csettings:
                csettings[json_id] = {}
            csettings[json_id]['image_url'] = url

        embed = await self._get_base_embed(ctx)
        embed.description = f"Image has been set for {name}."

        await ctx.send(embed=embed)

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

            async with self.config.user(ctx.author).csettings() as csettings:
                if character_id in csettings:
                    csettings.pop(character_id)

            if await self.config.user(ctx.author).active_char() == character_id:
                await self.config.user(ctx.author).active_char.set(None)

            await ctx.send(f"{name} has been removed from your characters.")

    async def json_id_from_query(self, ctx, query: str):
        query = query.lower()
        characters = await self.config.user(ctx.author).characters()

        for json_id in characters.keys():
            char_data = characters[json_id]['build']
            name = char_data['name']
            class_name = char_data['class']
            level = char_data['level']

            # TODO: this isn't great
            # either match directly to json id or partial match to variations
            if query == json_id or \
                query in f"{name} ({class_name} {level})".lower() or \
                query in f"{name} {class_name} {level}".lower() or \
                query in f"{name} {level}".lower() or \
                query in name.lower():
                return json_id

        return None

    @commands.command(aliases=["c", "pfc", "pfcheck"])
    async def check(self, ctx, *, query: str):
        """Make a skill check as the active character."""
        json_id = await self.config.user(ctx.author).active_char()
        if json_id is None:
            await ctx.send("Set an active character first with `character setactive`.")
            return

        data = await self.config.user(ctx.author).characters()
        char_data = data[json_id]['build']

        processed_query = self.process_query(query)

        check_name = processed_query['query'].lower()

        if check_name == "lore":
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
            if SKILL_DATA[skill][ABILITY] in ["str", "dex"]:
                mod += await self._get_armor_penalty(ctx, char_data)
        elif skill_type == "ability":
            mod = self._get_ability_mod(char_data['abilities'][SKILL_DATA[skill][ABILITY]])
        elif skill_type == "lore":
            mod = self._get_lore_mod(skill, char_data)
            lore_indicator = "Lore: "
        # catchall error, but shouldn't be able to get here
        else:
            await ctx.send(f"Could not understand `{check_name}`.")
            return

        bonus_str = self._get_rollable_arg(processed_query['b'])
        dc_str = self._get_single_rollable_arg(processed_query['dc'])
        repetition_str = self._get_single_rollable_arg(processed_query['rr'])

        name = char_data['name']
        article = "an" if skill[0] in ["a", "e", "i", "o", "u"] and not lore_indicator else "a"

        if not lore_indicator:
            skill = skill.capitalize()

        embed = await self._get_base_embed(ctx)
        embed.title = f"{name} makes {article} {lore_indicator}{skill} check!"

        dc = d20.roll(dc_str).total if dc_str else None

        if not repetition_str or d20.roll(repetition_str).total == 1:
            check_roll = d20.roll(self.make_dice_string(mod, bonus_str))
            description = str(check_roll)
            if dc is not None:
                _, label = self._get_degree_of_success(check_roll.total, check_roll.crit, dc)
                description = f"**DC {dc} | {label}**\n{description}"
            embed.description = description
        else:
            if dc is not None:
                embed.description = f"**DC {dc}**"
            for i in range(d20.roll(repetition_str).total):
                check_roll = d20.roll(self.make_dice_string(mod, bonus_str))
                field_name = f"Check {i + 1}"
                if dc is not None:
                    _, label = self._get_degree_of_success(check_roll.total, check_roll.crit, dc)
                    field_name += f", {label}"
                embed.add_field(name=field_name, value=str(check_roll))

        await ctx.send(embed=embed)

    @commands.command(aliases=["s", "pfs", "pfsave"])
    async def save(self, ctx, *, query: str):
        """Make a saving throw as the active character."""
        json_id = await self.config.user(ctx.author).active_char()
        if json_id is None:
            await ctx.send("Set an active character first with `character setactive`.")
            return

        data = await self.config.user(ctx.author).characters()
        char_data = data[json_id]['build']

        processed_query = self.process_query(query)

        save_name = processed_query['query'].lower()

        skill_type, skill = self.find_skill_type(save_name, char_data)
        if not skill_type:
            await ctx.send(f"Could not interpret `{save_name}` as a save.")
            return
        if skill_type != "save":
            await ctx.send(f"`{skill}` is a check.")
            return

        mod = self._get_skill_mod(skill, char_data)

        bonus_str = self._get_rollable_arg(processed_query['b'])
        dc_str = self._get_single_rollable_arg(processed_query['dc'])
        repetition_str = self._get_single_rollable_arg(processed_query['rr'])

        name = char_data['name']

        embed = await self._get_base_embed(ctx)
        embed.title = f"{name} makes a {skill.capitalize()} save!"

        dc = d20.roll(dc_str).total if dc_str else None

        if not repetition_str or d20.roll(repetition_str).total == 1:
            save_roll = d20.roll(self.make_dice_string(mod, bonus_str))
            description = str(save_roll)
            if dc is not None:
                _, label = self._get_degree_of_success(save_roll.total, save_roll.crit, dc)
                description = f"**DC {dc} | {label}**\n{description}"
            embed.description = description
        else:
            if dc is not None:
                embed.description = f"**DC {dc}**"
            for i in range(d20.roll(repetition_str).total):
                save_roll = d20.roll(self.make_dice_string(mod, bonus_str))
                field_name = f"Save {i + 1}"
                if dc is not None:
                    _, label = self._get_degree_of_success(save_roll.total, save_roll.crit, dc)
                    field_name += f", {label}"
                embed.add_field(name=field_name, value=str(save_roll))

        await ctx.send(embed=embed)

    def find_skill_type(self, check_name: str, char_data: dict):
        # check predefined data
        for skill in SKILL_DATA.keys():
            # note that "int" will always go to intelligence instead of intimidation
            if check_name in skill:
                return (SKILL_DATA[skill][TYPE], skill)

        # check lore skills
        lores = char_data['lores']
        for i in range(len(lores)):
            lore_name = "".join(lores[i][0].split(" ")).lower()
            check_name = "".join(check_name.split(" ")).lower()
            if check_name in lore_name:
                return ("lore", lores[i][0])

        return None, None

    def _get_ability_mod(self, score: int):
        return math.floor((score - 10) / 2)

    def _get_skill_mod(self, skill: str, char_data: dict):
        abilities = char_data['abilities']
        level = char_data['level']
        profs = char_data['proficiencies']
        misc_mods = char_data['mods']

        ability_mod = self._get_ability_mod(abilities[SKILL_DATA[skill][ABILITY]])
        prof_bonus = profs[skill] + (0 if profs[skill] == 0 else level)

        # TODO: no guarantee what format these keys will come in
        misc_bonus = 0
        for bonus_target in misc_mods.keys():
            bonus_list = misc_mods[bonus_target]
            if bonus_target.lower() == skill:
                misc_bonus = sum([bonus_list[b] for b in bonus_list.keys()])

        return ability_mod + prof_bonus + misc_bonus

    def _get_lore_mod(self, lore_name: str, char_data: dict):
        abilities = char_data['abilities']
        level = char_data['level']
        # list of lists of size 2 where [0] is the Name and [1] is the bonus
        lores = char_data['lores']

        ability_mod = self._get_ability_mod(abilities['int'])

        prof_bonus = 0
        for i in range(len(lores)):
            if lores[i][0] == lore_name:
                prof_bonus = lores[i][1] + (0 if lores[i][1] == 0 else level)

        return ability_mod + prof_bonus

    def make_dice_string(self, mod: int, bonus_str: str, num_dice: int=1, die_size: int=20):
        op = self._get_op(mod)
        bonus = f" + {bonus_str}" if bonus_str else ""

        return f"{num_dice}d{die_size} {op} {abs(mod)}{bonus}"

    def _get_op(self, value: int):
        return "-" if value < 0 else "+"

    @commands.command(aliases=["a", "pfa", "pfattack"])
    async def attack(self, ctx, *, query: str):
        """Attack with a weapon.
        
        To-hit bonuses can be added with the -b flag. Examples:
        `[p]attack dagger -b 1`
        `[p]attack staff -b -1`
        """
        json_id = await self.config.user(ctx.author).active_char()
        if json_id is None:
            await ctx.send("Set an active character first with `character setactive`.")
            return

        data = await self.config.user(ctx.author).characters()
        char_data = data[json_id]['build']

        await self._attack(ctx, char_data, 1, query)

    @commands.command(aliases=["ma"])
    async def multiattack(self, ctx, num_attacks: int, *, query: str):
        """Attack multiple times with a weapon.
        
        Multiple attack penalty will apply.
        To-hit bonuses, which will apply to all attacks, can be added with the -b flag. Examples:
        `[p]multiattack 3 shortsword -b 1`
        `[p]multiattack 2 sling -b +1-1+1`
        """
        json_id = await self.config.user(ctx.author).active_char()
        if json_id is None:
            await ctx.send("Set an active character first with `character setactive`.")
            return

        data = await self.config.user(ctx.author).characters()
        char_data = data[json_id]['build']

        # 18 chosen over 20 due to being a multiple of 3 (for inline field display)
        num_attacks = min(num_attacks, 18)

        await self._attack(ctx, char_data, num_attacks, query)

    async def _attack(self, ctx, char_data: dict, num_attacks: int, query: str):
        processed_query = self.process_query(query)

        weapon_query = processed_query['query'].lower()

        weapon = None
        for weap in char_data['weapons']:
            if weapon_query in weap['display'].lower():
                weapon = weap
        if weapon is None:
            await ctx.send(f"Did not find `{weapon_query}` in available weapons.")
            return

        async with self.config.user(ctx.author).csettings() as csettings:
            json_id = await self.config.user(ctx.author).active_char()
            if json_id not in csettings:
                csettings[json_id] = {}
            csettings[json_id]['last_weapon'] = weapon
            csettings[json_id]['consecutive_attacks'] = max(1, num_attacks)

        name = char_data['name']
        article = "an" if weapon['display'][0].lower() in ["a", "e", "i", "o", "u"] else "a"

        to_hit, damage_mod = self._get_weapon_mods(weapon, char_data)
        num_dice = self._get_num_damage_dice(weapon['str'])
        die_size = int(weapon['die'].split("d")[1])

        ac_str = self._get_single_rollable_arg(processed_query['ac'])
        to_hit_bonus_str = self._get_rollable_arg(processed_query['b'])
        damage_bonus_str = self._get_rollable_arg(processed_query['d'])

        embed = await self._get_base_embed(ctx)
        embed.title = f"{name} attacks with {article} {weapon['display']}!"

        if num_attacks <= 1:
            output, _, _ = self.make_attack_block(to_hit, damage_mod, to_hit_bonus_str,
                damage_bonus_str, ac_str, num_dice, die_size=die_size or 1)

            embed.description = output
        else:
            total_damage = 0
            for i in range(num_attacks):
                penalty = 4 if weapon['name'] in AGILE_WEAPONS else 5
                penalty = penalty * 2 if i > 1 else penalty if i > 0 else 0
                output, attack_roll, damage_roll = self.make_attack_block(to_hit - penalty,
                    damage_mod, to_hit_bonus_str, damage_bonus_str, ac_str, num_dice,
                    die_size=die_size or 1)
                if ac_str:
                    ac = d20.roll(ac_str).total
                    degree, _ = self._get_degree_of_success(attack_roll.total, attack_roll.crit,
                        ac)
                    if degree == CRIT_SUCCESS:
                        total_damage += damage_roll.total * 2
                    elif degree == SUCCESS:
                        total_damage += damage_roll.total
                else:
                    total_damage += damage_roll.total
                embed.add_field(name=f"Attack {i + 1}", value=output)

            embed.description = f"Total damage: `{total_damage}`"

        if not die_size:
            embed.set_footer(text="The d1 is filler. This weapon's damage varies.")

        await ctx.send(embed=embed)

    @commands.command(aliases=["attack2", "attack3", "ra", "repattack"])
    async def repeatattack(self, ctx, *, query: str=""):
        """Make another attack on the current turn.
        
        If no weapon is given, uses the most recently used weapon. Multiple attack penalty applies.
        To-hit bonuses can be added with the -b flag. Examples:
        `[p]repeatattack`
        `[p]repeatattack shortbow`
        `[p]repeatattack -b 1`
        """
        json_id = await self.config.user(ctx.author).active_char()
        if json_id is None:
            await ctx.send("Set an active character first with `character setactive`.")
            return

        data = await self.config.user(ctx.author).characters()
        char_data = data[json_id]['build']

        processed_query = self.process_query(query)
        if processed_query['query']:
            weapon_query = processed_query['query'].lower()
        else:
            weapon_query = None

        async with self.config.user(ctx.author).csettings() as csettings:
            if json_id not in csettings:
                csettings[json_id] = {}
            if 'consecutive_attacks' not in csettings[json_id]:
                csettings[json_id]['consecutive_attacks'] = 1
            if 'last_weapon' not in csettings[json_id] and not weapon_query:
                await ctx.send("Unable to repeat attack; you haven't made any. " + \
                    "Use `attack` or `multiattack` instead.")
                return

            weapon = None
            if weapon_query:
                for weap in char_data['weapons']:
                    if weapon_query in weap['display'].lower():
                        weapon = weap
                        csettings[json_id]['last_weapon'] = weapon
                if weapon is None:
                    await ctx.send(f"Did not find `{weapon_query}` in available weapons.")
                    return
            else:
                weapon = csettings[json_id]['last_weapon']

            num_attacks = csettings[json_id]['consecutive_attacks']

            name = char_data['name']
            article = "an" if weapon['display'][0].lower() in ["a", "e", "i", "o", "u"] else "a"

            to_hit, damage_mod = self._get_weapon_mods(weapon, char_data)
            num_dice = self._get_num_damage_dice(weapon['str'])
            die_size = int(weapon['die'].split("d")[1])

            ac_str = self._get_single_rollable_arg(processed_query['ac'])
            to_hit_bonus_str = self._get_rollable_arg(processed_query['b'])
            damage_bonus_str = self._get_rollable_arg(processed_query['d'])

            penalty = 4 if weapon['name'] in AGILE_WEAPONS else 5
            penalty = penalty * 2 if num_attacks > 1 else penalty if num_attacks > 0 else 0
            output, _, _ = self.make_attack_block(to_hit - penalty, damage_mod, to_hit_bonus_str,
                damage_bonus_str, ac_str, num_dice, die_size=die_size or 1)

            csettings[json_id]['consecutive_attacks'] += 1

            embed = await self._get_base_embed(ctx)
            embed.title = f"{name} attacks again with {article} {weapon['display']}!"
            embed.description = output
            if not die_size:
                embed.set_footer(text="The d1 is filler. This weapon's damage varies.")

            await ctx.send(embed=embed)

    def _get_weapon_mods(self, weapon: dict, char_data: dict):
        # new values that render manual calculations moot
        return weapon['attack'], weapon['damageBonus']

        # abilities = char_data['abilities']
        # level = char_data['level']
        # profs = char_data['proficiencies']
        # specifics = char_data['specificProficiencies']

		# # have to manually do all this stuff
        # if weapon['name'] in FINESSE_WEAPONS:
        #     ability_mod = self._get_ability_mod(max(abilities['str'], abilities['dex']))
        # elif weapon['name'] in RANGED_WEAPONS:
        #     ability_mod = self._get_ability_mod(abilities['dex'])
        # else:
        #     ability_mod = self._get_ability_mod(abilities['str'])

        # # TODO: how to establish when a weapon is being thrown?
        # if weapon['name'] in PROPULSIVE_WEAPONS:
        #     str_mod = self._get_ability_mod(abilities['str'])
        #     damage_mod = math.floor(str_mod / 2) if str_mod > 0 else str_mod
        # elif weapon['name'] in RANGED_WEAPONS:
        #     damage_mod = 0
        # else:
        #     damage_mod = self._get_ability_mod(abilities['str'])

        # if weapon['name'] in specifics['trained']:
        #     prof = 2
        # elif weapon['name'] in specifics['expert']:
        #     prof = 4
        # elif weapon['name'] in specifics['master']:
        #     prof = 6
        # elif weapon['name'] in specifics['legendary']:
        #     prof = 8
        # else:
        #     prof = profs[weapon['prof']]
        # prof_bonus = prof + (0 if prof == 0 else level)

        # return ability_mod + prof_bonus + weapon['pot'], damage_mod

    def _get_num_damage_dice(self, striking_rune: str):
        if striking_rune == "majorStriking":
            return 4
        elif striking_rune == "greaterStriking":
            return 3
        elif striking_rune == "striking":
            return 2
        else:
            return 1

    def make_attack_block(self, to_hit: int, damage_mod: int, to_hit_bonus_str: str,
        damage_bonus_str: str, ac_str: str, num_dice: int, die_size: int):
        attack_roll = d20.roll(self.make_dice_string(to_hit, to_hit_bonus_str))
        attack_line = f"**To hit**: {str(attack_roll)}"

        damage_roll = d20.roll(self.make_dice_string(damage_mod, damage_bonus_str,
            num_dice=num_dice, die_size=die_size))
        damage_line = f"**Damage**: {str(damage_roll)}"

        if ac_str:
            ac = d20.roll(ac_str).total
            attack_line = f"**To hit (AC {ac})**: {str(attack_roll)}"
            degree, _ = self._get_degree_of_success(attack_roll.total, attack_roll.crit, ac)

            if degree == CRIT_SUCCESS:
                attack_line += " (**crit**)"
            elif degree == CRIT_FAILURE:
                attack_line += " (**crit fail**)"

            if degree == CRIT_SUCCESS:
                damage_line += f" -> `{damage_roll.total * 2}`"
            elif degree <= FAILURE:
                damage_line = "**Miss!**"

        return f"{attack_line}\n{damage_line}", attack_roll, damage_roll

    def _get_degree_of_success(self, total: int, crit: int, dc: int):
        if total >= dc + 10:
            degree = CRIT_SUCCESS
        elif total >= dc:
            degree = SUCCESS
        elif total > dc - 10:
            degree = FAILURE
        else:
            degree = CRIT_FAILURE

        if crit == d20.CritType.CRIT:
            degree = min(CRIT_SUCCESS, degree + 1)
        elif crit == d20.CritType.FAIL:
            degree = max(CRIT_FAILURE, degree - 1)

        label = "Crit Success" if degree == CRIT_SUCCESS else "Success" if degree == SUCCESS else \
            "Failure" if degree == FAILURE else "Crit Failure"

        return degree, label

    # TODO: maybe make this its own class or something?
    def process_query(self, query_str: str):
        processed_flags = self._get_base_flags()

        # prepend a space so the flag finding will succeed even with no query. hey, if it works...
        query_str = " " + query_str

        flag_locs = []
        search_start = 0
        while search_start < len(query_str):
            # looks for instances of all the flags simultaneously
            next_flags = [query_str.find(f" -{flag} ", search_start) for flag in KNOWN_FLAGS]

            # no more flags, end loop
            if all([f < 0 for f in next_flags]):
                break
            # save location of earliest flag
            else:
                while -1 in next_flags:
                    next_flags.remove(-1)
                next_flag = min(next_flags)
                flag_locs.append(next_flag)
                search_start = next_flag + 2
        flag_locs.sort()

        if not flag_locs:
            processed_flags['query'] = query_str.strip()
        else:
            processed_flags['query'] = query_str[:flag_locs[0]].strip()

        for i in range(len(flag_locs)):
            if i == len(flag_locs) - 1:
                flag_and_arg = query_str[flag_locs[i]:]
            else:
                flag_and_arg = query_str[flag_locs[i]:flag_locs[i + 1]]

            flag_and_arg = flag_and_arg.strip()[1:]
            # split only on the first space, if it exists
            flag_and_arg = flag_and_arg.split(" ", 1)

            flag = flag_and_arg[0]
            if len(flag_and_arg) > 1:
                arg = flag_and_arg[1]
            else:
                arg = ""

            arg = arg.strip()
            if len(arg) > 1 and arg[0] in DOUBLE_QUOTES and arg[-1] in DOUBLE_QUOTES:
                arg = arg[1:-1]

            processed_flags[flag].append(arg)

        return processed_flags

    def _get_base_flags(self):
        processed_flags = {'query': ""}
        for flag in KNOWN_FLAGS:
            processed_flags[flag] = []
        return processed_flags

    def _get_single_rollable_arg(self, args: list):
        try:
            d20.roll(args[0])
            return args[0]
        # should catch both empty list and not rollable
        except:
            return ""

    def _get_rollable_arg(self, args: list):
        rollable_args = []
        for arg in args:
            # feels hacky
            try:
                d20.roll(arg)
                rollable_args.append(arg)
            except:
                # this was invalid and not rollable, don't use it
                pass
        return " + ".join(rollable_args)

    @commands.command(aliases=["pfspellbook", "pfspells", "spells"])
    async def spellbook(self, ctx):
        """List the active character's spells."""
        json_id = await self.config.user(ctx.author).active_char()
        if json_id is None:
            await ctx.send("Set an active character first with `character setactive`.")
            return

        data = await self.config.user(ctx.author).characters()
        char_data = data[json_id]['build']

        spell_count = 0

        embed = await self._get_base_embed(ctx)
        embed.title = "Spellbook"

        focus = char_data['focus']
        focus_points = char_data['focusPoints']
        # unsure if this will always be a reliable way to determine presence of focus spells
        if focus and focus_points > 0:
            focus_cantrips = []
            focus_spells = []
            for tradition in focus.keys():
                for stat in focus[tradition].keys():
                    cantrips = focus[tradition][stat]['focusCantrips']
                    focus_cantrips.extend(cantrips)
                    spell_count += len(cantrips)

                    spells = focus[tradition][stat]['focusSpells']
                    focus_spells.extend(spells)
                    spell_count += len(spells)

            focus_field_name = f"Focus {focus_points * SPELL_SLOT_SYMBOL}"
            focus_field = ""
            if focus_cantrips:
                focus_field += "**Cantrip**: " + ", ".join(focus_cantrips)
                focus_field += "\n**Spell**: "
            focus_field += ", ".join(focus_spells)
            embed.add_field(name=focus_field_name, value=focus_field, inline=False)

        spellcasting = char_data['spellCasters']
        if len(spellcasting) > 0:
            available_spells = {}
            available_slots = {}
            for source in spellcasting:
                # list of spells, per level
                all_leveled_spells = source['spells']
                for leveled_spells in all_leveled_spells:
                    level = leveled_spells['spellLevel']
                    spells = leveled_spells['list']
                    if level not in available_spells:
                        available_spells[level] = spells
                    else:
                        available_spells[level].extend(spells)
                    spell_count += len(spells)

                # display of spell slots, per level
                for level in range(1, len(source['perDay'])):
                    slots = source['perDay'][level]
                    if source['name'] == char_data['class']:
                        slot_str = slots * SPELL_SLOT_SYMBOL
                        if level not in available_slots:
                            available_slots[level] = [slot_str]
                        else:
                            available_slots[level].insert(0, slot_str)
                    elif slots > 0:
                        slot_str = f"{source['name']}: {slots * SPELL_SLOT_SYMBOL}"
                        if level not in available_slots:
                            available_slots[level] = [slot_str]
                        else:
                            available_slots[level].append(slot_str)

            # one field per level
            for level in available_spells.keys():
                spell_field = ", ".join(available_spells[level])
                field_name = "Cantrip" if level == 0 else f"Level {level} "
                if level > 0:
                    field_name += " | ".join(available_slots[level])
                embed.add_field(name=field_name, value=spell_field, inline=False)

        formula = char_data['formula']
        if formula:
            formulae = []
            for source in formula:
                formulae.extend(source['known'])
            formula_field = ", ".join(formulae)
            formula_field_name = f"Formulae ({len(formulae)})"
            embed.add_field(name=formula_field_name, value=formula_field, inline=False)

        plural = "s" if spell_count != 1 else ""
        embed.description = f"{char_data['name']} has {spell_count} spell{plural}."

        await ctx.send(embed=embed)

    @commands.command(aliases=["pfsheet"])
    async def sheet(self, ctx):
        """Show the active character's sheet."""
        json_id = await self.config.user(ctx.author).active_char()
        if json_id is None:
            await ctx.send("Set an active character first with `character setactive`.")
            return

        data = await self.config.user(ctx.author).characters()
        char_data = data[json_id]['build']

        level = char_data['level']
        profs = char_data['proficiencies']
        attributes = char_data['attributes']
        abilities = char_data['abilities']

        embed = await self._get_base_embed(ctx)
        embed.title = f"{char_data['name']}"

        desc_lines = []
        desc_lines.append(f"{char_data['class']} {level}")

        if 'classDC' in profs:
            key_mod = self._get_ability_mod(abilities[char_data['keyability']])
            class_dc = 10 + profs['classDC'] + (0 if profs['classDC'] == 0 else level) + key_mod
            desc_lines.append(f"**Class DC**: {class_dc}")

        max_hp = attributes['ancestryhp'] + attributes['bonushp']
        max_hp += (attributes['classhp'] + attributes['bonushpPerLevel'] + \
            self._get_ability_mod(abilities['con'])) * level
        ac = char_data['acTotal']['acTotal']
        desc_lines.append(f"**Max HP**: {max_hp} **AC**: {ac}")

        customs = sum([1 if "Custom Dialect" in l else 0 for l in char_data['languages']])
        plural = "s" if customs != 1 else ""
        custom_language_str = f" (+{customs} custom language{plural})" if customs else ""
        languages = []
        for language in char_data['languages']:
            if "Custom Dialect" not in language:
                languages.append(language)
        desc_lines.append(f"**Languages**: {', '.join(languages)}" + \
            f"{custom_language_str}")

        embed.description = "\n".join(desc_lines)

        ability_lines = []
        for ability in abilities.keys():
            if ability == 'breakdown':
                continue
            score = abilities[ability]
            mod = self._get_ability_mod(score)
            op = self._get_op(mod)
            ability_lines.append(f"**{ability.upper()}**: {score} ({op}{abs(mod)})")
        abilities_field = " ".join(ability_lines[:3]) + "\n" + " ".join(ability_lines[3:])
        embed.add_field(name="Ability Scores", value=abilities_field, inline=False)

        save_lines = []
        skill_lines = []
        for skill in SKILL_DATA.keys():
            if SKILL_DATA[skill][TYPE] == "ability":
                continue
            prof_label = self._get_prof_label(profs[skill])
            mod = self._get_skill_mod(skill, char_data)
            if SKILL_DATA[skill][TYPE] == "check" and SKILL_DATA[skill][ABILITY] in ["str", "dex"]:
                mod += await self._get_armor_penalty(ctx, char_data)
            op = self._get_op(mod)

            line = f"{prof_label}{skill.capitalize()}: ({op}{abs(mod)})"
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
            mod = self._get_lore_mod(skill[0], char_data)
            op = self._get_op(mod)
            lore_lines.append(f"{prof_label}{skill[0]}: ({op}{abs(mod)})")
        lore_field = "\n".join(lore_lines)
        embed.add_field(name="Lores", value=lore_field, inline=True)

        weapon_lines = []
        for weapon in char_data['weapons']:
            to_hit, damage_mod = self._get_weapon_mods(weapon, char_data)
            to_hit_op = self._get_op(to_hit)
            damage_op = self._get_op(damage_mod)
            num_dice = self._get_num_damage_dice(weapon['str'])

            if weapon['die'] == "d0":
                damage_display = "damage varies"
            else:
                damage_display = f"{num_dice}{weapon['die']} {damage_op} {abs(damage_mod)} damage"

            weapon_lines.append(f"**{weapon['display']}**: {to_hit_op}{abs(to_hit)} to hit, " + \
                f"{damage_display}")
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

    async def _get_armor_penalty(self, ctx, char_data: dict):
        async with self.config.user(ctx.author).preferences() as preferences:
            if 'armor_penalty' in preferences and not preferences['armor_penalty']:
                return 0

        all_armor = char_data['armor']

        worn_armor = None
        for armor in all_armor:
            if armor['worn'] and armor['name'] in ARMOR_DATA:
                worn_armor = armor
        if not worn_armor:
            return 0

        strength = char_data['abilities']['str']
        data = ARMOR_DATA[worn_armor['name']]

        if strength < data[STR_THRESH]:
            return data[PENALTY]
        else:
            return 0

    @commands.command(aliases=["checkpenalty"])
    async def armorpenalty(self, ctx, setting: str=""):
        """Toggle if the armor check penalty will apply to your characters."""
        if setting and setting.lower() not in ["off", "on"]:
            await ctx.send("Setting should be \"off\" or \"on\" (or left out, to just toggle).")
            return

        async with self.config.user(ctx.author).preferences() as preferences:
            if 'armor_penalty' not in preferences:
                preferences['armor_penalty'] = True
            current_setting = preferences['armor_penalty']

            if setting.lower() == "off":
                new_setting = False
            elif setting.lower() == "on":
                new_setting = True
            else:
                new_setting = not current_setting

            preferences['armor_penalty'] = new_setting

        label = "on" if new_setting else "off"

        await ctx.send(f"Turned armor check penalty **{label}** for all characters.")

    @commands.command(aliases=["specials"])
    async def feats(self, ctx):
        """List the active character's feats and specials.
        
        This is a list of what's on the Pathbuilder 2e Feats tab."""
        json_id = await self.config.user(ctx.author).active_char()
        if json_id is None:
            await ctx.send("Set an active character first with `character setactive`.")
            return

        data = await self.config.user(ctx.author).characters()
        char_data = data[json_id]['build']

        name = char_data['name']
        heritage = char_data['heritage']
        level = char_data['level']

        embed = await self._get_base_embed(ctx)
        embed.title = f"{name}'s Feats and Specials"

        feat_lines = []
        # list of four values: name, additional information, type, level
        for feat in char_data['feats']:
            if feat[2] != "Heritage":
                if feat[0] == "Assurance":
                    if feat[1].lower() in SKILL_DATA.keys():
                        prof = char_data['proficiencies'][feat[1].lower()] + level
                        skill = feat[1]
                    else:
                        prof = self._get_lore_mod(feat[1][6:], char_data) - \
                            self._get_ability_mod(char_data['abilities']['int'])
                        skill = feat[1][6:]
                    bonus = f" ({self._get_prof_label(prof - level)}{10 + prof} {skill})"
                else:
                    bonus = f" ({feat[1]})" if feat[1] else ""
                feat_lines.append(f"{feat[0]}{bonus}")
        feat_lines.sort()
        feats_field = "\n".join(feat_lines)
        embed.add_field(name="Feats", value=feats_field)
        
        special_lines = []
        for special in char_data['specials']:
            # label heritage under specials
            special_lines.append(f"{special}{' (Heritage)' if special == heritage else ''}")
        special_lines.sort()
        specials_field = "\n".join(special_lines)
        embed.add_field(name="Specials", value=specials_field)

        await ctx.send(embed=embed)

    @commands.command(aliases=["assurances"])
    async def assurance(self, ctx):
        """List the active character's Assurance skills, if they have any."""
        json_id = await self.config.user(ctx.author).active_char()
        if json_id is None:
            await ctx.send("Set an active character first with `character setactive`.")
            return

        data = await self.config.user(ctx.author).characters()
        char_data = data[json_id]['build']

        name = char_data['name']
        level = char_data['level']

        assurances = []
        for feat in char_data['feats']:
            if feat[0] == "Assurance":
                if feat[1].lower() in SKILL_DATA.keys():
                    prof = char_data['proficiencies'][feat[1].lower()] + level
                    skill = feat[1]
                else:
                    prof = self._get_lore_mod(feat[1][6:], char_data) - \
                        self._get_ability_mod(char_data['abilities']['int'])
                    skill = feat[1][6:]
                assurances.append(f"{self._get_prof_label(prof - level)}{10 + prof} {skill}")

        if not assurances:
            await ctx.send("This character does not have the Assurance feat.")
            return
        else:
            plural = "s" if len(assurances) > 1 else ""
            await ctx.send(f"{name}'s Assurance skill{plural}:\n" + "\n".join(assurances))

    @commands.command(aliases=["equip", "equipment", "inventory"])
    async def gear(self, ctx):
        """List the active character's gear."""
        json_id = await self.config.user(ctx.author).active_char()
        if json_id is None:
            await ctx.send("Set an active character first with `character setactive`.")
            return

        data = await self.config.user(ctx.author).characters()
        char_data = data[json_id]['build']

        name = char_data['name']

        embed = await self._get_base_embed(ctx)
        embed.title = f"{name}'s Gear"

        # container id or main: [name, [list of items]]
        all_items = {'main': ["Main Inventory", []]}
        containers = char_data['equipmentContainers']
        for container in containers.keys():
            all_items[container] = [containers[container]['containerName'], []]

        equipment = char_data['equipment']
        if not equipment:
            embed.description = "This character has no gear."
            await ctx.send(embed=embed)
            return

        for equip in equipment:
            # if it's length 2 it's in the main inventory
            # if it's length 3 equip[2] MIGHT be a container id
            # if it's length 4 equip[2] is a container id
            if len(equip) == 2:
                target = all_items['main'][1]
            else:
                if equip[2] in all_items:
                    target = all_items[equip[2]][1]
                else:
                    target = all_items['main'][1]
            target.append(f"{equip[0]} ({equip[1]})")

        for group in all_items.keys():
            if all_items[group][1]:
                all_items[group][1].sort()
                field = "\n".join(all_items[group][1])
                embed.add_field(name=f"{all_items[group][0]}", value=field)

        await ctx.send(embed=embed)

    async def _get_base_embed(self, ctx):
        embed = discord.Embed()
        json_id = await self.config.user(ctx.author).active_char()
        settings = await self.config.user(ctx.author).csettings()

        if json_id in settings and 'color' in settings[json_id] and settings[json_id]['color']:
            embed.colour = discord.Colour(settings[json_id]['color'])
        else:
            embed.colour = discord.Colour(random.randint(0x000000, 0xFFFFFF))

        if json_id in settings and 'image_url' in settings[json_id] and \
            settings[json_id]['image_url']:
            embed.set_thumbnail(url=settings[json_id]['image_url'])

        return embed

    @commands.command(aliases=["aon", "aonlookup", "pflookup"])
    async def lookup(self, ctx, *, query: str):
        """Look something up.
        
        Gives a link to a search on the Archives of Nethys for the given term.
        """
        await ctx.send(self._lmgtfy(f"`{query}`", query))

    @commands.command(aliases=['pffeat'])
    async def feat(self, ctx, *, feat_name: str):
        """Look up a feat (sort of)."""
        await ctx.send(self._lmgtfy("feats", feat_name))

    @commands.command(aliases=["pfitem"])
    async def item(self, ctx, *, item_name: str):
        """Look up a piece of equipment (sort of)."""
        await ctx.send(self._lmgtfy("items", item_name))

    @commands.command(aliases=["pfspell"])
    async def spell(self, ctx, *, spell_name: str):
        """Look up a spell (sort of)."""
        await ctx.send(self._lmgtfy("spells", spell_name))

    @commands.command(aliases=["pfweapon"])
    async def weapon(self, ctx, *, weapon_name: str):
        """Look up a weapon (sort of)."""
        await ctx.send(self._lmgtfy("weapons", weapon_name))

    def _lmgtfy(self, topic: str, query: str):
        aon_link = AON_SEARCH_BASE + urllib.parse.quote_plus(query)
        return f"Unfortunately, I don't have access to data on {topic}. " + \
            f"I can help you look it up on the Archives of Nethys, though:\n{aon_link}"

    # TODO: these should probably be refactored if possible?
    @commands.command()
    async def research(self, ctx, dtp: int, dc: int, *, query: str):
        """Spend downtime doing research.
        
        Bonuses can be added with the -b flag. Examples:
        `[p]research 2 23 arcana`
        `[p]research 1 18 diplomacy -b 2`
        """
        json_id = await self.config.user(ctx.author).active_char()
        if json_id is None:
            await ctx.send("Set an active character first with `character setactive`.")
            return

        data = await self.config.user(ctx.author).characters()
        char_data = data[json_id]['build']

        dtp = min(dtp, 24)

        processed_query = self.process_query(query)

        check_name = processed_query['query'].lower()

        skill_type, skill = self.find_skill_type(check_name, char_data)
        if not skill_type:
            await ctx.send(f"Could not interpret `{check_name}` as a check.")
            return

        if skill_type == "check" or skill_type == "save":
            mod = self._get_skill_mod(skill, char_data)
        elif skill_type == "ability":
            mod = self._get_ability_mod(char_data['abilities'][SKILL_DATA[skill][ABILITY]])
        elif skill_type == "lore":
            mod = self._get_lore_mod(skill, char_data)
        else:
            await ctx.send(f"Could not understand `{check_name}`.")
            return

        bonus_str = self._get_rollable_arg(processed_query['b'])

        name = char_data['name']

        embed = await self._get_base_embed(ctx)
        embed.title = f"{name} does some research!"

        total_kp = 0
        for i in range(dtp):
            research_roll = d20.roll(self.make_dice_string(mod, bonus_str))
            degree, _ = self._get_degree_of_success(research_roll.total, research_roll.crit, dc)
            if degree == CRIT_SUCCESS:
                kp = 2
            elif degree == SUCCESS:
                kp = 1
            elif degree == FAILURE:
                kp = 0
            else:
                # kp = -1
                kp = 0

            total_kp += kp
            embed.add_field(name=f"DTP {i + 1}: {kp} KP", value=str(research_roll))

        if skill_type != "lore":
            skill = skill.capitalize()

        embed.description = f"DC {dc} {skill}\n" + \
            f"Total KP from this session: **{total_kp}**"

        await ctx.send(embed=embed)

    @commands.command()
    async def legalwork(self, ctx, dtp: int, level: int, *, query: str):
        """Spend downtime doing legal work.

        Bonuses can be added with the -b flag. Examples:
        `[p]legalwork 2 3 medicine`
        `[p]legalwork 8 4 crafting -b 2`
        """
        await self._work(ctx, dtp, level, query, 'legal')

    @commands.command()
    async def criminalwork(self, ctx, dtp: int, level: int, *, query: str):
        """Spend downtime doing criminal work.

        Bonuses can be added with the -b flag. Examples:
        `[p]criminalwork 12 3 athletics`
        `[p]criminalwork 4 5 intimidation -b 2`
        """
        await self._work(ctx, dtp, level, query, 'criminal')

    async def _work(self, ctx, dtp: int, level: int, query: str, work_type: str):
        json_id = await self.config.user(ctx.author).active_char()
        if json_id is None:
            await ctx.send("Set an active character first with `character setactive`.")
            return

        data = await self.config.user(ctx.author).characters()
        char_data = data[json_id]['build']

        dtp = min(dtp, 24)
        level = min(max(level, 3), 8)

        processed_query = self.process_query(query)

        check_name = processed_query['query'].lower()

        skill_type, skill = self.find_skill_type(check_name, char_data)
        if not skill_type:
            await ctx.send(f"Could not interpret `{check_name}` as a check.")
            return

        if skill_type == "check":
            mod = self._get_skill_mod(skill, char_data)
            prof = char_data['proficiencies'][skill]
        elif skill_type == "lore":
            mod = self._get_lore_mod(skill, char_data)
            prof = 2
            for lore in char_data['lores']:
                if lore[0] == skill:
                    prof = lore[1]
        else:
            await ctx.send(f"Cannot use `{check_name}`.")
            return

        if prof < 2:
            await ctx.send("You must be trained in a skill to use it for work.")
            return

        bonus_str = self._get_rollable_arg(processed_query['b'])
        dc_str = self._get_single_rollable_arg(processed_query['dc'])

        name = char_data['name']

        embed = await self._get_base_embed(ctx)
        embed.title = f"{name} gets to work!"

        pay_rates = WORK_DATA[work_type][level]
        dc = pay_rates[WORK_DC] if not dc_str else d20.roll(dc_str).total

        work_rolls = [d20.roll(self.make_dice_string(mod, bonus_str)) for i in range(dtp)]
        successes = []
        labels = []
        for work_roll in work_rolls:
            degree, label = self._get_degree_of_success(work_roll.total, work_roll.crit, dc)
            successes.append(degree)
            labels.append(label)

        payments = []
        penalty_message = ""
        for success in successes:
            if success == CRIT_SUCCESS:
                increased_prof = min(8, prof + 2)
                payments.append(pay_rates[int(increased_prof / 2)])
            elif success == SUCCESS:
                payments.append(pay_rates[int(prof / 2)])
            elif success == FAILURE:
                if work_type == 'legal':
                    payments.append(pay_rates[FAILURE_PAY])
                else:
                    payments.append(0)
            else:
                payments.append(0)

        total_sp = sum(payments)

        for i in range(dtp):
            inline = True
            work_field = str(work_rolls[i])
            deduction = ""
            if successes[i] == CRIT_FAILURE and work_type == 'criminal':
                inline = False
                penalty = d20.roll("1d4")
                penalty_message = f"\n**Penalty**: {str(penalty)}\n"
                if penalty.total == 1:
                    penalty_message += "You must pay penance for your crimes in the form " + \
                        "of Jail Time or Community Service. You lose an additional DTP. "
                elif penalty.total == 2:
                    penalty_message += "You either need to pay someone off or get caught " + \
                        "and need to pay a fine. You lose gold equal to the gold in the " + \
                        "'Trained' column."
                    deduction = f"-{self._get_parsed_coins(pay_rates[TRAINED_PAY])}"
                    total_sp -= pay_rates[TRAINED_PAY]
                elif penalty.total == 3:
                    penalty_message += "Rumors of your criminal activity have made it to " + \
                        "the ears of important people. Lose 1 FP with the faction you " + \
                        "have the most FP with. If there is a tie, you can choose between " + \
                        "the tied factions."
                else:
                    penalty_message += "Something went wrong, and you got injured along " + \
                        "the way. At the start of your next mission, you have taken 5 damage."
                work_field += penalty_message

            coins = self._get_parsed_coins(payments[i])
            label = labels[i]
            field_title = f"DTP {i + 1}: {label}, {coins if not deduction else deduction}"
            embed.add_field(name=field_title, value=work_field, inline=inline)

        if skill_type != "lore":
            skill = skill.capitalize()

        embed.description = f"DC {dc} {skill} (Level {level})\n" + \
            f"Total pay from this session: **{self._get_parsed_coins(total_sp)}**"

        await ctx.send(embed=embed)

    def _get_parsed_coins(self, total_sp: int):
        sp = total_sp % 10
        gp = math.floor(total_sp / 10)

        sp_str = f"{sp} sp" if sp else ""
        gp_str = f"{gp} gp" if gp else ""

        return f"{gp_str}, {sp_str}" if gp and sp else gp_str if gp else sp_str if sp else "0 gp"
