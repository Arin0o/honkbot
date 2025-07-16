import discord
import json
from pathlib import Path
from redbot.core import commands
from redbot.core.data_manager import cog_data_path


class RTL(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.file_path = cog_data_path(self) / "owners.json"

    def _load_owners(self):
        if not self.file_path.exists():
            return {}
        with open(self.file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save_owners(self, owners):
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(owners, f, indent=4)

    @commands.group()
    @commands.guild_only()
    async def rtl(self, ctx):
        """RTL Hauptbefehl"""
        if ctx.invoked_subcommand is None:
            await ctx.send("Bitte verwende einen Unterbefehl (add, remove, addowner, removeowner, listowners, myroles).")

    @rtl.command(name="add")
    async def rtl_add(self, ctx, user: discord.Member, role: discord.Role):
        """Gibt einem Benutzer eine Rolle, sofern du berechtigt bist."""
        author_id = str(ctx.author.id)
        owners = self._load_owners()

        if author_id in owners and role.name in owners[author_id]:
            if role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
                await ctx.send("Du kannst keine gleich hohe oder höhere Rolle vergeben.")
                return
            try:
                await user.add_roles(role)
                await ctx.send(f"{user.mention} hat nun die Rolle {role.mention}")
            except Exception as e:
                await ctx.send(f"Fehler beim Zuweisen der Rolle: {e}")
        else:
            await ctx.send("Du bist nicht als Owner dieser Rolle eingetragen.")

    @rtl.command(name="remove")
    async def rtl_remove(self, ctx, user: discord.Member, role: discord.Role):
        """Entfernt eine Rolle von einem Benutzer, sofern du berechtigt bist."""
        author_id = str(ctx.author.id)
        owners = self._load_owners()

        if author_id in owners and role.name in owners[author_id]:
            try:
                await user.remove_roles(role)
                await ctx.send(f"{user.mention} hat die Rolle {role.mention} entfernt bekommen")
            except Exception as e:
                await ctx.send(f"Fehler beim Entfernen der Rolle: {e}")
        else:
            await ctx.send("Du bist nicht als Owner dieser Rolle eingetragen.")

    @commands.admin()
    @rtl.command(name="addowner")
    async def rtl_addowner(self, ctx, user: discord.Member, role: discord.Role):
        """Fügt einem Benutzer die Berechtigung hinzu, eine bestimmte Rolle zu vergeben."""
        owners = self._load_owners()
        user_id = str(user.id)

        if user_id not in owners:
            owners[user_id] = []

        if role.name not in owners[user_id]:
            owners[user_id].append(role.name)
            self._save_owners(owners)
            await ctx.send(f"{user.mention} ist jetzt Owner der Rolle {role.mention}.")
        else:
            await ctx.send(f"{user.mention} ist bereits Owner der Rolle {role.mention}.")

    @commands.admin()
    @rtl.command(name="removeowner")
    async def rtl_removeowner(self, ctx, user: discord.Member, role: discord.Role):
        """Entfernt einem Benutzer die Berechtigung, eine bestimmte Rolle zu vergeben."""
        owners = self._load_owners()
        user_id = str(user.id)

        if user_id in owners and role.name in owners[user_id]:
            owners[user_id].remove(role.name)
            if not owners[user_id]:
                del owners[user_id]  # Clean up empty entries
            self._save_owners(owners)
            await ctx.send(f"{user.mention} wurde als Owner der Rolle {role.mention} entfernt.")
        else:
            await ctx.send(f"{user.mention} ist kein Owner der Rolle {role.mention}.")

    @rtl.command(name="listowners")
    @commands.admin()
    async def rtl_listowners(self, ctx):
        """Zeigt alle Rollen-Owner an (nur Admins)."""
        owners = self._load_owners()
        if not owners:
            await ctx.send("Keine Rollen-Owner eingetragen.")
            return

        embed = discord.Embed(title="Rollen-Owner Übersicht", color=discord.Color.blue())
        for user_id, roles in owners.items():
            member = ctx.guild.get_member(int(user_id))
            name = member.display_name if member else f"Unbekannt ({user_id})"
            role_list = ", ".join(roles) if roles else "Keine"
            embed.add_field(name=name, value=role_list, inline=False)

        await ctx.send(embed=embed)

    @rtl.command(name="myroles")
    async def rtl_myroles(self, ctx):
        """Zeigt dir, welche Rollen du verwalten darfst."""
        owners = self._load_owners()
        user_id = str(ctx.author.id)

        if user_id not in owners or not owners[user_id]:
            await ctx.send("Du bist aktuell für keine Rollen eingetragen.")
            return

        role_names = owners[user_id]
        embed = discord.Embed(title="Deine verwaltbaren Rollen", color=discord.Color.green())
        embed.description = ", ".join(role_names)
        await ctx.send(embed=embed)
    @rtl.command(name="help")
    async def rtl_help(self, ctx):
        """Zeigt eine Übersicht aller RTL-Befehle."""
        embed = discord.Embed(title="RTL Hilfe", color=discord.Color.orange())
        embed.add_field(name="!rtl add <@User> <Rolle>", value="Gibt einem Nutzer eine Rolle, sofern du berechtigt bist.", inline=False)
        embed.add_field(name="!rtl remove <@User> <Rolle>", value="Entfernt eine Rolle vom Nutzer, sofern du berechtigt bist.", inline=False)
        embed.add_field(name="!rtl myroles", value="Zeigt dir, welche Rollen du selbst vergeben darfst.", inline=False)
        embed.add_field(name="!rtl addowner <@User> <Rolle>", value="(Admin) Gibt einem Nutzer die Berechtigung, eine bestimmte Rolle zu verwalten.", inline=False)
        embed.add_field(name="!rtl removeowner <@User> <Rolle>", value="(Admin) Entzieht einem Nutzer die Berechtigung für eine Rolle.", inline=False)
        embed.add_field(name="!rtl listowners", value="(Admin) Zeigt eine Liste aller Rollen-Owner an.", inline=False)
        await ctx.send(embed=embed)
