import datetime
import time
import pymongo
import nextcord as discord
from nextcord.ext import commands
import requests
import os

# Set up Discord API Token and MongoDB Access Link in a .env file and use the command "heroku local" to run the bot locally.

TOKEN = os.environ.get("IGCSEBOT_TOKEN")
LINK = os.environ.get("MONGO_LINK")
GUILD_ID = 576460042774118420

jsonData = json.load(open('objects.json'))
helper_roles = jsonData.helper_roles
study_roles = jsonData.study_roles
text_prompts = jsonData.text_prompts
subreddits = jsonData.subreddits

intents = discord.Intents().all()
bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')
    await bot.change_presence(activity=discord.Game(name="Flynn#5627"))


@bot.event
async def on_voice_state_update(member, before, after):
    if member.guild.id == 576460042774118420:
        if before.channel:  # When user leaves a voice channel
            if "study session" in before.channel.name.lower() and before.channel.members == []:  # If the study session is over
                await before.channel.edit(name="General")  # Reset channel name


@bot.event
async def on_thread_join(thread):
    await thread.join()  # Join all threads automatically


@bot.event
async def on_guild_join(guild):
    global gpdp
    gpdp.set_pref('rep_enabled', True, guild.id)
    await guild.create_role(name="Reputed", color=0x3498db)  # Create Reputed Role
    await guild.create_role(name="100+ Rep Club", color=0xf1c40f)  # Create 100+ Rep Club Role
    await guild.create_role(name="500+ Rep Club", color=0x2ecc71)  # Create 500+ Rep Club Role
    await guild.system_channel.send(
        "Hi! Please set server preferences using the slash command /set_preferences for this bot to function properly.")


@bot.event
async def on_member_join(member):
    if member.guild.id == 576460042774118420:  # r/igcse welcome message
        embed1 = discord.Embed.from_dict(eval(
            """{'color': 3066993, 'type': 'rich', 'description': "Hello and welcome to the official r/IGCSE Discord server, a place where you can ask any doubts about your exams and find help in a topic you're struggling with! We strongly suggest you read the following message to better know how our server works!\n\n***How does the server work?***\n\nThe server mostly entirely consists of the students who are doing their IGCSE and those who have already done their IGCSE exams. This server is a place where you can clarify any of your doubts regarding how exams work as well as any sort of help regarding a subject or a topic in which you struggle.\n\nDo be reminded that academic dishonesty is not allowed in this server and you may face consequences if found to be doing so. Examples of academic dishonesty are listed below (the list is non-exhaustive) - by joining the server you agree to follow the rules of the server.\n\n> Asking people to do your homework for you, sharing any leaked papers before the exam session has ended, etc.), asking for leaked papers or attempted malpractice are not allowed as per *Rule 1*. \n> \n> Posting pirated content such as textbooks or copyrighted material are not allowed in this server as per *Rule 7.*\n\n***How to ask for help?***\n\nWe have subject helpers for every subject to clear any doubts or questions you may have. If you want a subject helper to entertain a doubt, you should type in `'helper'`. A timer of **15 minutes** will start before the respective subject helper will be pinged. You will be reminded **3 minutes** before the time elapses to cancel the ping if your doubt has been entertained. Remember to cancel your ping once a helper is helping you!\n\n***How to contact the moderators?***\n\nYou can contact us by sending a message through <@861445044790886467> by responding to the bot, where it will be forwarded to the moderators to view. Do be reminded that only general server inquiries should be sent and other enquiries will not be entertained, as there are subject channels for that purpose.", 'title': 'Welcome to r/IGCSE!'}"""))
        embed2 = discord.Embed.from_dict(eval(
            "{'color': 3066993, 'type': 'rich', 'description': 'We also require all new users to pick up session roles. These make sure that you will have access to the appropriate general chat channels and for our helpers to give you more specific advice.\n\nReact to the corresponding reactions in <#932550807755304990> to verify and gain access to the rest of the server.\n\nAfterwards, react to the corresponding roles in <#932570912660791346> or <#932546951055032330> to gain access to your corresponding subject channels.', 'title': 'Verification system (PLEASE READ)'}"))
        channel = await member.create_dm()
        try:
            await channel.send(embed=embed1)
            await channel.send(embed=embed2)
        except:
            channel = member.guild.get_channel(920138547858645072)
            await channel.send(content=member.mention, embed=embed1)
            await channel.send(content=member.mention, embed=embed2)


@bot.event
async def on_message(message):
    if gpdb.get_pref('rep_enabled', message.guild.id):
        await repMessages(message)  # If message is replying to another message
    if message.channel.name == 'counting':  # To facilitate #counting
        await counting(message)
    if message.guild.id == 576460042774118420:
        if message.content.lower() == "pin":  # Pin a message
            if isHelper(message.author) or isModerator(message.author):
                msg = await message.channel.fetch_message(message.reference.message_id)
                await msg.pin()
                await msg.reply(f"This message has been pinned by {message.author.mention}.")
                await message.delete()

        if message.content.lower() == "unpin":  # Unpin a message
            if isHelper(message.author) or isModerator(message.author):
                msg = await message.channel.fetch_message(message.reference.message_id)
                await msg.unpin()
                await msg.reply(f"This message has been unpinned by {message.author.mention}.")
                await message.delete()


# Utility Functions

async def isModerator(member: discord.Member):
    roles = [role.id for role in member.roles]
    if 578170681670369290 in roles or 784673059906125864 in roles:  # r/igcse moderator role ids
        return True
    elif member.guild_permissions.administrator:
        return True
    return False


async def isHelper(member: discord.Member):
    roles = [role.name.lower() for role in member.roles]
    for role in roles:
        if "helper" in role:
            return True
    return False


# Reaction Roles



class DropdownRR(discord.ui.Select):
    def __init__(self, category, options):
        self._options = options
        selectOptions = [
            discord.SelectOption(emoji=option[0], label=option[1], value=option[2]) for option in options
        ]
        super().__init__(placeholder=f'Select your {category} subjects', min_values=0, max_values=len(selectOptions),
                         options=selectOptions)

    async def callback(self, interaction: discord.Interaction):
        added_role_names = []
        removed_role_names = []
        for option in self._options:
            role = interaction.guild.get_role(int(option[2]))
            if str(option[2]) in self.values:
                if role not in interaction.user.roles:
                    await interaction.user.add_roles(role)
                    added_role_names.append(role.name)
            else:
                if role in interaction.user.roles:
                    await interaction.user.remove_roles(role)
                    removed_role_names.append(role.name)
        if len(added_role_names) > 0 and len(removed_role_names) > 0:
            await interaction.send(
                f"Successfully opted for roles: {', '.join(added_role_names)} and unopted from roles: {', '.join(removed_role_names)}.",
                ephemeral=True)
        elif len(added_role_names) > 0 and len(removed_role_names) == 0:
            await interaction.send(f"Successfully opted for roles: {', '.join(added_role_names)}.", ephemeral=True)
        elif len(added_role_names) == 0 and len(removed_role_names) > 0:
            await interaction.send(f"Successfully unopted from roles: {', '.join(removed_role_names)}.", ephemeral=True)


class DropdownViewRR(discord.ui.View):
    def __init__(self):
        super().__init__()
        data = {
            "Sciences": [
                ["💡", "Physics", 685837416443281493],
                ["🧪", "Chemistry", 685837450895032336],
                ["🍀", "Biology", 685837475939221770],
                ["🔍", "Coordinated and Combined Sciences", 667769546475700235],
                ["🌲", "Environmental Management", 688357525984509984],
                ["🏃‍♂️", "Physical Education", 685837363003523097],
            ],
            "Mathematics": [
                ["🔢", "Mathematics", 688354722251276308],
                ["✳️", "Additional/Further Mathematics", 688355303808303170],
                ["♾️", "International Mathematics", 871702273640787988],
            ],
            # Add other subjects here
        }
        for category, options in data.items():
            self.add_item(DropdownRR(category, options))


@bot.slash_command(description="Pick up your roles", guild_ids=[GUILD_ID])
async def roles(interaction: discord.Interaction):
    await interaction.send(view=DropdownViewRR(), ephemeral=True)


@bot.command(description="Dropdown for picking up reaction roles", guild_ids=[GUILD_ID])
async def roles(ctx):
    await ctx.send(view=DropdownViewRR())


# Reputation


class ReputationDB:
    def __init__(self, link: str):
        self.client = pymongo.MongoClient(link, server_api=pymongo.server_api.ServerApi('1'))
        self.db = self.client.IGCSEBot
        self.reputation = self.db.reputation

    def bulk_insert_rep(self, rep_dict: dict, guild_id: int):
        # rep_dict = eval("{DICT}".replace("\n","")) to restore reputation from #rep-backup
        insertion = [{"user_id": user_id, "rep": rep, "guild_id": guild_id} for user_id, rep in rep_dict.items()]
        result = self.reputation.insert_many(insertion)
        return result

    def get_rep(self, user_id: int, guild_id: int):
        result = self.reputation.find_one({"user_id": user_id, "guild_id": guild_id})
        if result is None:
            return None
        else:
            return result['rep']

    def change_rep(self, user_id: int, new_rep: int, guild_id: int):
        result = self.reputation.update_one({"user_id": user_id, "guild_id": guild_id}, {"$set": {"rep": new_rep}})
        return new_rep

    def delete_user(self, user_id: int, guild_id: int):
        result = self.reputation.delete_one({"user_id": user_id, "guild_id": guild_id})
        return result

    def add_rep(self, user_id: int, guild_id: int):
        rep = self.get_rep(user_id, guild_id)
        if rep is None:
            rep = 1
            self.reputation.insert_one({"user_id": user_id, "guild_id": guild_id, "rep": rep})
        else:
            rep += 1
            self.change_rep(user_id, rep, guild_id)
        return rep

    def rep_leaderboard(self, guild_id):
        leaderboard = self.reputation.find({"guild_id": guild_id}, {"_id": 0, "guild_id": 0}).sort("rep", -1)
        return list(leaderboard)


repDB = ReputationDB(LINK)


async def isThanks(text):
    alternatives = ['thanks', 'thank you', 'thx', 'tysm', 'thank u', 'thnks', 'tanks', "thanku"]
    if "ty" in text.lower().split():
        return True
    else:
        for alternative in alternatives:
            if alternative in text.lower():
                return True


async def isWelcome(text):
    alternatives = ["you're welcome", "your welcome", "ur welcome", "your welcome", 'no problem']
    alternatives_2 = ["np", "np!", "yw", "yw!"]
    if "welcome" == text.lower():
        return True
    else:
        for alternative in alternatives:
            if alternative in text.lower():
                return True
        for alternative in alternatives_2:
            if alternative == text.lower().split():
                return True
    return False


async def repMessages(message):
    repped = []
    if message.reference:
        msg = await message.channel.fetch_message(message.reference.message_id)

    if message.reference and msg.author != message.author and not msg.author.bot and not message.author.mentioned_in(
            msg) and (
            await isWelcome(message.content)):
        repped = [message.author]
    elif await isThanks(message.content):
        for mention in message.mentions:
            if mention == message.author:
                await message.channel.send(f"Uh-oh, {message.author.mention}, you can't rep yourself!")
            elif mention.bot:
                await message.channel.send(f"Uh-oh, {message.author.mention}, you can't rep a bot!")
            else:
                repped.append(mention)

    if repped:
        for user in repped:
            rep = repDB.add_rep(user.id, message.guild.id)
            if rep == 100 or rep == 500:
                role = discord.utils.get(user.guild.roles, name=f"{rep}+ Rep Club")
                await user.add_roles(role)
                await message.channel.send(f"Gave +1 Rep to {user.mention} ({rep})\nWelcome to the {rep}+ Rep Club!")
            else:
                await message.channel.send(f"Gave +1 Rep to {user} ({rep})")
        leaderboard = repDB.rep_leaderboard(message.guild.id)
        members = [list(item.values())[0] for item in leaderboard[:3]]  # Creating list of Reputed member ids
        role = discord.utils.get(user.guild.roles, name="Reputed")
        if [member.id for member in role.members] != members:  # If Reputed has changed
            for m in role.members:
                await m.remove_roles(role)
            for member in members:
                member = message.guild.get_member(member)
                await member.add_roles(role)


@bot.slash_command(description="View someone's current rep")
async def rep(interaction: discord.Interaction,
              user: discord.User = discord.SlashOption(name="user", description="User to view rep of", required=True)):
    await interaction.response.defer()
    rep = repDB.get_rep(user.id, interaction.guild.id)
    await interaction.send(f"{user} has {rep} rep.", ephemeral=False)


@bot.slash_command(description="Change someone's current rep (for moderators)")
async def change_rep(interaction: discord.Interaction,
                     user: discord.User = discord.SlashOption(name="user", description="User to view rep of",
                                                              required=True),
                     new_rep: int = discord.SlashOption(name="new_rep", description="New rep amount", required=True)):
    await interaction.response.defer()
    if await isModerator(interaction.user):
        rep = repDB.change_rep(user.id, new_rep, interaction.guild.id)
    await interaction.send(f"{user} now has {rep} rep.", ephemeral=False)


@bot.slash_command(description="View the current rep leaderboard")
async def leaderboard(interaction: discord.Interaction,
                      page: int = discord.SlashOption(name="page", description="Page number to to display",
                                                      required=False),
                      user_to_find: discord.User = discord.SlashOption(name="user",
                                                                       description="User to find on the leaderboard",
                                                                       required=False)
                      ):
    await interaction.response.defer()
    leaderboard = repDB.rep_leaderboard(interaction.guild.id)  # Rep leaderboard
    leaderboard = [item.values() for item in leaderboard]  # Changing format of leaderboard
    chunks = [list(leaderboard)[x:x + 9] for x in
              range(0, len(leaderboard), 9)]  # Split into groups of 9

    pages = []
    for n, chunk in enumerate(chunks):
        embedVar = discord.Embed(title="Reputation Leaderboard", description=f"Page {n + 1} of {len(chunks)}",
                                 colour=discord.Colour.green())
        for user, rep in chunk:
            if user_to_find:
                if user_to_find.id == user:
                    page = n + 1
            user_name = interaction.guild.get_member(user)
            if rep == 0 or user_name is None:
                repDB.delete_user(user, interaction.guild.id)
            else:
                embedVar.add_field(name=user_name, value=str(rep) + "\n", inline=True)
        pages.append(embedVar)

    if not page: page = 1

    message = await interaction.send(embed=pages[page - 1])


# Misc Functions

@bot.command(description="Clear messages in a channel")
async def clear(ctx, num_to_clear: int):
    if not await isModerator(ctx.author):
        await ctx.send("You do not have the permissions to perform this action.")
    try:
        await ctx.channel.purge(limit=num_to_clear + 1)
    except:
        await ctx.reply("Oops! I can only delete messages sent in the last 14 days")

async def counting(message):
    if message.author.bot:
        await message.delete()
        return

    msgs = await message.channel.history(limit=2).flatten()
    try:
        msg = msgs[1]

        if "✅" in [str(reaction.emoji) for reaction in msg.reactions]:
            last_number = int(msg.content)
            last_author = msg.author
        else:
            last_number = 0
            last_author = None
    except:
        last_number = 0
        last_author = None

    try:
        if int(message.content) == last_number + 1 and last_author != message.author:
            await message.add_reaction("✅")
        else:
            await message.delete()
    except:
        await message.delete()


@bot.slash_command(description="Send messages using the bot (for mods)")
async def send_message(interaction: discord.Interaction,
                       message_text: str = discord.SlashOption(name="message_text",
                                                               description="Message to send",
                                                               required=True),
                       channel_to_send_to: discord.abc.GuildChannel = discord.SlashOption(name="channel_to_send_to",
                                                                                          description="Channel to send the message to",
                                                                                          required=True),
                       message_id_to_reply_to: int = discord.SlashOption(name="message_id_to_reply_to",
                                                                         description="Message to reply to (optional)",
                                                                         required=False)):
    if not await isModerator(interaction.user):
        await interaction.send("You are not authorized to perform this action.")
        return
    if message_id_to_reply_to:
        message_to_reply_to = channel_to_send_to.fetch_message(message_id_to_reply_to)
        await message_to_reply_to.reply(message_text)
        await interaction.send("Done!", ephemeral=True, delete_after=2)
    else:
        await channel_to_send_to.send(message_text)
        await interaction.send("Done!", ephemeral=True, delete_after=2)


@bot.slash_command(description="Pong!")
async def ping(interaction: discord.Interaction):
    await interaction.send("Pong!")


@bot.slash_command(description="Get a random joke")
async def joke(interaction: discord.Interaction):
    await interaction.response.defer()
    req = requests.get("https://icanhazdadjoke.com/", headers={"Accept": "application/json"})
    jsonobj = req.json()
    joke = jsonobj['joke']
    await interaction.send(joke)


# Wiki Page


class Groups(discord.ui.Select):
    def __init__(self):
        options = []
        for group in subreddits.keys():
            options.append(discord.SelectOption(label=group))
        super().__init__(
            placeholder="Choose a subject group...",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        group = self.values[0]
        view = discord.ui.View(timeout=None)
        for subject in subreddits[group].keys():
            view.add_item(
                discord.ui.Button(label=subject, style=discord.ButtonStyle.url, url=subreddits[group][subject]))
        await interaction.response.edit_message(view=view)


class DropdownView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(Groups())


@bot.slash_command(description="View the r/igcse wiki page", guild_ids=[GUILD_ID])
async def wiki(interaction: discord.Interaction):
    await interaction.send(view=DropdownView())


# Search past papers

@bot.slash_command(description="Search for IGCSE past papers with subject code/question text")
async def search(interaction: discord.Interaction,
                 query: str = discord.SlashOption(name="query", description="Search query", required=True)):
    await interaction.response.defer()
    try:
        response = requests.get(f"https://paper.sc/search/?as=json&query={query}").json()
        if len(response['list']) == 0:
            await interaction.send("No results found in past papers. Try changing your query for better results.",
                                   ephemeral=True)
        else:
            embed = discord.Embed(title="Potential Match",
                                  description="Your question matched a past paper question!",
                                  colour=discord.Colour.green())
            for n, item in enumerate(response['list'][:3]):
                # embed.add_field(name="Result No.", value=str(n+1), inline=False)
                embed.add_field(name="Subject", value=item['doc']['subject'], inline=True)
                embed.add_field(name="Paper", value=item['doc']['paper'], inline=True)
                embed.add_field(name="Session", value=item['doc']['time'], inline=True)
                embed.add_field(name="Variant", value=item['doc']['variant'], inline=True)
                embed.add_field(name="QP Link", value=f"https://paper.sc/doc/{item['doc']['_id']}", inline=True)
                embed.add_field(name="MS Link", value=f"https://paper.sc/doc/{item['related'][0]['_id']}",
                                inline=True)
            await interaction.send(embed=embed, ephemeral=True)
    except:
        await interaction.send("No results found in past papers. Try changing your query for better results.",
                               ephemeral=True)


# Moderation Actions

class GuildPreferencesDB:
    def __init__(self, link: str):
        self.client = pymongo.MongoClient(link, server_api=pymongo.server_api.ServerApi('1'))
        self.db = self.client.IGCSEBot
        self.pref = self.db.guild_preferences

    def set_pref(self, pref: str, pref_value, guild_id: int):
        """ 'pref' can be 'modlog_channel' or 'rep_enabled'. """
        if self.get_pref(pref, guild_id):
            result = self.pref.update_one({"guild_id": guild_id}, {"$set": {pref: pref_value}})
        else:
            result = self.pref.insert_one({"guild_id": guild_id, pref: pref_value})
        return result

    def get_pref(self, pref: str, guild_id: int):
        result = self.pref.find_one({"guild_id": guild_id})
        if result is None:
            return None
        else:
            return result.get(pref, None)


gpdb = GuildPreferencesDB(LINK)


@bot.slash_command(description="Set server preferences (for mods)")
async def set_preferences(interaction: discord.Interaction,
                          modlog_channel: discord.abc.GuildChannel = discord.SlashOption(name="modlog_channel",
                                                                                         description="Channel for log of timeouts, bans, etc.",
                                                                                         required=False),
                          rep_enabled: bool = discord.SlashOption(name="rep_enabled",
                                                                  description="Enable the reputation system?",
                                                                  required=False)):
    if not await isModerator(interaction.user):
        await interaction.send("You are not authorized to perform this action", ephemeral=True)
        return
    await interaction.response.defer()
    if modlog_channel:
        gpdb.set_pref('modlog_channel', modlog_channel.id, interaction.guild.id)
    if rep_enabled:
        gpdb.set_pref('rep_enabled', rep_enabled, interaction.guild.id)
    await interaction.send("Done.")


@bot.slash_command(description="Timeout a user (for mods)")
async def timeout(interaction: discord.Interaction,
                  user: discord.User = discord.SlashOption(name="user", description="User to timeout",
                                                           required=True),
                  time_: str = discord.SlashOption(name="duration",
                                                   description="Duration of timeout (e.g. 1d5h) up to 28 days (use 'permanent')",
                                                   required=True),
                  reason: str = discord.SlashOption(name="reason", description="Reason for timeout", required=True)):
    action_type = "Timeout"
    mod = interaction.user.mention
    if not await isModerator(interaction.user):
        await interaction.send(f"Sorry {mod}, you don't have the permission to perform this action.", ephemeral=True)
        return
    await interaction.response.defer()
    if time_.lower() == "unspecified" or time_.lower() == "permanent" or time_.lower() == "undecided":
        seconds = 86400 * 28
    else:
        seconds = 0
        if "d" in time_:
            seconds += int(time_.split("d")[0]) * 86400
            time_ = time_.split("d")[1]
        if "h" in time_:
            seconds += int(time_.split("h")[0]) * 3600
            time_ = time_.split("h")[1]
        if "m" in time_:
            seconds += int(time_.split("m")[0]) * 60
            time_ = time_.split("m")[1]
        if "s" in time_:
            seconds += int(time_.split("s")[0])
    if seconds == 0:
        await interaction.send("You can't timeout for zero seconds!", ephemeral=True)
        return
    await user.edit(timeout=discord.utils.utcnow() + datetime.timedelta(seconds=seconds))
    human_readable_time = f"{seconds // 86400}d {(seconds % 86400) // 3600}h {(seconds % 3600) // 60}m {seconds % 60}s"
    ban_msg_channel = bot.get_channel(gpdb.get_pref("modlog_channel", interaction.guild.id))
    if ban_msg_channel:
        last_ban_msg = await ban_msg_channel.history(limit=1).flatten()
        case_no = int(''.join(list(filter(str.isdigit, last_ban_msg[0].content.splitlines()[0])))) + 1
        ban_msg = f"""Case #{case_no} | [{action_type}]
Username: {user.name}#{user.discriminator} ({user.id})
Moderator: {mod} 
Reason: {reason}
Duration: {human_readable_time}
Until: <t:{int(time.time()) + seconds}> (<t:{int(time.time()) + seconds}:R>)"""
        await ban_msg_channel.send(ban_msg)
    await interaction.send(
        f"{user.name}#{user.discriminator} has been put on time out until <t:{int(time.time()) + seconds}>, which is <t:{int(time.time()) + seconds}:R>.")


@bot.slash_command(description="Untimeout a user (for mods)")
async def untimeout(interaction: discord.Interaction,
                    user: discord.User = discord.SlashOption(name="user", description="User to untimeout",
                                                             required=True)):
    action_type = "Remove Timeout"
    mod = interaction.user.mention
    if not await isModerator(interaction.user):
        await interaction.send(f"Sorry {mod}, you don't have the permission to perform this action.", ephemeral=True)
        return
    await user.edit(timeout=None)
    ban_msg_channel = bot.get_channel(gpdb.get_pref("modlog_channel", interaction.guild.id))
    if ban_msg_channel:
        last_ban_msg = await ban_msg_channel.history(limit=1).flatten()
        case_no = int(''.join(list(filter(str.isdigit, last_ban_msg[0].content.splitlines()[0])))) + 1
        ban_msg = f"""Case #{case_no} | [{action_type}]
Username: {user.name}#{user.discriminator} ({user.id})
Moderator: {mod}"""
        await ban_msg_channel.send(ban_msg)
    await interaction.send(f"Timeout has been removed from {user.name}#{user.discriminator}.")


@bot.slash_command(description="Ban a user from the server (for mods)")
async def ban(interaction: discord.Interaction,
              user: discord.User = discord.SlashOption(name="user", description="User to ban",
                                                       required=True),
              reason: str = discord.SlashOption(name="reason", description="Reason for ban", required=True)):
    action_type = "Ban"
    mod = interaction.user.mention
    if not await isModerator(interaction.user):
        await interaction.send(f"Sorry {mod}, you don't have the permission to perform this action.", ephemeral=True)
        return
    try:
        if interaction.guild.id == 576460042774118420:  # r/igcse
            await user.send(
                f"Hi there from {interaction.guild.name}. You have been banned from the server due to '{reason}'. If you feel this ban was done in error, to appeal your ban, please fill the form below.\nhttps://forms.gle/8qnWpSFbLDLdntdt8")
        else:
            await user.send(
                f"Hi there from {interaction.guild.name}. You have been banned from the server due to '{reason}'.")
    except:
        pass
    ban_msg_channel = bot.get_channel(gpdb.get_pref("modlog_channel", interaction.guild.id))
    if ban_msg_channel:
        last_ban_msg = await ban_msg_channel.history(limit=1).flatten()
        case_no = int(''.join(list(filter(str.isdigit, last_ban_msg[0].content.splitlines()[0])))) + 1
        ban_msg = f"""Case #{case_no} | [{action_type}]
Username: {user.name}#{user.discriminator} ({user.id})
Moderator: {mod} 
Reason: {reason}"""
        await ban_msg_channel.send(ban_msg)
    await interaction.guild.ban(user, delete_message_days=1)
    await interaction.send(f"{user.name}#{user.discriminator} has been banned.")


@bot.slash_command(description="Ban a user from the server (for mods)")
async def unban(interaction: discord.Interaction,
                user: int = discord.SlashOption(name="user_id", description="Id of the user to unban",
                                                required=True)):
    action_type = "Unban"
    mod = interaction.user.mention
    if not await isModerator(interaction.user):
        await interaction.send(f"Sorry {mod}, you don't have the permission to perform this action.", ephemeral=True)
        return

    bans = await interaction.guild.bans()
    for ban in bans:
        if ban.user.id == user:
            await interaction.guild.unban(ban.user)
            await interaction.channel.send(f"{ban.user.name}#{ban.user.discriminator} has been unbanned.")

            ban_msg_channel = bot.get_channel(gpdb.get_pref("modlog_channel", interaction.guild.id))
            if ban_msg_channel:
                last_ban_msg = await ban_msg_channel.history(limit=1).flatten()
                case_no = int(''.join(list(filter(str.isdigit, last_ban_msg[0].content.splitlines()[0])))) + 1
                ban_msg = f"""Case #{case_no} | [{action_type}]
Username: {ban.user.name}#{ban.user.discriminator} ({ban.user.id})
Moderator: {mod}"""
                await ban_msg_channel.send(ban_msg)
            return


@bot.slash_command(description="Kick a user from the server (for mods)")
async def kick(interaction: discord.Interaction,
               user: discord.User = discord.SlashOption(name="user", description="User to kick",
                                                        required=True),
               reason: str = discord.SlashOption(name="reason", description="Reason for kick", required=True)):
    action_type = "Kick"
    mod = interaction.user.mention
    if not await isModerator(interaction.user):
        await interaction.send(f"Sorry {mod}, you don't have the permission to perform this action.", ephemeral=True)
        return
    try:
        await user.send(
            f"Hi there from {interaction.guild.name}. You have been kicked from the server due to '{reason}'.")
    except:
        pass
    ban_msg_channel = bot.get_channel(gpdb.get_pref("modlog_channel", interaction.guild.id))
    if ban_msg_channel:
        last_ban_msg = await ban_msg_channel.history(limit=1).flatten()
        case_no = int(''.join(list(filter(str.isdigit, last_ban_msg[0].content.splitlines()[0])))) + 1
        ban_msg = f"""Case #{case_no} | [{action_type}]
Username: {user.name}#{user.discriminator} ({user.id})
Moderator: {mod} 
Reason: {reason}"""
        await ban_msg_channel.send(ban_msg)
    await interaction.guild.kick(user)
    await interaction.send(f"{user.name}#{user.discriminator} has been kicked.")


# Study Sessions


@bot.slash_command(description="Start a study session", guild_ids=[GUILD_ID])
async def study_session(interaction: discord.Interaction):
    try:
        role = interaction.guild.get_role(study_roles[interaction.channel.id])
    except:
        await interaction.send(
            "Please use this command in the subject channel of the subject you're starting a study session for.",
            ephemeral=True)
    study_sesh_channel = bot.get_channel(941276796937179157)
    msg_history = await study_sesh_channel.history(limit=3).flatten()
    for msg in msg_history:
        if (str(interaction.user.mention) in msg.content or str(role.mention) in msg.content) and \
                (msg.created_at.replace(tzinfo=None) + datetime.timedelta(minutes=60) > datetime.datetime.utcnow()):
            await interaction.send(
                "Please wait until one hour after your previous ping or after a study session in the same subject to start a new study session.",
                ephemeral=True)
            return
    voice_channel = interaction.user.voice
    if voice_channel is None:
        await interaction.send("You must be in a voice channel to use this command.", ephemeral=True)
    else:
        await study_sesh_channel.send(
            f"{role.mention} - Requested by {interaction.user.mention} - Please join {voice_channel.channel.mention}")
        await interaction.send(
            f"Started a {role.name.lower().replace(' study ping', '').title()} study session at {voice_channel.channel.mention}.")
        await voice_channel.channel.edit(
            name=f"{role.name.lower().replace(' study ping', '').title()} Study Session")


bot.run(TOKEN)
