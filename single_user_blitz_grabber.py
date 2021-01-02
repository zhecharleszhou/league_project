#!/usr/bin/env python
# coding: utf-8

# In[67]:


# guide : https://riot-api-libraries.readthedocs.io/en/latest/collectingdata.html 

import os
import requests
import pandas as pd
from cassiopeia import Champion, Champions
import pickle
import time


# In[92]:


## Get account details by providing the account name
def requestSummonerData(region,summonerName, APIKey):
    URL = f"https://{region}.api.riotgames.com/lol/summoner/v4/summoners/by-name/{summonerName}?api_key={APIKey}"
    response = requests.get(URL)
    return response.json()

def requestSummonerPerformance(region,summoner_id, APIKey):
    URL = "https://{}.api.riotgames.com/lol/league/v4/entries/by-summoner/{}?api_key={}".format(region,summoner_id,APIKey)
    response = requests.get(URL)
    return response.json()

def requestMatchList(region,acctID, APIKey):
    URL = f"https://{region}.api.riotgames.com/lol/match/v4/matchlists/by-account/{acctID}?api_key={APIKey}"
    response = requests.get(URL)
    return response.json()

def requestMatchInfo(region,matchID, APIKey):
    URL = "https://{}.api.riotgames.com/lol/match/v4/matches/{}?api_key={}".format(region,matchID,APIKey)
    response = requests.get(URL)
    return response.json()

def requestLeagueInfo(region,leagueID, APIKey):
    URL = "https://{}.api.riotgames.com/lol/league/v4/leagues/{}?api_key={}".format(region,leagueID,APIKey)
    response = requests.get(URL)
    return response.json()


# load champion names and IDs
def define_champ_names():
    df_champs = pd.DataFrame(columns=['champion_name','champion_ID'])
    champions = Champions(region="NA")
    index = 0
    for champion in champions:
            df_champs.loc[index] = [champion.name, champion.id ]
            index+=1
    return df_champs


def find_player_idx(match_info, summoner_name, acct_ID):
    # find index of player in player list
    for idx, participant in enumerate(match_info['participantIdentities']):
        if participant['player']['accountId'] == acct_ID and participant['player']['summonerName'] == summoner_name:
            player_key = idx
            
    return player_key

def calc_kda(statsDict): 
    if statsDict['deaths'] == 0:
        kda = statsDict['kills'] + statsDict['assists']
    else:
        kda = ( statsDict['kills'] + statsDict['assists'] ) / statsDict['deaths']
    return kda


def get_highest_rank(matchInfo, playerKey):
    if 'highestAchievedSeasonTier' not in matchInfo['participants'][playerKey]:
        thisRank = 'Unranked'
        matchRank = 0
    else:
        thisRank = matchInfo['participants'][playerKey]['highestAchievedSeasonTier']
        matchRank = rankNames.index(thisRank) + 1
    return matchRank


# In[93]:


def main_grab_data(region, summoner_name, APIKey):
    
    print(summoner_name)
    
    # initialize info
    df_user_matches = pd.DataFrame()
    dfChampNames = define_champ_names()
    
    # grab summoner data
    summoner_dat = requestSummonerData(region,summoner_name, APIKey)
    if 'accountId' in summoner_dat:
        acctID = summoner_dat['accountId']
    else:
        raise Exception('Invalid API key')
    
    # grab summoner general performance stats
    summoner_performance = requestSummonerPerformance(region,summoner_dat['id'], APIKey)
    player_rank = summoner_performance[0]['tier']

    # grab summoner match list
    matchList = requestMatchList(region,acctID, APIKey)
    numMatches = len(matchList ['matches'])

    # go through each match
    for iMatch in range(numMatches):

        # need to pause bc of rate limits for riotAPI
        if iMatch%40 == 0 and iMatch != 0: 

            time.sleep(121)

        matchID = matchList['matches'][iMatch]['gameId'] # get this match's ID

        # get request match data and extract metrics from match info
        match_info = requestMatchInfo(region,matchID, APIKey) # pull this game's info from riotAPI
        max_time = match_info['gameDuration']
        game_version = match_info['gameVersion']
        player_key = find_player_idx(match_info, summoner_name, acctID)
        stats_dict = match_info['participants'][player_key]['stats'] # get stats dict from this game
        playerTeam = match_info['participants'][player_key]['teamId']

        ############ preprocess data

        # calculate KDA
        kda = calc_kda(stats_dict)

        # figure out champion name from ID
        thisChampionID = match_info['participants'][player_key]['championId']
        tfIndex = dfChampNames['champion_ID'] == thisChampionID
        champName = dfChampNames[tfIndex]['champion_name'].item()

        # figure out player's match rank
        #match_rank = get_highest_rank(match_info, player_key)

        # get role and lane
        role = match_info['participants'][player_key]['timeline']['role']
        lane = match_info['participants'][player_key]['timeline']['lane']
        teamID = match_info['participants'][player_key]['teamId'] 

        all_player_dict = {}
        for iParticipant in range(0, 10):
            this_role = match_info['participants'][iParticipant]['timeline']['role']
            this_lane = match_info['participants'][iParticipant]['timeline']['lane']
            this_teamID = match_info['participants'][iParticipant]['teamId']

            thisPlayerChampionID = match_info['participants'][iParticipant]['championId']
            champIndex = dfChampNames['champion_ID'] == thisPlayerChampionID
            thisChampName =  dfChampNames[champIndex]['champion_name'].item()

            tmpID = f"{this_role}_{this_lane}"

            if this_lane == 'TOP' and this_teamID == teamID: 
                all_player_dict['player_top'] = thisChampName
            elif this_lane == 'JUNGLE' and this_teamID == teamID:
                all_player_dict['player_jung'] = thisChampName
            elif this_lane == 'MIDDLE' and this_teamID == teamID:
                all_player_dict['player_mid'] = thisChampName
            elif this_role == 'DUO_CARRY' and this_teamID == teamID:
                all_player_dict['player_ADC'] = thisChampName
            elif 'DUO_SUPPORT' in this_role and this_teamID == teamID:
                all_player_dict['player_supp'] = thisChampName
            elif this_lane == 'TOP' and this_teamID != teamID:
                all_player_dict['opp_top'] = thisChampName
            elif this_lane == 'JUNGLE' and this_teamID != teamID:
                all_player_dict['opp_jung'] = thisChampName
            elif this_lane == 'MIDDLE' and this_teamID != teamID:
                all_player_dict['opp_mid'] = thisChampName
            elif 'DUO_CARRY' in this_role and this_teamID != teamID:
                all_player_dict['opp_ADC'] = thisChampName
            elif 'DUO_SUPPORT' in this_role and this_teamID != teamID:
                all_player_dict['opp_supp'] = thisChampName


        if len(all_player_dict) != 10:
            continue

        ############ put data together 

        if role in ['SOLO','NONE']:
            true_role = lane
        else:
            true_role = role


        ######### add data to dataframes to save
        if df_user_matches.shape[0] == 0:
            next_idx = 0
        else:
            next_idx = df_user_matches.index[-1]+1

        df_user_matches.loc[next_idx, 'acct_id'] = acctID
        df_user_matches.loc[next_idx, 'match_id'] = matchID
        df_user_matches.loc[next_idx, 'match_rank'] = player_rank
        df_user_matches.loc[next_idx, 'role'] = role
        df_user_matches.loc[next_idx, 'champ'] = champName
        df_user_matches.loc[next_idx, 'win'] = int(stats_dict['win'])

        df_user_matches.loc[next_idx, 'kills'] = stats_dict['kills']
        df_user_matches.loc[next_idx, 'deaths'] = stats_dict['deaths']
        df_user_matches.loc[next_idx, 'assists'] = stats_dict['assists']
        df_user_matches.loc[next_idx, 'gold_earned'] = stats_dict['goldEarned']
        df_user_matches.loc[next_idx, 'vision_score'] = stats_dict['visionScore']
        df_user_matches.loc[next_idx, 'crowd_control_time'] = stats_dict['timeCCingOthers']
        df_user_matches.loc[next_idx, 'dmg_taken'] = stats_dict['totalDamageTaken']
        df_user_matches.loc[next_idx, 'dmg_dealt'] = stats_dict['totalDamageDealt']
        df_user_matches.loc[next_idx, 'objective_dmg'] = stats_dict['damageDealtToObjectives']
        df_user_matches.loc[next_idx, 'acct_id'] = acctID

        df_user_matches.loc[next_idx, 'player_top'] = all_player_dict['player_top']
        df_user_matches.loc[next_idx, 'player_jung'] = all_player_dict['player_jung']
        df_user_matches.loc[next_idx, 'player_mid'] = all_player_dict['player_mid']
        df_user_matches.loc[next_idx, 'player_ADC'] = all_player_dict['player_ADC']
        df_user_matches.loc[next_idx, 'player_supp'] = all_player_dict['player_supp'],

        df_user_matches.loc[next_idx, 'opp_top'] = all_player_dict['opp_top']
        df_user_matches.loc[next_idx, 'opp_jung'] = all_player_dict['opp_jung']
        df_user_matches.loc[next_idx, 'opp_mid'] = all_player_dict['opp_mid']
        df_user_matches.loc[next_idx, 'opp_ADC'] = all_player_dict['opp_ADC'] 
        df_user_matches.loc[next_idx, 'opp_supp'] = all_player_dict['opp_supp']

        print('Added match #' + str(iMatch))

    return df_user_matches


# In[94]:


if __name__ == "__main__":
    
    ## Parameters
    APIKey = os.environ.get('League_API')
    region = 'na1'
    summoner_name = 'Duvet Cover'
    flag_save_load = 0 # 1 if save, 2 if load
    
    df_user_matches = main_grab_data(region,summoner_name, APIKey)
    
    if flag_save_load == 1:
        with open(r'.\sample_match_info.pkl', 'wb') as handle:
            pickle.dump(match_info, handle, protocol=pickle.HIGHEST_PROTOCOL)
    
    elif flag_save_load == 2:
        with open(r'.\sample_match_info.pkl', 'rb') as handle:
            match_info = pickle.load(handle)





