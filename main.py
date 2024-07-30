import pymysql
import discord
from discord import app_commands
from discord.ext import commands

host = ''
user = ''
password = ''
database = ''

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)
is_client_running = False

tree = app_commands.CommandTree(client)


@client.event
async def on_ready():
    global is_client_running

    if not is_client_running:
        await tree.sync(guild=discord.Object(id=))
        print(f'{client.user} has connected to Discord!')
        await client.change_presence(activity=discord.Game(name="Beta Testing"))


@tree.command(name='setup', description='Setup with the bot', guild=discord.Object(id=))
async def setup(interaction, name: str):
    try:
        id = interaction.user.id
        connection = pymysql.connect(host=host, user=user, password=password, database=database)
        cur = connection.cursor()

        cur.execute("""SELECT EXISTS (SELECT * FROM users WHERE id = %s)""", (id,))
        id_check = cur.fetchall()
        cur.execute("""SELECT EXISTS (SELECT * FROM users WHERE username = %s)""", (name,))
        name_check = cur.fetchall()

        if id_check[0][0] != 1 and name_check[0][0] != 1:
            cur.execute("""INSERT INTO users (id, username, points) VALUES (%s, %s, %s)""", (id, name, 0))
            connection.commit()
            connection.close()
            await interaction.response.send_message('User added', ephemeral=True)
        else:
            await interaction.response.send_message('User or username already exists', ephemeral=True)
    except Exception as e:
        print(e)


@tree.command(name='seestore', description='Inspect the store',
              guild=discord.Object(id=))
@commands.cooldown(rate=1, per=300, type=commands.BucketType.user)
async def seestore(interaction):
    try:
        z = []
        await interaction.response.defer()
        connection = pymysql.connect(host=host, user=user, password=password, database=database)
        cur = connection.cursor()
        cur.execute("""SELECT * FROM `store` WHERE owner IS NULL""")
        output = cur.fetchall()

        for j in range(len(output)):
            outputstr = (
                    'Name: ' + output[j][0] + ', Rarity: ' + output[j][1] + ', Price: ' + str(output[j][2]) + ' points')
            z.append(outputstr)

        for i in range(len(z)):
            await interaction.channel.send(z[i])
        connection.close()
        await interaction.followup.send('ASTRAL MERCHANT:')
    except Exception as e:
        print(e)


@seestore.error
async def command_name_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        em = discord.Embed(title=f"Command slowed", description=f"Try again in {error.retry_after:.2f}s.")
        await ctx.send(embed=em)


@tree.command(name='seeitem', description='Inspect an item',
              guild=discord.Object(id=))
async def viewitem(interaction, name: str):
    try:
        connection = pymysql.connect(host=host, user=user, password=password, database=database)
        cur = connection.cursor()
        cur.execute("""SELECT EXISTS (SELECT * FROM TheLootersTable WHERE name = %s)""", (name,))
        item_check = cur.fetchall()

        if item_check[0][0] != 0:
            cur.execute("""SELECT * FROM `TheLootersTable` WHERE `name` = %s""", (name,))
            output = cur.fetchall()

            if output[0][1] == 'C':
                rarity = 'Common'
            elif output[0][1] == 'U':
                rarity = 'Uncommon'
            elif output[0][1] == 'R':
                rarity = 'Rare'
            elif output[0][1] == 'V':
                rarity = 'Very Rare'
            else:
                rarity = 'Legendary'
            outputstr = ('Name: ' + str(output[0][0]) + ', Rarity: ' + rarity + ', Price: ' + str(
                output[0][2]) + ', URL: ' + str(output[0][4]))
            connection.close()
            await interaction.response.send_message(outputstr, ephemeral=True)
        else:
            await interaction.response.send_message('Item does not exist, try again', ephemeral=True)
    except Exception as e:
        print(e)


@tree.command(name='addpoint', description='(STAFF) Add a point to a user',
              guild=discord.Object(id=))
@app_commands.checks.has_role('staff')
async def addpoint(interaction, name: str, amount: int):
    try:
        connection = pymysql.connect(host=host, user=user, password=password, database=database)
        cur = connection.cursor()
        cur.execute("""SELECT EXISTS (SELECT * FROM users WHERE username = %s)""", (name,))
        name_check = cur.fetchall()

        if name_check[0][0] == 1:
            cur.execute("""UPDATE users SET points = points + %s WHERE username=%s""", (amount, name,))
            connection.commit()
            connection.close()
            await interaction.response.send_message('Point(s) added', ephemeral=True)
        else:
            connection.close()
            await interaction.response.send_message('Username does not exist', ephemeral=True)
    except Exception as e:
        print(e)


@tree.command(name='buyitem', description='Purchase an item from the store',
              guild=discord.Object(id=))
async def buyitem(interaction, itemname: str):
    try:
        connection = pymysql.connect(host=host, user=user, password=password, database=database)
        cur = connection.cursor()

        cur.execute("""SELECT points from users WHERE id = %s""", (str(interaction.user.id, )))
        user_points = cur.fetchall()

        cur.execute("""SELECT price from store WHERE name = %s""", (str(itemname, )))
        item_cost = cur.fetchall()

        cur.execute("""SELECT owner from TheLootersTable WHERE name = %s""", (str(itemname, )))
        item_owner = cur.fetchall()

        cur.execute("""SELECT username from users WHERE id = %s""", (str(interaction.user.id, )))
        user_name = cur.fetchall()

        if len(item_cost) == 0:
            connection.close()
            await interaction.response.send_message('Item does not exist or is not in the store', ephemeral=True)
        elif item_owner[0][0] is not None:
            connection.close()
            await interaction.response.send_message('Item has already been purchased', ephemeral=True)
        elif item_cost[0][0] > user_points[0][0]:
            connection.close()
            await interaction.response.send_message('User does not have enough points to purchase', ephemeral=True)
        else:
            cur.execute("""UPDATE TheLootersTable SET owner = %s WHERE name = %s""", (user_name[0][0], str(itemname),))
            connection.commit()
            cur.execute("""UPDATE store SET owner = %s WHERE name = %s""", (user_name[0][0], str(itemname),))
            connection.commit()
            cur.execute("""UPDATE users SET points = points - %s WHERE id = %s""",
                        (item_cost[0][0], (str(interaction.user.id, )),))
            connection.commit()
            connection.close()
            await interaction.channel.send(str(user_name[0][0] + ' has purchased ' + str(itemname) + '!'))
            await interaction.response.send_message('Item has been purchased', ephemeral=True)
    except Exception as e:
        print(e)


@tree.command(name='myitems', description='View items you have purchased',
              guild=discord.Object(id=))
async def myitems(interaction):
    try:
        z = []
        connection = pymysql.connect(host=host, user=user, password=password, database=database)
        cur = connection.cursor()

        cur.execute("""SELECT username from users WHERE id = %s""", (str(interaction.user.id, )))
        user_name = cur.fetchall()
        if len(user_name) != 0:
            cur.execute("""SELECT username from users WHERE id = %s""", (str(interaction.user.id, )))
            user_name = cur.fetchall()

            cur.execute("""SELECT name from TheLootersTable WHERE owner = %s""", (user_name[0][0],))
            personal_items = cur.fetchall()

            for i in range(len(personal_items)):
                z.append(personal_items[i][0])
            connection.close()
            await interaction.response.send_message(z, ephemeral=True)
        else:
            connection.close()
            await interaction.response.send_message('User does not exist, please run /setup to join the market',
                                                    ephemeral=True)
    except Exception as e:
        print(e)


@tree.command(name='resetshop', description='(STAFF) Update the contents of the shop',
              guild=discord.Object(id=))
@app_commands.checks.has_role('staff')
async def randtest(interaction, areyousure: str):
    try:
        connection = pymysql.connect(host=host, user=user, password=password, database=database)
        cur = connection.cursor()
        cur.execute("""DELETE FROM store""")
        connection.commit()
        cur.execute(
            """INSERT INTO store SELECT * FROM TheLootersTable WHERE rarity=%s AND owner IS NULL ORDER BY RAND () LIMIT 5""",
            'C', )
        connection.commit()
        cur.execute(
            """INSERT INTO store SELECT * FROM TheLootersTable WHERE rarity=%s AND owner IS NULL ORDER BY RAND () LIMIT 4""",
            'U', )
        connection.commit()
        cur.execute(
            """INSERT INTO store SELECT * FROM TheLootersTable WHERE rarity=%s AND owner IS NULL ORDER BY RAND () LIMIT 3""",
            'R', )
        connection.commit()
        cur.execute(
            """INSERT INTO store SELECT * FROM TheLootersTable WHERE rarity=%s AND owner IS NULL ORDER BY RAND () LIMIT 2""",
            'V', )
        connection.commit()
        cur.execute(
            """INSERT INTO store SELECT * FROM TheLootersTable WHERE rarity=%s AND owner IS NULL ORDER BY RAND () LIMIT 2""",
            'L', )
        connection.commit()
        connection.close()
        await interaction.response.send_message('SHOP REFRESHED', ephemeral=True)
    except Exception as e:
        print(e)


@tree.command(name='whoami', description='View details about your market data',
              guild=discord.Object(id=))
async def whoami(interaction):
    try:
        connection = pymysql.connect(host=host, user=user, password=password, database=database)
        cur = connection.cursor()
        cur.execute("""SELECT username from users WHERE id = %s""", (str(interaction.user.id, )))
        user_name = cur.fetchall()
        if len(user_name) != 0:
            cur.execute('SELECT * FROM users WHERE id = %s', (str(interaction.user.id, )))
            output = cur.fetchall()
            outputstr = ('Name: ' + str(output[0][1]) + ', Points: ' + str(output[0][2]))
            connection.close()
            await interaction.response.send_message(outputstr, ephemeral=True)
        else:
            connection.close()
            await interaction.response.send_message('User does not exist, please run /setup to join the market',
                                                    ephemeral=True)
    except Exception as e:
        print(e)


@tree.command(name='seeusers', description='(STAFF) Get user list',
              guild=discord.Object(id=))
@app_commands.checks.has_role('staff')
async def seeusers(interaction):
    try:
        z = []
        await interaction.response.defer()
        connection = pymysql.connect(host=host, user=user, password=password, database=database)
        cur = connection.cursor()
        cur.execute("""SELECT * FROM `users`""")
        output = cur.fetchall()

        for j in range(len(output)):
            outputstr = (
                    'User: ' + output[j][1] + ', Points: ' + str(output[j][2]))
            z.append(outputstr)

        userlist = await interaction.user.create_dm()
        await userlist.send('----')
        for i in range(len(z)):
            await userlist.send(z[i])
        connection.close()
        await interaction.followup.send('User list sent')
    except Exception as e:
        print(e)


intents = discord.Intents.default()
intents.message_content = True

client.run('')
