from alexa.ask import voice, Request, ResponseBuilder as r

import recipe
import scrape
import json
import decimal
import boto3

"""
In this file we specify default event handlers which are then populated into the handler map using metaprogramming
Copyright Anjishnu Kumar 2015

Each VoiceHandler function receives a Request object as input and outputs a Response object 
A response object is defined as the output of ResponseBuilder.create_response()
"""


def lambda_handler(request_obj, context={}):
    '''      
    This is the main function to enter to enter into this code. 
    If you are hosting this code on AWS Lambda, this should be the entry point. 
    Otherwise your server can hit this code as long as you remember that the
    input 'request_obj' is JSON request converted into a nested python object.        
    '''

    request = Request(request_obj)

    ''' inject user relevant metadata into the request if you want to, here.
    
    e.g. Something like : 
    ... request.meta_data['user_name'] = some_database.query_user_name(request.get_user_id()) 
    
    Then in the handler function you can do something like -
    ... return r.create_response('Hello there {}!'.format(request.meta_data['user_name']))
    '''    
    return voice.route_request(request)

    
@voice.intent_handler(intent="FinishIntent")
def finish_intent_handler(request):
    db = Database(request.user_id())
#    db.setItem("IngStep", -1)
#    db.setItem("DirStep", -1)
    return r.create_response(message="Enjoy your meal!", end_session=True)

@voice.default_handler()
def default_handler(request):
    """ The default handler gets invoked if no handler is set for a request """
    outMessage = "I can find you a recipe, list your recipes, or load a custom recipe."
    return r.create_response(message=outMessage)


@voice.request_handler("LaunchRequest")
def launch_request_handler(request):
    """
    Annotate functions with @VoiceHandler so that they can be automatically mapped 
    to request types.
    Use the 'request_type' field to map them to non-intent requests
    """
    outMessage = "Hello! I'm Cookmate, your best friend in the kitchen! " +\
                 "I can help you find a recipe for a meal, or " +\
                 "load a custom recipe of yours! What would you like me to do?"
    return r.create_response(message=outMessage)


@voice.request_handler(request_type="SessionEndedRequest")
def session_ended_request_handler(request):
    db = Database(request.user_id())
    db.setItem("IngStep", -1)
    db.setItem("DirStep", -1)
    return r.create_response(message="Enjoy your meal!")


@voice.intent_handler(intent='LoadRecipeIntent')
def get_recipe_intent_handler(request):
    """
        Loads and prepares a custom recipe from the user input
    """
    # Get variables like userId, slots, intent name etc from the 'Request' object
    recipe = request.get_slot_value("LoadRecipe") 
    recipe = recipe if recipe else ""
    outMessage = "Your " + recipe + " recipe is ready to be made. Say start or next to continue."
    recipe = scrape.Recipe(custom = recipe)
    db = Database(request.user_id())
    db.loadRecipe(recipe)
    return r.create_response(message=outMessage)


@voice.intent_handler(intent="FindRecipeIntent")
def next_recipe_intent_handler(request):
    """
        gets the top three URLS for the desired type of recipes
    """
    food = request.get_slot_value("FindRecipe")

    outMessage = ""
 
    # go find a recipe
    try:
        webPage = scrape.FindRecipe(food)
    except:
        outMessage = "Please start over and phrase the request in another way. "+\
                     "I had trouble hearing what you said."
        return r.create_response(message=outMessage)

    webPage.storeTopFive()
    topRecipes = webPage.returnTopFive()
    
    db = Database(request.user_id())
    db.updateLinks(topRecipes)
    topRecipes.sort()

    outMessage = "The top 3 {0} recipes are 1. {1}, 2. {2}, and 3. {3}.".format(food,
                                                                       topRecipes[0][0],
                                                                       topRecipes[1][0],
                                                                       topRecipes[2][0])
    outMessage += " Which one would you like to make?"
    rePrompt = "Please pick an option 1 through 3."

    return r.create_response(message=outMessage, reprompt_message=rePrompt)


@voice.intent_handler(intent="ChoiceIntent")
def choose_recipe_intent_handler(request):
    """
        Gets the information for the next recipe that they will be making
    """
    # check for no recipe specified yet
    
    choiceNum = request.get_slot_value("Choice")
    
    if ((1 <= int(choiceNum)) and (int(choiceNum) <= 3)):
        db = Database(request.user_id())
        db.updateChoice(choiceNum)
        # get what step we're on
        db.setItem("IngStep", -1)
        db.setItem("DirStep", -1)
        print(choiceNum)
        link = db.getLink(choiceNum)
        print(link)
        recipe = scrape.Recipe(link)
        db.loadRecipe(recipe)

    outMessage = recipe.nameOfRecipe + " selected. "
    outMessage += "Say: 'start' to continue, or, 'cancel' to end."

    return r.create_response(message=outMessage)


@voice.intent_handler(intent="GetInfoIntent")
def get_info_intent(request):
    """
        Returns the specific piece of information the user asked for
    """
    userIng = request.get_slot_value("Ingredient")
    db = Database(request.user_id())
    ingredients = db.getAllIngredients()

    outMessage = "I'm sorry, I didn't find {0} in the ingredients.".format(userIng)

    if userIng:
        for ingredient in ingredients:
            if (userIng in ingredient):
                outMessage = "You need " + str(ingredient) + " for this recipe."

    ovenBool = request.get_slot_value("Appliance")
    ovenBool = ovenBool if ovenBool == "oven" else ""
    if ovenBool:
        outMessage = "The oven needs to be set to " 
        outMessage += str(db.getRecipeItem("OvenTemp"))

    return r.create_response(message=outMessage)

@voice.intent_handler(intent="GetTimeIntent")
def get_time_intent_handler(request):
    db = Database(request.user_id()) 
    cookTime = db.getRecipeInfo("CookTime")

    outMessage = ""

    try:
        if (cookTime < 0):
            outMessage = "Time information was not provided for this recipe"
        else:
            cookTime.replace('PT', '')
            outMessage = "The cook time for this recipe is: " + cookTime
            return r.create_response(message=outMessage)

        totalTime = db.getRecipeInfo("TotalTime")

        if (totalTime < 0):
            outMessage = "Time information was not provided for this recipe"
        else:
            totalTime.replace('PT', '')
            outMessage = "The total time taken for this recipe is: " + totalTime
            return r.create_response(message=outMessage)

    except:
        outMessage = "Time information was not provided for this recipe"

    return r.create_response(message=outMessage, reprompt_message=rePrompt)

@voice.intent_handler(intent="GetNutIntent")
def get_nut_intent_handler(request):
    """
        returns how many calories in a recipe
    """
    db = Database(request.user_id())
    nutritionInfo = int(db.getRecipeInfo("NutritionInfo"))

    outMessage = "I'm sorry, nutrition information is not available on this recipe."
    if (nutritionInfo >= 0):
        outMessage = "There are " + str(nutritionInfo) + " calories per serving in this recipe."

    return r.create_response(message=outMessage)

@voice.intent_handler(intent="RepeatIntent")
def repeat_intent_handler(request):
    """
        Should repeat the last command entered
    """
    db = Database(request.user_id()) 
    ingStepNum = int(db.getItem("IngStep"))
    dirStepNum = int(db.getItem("DirStep"))
    totalIng = int(db.getRecipeItem("TotalIng"))
    totalStep = int(db.getRecipeItem("TotalStep"))

    outMessage = ""
    if (ingStepNum < 0 and dirStepNum < 0):
        outMessage = "I can help you find a recipe for a meal, or " +\
                     "load a custom recipe of yours! What would you like me to do?"

    if (ingStepNum >= 0 and ingStepNum < totalIng):
        if (ingStepNum != 0):
            db.setItem("IngStep", ingStepNum - 1)
            outMessage = db.getNextIngredient()
            db.setItem("IngStep", ingStepNum)

    elif (dirStepNum >= 0 and dirStepNum <= totalStep):
        if (dirStepNum != 0):
            db.setItem("DirStep", dirStepNum - 1)
            outMessage = db.getNextStep()
            db.setItem("DirStep", dirStepNum)
    
    return r.create_response(message=outMessage, reprompt_message="Say next to continue")

@voice.intent_handler(intent="NextIntent")
def next_recipe_intent(request):
    """
        Plays the first ingredient
    """

    db = Database(request.user_id())
    ingStepNum = int(db.getItem("IngStep"))
    dirStepNum = int(db.getItem("DirStep"))
    totalIng = int(db.getRecipeItem("TotalIng"))
    totalStep = int(db.getRecipeItem("TotalStep"))
    outMessage = ""

    if (ingStepNum < 0 and dirStepNum < 0):
        # if both our steps are -1 then we start with
        # ingredients first
        db.setItem("IngStep", 0)
        ingStepNum = 0
        outMessage = "You'll need: "

    if (ingStepNum >= 0 and ingStepNum < totalIng):
        # set our outMessage to be the ingredient
        # and then update our ingredient counter
        outMessage += db.getNextIngredient()
        db.setItem("IngStep", ingStepNum + 1)
        db.setItem("DirStep", -1)

        if (ingStepNum + 1 == totalIng):
            outMessage = "Now, here are the directions: "
            db.setItem("DirStep", 0)
            db.setItem("IngStep", -1)

    elif (dirStepNum >= 0 and dirStepNum < totalStep):
        outMessage += db.getNextStep()
        db.setItem("IngStep", -1)
        db.setItem("DirStep", dirStepNum + 1)

    if (dirStepNum == totalStep and ingStepNum < 0):
        outMessage = "That's the whole recipe! Enjoy your meal! Cookmate: out."
        return r.create_response(message=outMessage, end_session=True)

    return r.create_response(message=outMessage,
                             reprompt_message="Say next to continue",
                             end_session=True)


class Database:

    TABLENAME = "Link"
    RECIPETABLE = "Recipe"

    def __init__(self, user_id = None):
        self.client = boto3.client('dynamodb')
        self.user_id = user_id

    def updateChoice(self, choiceNum): 
        """
            update the users choice
        """
        self.client.update_item(TableName=self.TABLENAME,
                        Key={
                        "UserID": {"S": self.user_id},
                    },
                        UpdateExpression="SET Choice = :val1",
                        ExpressionAttributeValues={
                        ':val1': {"N": choiceNum}
                    },
                        ReturnValues="UPDATED_NEW"
                    )

    def updateLinks(self, topRecipes):
        self.client.update_item(TableName=self.TABLENAME,
                    Key={
                        "UserID": {"S": self.user_id},
                    },
                    UpdateExpression="set URLS = :a",
                    ExpressionAttributeValues={
                        ":a": {"SS": [topRecipes[0][1],
                                      topRecipes[1][1],
                                      topRecipes[2][1]
                                     ]
                            }
                        },
                    ReturnValues="UPDATED_NEW"
                )

    def getLink(self, choiceNum):
        """
            gets the top 3 links for the specific recipe
        """
        results = self.client.get_item(TableName=self.TABLENAME,
                    Key={
                    "UserID": {"S": self.user_id}
                },
                    ProjectionExpression="URLS"
                )
        
        return results['Item']['URLS']['SS'][int(choiceNum) - 1]
    

    def getItem(self, key):

        result = self.client.get_item(TableName=self.TABLENAME,
                    Key={
                    "UserID": {"S": self.user_id}
                },
                    ProjectionExpression=key
                )
        return int(result['Item'][key]['N'])

    def getRecipeInfo(self, key):
        result = self.client.get_item(TableName=self.RECIPETABLE,
                    Key={
                    "UserID": {"S": self.user_id}
                },
                    ProjectionExpression=key
                )
        return result['Item'][key]['S']


    def getRecipeItem(self, key):

        result = self.client.get_item(TableName=self.RECIPETABLE,
                    Key={
                    "UserID": {"S": self.user_id}
                },
                    ProjectionExpression=key
                )
        return int(result['Item'][key]['N'])

    def getAllIngredients(self):
        results = self.client.get_item(TableName=self.RECIPETABLE,
                    Key={
                    "UserID": {"S": self.user_id}
                },
                    ProjectionExpression="Ingreds"
                )

        return results['Item']['Ingreds']['SS']
        

    def getNextIngredient(self):
        results = self.client.get_item(TableName=self.RECIPETABLE,
                    Key={
                    "UserID": {"S": self.user_id}
                },
                    ProjectionExpression="Ingreds"
                )
        ingStep = int(self.getItem("IngStep"))

        return results['Item']['Ingreds']['SS'][ingStep]

    def getNextStep(self):
        results = self.client.get_item(TableName=self.RECIPETABLE,
                    Key={
                    "UserID": {"S": self.user_id}
                },
                    ProjectionExpression="Steps"
                )
        dirStep = int(self.getItem("DirStep"))

        return results['Item']['Steps']['SS'][dirStep]
    
    def setItem(self, key, count):
        self.client.update_item(TableName=self.TABLENAME,
                    Key={
                        "UserID": {"S": self.user_id},
                    },
                    UpdateExpression="set " + key + " = :val1",
                    ExpressionAttributeValues={
                        ":val1": {"N": str(count)}
                    },
                    ReturnValues="UPDATED_NEW"
                )

    def loadRecipe(self, recipe):
        self.client.put_item(TableName=self.RECIPETABLE,
                Item={
                        "UserID": {"S": self.user_id},
                        "Ingreds": {"SS": recipe.ingredients},
                        "Steps":   {"SS": recipe.steps}
                })

        self.client.update_item(TableName=self.RECIPETABLE,
                        Key={
                        "UserID": {"S": self.user_id},
                    },
                        UpdateExpression="SET CookTime = :val1,"+\
                                         "PrepTime = :val2,"+\
                                         "TotalTime = :val3,"+\
                                         "OvenTemp = :val4,"+\
                                         "NameOfRecipe = :val5,"+\
                                         "NutritionInfo = :val6,"+\
                                         "TotalStep = :val9,"+\
                                         "TotalIng = :val10",
                        ExpressionAttributeValues={
                        ':val1': {"S": str(recipe.cookTime)},
                        ':val2': {"S": str(recipe.prepTime)},
                        ':val3': {"S": str(recipe.totalTime)},
                        ':val4': {"N": str(recipe.ovenTemp)},
                        ':val5': {"S": str(recipe.nameOfRecipe)},
                        ':val6': {"S": str(recipe.nutritionInfo)},
                        ':val9': {"N": str(len(recipe.steps))},
                        ':val10': {"N": str(len(recipe.ingredients))}
                    },
                        ReturnValues="UPDATED_NEW"
                    )



#helper class to conver a DynamoDB to JSON
class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            if o % 1 > 0:
                return float(o)
            else:
                return int(o)

        return super(DecimalEncoder, self).default(o)

