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
    "Shortsword", "Shuriken", "Sickle", "Spiked Gauntlet", "Starknife", "Sword Cane", "Tekko-Kagi",
    "Tengu Gale Blade", "Thunder Sling", "Wakizashi", "War Razor", "Whipstaff"]
FINESSE_WEAPONS = ["Bow Staff - Melee", "Butterfly Sword", "Claw Blade", "Combat Lure",
    "Corset Knife", "Dagger", "Dancer's Spear", "Dogslicer", "Dueling Sword", "Elven Curve Blade",
    "Feng Huo Lun", "Fighting Fan", "Filcher's Fork", "Fist", "Flyssa", "Karambit", "Kukri",
    "Light Mace", "Main-gauche", "Rapier", "Sai", "Sawtooth Saber", "Shears", "Shortsword",
    "Sickle", "Spiked Chain", "Starknife", "Sword Cane", "Tekko-Kagi", "Tengu Gale Blade",
    "Wakizashi", "War Razor", "Whip", "Whipstaff"]
PROPULSIVE_WEAPONS = ["Composite Longbow", "Composite Shortbow", "Daikyu", "Gakgung",
    "Halfling Sling Staff", "Mikazuki - Ranged", "Phalanx Piercer", "Sling", "Spraysling",
    "Thunder Sling"]
RANGED_WEAPONS = ["Blowgun", "Bola", "Bomb", "Bow Staff - Ranged", "Composite Longbow",
    "Composite Shortbow", "Crescent Cross - Ranged", "Crossbow", "Daikyu", "Dart", "Gakgung",
    "Gauntlet Bow", "Halfling Sling Staff", "Hand Crossbow", "Harpoon", "Heavy Crossbow",
    "Javelin", "Lancer - Ranged", "Longbow", "Mikazuki - Ranged", "Phalanx Piercer", "Rotary Bow",
    "Shield Bow", "Shortbow", "Shuriken", "Sling", "Spraysling", "Sukgung", "Thunder Sling",
    "Wrecker - Ranged"]


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
        for json_id in characters.keys():
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

        if re.match(r"^#?[0-9a-fA-F]{6}$", color) or color.lower() == "random":
            async with self.config.user(ctx.author).csettings() as csettings:
                if json_id not in csettings:
                    csettings[json_id] = {}

                if color.lower() == "random":
                    csettings[json_id]['color'] = None
                else:
                    csettings[json_id]['color'] = int(color.lstrip("#"), 16)
            embed = await self._get_base_embed(ctx)
            embed.description = "Embed color has been set."
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"Could not interpret `{color}` as a color.")

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
            # either match to json id or partial match to a character name
            if query == json_id or query in characters[json_id]['build']['name'].lower():
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

        query_parts = [p.strip() for p in query.split("-b")]

        check_name = query_parts[0].lower()

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

        # feels a little hacky
        bonuses = sum([d20.roll(b).total for b in query_parts[1:]])

        name = char_data['name']
        article = "an" if skill[0] in ["a", "e", "i", "o", "u"] and not lore_indicator else "a"

        embed = await self._get_base_embed(ctx)
        embed.title = f"{name} makes {article} {lore_indicator}{skill.capitalize()} check!"
        embed.description = str(d20.roll(self.make_dice_string(mod, bonuses)))

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

        query_parts = [p.strip() for p in query.split("-b")]

        save_name = query_parts[0].lower()

        skill_type, skill = self.find_skill_type(save_name, char_data)
        if not skill_type:
            await ctx.send(f"Could not interpret `{save_name}` as a save.")
            return
        if skill_type != "save":
            await ctx.send(f"`{skill}` is a check.")
            return

        mod = self._get_skill_mod(skill, char_data)

        bonuses = sum([d20.roll(b).total for b in query_parts[1:]])

        name = char_data['name']

        embed = await self._get_base_embed(ctx)
        embed.title = f"{name} makes a {skill.capitalize()} save!"
        embed.description = str(d20.roll(self.make_dice_string(mod, bonuses)))

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

    def make_dice_string(self, mod: int, bonuses: int, num_dice: int=1, die_size: int=20):
        op = self._get_op(mod)
        bonus_op = self._get_op(bonuses)
        bonus_str = f" {bonus_op} {abs(bonuses)}" if bonuses else ""

        return f"{num_dice}d{die_size} {op} {abs(mod)}{bonus_str}"

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
        query_parts = [p.strip() for p in query.split("-b")]

        weapon_name = query_parts[0]

        weapon = None
        for weap in char_data['weapons']:
            if weapon_name.lower() in weap['display'].lower():
                weapon = weap
        if weapon is None:
            await ctx.send(f"Did not find `{weapon_name}` in available weapons.")
            return

        async with self.config.user(ctx.author).csettings() as csettings:
            json_id = await self.config.user(ctx.author).active_char()
            if json_id not in csettings:
                csettings[json_id] = {}
            csettings[json_id]['last_weapon'] = weapon
            csettings[json_id]['consecutive_attacks'] = max(1, num_attacks)

        name = char_data['name']
        article = "an" if weapon['display'][0] in ["a", "e", "i", "o", "u"] else "a"

        to_hit, damage_mod = self._get_weapon_mods(weapon, char_data)
        num_dice = self._get_num_damage_dice(weapon['str'])
        die_size = int(weapon['die'].split("d")[1])

        # TODO: uh oh. damage bonuses?
        to_hit_bonus = sum([d20.roll(b).total for b in query_parts[1:]])

        embed = await self._get_base_embed(ctx)
        embed.title = f"{name} attacks with {article} {weapon['display']}!"

        if num_attacks <= 1:
            output, _, _ = self.make_attack_block(to_hit, damage_mod, to_hit_bonus, num_dice,
                die_size)

            embed.description = output
        else:
            total_damage = 0
            for i in range(num_attacks):
                penalty = 4 if weapon['name'] in AGILE_WEAPONS else 5
                penalty = penalty * 2 if i > 1 else penalty if i > 0 else 0
                output, attack_roll, damage_roll = self.make_attack_block(to_hit - penalty,
                    damage_mod, to_hit_bonus, num_dice, die_size)
                if attack_roll.crit == d20.CritType.CRIT:
                    total_damage += (damage_roll.total + damage_mod) * 2
                else:
                    total_damage += damage_roll.total + damage_mod
                embed.add_field(name=f"Attack {i + 1}", value=output)

            embed.description = f"Total damage: `{total_damage}`"

        await ctx.send(embed=embed)

    @commands.command(aliases=["attack2", "attack3", "ra", "repattack"])
    async def repeatattack(self, ctx, *, bonus_str=""):
        """Make another attack with the most recently used weapon.

        Repeated attacks are assumed to be part of the same turn; multiple attack penalty applies.
        To-hit bonuses can be added with the -b flag. Examples:
        `[p]repeatattack`
        `[p]repeatattack -b 1`
        """
        json_id = await self.config.user(ctx.author).active_char()
        if json_id is None:
            await ctx.send("Set an active character first with `character setactive`.")
            return

        data = await self.config.user(ctx.author).characters()
        char_data = data[json_id]['build']

        async with self.config.user(ctx.author).csettings() as csettings:
            if json_id not in csettings:
                csettings[json_id] = {}
            if 'consecutive_attacks' not in csettings[json_id]:
                csettings[json_id]['consecutive_attacks'] = 1
            if 'last_weapon' not in csettings[json_id]:
                await ctx.send("Unable to repeat attack; you haven't made any. " + \
                    "Use `attack` or `multiattack` instead.")
                return

            weapon = csettings[json_id]['last_weapon']
            num_attacks = csettings[json_id]['consecutive_attacks']

            bonuses = [b.strip() for b in bonus_str.split("-b")]

            name = char_data['name']
            article = "an" if weapon['display'][0] in ["a", "e", "i", "o", "u"] else "a"

            to_hit, damage_mod = self._get_weapon_mods(weapon, char_data)
            num_dice = self._get_num_damage_dice(weapon['str'])
            die_size = int(weapon['die'].split("d")[1])

            to_hit_bonus = sum([d20.roll(b).total for b in bonuses[1:]])

            penalty = 4 if weapon['name'] in AGILE_WEAPONS else 5
            penalty = penalty * 2 if num_attacks > 1 else penalty if num_attacks > 0 else 0
            output, _, _ = self.make_attack_block(to_hit - penalty, damage_mod, to_hit_bonus,
                num_dice, die_size)

            csettings[json_id]['consecutive_attacks'] += 1

            embed = await self._get_base_embed(ctx)
            embed.title = f"{name} attacks again with {article} {weapon['display']}!"
            embed.description = output

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
            damage_mod = math.floor(str_mod / 2) if str_mod > 0 else str_mod
        elif weapon['name'] in RANGED_WEAPONS:
            damage_mod = 0
        else:
            damage_mod = self._get_ability_mod(abilities['str'])

        prof_bonus = profs[weapon['prof']] + (0 if profs[weapon['prof']] == 0 else level)

        return ability_mod + prof_bonus + weapon['pot'], damage_mod + weapon['damageBonus']

    def _get_num_damage_dice(self, striking_rune: str):
        if striking_rune == "majorStriking":
            return 4
        elif striking_rune == "greaterStriking":
            return 3
        elif striking_rune == "striking":
            return 2
        else:
            return 1

    def make_attack_block(self, to_hit: int, damage_mod: int, to_hit_bonus: int, num_dice: int,
        die_size: int):
        attack_roll = d20.roll(self.make_dice_string(to_hit, to_hit_bonus))
        attack_line = f"**To hit**: {str(attack_roll)}"

        damage_roll = d20.roll(self.make_dice_string(damage_mod, bonuses=0, num_dice=num_dice,
            die_size=die_size))
        damage_line = f"**Damage**: {str(damage_roll)}"

        if attack_roll.crit == d20.CritType.CRIT:
            attack_line += " (**crit**)"
            damage_line += f" -> `{(damage_roll.total + damage_mod) * 2}`"

        return f"{attack_line}\n{damage_line}", attack_roll, damage_roll

    @commands.command(aliases=["pfspellbook", "pfspells", "spells"])
    async def spellbook(self, ctx):
        """Show the active character's spells."""
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
            focus_spells = []
            for tradition in focus.keys():
                for stat in focus[tradition].keys():
                    spells = focus[tradition][stat]['focusSpells']
                    focus_spells.extend(spells)
                    spell_count += len(spells)
            focus_field_name = f"Focus Spells {focus_points * SPELL_SLOT_SYMBOL}"
            focus_field = ", ".join(focus_spells)
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

        embed = await self._get_base_embed(ctx)
        embed.title = f"{char_data['name']}"
        embed.description = f"{char_data['class']} {char_data['level']}"

        ability_lines = []
        for ability in char_data['abilities'].keys():
            if ability == 'breakdown':
                continue
            mod = self._get_ability_mod(char_data['abilities'][ability])
            op = self._get_op(mod)
            ability_lines.append(f"**{ability.upper()}**: ({op}{mod})")
        abilities_field = " ".join(ability_lines[:3]) + "\n" + " ".join(ability_lines[3:])
        embed.add_field(name="Ability Scores", value=abilities_field, inline=False)

        profs = char_data['proficiencies']
        save_lines = []
        skill_lines = []
        for skill in SKILL_DATA.keys():
            if SKILL_DATA[skill][TYPE] == "ability":
                continue
            prof_label = self._get_prof_label(profs[skill])
            mod = self._get_skill_mod(skill, char_data)
            op = self._get_op(mod)

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
            op = self._get_op(mod)
            lore_lines.append(f"{prof_label}{skill[0].capitalize()}: ({op}{mod})")
        lore_field = "\n".join(lore_lines)
        embed.add_field(name="Lores", value=lore_field, inline=True)

        weapon_lines = []
        for weapon in char_data['weapons']:
            to_hit, damage_mod = self._get_weapon_mods(weapon, char_data)
            to_hit_op = self._get_op(to_hit)
            damage_op = self._get_op(damage_mod)
            num_dice = self._get_num_damage_dice(weapon['str'])
            weapon_lines.append(f"**{weapon['display']}**: {to_hit_op}{to_hit} to hit, " + \
                f"{num_dice}{weapon['die']} {damage_op} {damage_mod} damage")
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

    async def _get_base_embed(self, ctx):
        embed = discord.Embed()
        json_id = await self.config.user(ctx.author).active_char()
        settings = await self.config.user(ctx.author).csettings()

        if json_id in settings and 'color' in settings[json_id] and settings[json_id]['color']:
            embed.colour = discord.Colour(settings[json_id]['color'])
        else:
            embed.colour = discord.Colour(random.randint(0x000000, 0xFFFFFF))

        return embed

    @commands.command(aliases=["aon", "aonlookup", "pflookup"])
    async def lookup(self, ctx, *, query):
        """Look something up.
        
        Gives a link to a search on the Archives of Nethys for the given term.
        """
        await ctx.send(self._lmgtfy(f"`{query}`", query))

    @commands.command(aliases=['pffeat'])
    async def feat(self, ctx, *, feat_name):
        """Look up a feat (sort of)."""
        await ctx.send(self._lmgtfy("feats", feat_name))

    @commands.command(aliases=["pfitem"])
    async def item(self, ctx, *, item_name):
        """Look up a piece of equipment (sort of)."""
        await ctx.send(self._lmgtfy("items", item_name))

    @commands.command(aliases=["pfspell"])
    async def spell(self, ctx, *, spell_name):
        """Look up a spell (sort of)."""
        await ctx.send(self._lmgtfy("spells", spell_name))

    @commands.command(aliases=["pfweapon"])
    async def weapon(self, ctx, *, weapon_name):
        """Look up a weapon (sort of)."""
        await ctx.send(self._lmgtfy("weapons", weapon_name))

    def _lmgtfy(self, topic: str, query: str):
        aon_link = AON_SEARCH_BASE + urllib.parse.quote_plus(query)
        return f"Unfortunately, I don't have access to data on {topic}. " + \
            f"I can help you look it up on the Archives of Nethys, though:\n{aon_link}"

    @commands.command()
    async def research(self, ctx, days: int, dc: int, *, query: str):
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

        days = min(days, 24)

        query_parts = [p.strip() for p in query.split("-b")]

        check_name = query_parts[0].lower()

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

        bonuses = sum([d20.roll(b).total for b in query_parts[1:]])

        name = char_data['name']
        article = "an" if skill[0] in ["a", "e", "i", "o", "u"] else "a"

        embed = await self._get_base_embed(ctx)
        embed.title = f"{name} does some research!"

        total_kp = 0
        for i in range(days):
            research_roll = d20.roll(self.make_dice_string(mod, bonuses))
            if research_roll.total >= dc + 10:
                kp = 2
            elif research_roll.total >= dc:
                kp = 1
            elif research_roll.total > dc - 10:
                kp = 0
            else:
                kp = -1

            if research_roll.crit == d20.CritType.CRIT:
                kp = min(2, kp + 1)
            elif research_roll.crit == d20.CritType.FAIL:
                kp = max(-1, kp - 1)
            total_kp += kp
            embed.add_field(name=f"DTP {i + 1}: {kp} KP", value=str(research_roll))

        embed.description = f"DC {dc} {skill.capitalize()}\n" + \
            f"Total KP from this session: **{total_kp}**"

        await ctx.send(embed=embed)
