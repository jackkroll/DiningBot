import cloudscraper,dotenv,os, discord
from datetime import datetime, timezone, timedelta
from fake_useragent import UserAgent
dotenv.load_dotenv()
bot = discord.Bot()

locations = {"Wads" :"64b9990ec625af0685fb939d", "McNair":"64a6b628351d5305dde2bc08", "DHH" :"64e3da15e45d430b80c9b981"}
bloat = ["Salad Bar", "Made to Order Deli", "Rice It Up", "Deli"]
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
        self.updatePeriods()

    def updatePeriods(self):
        date_today = datetime.now(timezone(timedelta(hours=-4))).strftime('%Y-%m-%d')
        info = make_scraper_request(
            f"https://api.dineoncampus.com/v1/location/{self.locationKey}/periods?platform=0&date={date_today}").json()
        for period in info["periods"]:
            newPeriod = Period(period["name"], period["id"])
            self.periods.append(newPeriod)

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

    #https://api.dineoncampus.com/v1/location/{location}/periods?={}platform=0&date=2025-4-6
    response = scraper.get(url, headers=headers)
    return response

@bot.command(name= "menu", guild_ids = [585594090863853588])
@discord.option("location", choices = ["Wads", "McNair", "DHH"])
@discord.option("meal", choices = ["Breakfast", "Lunch", "Dinner"])
async def menu(ctx, location: str, meal: str):
    await ctx.response.defer()
    embed = discord.Embed(
        title = f"{meal} at {location}"
    )
    embed.color = discord.Color.from_rgb(255,205,0)
    match meal:
        case "Breakfast":
            index = 0
        case "Lunch":
             index = 1
        case "Dinner":
            index = 2
    stalls = Location(locationName= location, locationKey=locations.get(location)).fetchItemsInPeriod(index)
    for stall in stalls:
        if stall[0] in bloat or len(stall[1]) == 0:
            continue
        items = ""
        for item in stall[1]:
            items += f"- {item}\n"
        embed.add_field(name=stall[0], value= items)
    await ctx.followup.send(embed = embed)

bot.run(os.getenv("TOKEN"))