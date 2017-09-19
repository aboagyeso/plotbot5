# Dependencies
import matplotlib
matplotlib.use('Agg')
import tweepy, time, json
import pandas as pd
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import matplotlib.pyplot as plt
import datetime, re, os, pytz

# Setting timezone to EST
timezone = pytz.timezone("US/Eastern")

# Create sentiment analyser object
analyzer = SentimentIntensityAnalyzer()

# Variable assignment
consumer_key = os.environ['twtconkey']
consumer_secret = os.environ['twtconsec']
access_token = os.environ['twtacctok']
access_token_secret = os.environ['twtaccsec']
dt = datetime.datetime.today().strftime('%m/%d/%y')
dt1 = datetime.datetime.today().strftime('%m-%d-%y')
sinceId_gbl = 908927652945383425
analysedList = []

# Tweepy API Authentication
auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
auth.set_access_token(access_token, access_token_secret)
api = tweepy.API(auth, wait_on_rate_limit=True, wait_on_rate_limit_notify=True)

myUsrDtls = api.me()
myScreenName = "@" + myUsrDtls.screen_name

# Create function to get tweets requesting for analysis
# returns a list of lists with eahc tweet specific tweetId, requestedUser, targetedUser
def getTargettedTweets(sinceId_lcl):

    global sinceId_gbl
    twtInfo_lst = []
    
    for page in tweepy.Cursor(api.mentions_timeline, since_id=sinceId_lcl, wait_on_rate_limit=True, wait_on_rate_limit_notify=True).pages(2):
        for tweet in page:
            tweetInfo = json.dumps(tweet._json, indent=3)
            tweetInfo = json.loads(tweetInfo)
            twtText = tweetInfo["text"]
            if sinceId_gbl == sinceId_lcl:
                sinceId_gbl = tweetInfo["id"]
            if (myScreenName in twtText) and ("Analyse" in twtText):
                userInfo = []
                sinceId = tweetInfo["id"]
                twted_user = "@"+tweetInfo['user']['screen_name']
                trgted_user = "@"+tweetInfo['entities']['user_mentions'][1]['screen_name']
                userInfo.append(sinceId)
                userInfo.append(twted_user)
                userInfo.append(trgted_user)
                twtInfo_lst.append(userInfo)
    return twtInfo_lst

# Function to perform sentiment analysis of a specific user's latest 500 tweets
# Reply back to original request tweet with the sentiment plot 
def analyseUserTweets(trgtUsrInfo):
    compound_list, twtsAgo_list, screenName_list = [], [], []
    tweetsAgo = 0

    for page in tweepy.Cursor(api.user_timeline, id=trgtUsrInfo[2], wait_on_rate_limit=True, wait_on_rate_limit_notify=True).pages(25):
        for tweet in page:
            tweetInfo = json.dumps(tweet._json, indent=3)
            tweetInfo = json.loads(tweetInfo)
            target_string = tweetInfo['text']
            sentmt = analyzer.polarity_scores(target_string)
            compound_list.append(sentmt['compound'])
            screenName_list.append(tweetInfo['user']['screen_name'])
            twtsAgo_list.append(tweetsAgo)
            tweetsAgo = tweetsAgo + 1
    
    # Create dataframe to plot the graph
    df = pd.DataFrame({'Tweets Ago':twtsAgo_list,'Compound Sentiments':compound_list,'ScreenName':screenName_list})

    # Plot the graph, save it as an image and tweet it back onto the original tweet
    g = plt.plot(df['Tweets Ago'],df['Compound Sentiments'],marker='o',markersize=10)
    g = plt.gca()
    g.invert_xaxis()
    plt.xlabel('Tweets Ago')
    plt.ylabel('Tweet Polarity')
    plt.title('Sentiment Analysis of Tweets ('+dt+')')
    plt.legend(title='Tweets',bbox_to_anchor=(1, 1), loc='upper left', ncol=1,labels='@'+df['ScreenName'])
    fileName = 'SentimentAnalysis_'+trgtUsrInfo[2][1:]+'.png'
    plt.savefig(fileName, bbox_inches='tight')
    api.update_with_media(fileName, trgtUsrInfo[1]+" As per your request, see the tweet sentiments analysis for user: "+trgtUsrInfo[2], in_reply_to_status_id=trgtUsrInfo[0])
    plt.gcf().clear()
    os.remove(fileName)

# Infinite loop to keep checking on latest requests to analyse sentiment every 15 minutes
while(True):
    trgt_twts_lst = getTargettedTweets(sinceId_gbl)

    for trgt_twt in trgt_twts_lst:
        twtToAnalyse = trgt_twt[2] + "_" + dt1
        if twtToAnalyse in analysedList:
            api.update_status(trgt_twt[1]+" We have already analysed tweet sentiments for user "+trgt_twt[2]+ " earlier today, hence skipping..", in_reply_to_status_id=trgt_twt[0])
        else:
            analysedList.append(twtToAnalyse)
            analyseUserTweets(trgt_twt)
            
    api.update_status("Next sentiment analysis will be performed at- " + (datetime.datetime.now().replace(tzinfo=pytz.utc).astimezone(timezone) + datetime.timedelta(minutes = 1)).strftime('%m-%d-%y %H:%M:%S') + " EST.")
    time.sleep(60)
