import asyncio
from operator import truediv

import cloudscraper,dotenv,os, discord
from datetime import datetime, timezone, timedelta
from fake_useragent import UserAgent
dotenv.load_dotenv()
bot = discord.Bot()

locations = {"Wads" :"64b9990ec625af0685fb939d", "McNair":"64a6b628351d5305dde2bc08", "DHH" :"64e3da15e45d430b80c9b981"}
bloat = ["Salad Bar", "Made to Order Deli", "Rice It Up", "Deli", "Salad", "House of Green", "Fifth & Fresh"]
scraper = cloudscraper.create_scraper()
ua = UserAgent()


class Period:
    def __init__(self, periodName, periodKey):
        self.periodName = periodName
        self.periodKey = periodKey
    def fetchPeriodKey(self):
        return self.periodKey

class Location:
    def __init__(self, locationName, locationKey):
        self.locationName = locationName
        self.locationKey = locationKey
        self.periods = []
        self.closed = False
        self.updatePeriods()

    def updatePeriods(self):
        date_today = datetime.now(timezone(timedelta(hours=-4))).strftime('%Y-%m-%d')
        info = make_scraper_request(
            f"https://api.dineoncampus.com/v1/location/{self.locationKey}/periods?platform=0&date={date_today}")
        info = info.json()
        try:
            for period in info["periods"]:
                newPeriod = Period(period["name"], period["id"])
                self.periods.append(newPeriod)
        except KeyError:
            self.closed = True
        if len(self.periods) == 0:
            self.closed = True

    def fetchMealPeriodIndex(self, periodName):
        index = 0
        for meal in self.periods:
            if meal.periodName.lower() == periodName.lower():
                return index
            index += 1
        return -1

    def fetchPeriod(self, index):
        date_today = datetime.now(timezone(timedelta(hours=-4))).strftime('%Y-%m-%d')
        info = make_scraper_request(
                f"https://api.dineoncampus.com/v1/location/{self.locationKey}/periods/{self.periods[index].fetchPeriodKey()}?platform=0&date={date_today}").json()
        return info

    def fetchItemsInPeriod(self, index):
        menu = self.fetchPeriod(index)
        stalls = []
        for category in menu["menu"]["periods"]["categories"]:
            stallName = category["name"]
            items = []
            for item in category["items"]:
                items.append(item["name"])
            stalls.append((stallName, items))
        return stalls


def make_scraper_request(url):
    headers = {"User-Agent" : ua.random}
    response = scraper.get(url, headers=headers)
    return response

@bot.command(name = "open")
async def allOpenLocations(ctx):
    await ctx.response.defer()
    diningLocations = []
    for dining_hall in locations.keys():
        diningLocations.append(Location(locationName=dining_hall, locationKey=locations.get(dining_hall)))
    message = ""
    allOpen = True
    for location in diningLocations:
        if location.closed:
            allOpen = False
            message += f"**{location.locationName}** is currently **closed** ❌\n"
        else:
            message += f"**{location.locationName}** is currently **open** ✅\n"
    if allOpen:
        message = f"All locations are currently **open**"
    await ctx.followup.send(message)

async def postMenuAtTime(meal):
    duration = 120 # How long it updates for (minutes)
    updateFrequency = 5 #Last update time
    message = None
    for i in range(0,duration,updateFrequency):
        embeds = []
        for dining_hall in locations.keys():
            print(dining_hall)
            embed = discord.Embed(
                title=f"{meal} at {dining_hall}"
            )

            embed.color = discord.Color.from_rgb(255, 205, 0)
            location = Location(locationName=dining_hall, locationKey=locations.get(dining_hall))
            if location.closed:
                embed.add_field(name="**Closed**", value=f"Not open for {meal} today")
                embed.color = discord.Color.red()
                embeds.append(embed)
                await asyncio.sleep(5)
                continue
            mealIndex = location.fetchMealPeriodIndex(meal)
            stalls = location.fetchItemsInPeriod(mealIndex)
            for stall in stalls:
                if stall[0] in bloat or len(stall[1]) == 0:
                    continue
                items = ""
                for item in stall[1]:
                    items += f"- {item}\n"
                embed.add_field(name=stall[0], value=items)
            now = datetime.now()
            embed.set_footer(text=f"Last updated: {now.hour}:{now.minute}")
            embeds.append(embed)
            await asyncio.sleep(5)

        await bot.wait_until_ready()
        channel = bot.get_guild(1365850565065834566).get_channel(1365851461959024660)
        if message == None:
            message = await channel.send(embeds=embeds)
        else:
            await message.edit(embeds=embeds)
        await asyncio.sleep(updateFrequency * 60)

async def sendFamilyDinnerPoll():
    poll = discord.Poll("Family Dinner?", duration=6)
    diningLocations = []
    embeds = []
    await bot.wait_until_ready()
    channel = bot.get_guild(1365850565065834566).get_channel(1365851461959024660)

    for dining_hall in locations.keys():
        location = Location(locationName=dining_hall, locationKey=locations.get(dining_hall))
        if not location.closed:
            for period in location.periods:
                if period.periodName == "Dinner":
                    diningLocations.append(location)
                    embed = discord.Embed(
                        title=f"{dining_hall}"
                    )
                    embed.color = discord.Color.from_rgb(255, 205, 0)
                    mealIndex = location.fetchMealPeriodIndex("Dinner")
                    stalls = location.fetchItemsInPeriod(mealIndex)
                    for stall in stalls:
                        if stall[0] in bloat or len(stall[1]) == 0:
                            continue
                        items = ""
                        for item in stall[1]:
                            items += f"- {item}\n"
                        embed.add_field(name=stall[0], value=items)
                    embeds.append(embed)
    if len(diningLocations) == 0:
        await channel.send("No locations are currently open for dinner")
        return
    for location in diningLocations:
        poll.add_answer(text=location.locationName)
    poll.add_answer(text="I'm busy :(")
    await channel.send(embeds=embeds, poll=poll)

@bot.command(name= "menu")
@discord.option("dining_hall", choices = ["Wads", "McNair", "DHH"])
@discord.option("meal", choices = ["Breakfast", "Lunch", "Dinner"])
async def menu(ctx, dining_hall: str, meal: str):
    await ctx.response.defer()
    embed = discord.Embed(
        title = f"{meal} at {dining_hall}"
    )
    embed.color = discord.Color.from_rgb(255,205,0)
    location = Location(locationName=dining_hall, locationKey=locations.get(dining_hall))
    if location.closed:
        await ctx.followup.send(dining_hall + " is closed")
        return
    mealIndex = location.fetchMealPeriodIndex(meal)
    stalls = location.fetchItemsInPeriod(mealIndex)
    for stall in stalls:
        if stall[0] in bloat or len(stall[1]) == 0:
            continue
        items = ""
        for item in stall[1]:
            items += f"- {item}\n"
        embed.add_field(name=stall[0], value= items)
    await ctx.followup.send(embed = embed)

@bot.command(name="cams")
@discord.option("location", choices = ["aerial", "plaza", "midcampus", "walker", "east", "collegeave", "bridge", "portagewest","portageeast",])
async def cams(ctx, location: str):

    match location:
        case "aerial":
            locationWeb = "campus-aerial"
        case "plaza":
            locationWeb = "husky-plaza"
        case "midcampus":
            locationWeb = "mid-campus"
        case "walker":
            locationWeb = "walker-lawn"
        case "east":
            locationWeb = "east-hall-construction"
        case "collegeave":
            locationWeb = "college-avenue-view"
        case "bridge":
            locationWeb = "lift-bridge"
        case "portagewest":
            locationWeb = "keweenaw-waterway-west-via-glrc"
        case "portageeast":
            locationWeb = "keweenaw-waterway-east-via-glrc"
        case _:
            locationWeb = "campus-aerial"
    await ctx.respond(f"https://www.mtu.edu/mtu_resources/php/webcams/cache/{locationWeb}.jpg")

async def waitForDinner():
    now = datetime.now()
    while True:
        if now.hour == 6 + 12 and now.minute in [0, 1, 2]:
            await sendFamilyDinnerPoll()
            await asyncio.sleep(23 * 60 * 60)
        else:
            await asyncio.sleep(90)

async def postMenus():
    while True:
        now = datetime.now()
        if now.hour in [7, 11, 17] and now.minute in [0, 1, 2]:
            if now.hour == 7:
                meal = "Breakfast"
            elif now.hour == 11:
                meal = "Lunch"
            else:
                meal = "Dinner"
            await postMenuAtTime(meal)
        else:
            await asyncio.sleep(90)

#bot.loop.create_task(waitForDinner())
bot.loop.create_task(postMenus())
bot.run(os.getenv("TOKEN"))