import discord
import json

from redbot.core import commands, app_commands


class rtl(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.group()
    @commands.guild_only()
    

    #Überbefehl
    async def rtl(self, ctx):
        pass

    #User rolle geben
    @rtl.command(name="add")
    #user: discord.member fordert die angabe eines discord useres bei befehl ausführung und role: discord.role eine rolle

    async def rtl_add(
        self, ctx, user: discord.Member, role: discord.Role
        ):
            
            #speichert die discord id des befehl senders in eine int variable
            author_id = ctx.author.id

            #öffnet die owners.json mit dem modos read (r) und speichert das in read_file
            with open("owners.json", mode="r", encoding="utf-8") as read_file:

                #versucht die datei welche in read_file gespeichert ist als json in die variable owners zu laden
                try:
                    owners= json.load(read_file)

                #wenn das nicht funktioniert wird ein text ausgegeben durch ctx.send("") await wird benötigt damit er es auch schickt
                except:
                    await ctx.send("Irgendwas ist beim öffnen der datei falschgelaufen versuche mit !rtl addowner einen eintrag hinzuzufügen")

                # wenn das öffnen funktioniert hat macht er hier weiter
                else:

                    #fragt ab ob in der owners json datei ein eintrag ist dir gleich ist wie die author id welche mit str() in ein string gemacht wird
                    if str(author_id) in owners:

                        #fragt ab ob die role in der owner datei unter dem unterpunkt der author id vorhanden ist 
                        if str(role.name) in owners[str(author_id)]:

                            #versucht dem angegebenen user die rolle zu geben
                            try:
                                await user.add_roles(role)
                                await ctx.send("<@" + str(user.id) + "> hat nun die Rolle " + role.mention)
                            except:
                                
                            #ausgebe falls es nicht möglich war
                                await ctx.send("Ein fehler ist aufgetreten beim versuch dem user die rolle zu geben. Hat er sie bereits?")
                        else:
                            await ctx.send("Du bist nicht als Owner dieser rolle eingetragen")
                    else:
                        await ctx.send("Du bist bei keiner rolle als Onwer hinterlegt")
                    


    #User rolle entfernen
    @rtl.command(name="remove")
    async def rtl_remove(
        self, ctx, user: discord.Member, role: discord.Role
        ):
            role_ping = discord.utils.get(ctx.guild.roles,name=role.name)
            author_id = ctx.author.id
            with open("owners.json", mode="r", encoding="utf-8") as read_file:
                try:
                    owners= json.load(read_file)
                except:
                    await ctx.send("Irgendwas ist beim öffnen der datei falschgelaufen versuche mit !rtl addowner einen eintrag hinzuzufügen")
                else:
                    if str(author_id) in owners:
                        if str(role.name) in owners[str(author_id)]:
                            try:
                                await user.remove_roles(role)
                                await ctx.send("<@" + str(user.id) + "> hat die Rolle " + role_ping.mention + " nun nichtmehr")
                            except:
                                await ctx.send("Ein fehler ist aufgetreten beim versuch dem user die rolle zu entfernen. Hat er sie garnicht?")
                        else:
                            await ctx.send("Du bist nicht als Owner dieser rolle eingetragen")
                    else:
                        await ctx.send("Du bist bei keiner rolle als Onwer hinterlegt")


    #User Owner der rolle geben
    @commands.admin()
    @rtl.command(name="addowner")
    async def rtl_addowner(
        self, ctx, user: discord.Member, role: discord.Role
        ):
            role_ping = discord.utils.get(ctx.guild.roles,name=role.name)
            
            try:
                with open("owners.json", mode="r", encoding="utf-8") as read_file:
                    owners= json.load(read_file)
            except:
                await ctx.send("Eine neue Json Datei wird angelegt")
                newowner = {str(user.id):  [str(role)]}
                add_json = json.dumps(newowner)
                newowner = json.loads(add_json)

                with open("owners.json", mode="w", encoding="utf-8") as write_file:
                    json.dump(newowner, write_file, indent= 4)
                        
                    await ctx.send("<@" + str(user.id) + "> ist nun der Besitzer der Rolle " + role_ping.mention)
            else:

                if str(user.id) not in owners:
                    newowner = [str(role.name)]
                    owners[str(user.id)] = []
                    owners[str(user.id)].extend(newowner)

                    with open("owners.json", mode="w", encoding="utf-8") as write_file:
                        json.dump(owners, write_file, indent= 4)

                        await ctx.send("<@" + str(user.id) + "> ist nun der Besitzer der Rolle " + role_ping.mention)

                else:
                    if str(role.name) not in owners[str(user.id)]:
                        newowner = [str(role.name)]
                        owners[str(user.id)].extend(newowner)
                        with open("owners.json", mode="w", encoding="utf-8") as write_file:
                            json.dump(owners, write_file, indent= 4)
                            await ctx.send("<@" + str(user.id) + "> ist nun der Besitzer der Rolle " + role_ping.mention)
                    else:
                        await ctx.send("<@" + str(user.id) + "> ist schon Besitzer der Rolle " + role_ping.mention)
                            
    #User den besitzer der rolle entfernen
    @commands.admin()
    @rtl.command(name="removeowner")
    async def rtl_removeowner(
        self, ctx, user: discord.Member, role: discord.Role
        ):
            role_ping = discord.utils.get(ctx.guild.roles,name=role.name)
            
            try:
                with open("owners.json", mode="r", encoding="utf-8") as read_file:
                    owners= json.load(read_file)
            except:
                await ctx.send("die json Datei wurde nicht gefunden oder es sind keine einträge vorhanden")
            else:
                if str(user.id) in owners and isinstance(owners[str(user.id)], list):
                    if str(role.name) in owners[str(user.id)]:
                        owners[str(user.id)].remove(str(role.name))
                        with open("owners.json", mode="w", encoding="utf-8") as write_file:
                            json.dump(owners, write_file, indent= 4)
                            await ctx.send("Der Benutzer <@" + str(user.id) + "> wurde als Besitzer von " + role_ping.mention + " entfernt")
                    else:
                        await ctx.send("Der Benutzer <@" + str(user.id) + "> besitzt die rolle " + role_ping.mention + " nicht")
                else:
                    await ctx.send("Der Benutzer <@" + str(user.id) + "> hat keinen Owner eintrag")
