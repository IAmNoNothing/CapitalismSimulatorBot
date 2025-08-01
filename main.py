import discord
import database
from discord.ext import commands
from discord import Member
import tabulate

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix='!', intents=intents)
teefia_id = 1220275992778506290
kiuwny_id = 668047136964870165

db = database.Database('bot.db')

async def update_users():
    guild = bot.get_guild(teefia_id)
    if guild is None:
        print("Guild not found, wtf")
        return

    await guild.chunk()

    db.update_user_ids([user.id for user in guild.members])
    print("User database updated")

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    await update_users()

@bot.command()
async def balance(ctx, member: Member = None):
    member = member or ctx.author
    user_id = member.id

    _balance, error = db.get_balance(user_id)

    if error is not None:
        await ctx.send(f"Помилка: {error}")
        return

    await ctx.send(f"Баланс користувача {member.display_name}: {_balance}")

@bot.command()
async def update(ctx):
    if ctx.author.guild_permissions.administrator or ctx.author.id == kiuwny_id:
        await update_users()
        await ctx.send("База даних оновлена.")
    else:
        await ctx.send("Ви не маєте прав для виконання цієї команди.")

@bot.command()
async def create_item(ctx, item_name, amount = 1, member: Member = None):
    if ctx.author.guild_permissions.administrator or ctx.author.id == kiuwny_id:
        member = member or ctx.author
        db.create_item(member.id, item_name, amount)
        await ctx.send(f"Предмет {item_name} створено.")
    else:
        await ctx.send("Ви не маєте прав для виконання цієї команди.")

@bot.command()
async def delete_item(ctx, item_name, member: Member = None):
    if ctx.author.guild_permissions.administrator or ctx.author.id == kiuwny_id:
        member = member or ctx.author
        db.delete_item(member.id, item_name)
        await ctx.send(f"Предмет {item_name} видалено.")
    else:
        await ctx.send("Ви не маєте прав для виконання цієї команди.")

@bot.command()
async def inventory(ctx, member: Member = None):
    member = member or ctx.author
    items = db.get_inventory(member.id)
    if items:
        items_str = '\n'.join(f" - {item[0]}: {item[1]}" for item in items)
        await ctx.send(f"Інвентар користувача {member.display_name}:\n{items_str}")
    else:
        await ctx.send(f"Інвентар користувача {member.display_name} порожній.")

@bot.command()
async def auction(ctx, member: Member = None, item=None, min_price=None, max_price=None, min_amount=None):
    member_id = member.id if member else None
    _auction = db.get_auction(member_id, item, min_price, max_price, min_amount)

    if _auction:
        if ctx.guild is None:
            await ctx.send("Сервер не знайдено, спробуйте (!update)")
            return
        headers = ["ID", "Продавець", "Предмет", "Кількість", "Ціна"]
        rows = [[_id, ctx.guild.get_member(user_id).display_name, _item, amount, price] for _id, user_id, _item, amount, price in _auction]
        auction_str = tabulate.tabulate(rows, headers=headers, tablefmt="pipe")
        await ctx.send(f"Аукціон:\n```plaintext\n{auction_str}```")
    else:
        await ctx.send("Аукціон пустий.")

@bot.command()
async def sell(ctx, item=None, amount=None, price=None):
    if item is None or amount is None or price is None:
        await ctx.send("Ви повинні вказати предмет, кількість і ціну.")
        return

    item_amount = db.get_user_item_count(ctx.author.id, item)
    if item_amount == 0:
        await ctx.send("У вас немає такого предмету.")
        return

    if int(amount) > item_amount:
        await ctx.send("У вас замало цього предмету.")
        return

    db.put_item_on_auction(ctx.author.id, item, amount, price)
    await ctx.send(f"Предмет {amount} шт. {item} поставлено на аукціон за {price} кредитів за штуку.")

@bot.command()
async def buy(ctx, auction_id=None, amount=None):
    result = db.buy_from_auction(ctx.author.id, int(auction_id), int(amount))

    if result is None:
        await ctx.send("Немає такого лоту.")
        return

    user_id, item, amount, price = result
    await ctx.send(f"Ви купили {amount} шт. {item} за {price} кредитів за штуку.")

@bot.command()
async def insert_liquidity(ctx, amount):
    if ctx.author.id == kiuwny_id or ctx.author.guild_permissions.administrator:
        db.insert_liquidity(int(amount))
        await ctx.send(f"Економіка отримала {amount} кредитів.")
    else:
        await ctx.send("Ви не маєте прав для виконання цієї команди.")

@bot.command()
async def liquidity(ctx):
    _liqd = db.get_liquidity()
    await ctx.send(f"Економіка всього має {_liqd[0]} кредитів, розподілених між {_liqd[1]} користувачами.")

with open('token.txt', 'r') as f:
    token = f.read()

bot.run(token)
