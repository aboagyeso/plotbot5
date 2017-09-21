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

# Create sentiment analyzer object
analyzer = SentimentIntensityAnalyzer()

# Variable assignment
consumer_key = os.environ['twtconkey']
consumer_secret = os.environ['twtconsec']
access_token = os.environ['twtacctok']
access_token_secret = os.environ['twtaccsec']

dt = datetime.datetime.today().strftime('%m/%d/%y')
mth = datetime.datetime.today().strftime('%m-%y')
analyzedAccts_lst, pendingAnalysis_lst, analysisRequestedFor_lst = [], [], []
analyzedAccWithTime = {}

# Tweepy API Authentication
auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
auth.set_access_token(access_token, access_token_secret)
api = tweepy.API(auth, wait_on_rate_limit=True, wait_on_rate_limit_notify=True)

myUsrDtls = api.me()
myScreenName = "@" + myUsrDtls.screen_name

# Function to perform sentiment analysis of a specific user's latest 500 tweets 
# & reply back to request tweet with the plot.
def analyzeUserTweets(trgtUsrInfo):

    compound_list, twtsAgo_list, screenName_list = [], [], []
    tweetsAgo = 0

    try:
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
        return True
    except:
        return False


# Create function to get tweets requesting for analysis
# Add the tweet data (tweet id, requester & target account) into a 2 lists: 
# i).  All requests 
# ii). Pending requests
def getLatestRequests():

    global analysisRequestedFor_lst
    global pendingAnalysis_lst

    try:
        for tweet in tweepy.Cursor(api.search, q=myScreenName, count=20, result_type="recent", include_entities=True, lang="en", wait_on_rate_limit=True, wait_on_rate_limit_notify=True).items():
            tweetInfo = json.dumps(tweet._json, indent=3)
            tweetInfo = json.loads(tweetInfo)
            twtText = tweetInfo["text"]
            if (myScreenName in twtText) and (("Analyze" in twtText) or ("analyze" in twtText)):
                userInfo = []
                twt_id = tweetInfo["id"]
                twted_user = "@"+tweetInfo['user']['screen_name']
                trgted_user = "@"+tweetInfo['entities']['user_mentions'][1]['screen_name']
                userInfo.append(twt_id)
                userInfo.append(twted_user)
                userInfo.append(trgted_user)
                if userInfo in analysisRequestedFor_lst:
                    pass
                else:
                    analysisRequestedFor_lst.append(userInfo)
                    pendingAnalysis_lst.append(userInfo)
    except:
        pass

# Infinite loop to keep checking on latest requests to analyze sentiment every 15 minutes
while(True):
    getLatestRequests()
    if (len(pendingAnalysis_lst) == 0):
        pass
    else:
        twtDtls = pendingAnalysis_lst[0]
        acctToAnalyze = twtDtls[2] + "_" + mth
        isAnalyzed = False
        if acctToAnalyze in analyzedAccts_lst:
            try: 
                api.update_status(twtDtls[1]+" Analyzed "+twtDtls[2]+ " on "+ analyzedAccWithTime[acctToAnalyze] + ". Sorry now: "+ (datetime.datetime.utcfromtimestamp(time.time()).replace(tzinfo=pytz.utc).astimezone(timezone)).strftime('%m-%d-%y %H:%M:%S')+" "+(datetime.datetime.utcfromtimestamp(time.time()).replace(tzinfo=pytz.utc).astimezone(timezone)).tzname() +". Check homepage for report or try next month.", in_reply_to_status_id=twtDtls[0])
                isAnalyzed = True
            except:
                isAnalyzed = False
        else:
            isAnalyzed = analyzeUserTweets(twtDtls)
            if isAnalyzed:
                analyzedAccts_lst.append(acctToAnalyze)
                analyzedAccWithTime[acctToAnalyze] = (datetime.datetime.utcfromtimestamp(time.time()).replace(tzinfo=pytz.utc).astimezone(timezone)).strftime('%m-%d-%y')
        del pendingAnalysis_lst[0]
    time.sleep(300)
