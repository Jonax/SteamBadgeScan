#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
STEAM BADGE MARKET ANALYSIS
	- Jon Wills (git@chromaticaura.net)

A series of scripts to analyse various sources of data from the Steam 
platform, for the purpose of acquiring badges as cheaply as possible.  The
end result is a CSV holding all badges available to the target user/profile, 
accompanied by & ranked by the cost to buy the respective cards from the 
Community Market at time of execution.  

NOTE: This was quickly written by the author during the Steam Holiday Sale 
2014 for his own purposes.  The code is provided as-is, and no guarantee of 
maintenance or further feature development is provided by the author.  
'''

import codecs
import json
import locale
import math
import os
import requests
import re
import random
import time
import argparse
from collections import OrderedDict
from datetime import datetime
from decimal import Decimal
from lxml import etree
from lxml.cssselect import CSSSelector

__author__ = "Jon Wills"
__copyright__ = "Copyright 2014, Chromatic Aura"
__credits__ = ["Jon Wills"]
__version__ = "1.0.0"
__maintainer__ = "Jon Wills"
__email__ = "git@chromaticaura.net"
__status__ = "Development"

global TARGET_STEAM_USERNAME
MAX_LEVEL_NORMAL = 5
MAX_LEVEL_FOIL = 1

# ================================================================
# GENERAL FUNCTIONS
# ================================================================

def GetSteamBadgeHtml(appId, foil = False):
	url = "http://steamcommunity.com/id/%s/gamecards/%d" % (TARGET_STEAM_USERNAME, appId)
	
	if foil:
		url = url + "/?border=1"
	
	r = requests.get(url)
	Sleep()
	
	return etree.HTML(r.text)

def GetSteamMarketUrl(appId, foil = False):
	borderId = int(foil)

	# Trading cards are retrieved Z-A to simplify looking for matching cards
	# in order to avoid a potential "A2 in A1" bug (namely Costume Quest's 
	# "Fall Valley" & "Fall Valley Carnival" false positives).
	url = "http://steamcommunity.com/market/search/render/?appid=753&category_753_cardborder[]=tag_cardborder_%d&category_753_Game[]=tag_app_%d&count=20&sort_column=name&sort_dir=asc" % (borderId, appId)
	
	return url
	
def GetSteamUserGamesJson():
	GAMES_JSON_REGEX = re.compile("var rgGames = (?P<games_json>.+);")

	url = "http://steamcommunity.com/id/%s/games/?tab=all&sort=name" % TARGET_STEAM_USERNAME
	r = requests.get(url)
	Sleep()
	
	match = GAMES_JSON_REGEX.search(r.text)
		
	return json.loads(match.group("games_json"))

def Sleep():
	t = 1.0 + (random.random() * 5.0)
	
	time.sleep(t)
		
def CheckForSteamBadge(appId, foil = False):
	url = "http://steamcommunity.com/id/%s/gamecards/%d" % (TARGET_STEAM_USERNAME, appId)
	
	if foil:
		url = url + "/?border=1"
	
	r = requests.get(url)
	Sleep()
	
	return r.url == url

def GetExistingBadgeLevel(html):
	EARNED_LEVEL_REGEX = re.compile("Level (?P<level>[0-9]+)")
	EARNED_BADGE_SELECTOR = CSSSelector("div.badge_info_description")

	# If the page has the div for displaying the user's current badge
	# level, then the user already has the badge and we can grab the right level.
	earned_badge_div = next((d for d in EARNED_BADGE_SELECTOR(html)), None)
	
	# If the div is missing, user doesn't have the badge yet so assume a 
	# level of 0.  
	if earned_badge_div == None:
		return 0
	
	# The div containing the user's current badge level has three child
	# divs of classes "badge_info_title", None, and "badge_info_unlocked".  
	# The child div without a class holds the actual level.  
	level_div = next((d for d in earned_badge_div if d.get("class") == None), None)
	if level_div == None:
		return 0
		
	levelMatch = EARNED_LEVEL_REGEX.search(level_div.text)
	if levelMatch == None:
		return 0
		
	return int(levelMatch.group("level"))
	
def GetBadgeCards(html):
	CARD_SELECTOR = CSSSelector("div.badge_card_set_card")
	CARD_TEXT_SELECTOR = CSSSelector("div.badge_card_set_text")

	cards = {}

	for c in CARD_SELECTOR(html):
		classes = c.get("class").split(" ")
		
		# Cards the user has will have the "owned" class, otherwise 
		# the class is "unowned".  
		ownCard = "owned" in classes
		
		nameDiv = next(d for d in CARD_TEXT_SELECTOR(c))
		
		# Which div to look at for the card's name depends on whether user
		# has the card; third if the card is owned, first otherwise.  
		elemIdx = ownCard and 2 or 0
		cardName = list(nameDiv.itertext())[elemIdx].strip()
		
		cards[cardName] = ownCard
	
	return cards

def CanLevelBadgeUp(badge):
	if badge["rarity"] == "normal":
		return badge["level"] < MAX_LEVEL_NORMAL
	elif badge["rarity"] == "foil":
		return badge["level"] < MAX_LEVEL_FOIL
	else:
		return False

def GetMarketListingsForBadge(appId, foil = False):
	MARKET_LISTING_SELECTOR = CSSSelector("div.market_listing_row")
	CARD_NAME_SELECTOR = CSSSelector("span.market_listing_item_name")
	CARD_QUANTITY_SELECTOR = CSSSelector("span.market_listing_num_listings_qty")
	CARD_PRICE_SELECTOR = CSSSelector("div.market_listing_their_price > span.market_table_value > span")
	USD_PRICE_REGEX = re.compile("\$(?P<price>[0-9]+.[0-9]{2}) USD")
	
	listings = []
	
	url = GetSteamMarketUrl(appId, foil)

	validResult = False
	while not validResult:
		r = requests.get(url)
		
		Sleep()
	
		if "There was an error performing your search. Please try again later." in r.text:
			print "\t" + "Retrying %d %s" % (appId, foil and "Foil" or "Normal")
		else:
			validResult = True
	
	html = etree.HTML(r.json()["results_html"])
	
	for e in MARKET_LISTING_SELECTOR(html):
		link = e.getparent().get("href")
		
		match = USD_PRICE_REGEX.match(CARD_PRICE_SELECTOR(e)[0].text)
		
		listings.append({
			"name": CARD_NAME_SELECTOR(e)[0].text,
			"quantity": int(CARD_QUANTITY_SELECTOR(e)[0].text.replace(",", "")),
			"price": float(match.group("price")),
			"link": link
		})
	
	return listings

def CompareMarketData(a, b):
	value = Decimal(a["set_price"]).quantize(Decimal('.01')) - Decimal(b["set_price"]).quantize(Decimal('.01'))
	if value != 0:
		return (value > 0) and 1 or -1
		
	value = a["availability"] - b["availability"]
	if value != 0:
		return -value
	
	return 0

# ================================================================
# STAGE FUNCTIONS
# ================================================================
	
def GetAllUserGames():
	print "-" * 32
	print "Stage I -- Finding all games owned by %s" % TARGET_STEAM_USERNAME
	print "-" * 32

	games = GetSteamUserGamesJson()
	
	with codecs.open("output/games.json", "w", "utf-8") as output:
		json.dump(games, output, indent = 4)
	
	print "%s has %d games" % (TARGET_STEAM_USERNAME, len(games))
	print "=" * 32
	print
	
def GetBadges():
	if not os.path.isfile("output/games.json"):
		print "ERROR: games.json not found, run GetAllUserGames() first"
		sys.exit()
	
	games = None
	with codecs.open("output/games.json", "r", "utf-8") as input:
		games = json.load(input)
		
	print "-" * 32
	print "Stage II -- Finding all badges for user's games"
	print "-" * 32

	badges = []
	for i, app in enumerate(games):	
		print "[%d / %d] %s (%d)" % (i + 1, len(games), app["name"].encode("ascii", "ignore"), app["appid"])

		# Normal Badge
		if CheckForSteamBadge(app["appid"]):
			print "\t" + "Normal"
			
			badges.append({
				"id": app["appid"],
				"name": "%s (%s)" % (app["name"], "Normal"),
				"rarity": "normal"
			})
		
		# Foil Badge
		if CheckForSteamBadge(app["appid"], True):
			print "\t" + "Foil"
			
			badges.append({
				"id": app["appid"],
				"name": "%s (%s)" % (app["name"], "Foil"),
				"rarity": "foil"
			})

	with codecs.open("output/badges.json", "w", "utf-8") as output:
		json.dump(badges, output, indent = 4)
		
	print "%d badges found across %d games" % (len(badges), len(games))
	print "=" * 32
	print
	
def GetCards():
	if not os.path.isfile("output/badges.json"):
		print "ERROR: badges.json not found, run GetBadges() first"
		sys.exit()

	badges = None
	with codecs.open("output/badges.json", "r", "utf-8") as input:
		badges = json.load(input)
		
	print "-" * 32
	print "Stage III -- Finding all badges with available level-ups"
	print "-" * 32
		
	for i, b in enumerate(badges):
		print "[%d/%d] %s" % (i + 1, len(badges), b["name"].encode("ascii", "ignore"))
			
		html = GetSteamBadgeHtml(b["id"], b["rarity"] == "foil")
		
		b["level"] = GetExistingBadgeLevel(html)
		b["cards"] = GetBadgeCards(html)
		
		if CanLevelBadgeUp(b):
			numOwnedCards = len([own for own in b["cards"].itervalues() if own])
			numTotalCards = len(b["cards"])
			
			if numOwnedCards == 0:
				print "\t" + "Level %d available" % (b["level"] + 1)
			else:
				print "\t" + "Progress to Level %d: %d / %d cards" % (b["level"] + 1, numOwnedCards, numTotalCards)
		else:
			print "\t" + "Already at max level, filtering out."
		
		print

	badges = [b for b in badges if CanLevelBadgeUp(b)]
			
	with codecs.open("output/available_badges.json", "w", "utf-8") as output:
		json.dump(badges, output, indent = 4)
		
	print "%d badges with possible level ups" % len(badges)
	print "=" * 32
	print

def SearchMarketData():
	if not os.path.isfile("output/available_badges.json"):
		print "ERROR: available_badges.json not found, run GetCards() first"
		sys.exit()

	badges = None
	with codecs.open("output/available_badges.json", "r", "utf-8") as input:
		badges = json.load(input)
		
	print "-" * 32
	print "Stage IV -- Finding latest card prices on Steam Community Market"
	print "-" * 32
		
	for i, b in enumerate(badges):
		print "[%d/%d] %s" % (i + 1, len(badges), b["name"].encode("ascii", "ignore"))
		
		listings = GetMarketListingsForBadge(b["id"], b["rarity"] == "foil")
		
		for l in listings:
			matchingCard = next((c for c in b["cards"] if c == l["name"]), None)
			
			if matchingCard == None and b["rarity"] == "foil":
				matchingCard = next((c for c in b["cards"] if ("%s (Foil)" % c) == l["name"]), None)
			
			if matchingCard == None:
				matchingCard = next((c for c in b["cards"] if c in l["name"]), None)

			if matchingCard != None:
				if "Costume Quest" in b["name"]:
					print (l["name"], matchingCard)
			
				l["ownCard"] = b["cards"][matchingCard]
			
				b["cards"][matchingCard] = l
		
	with codecs.open("output/market_data.json", "w", "utf-8") as output:
		json.dump(badges, output, indent = 4)
		
	print "Market data recorded for %d badges" % len(badges)
	print "=" * 32
	print
		
def AnalyseMarketData():
	if not os.path.isfile("output/market_data.json"):
		print "ERROR: market_data.json not found, run SearchMarketData() first"
		sys.exit()

	badges = None
	with codecs.open("output/market_data.json", "r", "utf-8") as input:
		badges = json.load(input)

	print "-" * 32
	print "Stage V -- Analysis & Aggregation"
	print "-" * 32
		
	results = []
	for b in badges:
		cards = b["cards"].values()

		numOwnedCards = len([c for c in cards if c["ownCard"]])
		numTotalCards = len(cards)
	
		results.append({
			"name": b["name"],
			"appid": b["id"],
			"rarity": b["rarity"],
			"progress": "%d / %d" % (numOwnedCards, numTotalCards),
			"set_price": sum(c["price"] for c in cards),
			"availability": min(c["quantity"] for c in cards)
		})
			
	results.sort(cmp = CompareMarketData)
	
	with codecs.open("output/results.json", "w", "utf-8") as output:
		json.dump(results, output, indent = 4)
		
	with codecs.open("results.csv", "w", "utf-8") as output:
		output.write(",".join(("Badge", "Rarity", "Progress", "Set Price", "Availability", "Link")))
		output.write("\r\n") 
	
		for t in results:
			url = GetSteamMarketUrl(t["appid"], t["rarity"] == "foil")
			
			output.write(",".join(("\"%s\"" % t["name"], t["rarity"], "$%.02f" % t["set_price"], "%d" % t["availability"], url)))
			output.write("\r\n") 
			
	print "=" * 32
	print
	print "=" * 32
	print "Job Done!  Import results.csv into Excel or your favourite substitute to get a nicer view."
	print "=" * 32

	
# ================================================================
# ROOT FUNCTION
# ================================================================
if __name__ == "__main__":
	parser = argparse.ArgumentParser(description = "Determine price of various Steam badges available to a given Steam account.")
	parser.add_argument("user", help="The public ID for the target Steam account (NOTE: Grab from the profile's URL on steamcommunity.com")

	args = parser.parse_args()
	
	# Grab & store the target Steam username.  This'll be used in various
	# stages.  
	global TARGET_STEAM_USERNAME
	TARGET_STEAM_USERNAME = args.user

	print
	
	random.seed(datetime.utcnow())
	
	# Make sure the output folder is created, so that output between stages
	# can be stored.  
	if not os.path.isdir("output"):
		os.makedirs("output")

	# Main controls for the script.  Each stage will use the latest output
	# from the previous stage, so comment/uncomment each call as required and
	# cache results when available. 
	GetAllUserGames()
	GetBadges()
	GetCards()
	SearchMarketData()	
	AnalyseMarketData()
