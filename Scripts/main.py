import os, asyncio, random, discord, json, requests, re, datetime
from dotenv import load_dotenv
from discord.ext import commands
import utils
from CFListScraper import ScrapeList
import RanklistCreator as rl
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

bot = commands.Bot(command_prefix='cp!')
cf_scraper = ScrapeList()
@bot.event
async def on_ready():
    print(f'{bot.user.name} has connected to Discord!!!')

@bot.command(name='test', help='Simple command for testing if the bot is active!!')
async def test_bot(ctx):
    await ctx.send(f'Hello human! BEEP BEEP BOOP BOOP')

@bot.command(name='create-channel',help='Creates a channel in you Discord server if it does not exist. (Works only for admin mode)')
@commands.has_role('admin')
async def create_channel(ctx, channel_name: str):
    guild_name = ctx.guild
    existing_channel = discord.utils.get(guild_name.channels, name=channel_name)
    if existing_channel:
        await ctx.send(f'The channel {channel_name} already exists.')
        print(f'The channel {channel_name} already exists.')
    else:
        print(f'Creating a new channel: {channel_name}')
        await guild_name.create_text_channel(channel_name)
        await ctx.send(f'New channel {channel_name} created.')

@bot.event
async def on_command_error(ctx,error):
    if isinstance(error, commands.errors.CheckFailure):
        await ctx.send('You do not have the correct role for this command.')

# ~~~~~~~ CODEFORCES ~~~~~~~~~~~
###### Creating Coroutines for User Info#############

@bot.command(name='info', help='Displays user\'s info on Codeforces.')
async def user_info(ctx, handle) :
    url = f' https://codeforces.com/api/user.info?handles={handle}'
    obj = requests.get(url)
    data = json.loads(obj.text)

    if data['status']=="FAILED":
        await ctx.send(f'{data["comment"]}')
        return
    
    pic = "https:" + data['result'][0]['titlePhoto']
    rating = data['result'][0]['rating']
    colour, rank = utils.get_rank(rating)
    embed = discord.Embed(title=f'{handle}', description=f'{data["result"][0]["organization"]} {data["result"][0]["city"]} {data["result"][0]["country"]}', colour=colour)
    embed.add_field(name=f'{rating} ({rank})', value=f'Max Rating : {data["result"][0]["maxRating"]}', inline=False)
    embed.set_image(url=pic)
    await ctx.channel.send(embed=embed)

@bot.command(name='blog', help='Displays user\'s latest 5 blogs within a given upvotes/date range alongwith the tags related to them.', usage='handle [u>=upvotes] [u<=upvotes] [d>=[[dd]mm]yyyy] [d<[[dd]mm]yyyy] [+tags...]')
async def user_blogs(ctx, handle, *args) :
    url = f'https://codeforces.com/api/user.blogEntries?handle={handle}'
    obj = requests.get(url)
    data = json.loads(obj.text)
    url = f'https://codeforces.com/api/user.info?handles={handle}'
    obj = requests.get(url)
    data2 = json.loads(obj.text)

    if data['status'] == "FAILED" or data2['status'] == "FAILED":
        await ctx.send(f'{data["comment"]}')
    elif len(data['result']) == 0:
        await ctx.send(f'{handle} has written no blogs.')
    else:
        pic = "https:" + data2['result'][0]['titlePhoto']
        rat_ub, rat_lb = 5000, -5000
        date_ub, date_lb = datetime.datetime.now(), datetime.datetime(2000, 1, 1)
        tags = []

        for arg in args:
            if arg[0:1] == '+' :
                tags.append(arg[1:])
            elif len(arg) <= 3 :
                await ctx.send('Invalid parameters. Please try again with correct parameters.')
                return
            elif arg[0:3] == 'u>=' :
                if utils.isValidInteger(arg[3:]) == False :
                    await ctx.send('The upvotes range should be an integer.')
                    return
                else :
                    rat_lb = max(rat_lb, int(arg[3:]))
            elif arg[0:3] == 'u<=' :
                if utils.isValidInteger(arg[3:]) == False :
                    await ctx.send('The upvotes range should be an integer.')
                    return
                else :
                    rat_ub = min(rat_ub, int(arg[3:]))
            elif arg[0:3] == 'd>=':
                if utils.isValidDate(arg[3:]) == False:
                    await ctx.send('The date should in DDMMYYYY or MMYYYY or YYYY format.')
                    return
                else :
                    date_lb = max(utils.isValidDate(arg[3:]), date_lb)
            elif arg[0:2] == 'd<' :
                if utils.isValidDate(arg[2:]) == False:
                    await ctx.send('The date should in DDMMYYYY or MMYYYY or YYYY format.')
                    return
                else :
                    date_ub = min(utils.isValidDate(arg[2:]), date_ub)
            else:
                await ctx.send('Invalid parameters. Please try again with correct parameters.')
                return

        stop_id, var = data['result'][-1]['id'], 0
        ans = []
        while(1):
            latest_blog = data['result'][var]
            blog_date = datetime.datetime.fromtimestamp(latest_blog['creationTimeSeconds'])
            if latest_blog['rating'] <= rat_ub and latest_blog['rating'] >= rat_lb and blog_date >= date_lb and blog_date <= date_ub :
                if len(tags) > 0 :
                    blg = utils.tag_match(tags, latest_blog)
                    if blg != False and blg not in ans:
                        ans.append(blg)
                else :
                    ans.append(latest_blog)
            if(data['result'][var]['id'] == stop_id):
                break
            var = var + 1
        
        var = 0
        if len(ans) == 0 :
            embed = discord.Embed(title=f'Error.', color=0x000000)
            embed.add_field(name=f'Invalid parameters', value=f'There are no blogs present in your given range of {handle}.', inline=False)
            await ctx.channel.send(embed=embed)
        else :
            embed = discord.Embed(title=f'{handle}\'s latest blog list :', color=0x000000)
            embed.set_thumbnail(url=pic)
            for blog in ans:
                lat_blog = f'https://codeforces.com/blog/entry/{blog["id"]}'
                title = re.sub(r'<.*?>', '', blog['title'])
                date = datetime.datetime.fromtimestamp(blog['creationTimeSeconds'])
                var = var+1
                embed.add_field(name=f'{var}. {title}', value=f'Upvotes={blog["rating"]}, Date : {date.strftime("%d/%m/%Y")}, [Link of the blog]({lat_blog})', inline=False)
                if(var==5):
                    break
            
            await ctx.channel.send(embed=embed)

@bot.command(name='stalk', help='Displays user\'s latest solved problems.', usage='handle id [+contest] [+practice] [+unofficial] [+virtual]')
async def user_ques(ctx, handle, *args):
    url = f'https://codeforces.com/api/user.status?handle={handle}&from=1'
    obj = requests.get(url)
    data = json.loads(obj.text)
    if data['status'] == "FAILED":
        await ctx.send(f'{data["comment"]}')
        return
    elif len(data['result']) == 0:
        await ctx.send(f'{handle} has made no submissions yet.')
        return

    official, virtual, practice, unoff = False, False, False, False
    var = 0
    embeds, val = [], ''
    ques = []

    for arg in args:
        if arg == '+contest':
            official = True
        elif arg == '+virtual':
            virtual = True
        elif arg == '+practice':
            practice = True
        elif arg == '+unofficial':
            unoff = True
        else :
            await ctx.send('Invalid arguments. Please enter correct arguments and then try again.')
            return

    for prob in data['result']:
        idx = str(prob['contestId']) + prob['problem']['index']
        part = prob["author"]["participantType"]
        check = utils.check_status(official, virtual, practice, unoff, part)
        if prob['verdict'] == 'OK' and check == 1 and idx not in ques:
            if var%10==0 :
                embed = discord.Embed(color=0x000000)
            url = 'https://codeforces.com/problemset/problem/'
            url += str(prob['contestId'])
            url += '/'
            url += prob["problem"]["index"]
            ques.append(idx)
            if 'rating' not in prob["problem"]:
                rat = '?'
            else :
                rat = prob['problem']['rating']
            tmp = f'[({prob["contestId"]}{prob["problem"]["index"]}) {prob["problem"]["name"]}]({url}) [{rat}]\n'
            val += tmp
            var = var + 1
            if var%10==0 :
                embed.add_field(name=f'{handle}\'s latest Accepted solutions :', value=val, inline=True)
                val = ''
                embeds.append(embed)
            if var == 100:
                break
    
    if var == 0:
        await ctx.send(f'{handle} has not yet submitted a correct solution in the given range.')
        return

    if var%10 != 0 :
        embed.add_field(name=f'{handle}\'s latest Accepted solutions :', value=val, inline=False)
        embeds.append(embed)
    
    i = 0
    for embed in embeds:
        embed.set_footer(text=f'\nPage : {i+1}/{len(embeds)}')
        i += 1
    message = await ctx.channel.send(embed=embeds[0])
    emojis = ['\u23ee', '\u25c0', '\u25b6', '\u23ed']
    for emoji in emojis:
        await message.add_reaction(emoji)

    i, emoji = 0, ''
    while True :
        if emoji == '\u23ee' :
            i = 0
            await message.edit(embed = embeds[i])
        if emoji == '\u25c0' :
            if i > 0 :
                i = i - 1
                await message.edit(embed=embeds[i])
        if emoji == '\u25b6' :
            if i < len(embeds) - 1 :
                i = i + 1
                await message.edit(embed=embeds[i])
        if emoji == '\u23ed' :
            i = len(embeds) - 1
            await message.edit(embed=embeds[i])
        
        def predicate(message):
            def check(reaction, user):
                if reaction.message.id != message.id or user == bot.user:
                    return False
                for em in emojis :
                    if reaction.emoji == em :
                        return True
                return False
            return check
        
        try:
            react, user = await bot.wait_for('reaction_add', timeout=15, check=predicate(message))
        except asyncio.TimeoutError:
            break
        emoji = str(react)
        await message.remove_reaction(emoji, member=user)

    for emoji in emojis:
        await message.clear_reaction(emoji)

@bot.command(name='gimme', help='Displays a random problem of a given tag within a rating range.', usage='tag [lower [upper]]')
async def user_contest(ctx, tag, *args):
    tag = tag.replace('-', '%20')
    print(tag)
    url = f'https://codeforces.com/api/problemset.problems?tags={tag}'
    obj = requests.get(url)
    data = json.loads(obj.text)
    if data['status'] == "FAILED":
        await ctx.send(f'{data["comment"]}')
        return
    elif len(data['result']['problems']) == 0:
        await ctx.send(f'{tag} is not a valid tag on Codeforces.')
        return

    rat_lb, rat_ub = 0, 5000
    var = 0
    for arg in args :
        if var == 2 :
            await ctx.send('There should be at most two integers specifying the rating range.')
            return
        if utils.isValidInteger(arg) == False :
            await ctx.send('The rating range should be in integer format only.')
            return
        arg = utils.isValidInteger(arg)
        var = var + 1
        if var == 1 :
            rat_lb = max(rat_lb, arg)
        if var == 2 :
            rat_ub = min(rat_ub, arg)

    problems = []
    for prob in data['result']['problems'] :
        if 'rating' not in prob:
            continue
        else :
            if prob['rating'] >= rat_lb and prob['rating'] <= rat_ub :
                problems.append(prob)

    if len(problems) == 0 :
        await ctx.send('No problem fit within your given rating range.')
        return

    rand_prob = random.choice(problems)

    url = f'https://codeforces.com/api/contest.standings?contestId={rand_prob["contestId"]}&from=1&count=1&showUnofficial=true'
    obj = requests.get(url)
    data = json.loads(obj.text)
    name = data['result']['contest']['name']
    url = f'https://codeforces.com/contest/{rand_prob["contestId"]}/problem/{rand_prob["index"]}'

    embed = discord.Embed(description=f'[{rand_prob["contestId"]}{rand_prob["index"]}. {rand_prob["name"]}]({url})', color=0x000000)
    embed.add_field(name=f'{name}', value=f'Rating : {rand_prob["rating"]}', inline=False)   
    await ctx.channel.send(embed=embed)


######################################################


###### Creating coroutines for standings by use of lists ########

@bot.command(name='ranklist',help='Displays the standings along with rating changes of the users in a list specified by user (Shows at max 17 positions)')
async def disp_ranklist(ctx,contest_id: str='',key:str=''):
    handles=''
    if(contest_id==''):
        await ctx.send("Enter a contest id")
        return
    if(key!=''):
        handles = cf_scraper.list_scrape(key)
        STANDINGS_URL=f'https://codeforces.com/api/contest.standings?contestId={contest_id}&handles={handles}&showUnofficial=true'
        STANDINGS_URL_OFF=f'https://codeforces.com/api/contest.standings?contestId={contest_id}&handles={handles}&showUnofficial=false'
        obj = requests.get(STANDINGS_URL)
        objoff = requests.get(STANDINGS_URL_OFF)
    else:
        STANDINGS_URL=f'https://codeforces.com/api/contest.standings?contestId={contest_id}&from=1&count=16&showUnofficial=true'
        STANDINGS_URL_OFF=f'https://codeforces.com/api/contest.standings?contestId={contest_id}&from=1&count=16&showUnofficial=false'
        obj = requests.get(STANDINGS_URL)
        objoff = requests.get(STANDINGS_URL_OFF)
        handles='yay'
    print(handles)
    if(handles==''):
        await ctx.send("Such a list does not exist")
        return
    temp = json.loads(obj.text)
    temp2 = json.loads(objoff.text)
    print("reached here")
    if(temp['status']=="FAILED"):
        await ctx.send(f'{temp["comment"]}')
    elif(temp2['status']=="FAILED"):
        await ctx.send(f'{temp2["comment"]}')
    elif len(temp['result'])==0:
        await ctx.send(f'No data available to display')
    else:
        print("entered in here")
        ans = rl.create_ranklist(temp,temp2)
        print(ans)
        await ctx.send(ans)




###########################################################


###### Coroutines for rating changes ###################

#####################################################

########### Coroutines for problemset ###############

###################################################

############ Coroutines for contest lists ###############


###############################################

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

bot.run(TOKEN)
