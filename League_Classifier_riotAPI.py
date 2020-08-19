# -*- coding: utf-8 -*-
"""
Created on Sat May  4 17:22:12 2019

Objective: Load and clean League of Legends game data to identify important 
    game features that contribute and predict game outcome. This is important 
    because the goal of many players is to identify aspects of the game to improve
    on and the analyses outlined below is generalizable to all skill-based games
    and sports.
    
Data from: https://github.com/DoransLab/data/tree/master/champion_clustering

@author: Zhe Charles Zhou
"""

#### Import toolboxes

import numpy as np
import pandas as pd

import matplotlib.pyplot as plt
import seaborn as sns

# use riotAPI_matchInfo for individual match info; riotAPI_avgMatchInfo to take avg across all matches for each sample
from riotAPI_avgMatchInfo import dfPlayer, dataYPlayer # IMPORTANT: separate script to pull data from RiotAPI for specific player data


from skopt import BayesSearchCV
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.model_selection import GridSearchCV,train_test_split,cross_val_score
from sklearn.metrics import classification_report,confusion_matrix
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_curve, roc_auc_score
import warnings
warnings.filterwarnings('ignore')

#### Load data

data=pd.read_csv("C:\\Users\\The Iron Maiden\\Documents\\DataScienceProjects\\totalSup.csv")

# make the column names reference-friendly
data.columns = data.columns.str.strip().str.lower().str.replace(' ', '_')
print(data.columns)

# separate category and feature data
dataX_all=data.drop('win',axis=1)
dataY=data['win']

# define columns to analyze
columns2Keep = ['champion_name','match_rank_score','max_time','gold_earned','wards_placed','damage_dealt_to_objectives','damage_dealt_to_turrets','kda','total_damage_dealt_to_champions', 'total_damage_taken', 'total_minions_killed']
dataX = dataX_all[columns2Keep]

# append player data for on hot encoding and scaling
numPlayerSamps = dfPlayer.shape[0]

###### Logistic regression Data Preprocessing

# Define which columns should be encoded vs scaled
columns_to_encode = ['champion_name']
columns_to_scale  = columns2Keep[1:]
# we're going to encode the categorical data together (dataX + player) since we might find new champions in the player data
dataToEncode_plusPlayer = dataX[columns_to_encode].append(dfPlayer[columns_to_encode])

# Instantiate encoder/scaler
scaler = StandardScaler()
ohe    = OneHotEncoder(sparse=False)
# Scale and Encode the continuous and categorical data separately
scaled_columnsX  = scaler.fit_transform(dataX[columns_to_scale]) 
encoded_columns =    ohe.fit_transform(dataToEncode_plusPlayer)

scaled_columns_player  = scaler.transform(dfPlayer[columns_to_scale]) 

# IMPORTANT: split appended player data off after one hot encoding 
encodedColumnsX = encoded_columns[:-numPlayerSamps,:]
encodedColumns_Player = encoded_columns[-numPlayerSamps:,:]

# Concatenate (Column-Bind) Processed Columns Back Together
processedX = np.concatenate([scaled_columnsX, encodedColumnsX], axis=1)
processedPlayerX = np.concatenate([scaled_columns_player, encodedColumns_Player], axis=1)


# from scikitlearn: split data into test and training sets
xTrain,xTest,yTrain,yTest=train_test_split(processedX,dataY,test_size=0.2,random_state=42)

###### Logistic regression

params_lrc=[
{
    'penalty':['l1','l2'],
    'C':[ 0.01, 0.1,1, 10],
    'random_state':[0]
    },
]


lrc=LogisticRegression()

gs_model = GridSearchCV(lrc, params_lrc,  cv= 5, scoring='accuracy') 
gs_model.fit(xTrain, yTrain)
print('Best parameters set:')
print(gs_model.best_params_)

pred = gs_model.predict(xTest)

from sklearn.metrics import accuracy_score
print('Optimized logistic regression performance: ',
      round(accuracy_score(yTest,pred),5)*100,'%')

# save the model to disk
#filename = 'final_logRegLoL.sav'
#pickle.dump(gs_model, open(filename, 'wb'))
#gs_model = pickle.load(open(filename, 'rb'))

#### examine contribution of variables to win

numVars = len(columns_to_scale)

bestLR=LogisticRegression(C=1,penalty='l1',random_state=0)
bestLR.fit(xTrain, yTrain)

logCoefs = bestLR.coef_

x_labels = ['Rank','MaxTime','Gold','Wards','ObjDmg','TurretDmg','KDA','ChampDmg', 'dmgTaken', 'minion#','percDmgTaken']
plt.bar(columns_to_scale[0:numVars],logCoefs[0,0:numVars])
plt.ylabel('Coef Score')
plt.xticks(np.arange(numVars), x_labels, rotation = 45, fontsize=13 )
plt.title('Log Reg Coef Scores')

# plot absolute value of coeff and sort by highest coeff

logCoefs_abs = abs(bestLR.coef_)
logCoefs_absSort = sorted(logCoefs_abs[0,0:numVars],reverse=True)
sortedInds = np.argsort(-logCoefs_abs[0,0:numVars])

plt.figure(figsize=(10,5))
plt.bar(columns_to_scale[0:numVars],logCoefs_absSort)
plt.ylabel('Coefficient Score (Impact)', fontsize=25)
plt.xticks(np.arange(numVars), [x_labels[i] for i in sortedInds], rotation = 45, fontsize=17 ) # need to reorder x labels according to sorting of coeffs
plt.yticks(fontsize=20)
plt.title('Player Metrics Sorted by Impact on Win/Loss', fontsize=27)

#### calculate model performance for test data

## calculate predicted probability
#prob = gs_model.predict_proba(xTest)[:,1]
## calculate true and false pos 
#falsePos,truePos,thresh = roc_curve(yTest,prob)
##Calculate area under the curve
#AUCscore = roc_auc_score(yTest,prob)
#
## ROC plot
#sns.set_style('whitegrid')
#plt.figure(figsize=(8,5))
#
#plt.plot(falsePos,truePos)
#plt.plot([0,1],ls='--')
#plt.plot([0,0],[1,0],c='.5')
#plt.plot([1,1],c='.5')
#
#plt.title('ROC Curve; AUC = ' + str(round(AUCscore,5)) + '; Model Test Accuracy = ' + str(round(accuracy_score(yTest,pred),3)*100) + '%')
#plt.ylabel('True positive rate')
#plt.xlabel('False positive rate')
#plt.show()

#### Now predict game outcome for player data pulled from riot API

pred = gs_model.predict(processedPlayerX)

print('Optimized logistic regression performance: ',
      round(accuracy_score(dataYPlayer,pred),5)*100,'%')

# calculate predicted probability
prob = gs_model.predict_proba(processedPlayerX)[:,1]
# calculate true and false pos 
falsePos,truePos,thresh = roc_curve(dataYPlayer,prob)
#Calculate area under the curve
AUCscore = roc_auc_score(dataYPlayer,prob)

# ROC plot
sns.set_style('whitegrid')
plt.figure(figsize=(8,5))

plt.plot(falsePos,truePos)
plt.plot([0,1],ls='--')
plt.plot([0,0],[1,0],c='.5')
plt.plot([1,1],c='.5')

plt.title('ROC Curve; AUC = ' + str(round(AUCscore,5)) + '; Model Test Accuracy = ' + str(round(accuracy_score(dataYPlayer,pred),3)*100) + '%',fontsize = 20)
plt.ylabel('True positive rate',fontsize = 20)
plt.xlabel('False positive rate',fontsize = 20)
plt.yticks(fontsize=20)
plt.xticks(fontsize=20)
plt.show()

######

tmpDf = pd.DataFrame(np.array([[1,10], [2,100],[3,50] ]),columns = ['var1','var2'])
tmpNormDf=( df_2norm-df_2norm.min() )/( df_2norm.max()-df_2norm.min() )

import plotly.graph_objects as go

# append column for data group
tmpData = dataX.drop('champion_name',axis=1).assign(Group='data')
tmpDataPlayer = dfPlayer.drop('champion_name',axis=1).assign(Group='player')
allDataWithPlayer = tmpData.append(tmpDataPlayer, ignore_index=True)

# normalize (0-1) ccontinuous data and add back on group
df_2norm = allDataWithPlayer.iloc[:,1:-1]
normalized_df=( df_2norm-df_2norm.min() )/( df_2norm.max()-df_2norm.min() )
normalized_df['Group']=allDataWithPlayer['Group']

col2Group = columns2Keep[1:-1]
justDataData = normalized_df.loc[normalized_df['Group'] == 'data']
norm_dataMean = justDataData[0:1000].mean(axis=0)
norm_playerMean = normalized_df.loc[normalized_df['Group'] == 'player'].mean(axis=0)

#################

categories = columns2Keep[1:-1]

fig = go.Figure()

fig.add_trace(go.Scatterpolar(
      r=norm_dataMean,
      theta=categories,
      fill='toself',
      name='Average Player Performance'
))

fig.add_trace(go.Scatterpolar(
      r=norm_playerMean,
      theta=categories,
      fill='toself',
      name='Your Performance'
))

fig.update_layout(
  polar=dict(
    radialaxis=dict(
      visible=True,
     
    )),
  showlegend=True
)
# fig.show()
plot(fig, auto_open=True)



