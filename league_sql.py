#!/usr/bin/env python
# coding: utf-8

# https://leportella.com/english/2019/01/10/sqlalchemy-basics-tutorial.html?fbclid=IwAR15Ck3iit3b1kfd4iE3ZhNtEHbvs8mP7gHgAaguy0Ts9VNBD7AurRKn3zM
import sqlalchemy
import single_user_blitz_grabber
import os
import importlib
import pandas as pd

saved_csv_fname = 'user_dat_csv'

engine = sqlalchemy.create_engine('mysql://root:Ironmaiden1!@localhost/duvet_cover_matches') # connect to server
engine.connect()

with engine.connect() as connection:
    result = connection.execute("""DROP TABLE matches""")


with engine.connect() as connection:
    result = connection.execute("""CREATE TABLE matches (acct_id VARCHAR(50), match_id INT(100), match_rank VARCHAR(10), 
                                role VARCHAR(10), champ VARCHAR(10), win FLOAT(2), kills FLOAT(3), deaths FLOAT(3),
                                assists FLOAT(3), gold_earned FLOAT(20), player_top VARCHAR(20), player_jung VARCHAR(20),
                                player_mid VARCHAR(20), player_ADC VARCHAR(20), player_supp VARCHAR(20), opp_top VARCHAR(20),
                                opp_jung VARCHAR(20), opp_mid VARCHAR(20), opp_ADC VARCHAR(20), opp_supp VARCHAR(20))""")


## Parameters
if os.path.exists(saved_csv_fname):
    pd.read_csv(saved_csv_fname)
else:
    APIKey = os.environ.get('League_API')
    region = 'na1'
    summoner_name = 'Duvet Cover'
    importlib.reload(single_user_blitz_grabber)
    df_user_matches = single_user_blitz_grabber.main_grab_data(region, summoner_name, APIKey)


df_user_matches.to_csv(saved_csv_fname)

##
df_user_matches.to_sql(con=engine, name='matches', if_exists='replace')



with engine.connect() as connection:
    result = connection.execute("SELECT * FROM matches")
    for row in result:
        print("username:", row['champ'])






