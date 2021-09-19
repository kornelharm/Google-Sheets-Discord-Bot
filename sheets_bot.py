from __future__ import print_function
import os
import discord
import math
from discord.ext import tasks, commands
#import sheetsInterface as SI
import time
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import datetime

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

# The ID of the spreadsheet.
TARGET_SHEET = ''

# The bot object used to interface with the discord bot
bot = commands.Bot(command_prefix = '!')

global sheetValues
sheetValues = dict()
global sheet
global processedGames
processedGames = dict()
global allProcessedGames
allProcessedGames = []

def initialize():
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('sheets', 'v4', credentials=creds)

    # Call the Sheets API
    sheet = service.spreadsheets()
    return sheet

# Returns a dict containing the values in the specified spreadsheet and range
# Returns all information about those values
def retrieve(sheetObj, spreadsheet : str, inputRange : str):
    result = sheetObj.values().get(spreadsheetId=spreadsheet, range=inputRange).execute()
    return result

# Returns a 2-D list containing the values in the specified spreadsheet and range
# Returns purely the values (Better performance)
def retrieveValues(sheetObj, spreadsheet : str, inputRange : str):
    result = sheetObj.values().get(spreadsheetId=spreadsheet, range=inputRange, fields = 'values').execute()
    return result["values"]

def getTime(match : list):
	 #time.strptime()
	 timeString = f"{match[0]} {match[1]}"
	 return time.mktime(datetime.datetime.strptime(timeString, "%m/%d/%y %H:%M").timetuple())


# Returns an organized match list from the spreadsheet (removes header)
# Also removes all games with dates/times which have passed
def organizedGame(game : list):
	processedGame = []
	# For every match(row) except for the header
	for match in game[1:]:
		# If the matchtime has not passed
		if((match) and (time.time() < getTime(match))):

			processedGame.append(match)
	processedGame.sort(key=getTime)
	return processedGame

# Returns the next upcoming match (any game)
def nextMatch():
	return allProcessedGames[0]

		

# Refreshes internal database, initialized at the end of on_ready
@tasks.loop(seconds=60.0)
async def refresh(sheetObj):
	# Retrieve all of the values from each sheet, insert into sheetValues
	sheetValues['CSGO'] = retrieveValues(sheetObj, TARGET_SHEET, 'CSGO')
	sheetValues['Valorant'] = retrieveValues(sheetObj, TARGET_SHEET, 'Valorant')
	sheetValues['Miscellaneous'] = retrieveValues(sheetObj, TARGET_SHEET, 'Miscellaneous')


	# For each game imported, process them individually
	for game in sheetValues:
		processedGames[f"{game}"] = organizedGame(sheetValues[game])

	if(allProcessedGames):
		allProcessedGames.clear()

	# Combine each game into one list
	for game in processedGames:
		for match in processedGames[game]:
			allProcessedGames.append(match)
	
	# Sort the compounded list
	allProcessedGames.sort(key=getTime)
	
	

@bot.event
async def on_ready():
	global guild
	guild = bot.guilds[0]

	print(f'{bot.user} is connected to the server.')
	sheet = initialize()
	refresh.start(sheet)
	print("Initialization Complete")

#  R    G   B
# 255, 105, 0
	
# Displays the latency of the bot
@bot.command(brief="Displays the latency of the bot")
async def ping(ctx):
	
	embed = discord.Embed(
		title = f"Latency: {round((bot.latency)*1000)} ms",
		colour = discord.Colour.from_rgb(255, 105, 0)
	)
	
	await ctx.send(embed=embed)
	await ctx.message.delete()

# Lists up to 3 upcoming matches
@bot.command(name="upcoming", brief="Lists the next 3 upcoming matches")
async def upcoming(ctx):
	if(len(allProcessedGames) == 0):
		embed = discord.Embed(
			title = f"There are no scheduled matches",
			colour = discord.Colour.from_rgb(255, 105, 0)
		)

	else:
		embed = discord.Embed(
			title = f"Upcoming Matches",
			colour = discord.Colour.from_rgb(255, 105, 0)
		)

		for index in range(min(3, len(allProcessedGames))):
			match = allProcessedGames[index]
			embed.add_field(name=f"{match[3]}", value=f"{match[0]}, {match[1]} EST", inline=False)

	await ctx.send(embed=embed)
	await ctx.message.delete()

# Prints each CSGO match from the sheet into console
@bot.command(name="print", hidden=True)
async def printGames(ctx):
	
	for match in sheetValues["CSGO"]:
		for column in match:
			print(f"{column.ljust(20)}", end="")
		print()

	await ctx.message.delete()


# Prints each CSGO match from the sheet into console
@bot.command(name="ros", brief="Links to the google drive containing the ROS docs")
async def ros(ctx):
	
	embed = discord.Embed(
		title = f"ROS:",
		colour = discord.Colour.from_rgb(255, 105, 0),
		description = f"[**LINK**](insert link here)"

	)

	await ctx.send(embed=embed)
	await ctx.message.delete()

# Lists the next matchup
@bot.command(name="teams", brief="Lists the teams competing in the next game")
async def teams(ctx):
	try:
		match = nextMatch()
		embed = discord.Embed(
			title = f"Next Game:",
			colour = discord.Colour.from_rgb(255, 105, 0),
			description = f"{match[3]}"
		)
		
	except IndexError:
		embed = discord.Embed(
			title = f"There are no scheduled matches",
			colour = discord.Colour.from_rgb(255, 105, 0),
		)
	
	finally:
		await ctx.send(embed=embed)
		await ctx.message.delete()

# Lists the calltime of the next game
@bot.command(name="calltime", brief="Lists the calltime of the next match")
async def calltime(ctx):
	try:
		match = nextMatch()
		embed = discord.Embed(
			title = f"Calltime of Next Match:",
			colour = discord.Colour.from_rgb(255, 105, 0),
			description = f"{match[2]} EST"
		)

	except IndexError:
		embed = discord.Embed(
			title = f"There are no scheduled matches",
			colour = discord.Colour.from_rgb(255, 105, 0),
		)

	finally:
		await ctx.send(embed=embed)
		await ctx.message.delete()

# Lists the next match and all of its information
@bot.command(name="next", brief="Lists info about the upcoming match")
async def next(ctx):
	try:
		match = nextMatch()
		embed = discord.Embed(
			title = f"{match[3]}",
			colour = discord.Colour.from_rgb(255, 105, 0),
			description = f"***{match[0]}***,   ***{match[1]} EST***"
		)

		embed.add_field(name=f"Casters", value=f"{match[4]}", inline=True)
		embed.add_field(name=f"Producer", value=f"{match[5]}", inline=True)
		embed.add_field(name=f"Observer(s)", value=f"{match[6]}", inline=True)
		embed.add_field(name=f"Confirmed", value=f"{match[7]}", inline=True)
		try:
			embed.add_field(name=f"Notes", value=f"{match[8]}", inline=False)
		except IndexError:
			pass

	# There are no upcoming matches
	except IndexError:

		embed = discord.Embed(
			title = f"There are no scheduled matches",
			colour = discord.Colour.from_rgb(255, 105, 0),
		)
		
	finally:
		await ctx.send(embed=embed)
		await ctx.message.delete()

#bot.run(DISCORD ID)