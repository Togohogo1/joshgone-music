import os
import typing
import re
import asyncio
import math

import aiosqlite
from discord.ext import commands

class Chant(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.group(name="chants", ignore_extra=False, pass_context=True, invoke_without_command=True)
    async def _chants(self, ctx):
        """Configure chants"""
        await self._list(ctx)

    @staticmethod
    def pack(strings, *, maxlen=2000):
        current = []
        length = 0
        for name in strings:
            if len(name) + length > maxlen:
                yield "".join(current)
                current = []
                length = 0
            length += len(name)
            current.append(name)
        if current:
            yield "".join(current)

    @_chants.command(name="regexlist", ignore_extra=False, hidden=True)
    async def _regexlist(self, ctx, max_amount: typing.Optional[int] = -1, *, regex):
        async with aiosqlite.connect(os.environ["JOSHGONE_DB"]) as db:
            async with db.execute("SELECT chant_name FROM chants WHERE server_id = ?;", (ctx.guild.id,)) as cursor:
                names = [row[0] async for row in cursor]
        found = []
        for name in names:
            if len(found) == max_amount:
                break
            if not re.search(regex, name):
                continue
            found.append(name)
        length = len(found)
        if not found:
            found = ["None"]
        for i in range(1, len(found)):
            found[i] = f", {found[i]}"
        found.insert(0, f"Found {length}: ")
        for message in self.pack(found):
            await ctx.send(message)

    @_chants.command(name="regexremove", ignore_extra=False, hidden=True)
    @commands.is_owner()
    async def _regexremove(self, ctx, max_amount: typing.Optional[int] = -1, *, regex):
        async with aiosqlite.connect(os.environ["JOSHGONE_DB"]) as db:
            async with db.execute("SELECT chant_name FROM chants WHERE server_id = ?;", (ctx.guild.id,)) as cursor:
                names = [row[0] async for row in cursor]
        removed = []
        for name in names:
            if len(remove) == max_amount:
                break
            if not re.search(regex, name):
                continue
            removed.append(name)
        async with aiosqlite.connect(os.environ["JOSHGONE_DB"]) as db:
            for name in removed:
                await db.execute("DELETE FROM chants WHERE server_id = ? AND chant_name = ?;", (ctx.guild.id, name))
            await db.commit()
        length = len(removed)
        if not removed:
            removed = ["None"]
        for i in range(1, len(removed)):
            removed[i] = f", {removed[i]}"
        removed.insert(0, f"Removed {length}: ")
        for message in self.pack(removed):
            await ctx.send(message)

    @_chants.command(name="list", ignore_extra=False)
    async def _list(self, ctx, debug: bool = False):
        """List available chants"""
        async with aiosqlite.connect(os.environ["JOSHGONE_DB"]) as db:
            async with db.execute("SELECT chant_name FROM chants WHERE server_id = ?;", (ctx.guild.id,)) as cursor:
                names = [row[0] async for row in cursor]
        if debug:
            names = [f"`{name}`" for name in names]
        length = len(names)
        if not names:
            names = ["None"]
        for i in range(1, len(names)):
            names[i] = f", {names[i]}"
        names.insert(0, f"Chants [{length}]: ")
        for message in self.pack(names):
            await ctx.send(message)

    @_chants.command(name="update")
    @commands.check_any(
        commands.has_permissions(manage_messages=True),
        commands.has_role("enchanter"),
    )
    async def _update(self, ctx, name, *, text):
        """Update a chant

        This will silently overwrite any previous chant with the same name.
        """
        if len(name) > 35:
            raise ValueError("name too long (length over 35)")
        if not name.isprintable():
            raise ValueError(f"Name not printable: {name!r}")
        async with aiosqlite.connect(os.environ["JOSHGONE_DB"]) as db:
            async with db.execute("SELECT COUNT(*) FROM chants WHERE server_id = ?;", (ctx.guild.id,)) as cursor:
                if not (row := await cursor.fetchone()):
                    raise ValueError("could not get count of chants")
                if row[0] >= 500:
                    raise ValueError(f"too many chants stored: {row[0]}")
            await db.execute("INSERT OR REPLACE INTO chants VALUES (?, ?, ?);", (ctx.guild.id, name, text))
            await db.commit()
        await ctx.send(f"Updated chant {name}")

    @_chants.command(name="add")
    @commands.check_any(
        commands.has_permissions(manage_messages=True),
        commands.has_role("enchanter"),
    )
    async def _add(self, ctx, name, *, text):
        """Add a chant

        This will fail if a chant with the same name already exists.
        """
        if len(name) > 35:
            raise ValueError("name too long (length over 35)")
        if not name.isprintable():
            raise ValueError(f"Name not printable: {name!r}")
        async with aiosqlite.connect(os.environ["JOSHGONE_DB"]) as db:
            async with db.execute("SELECT chant_text FROM chants WHERE server_id = ? AND chant_name = ? LIMIT 1;", (ctx.guild.id, name)) as cursor:
                if (row := await cursor.fetchone()):
                    await ctx.send(f"Chant {name} exists")
                    return
            async with db.execute("SELECT COUNT(*) FROM chants WHERE server_id = ?;", (ctx.guild.id,)) as cursor:
                if not (row := await cursor.fetchone()):
                    raise ValueError("could not get count of chants")
                if row[0] >= 500:
                    raise ValueError(f"too many chants stored: {row[0]}")
            await db.execute("INSERT INTO chants VALUES (?, ?, ?);", (ctx.guild.id, name, text))
            await db.commit()
        await ctx.send(f"Added chant {name}")

    @_chants.command(name="check", ignore_extra=False)
    async def _check(self, ctx, name: str):
        """Output the text for a single chant"""
        async with aiosqlite.connect(os.environ["JOSHGONE_DB"]) as db:
            async with db.execute("SELECT chant_text FROM chants WHERE server_id = ? AND chant_name = ? LIMIT 1;", (ctx.guild.id, name)) as cursor:
                if (row := await cursor.fetchone()):
                    await ctx.send(f"Chant {name} {{`{name!r}`}}: {row[0]}")
                else:
                    await ctx.send(f"Chant {name} {{`{name!r}`}} doesn't exist")

    @_chants.command(name="remove", ignore_extra=False)
    @commands.check_any(
        commands.has_permissions(manage_messages=True),
        commands.has_role("enchanter"),
    )
    async def _remove(self, ctx, name: str):
        """Remove a chant"""
        async with aiosqlite.connect(os.environ["JOSHGONE_DB"]) as db:
            await db.execute("DELETE FROM chants WHERE server_id = ? AND chant_name = ?;", (ctx.guild.id, name))
            await db.commit()
        await ctx.send(f"Removed chant {name}")

    @commands.command(name="chant", aliases=["h"], ignore_extra=False)
    async def _chant(self, ctx, name: str, repeats: int = 5, delay: float = 2):
        """Repeat a chant multiple times

        `repeat` specifies the number of times to repeat the chant
        `delay` specifies the number of seconds to wait between chants
        """
        if not math.isfinite(delay):
            raise ValueError(f"{delay!r} is not finite")
        for _ in range(repeats):
            async with aiosqlite.connect(os.environ["JOSHGONE_DB"]) as db:
                async with db.execute("SELECT running FROM server WHERE server_id = ? LIMIT 1;", (ctx.guild.id,)) as cursor:
                    if not (row := await cursor.fetchone()) or not row[0]:
                        break
                async with db.execute("SELECT chant_text FROM chants WHERE server_id = ? AND chant_name = ? LIMIT 1;", (ctx.guild.id, name)) as cursor:
                    row = await cursor.fetchone()
                    if not row:
                        break
                    text = row[0]
                    if not text:
                        break
            await ctx.send(text)
            await asyncio.sleep(delay)

    @commands.command(name="chant1", aliases=["h1"], ignore_extra=False)
    async def _chant1(self, ctx, name: str, delay: float = 2):
        """Repeats a chant once

        `delay` specifies the number of seconds to wait between chants
        """
        await self._chant(ctx, name, 1, delay)

def setup(bot):
    bot.add_cog(Chant(bot))
