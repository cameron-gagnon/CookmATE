from __future__ import print_function

from BeautifulSoup import BeautifulSoup
import urllib2
import re
import threading
import requests
import recipe

UA = "Mozilla/5.0 (Windows; U; Windows NT 5.1; de; rv:1.9.1.5) Gecko/20091102 Firefox/3.5.5"

class Recipe:
    """
        Stores information about a recipe that we can either store into
        a database, or have Alexa pull from to get specific info the user asks
        about.
    """
    # ingredients will be an array where the first index is the first
    # ingredient; same goes for the steps

    def __init__(self, link="", custom = None):
        # I know this is bad practice to copy/paste so much
        # if we get a valid link then we parse it
        if link != "":
            self.parsedInfo = Parse(link)
            # init variables if we have a link
            self.cookTime  = self.parsedInfo.cookTime
            self.prepTime  = self.parsedInfo.prepTime
            self.totalTime = self.parsedInfo.totalTime
            self.ovenTemp  = self.parsedInfo.ovenTemp
            self.nameOfRecipe = self.parsedInfo.name    
            self.nutritionInfo = self.parsedInfo.nutritionInfo.calories
            self.ingredients = self.parsedInfo.ingredients   
            self.steps = self.parsedInfo.steps   

        elif (custom.lower() == "chocolate chip cookie"):
            test = recipe.ChocCookies
            self.cookTime  = test.TEST_BAKE
            self.prepTime  = test.TEST_PREP
            self.totalTime = test.TEST_TOTAL
            self.ovenTemp  = test.OVEN_TEMP
            self.nameOfRecipe  = test.TEST_NAME
            self.nutritionInfo = test.NUTRITION_INFO
            self.ingredients = test.TEST_INGREDIENTS
            self.steps = test.TEST_STEPS 

        elif (custom.lower() == "snow cone"):
            test = recipe.SnowCones
            self.cookTime  = test.TEST_BAKE
            self.prepTime  = test.TEST_PREP
            self.totalTime = test.TEST_TOTAL
            self.ovenTemp  = test.OVEN_TEMP
            self.nameOfRecipe  = test.TEST_NAME
            self.nutritionInfo = test.NUTRITION_INFO
            self.ingredients = test.TEST_INGREDIENTS
            self.steps = test.TEST_STEPS 

class Parse:
    """
        Parses a recipe from allRecipes.com and returns our fields that
        we take interest in:
        ingredients, steps, cook/prep time, and nutritional information
    """

    def __init__(self, link):

        # open and get the html of the link that we want
        linkHTML = requests.get(link, headers={'User-Agent': UA}).content
        linkSoup = BeautifulSoup(linkHTML)
        
        self.ingredients = []
        self.steps = []
        self.getIngredients(linkSoup)
        self.getSteps(linkSoup)
        self.getMetaInfo(linkSoup)
        self.getName(linkSoup)
        self.getNutrition(linkSoup)
       
    def getNutrition(self, linkSoup):
        """
            gets the nutrition info for recipe
        """
        self.nutritionInfo = Nutrition(linkSoup)

    def getIngredients(self, linkSoup):
        """
            get a list of all the ingredients associated with a recipe
        """
        for ingred in linkSoup.findAll("span", {"itemprop":"ingredients"}):
            # these checks help make sure the things we add are
            # actually ingredients and not just text or blank space
            # from the website
            if ingred.text[:3] != "Add" and ingred.text != "":
                self.ingredients.append(ingred.text)

    def getSteps(self, linkSoup):
        """
            gets the steps for a recipe
        """
        for step in linkSoup.findAll("span", {"class":"recipe-directions__list--item"}):
            # check for oven temperature and if we find it, add it to
            # our data
            match = re.search(r'Preheat oven to (\d*) degrees F',
                            step.text,
                            flags=re.IGNORECASE)
            if match:
                # group(1) is just the 350 or whatever the temperature is
                # of our oven
                self.ovenTemp = match.group(1)
            # if no temperature if found, we set it to -1 so we can
            # check for 'null' values later
            else:
                self.ovenTemp = -1

            if step.text != '':
                self.steps.append(step.text)

    def getMetaInfo(self, linkSoup):
        """
            gets meta data about the recipe such as cook time and prep time
        """

        try:
            self.prepTime = linkSoup.find("time", {"itemprop":"prepTime"})["datetime"]
            self.cookTime = linkSoup.find("time", {"itemprop":"cookTime"})["datetime"]
            self.totalTime = linkSoup.find("time", {"itemprop":"totalTime"})["datetime"]

        except(TypeError):
            print("Prep/Cook time info isn't available for this recipe")
            self.prepTime = -1
            self.cookTime = -1
            self.totalTime = -1


    def getName(self, linkSoup):
        """
            gets the name of the recipe
        """
        self.name = linkSoup.find("h1", {"itemprop":"name"}).text

class Nutrition:

    def __init__(self, linkSoup):
       self.getCalories(linkSoup) 

    def getCalories(self, linkSoup):
        """ gets the calorie count of the recipe """

        self.calories = linkSoup.find("span", {"class": "calorie-count"}).text
        # get rid of 'cals' after the number of calories
        self.calories = re.sub('[a-z]', '', self.calories)


class FindRecipe:

    def __init__(self, searchTerm):
        self.userSearchTerm = searchTerm
        searchTerm.replace(" ", "%20")
        url = "https://allrecipes.com/search/results/?wt=" + searchTerm + "&sort=p"
        
        self.resultsHTML = requests.get(url,
                                        headers={'User-Agent': UA}).content


    def storeTopFive(self):
        soup = BeautifulSoup(self.resultsHTML)

        # get up to 10 results of our search
        results = soup.findAll("article", {"class":"grid-col--fixed-tiles"}, limit=10)
        self.topFiveResults = []
        # get the top 5 results and then store them
        for ans in results:
            if (len(self.topFiveResults) >= 5):
                break
            try:
                # adds the text and url of each result strips any whitespace
                self.topFiveResults.append((ans.a.h3.text.strip(' \r\n'),
                        "https://allrecipes.com" + ans.a['href']))
                print(ans.a.h3.text)
                # remove the last item if we added an ad
                if ("allrecipes" in ans.a.h3.text.lower()):
                    self.topFiveResults.pop()

            except AttributeError:
                print("Not an actual recipe maybe?")
                continue

    def returnTopFive(self):
        return self.topFiveResults

    def returnURL(self, choice):
        """
            returns the url of choice the user specified
            topFiveResults[0] == tuple of info
            topFiveResults[0][0] == Name of recipe
            topFiveResults[0][1] == url of recipe
        """
        return self.topFiveResults[choice - 1][1]
