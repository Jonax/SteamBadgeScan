SteamBadgeScan
==============

A series of scripts to analyse various sources of data from the Steam platform, for the purpose of acquiring badges as cheaply as possible.  The end result is a CSV holding all badges available to the target user/profile, accompanied by & ranked by the cost to buy the respective cards from the Community Market at time of execution.  

NOTE: This was quickly written by the author during the Steam Holiday Sale 2014 for his own purposes.  The code is provided as-is - No guarantee of maintenance or further feature development is provided by the author.  

How It Works
------------

Accessing data from Steam Community is done via a variety of sources that changes based on the data in question - The Games view stores them as JSON data embedded in the HTML file, Community Market listings for cards can be found using a semi-hidden JSON API, and almost everything else that's relevant can be retrieved via the static HTML returned when looking up badges.  

The script retrieves the necessary information via a series of stages:
- GetAllUserGames() - Retrieves all owned games from the target user's Steam profile
- GetBadges() - Determines all badges associated with the user's games.  
- GetCards() - Retrieves all cards for the badges.  Also determines the level of badges the user already has, and filters out those which're at max level (lvl.5 for Normal badges, lvl.1 for Foil badges).  
- SearchMarketData() - Queries the Steam Community Market for each badge's cards.  
- AnalyseMarketData() - Analyses, aggregates & formats the market data to a human-readable format.  

Each of these stages check for & read the previous stage's output, and generates new output for the following stage.  For this reason, output can be cached to save time (e.g. GetAllUserGames() & GetBadges() only need to be run when games have been bought), and can be controlled by commenting out the various function calls in the root function at the bottom of the file.  

The end result is a CSV file that can be imported to Excel or another app, listing the badges available to the given user in order of total price for all the cards (sans cards the user already has).  

Prerequisites
-------------

Python 2.7 is required (due to argparse), as well as the following libraries:
- requests
- lxml
- cssselect

All can be installed using *pip*.

Usage
-----

	scan.py <username>

Where *username* is the profile ID as listed in the profile's URL on steamcommunity.com.  e.g.
	http://steamcommunity.com/id/jonaxc
	
	scan.py jonaxc

Limitations
-----------

- Script assumes a basic knowledge of Python programming.  
- Badge checking is limited to Game badges only.  Non-Game badges (e.g. Steam Sales, Pillar of Community etc) are omitted.  
- Error checking & reporting is minimal.  
- Caching is manual and is up to the user to determine.  
- Final output is limited to CSV due to being easily created and supported by most spreadsheet apps