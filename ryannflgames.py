import nflgame as nfl
import pandas as pd
import numpy as np

#variable for year
year = 2016
#variale for number of teams in league
leaguesize = 14
#variables for cut offs and pos tiers by week
onernkcutoff = leaguesize
twornkcutoff = leaguesize * 2

#League scoring system variables
pts_r_yds = 0.1 #rushing/receiving yards
pts_r_tds = 6 #rushing/receiving TDs
pts_r_recs = 0 #receptions
pts_r_atts = 0 #rushing attempts
pts_p_yds = 0.04 #passing yards
pts_p_tds = 4 #passing tds
pts_p_ints = -2 #interceptions
pts_fumbles_lost = -2 #fumbles lost
pts_twoptm = 2 #two point conversions
pts_ret_tds = 6 #return TDs
pts_fumble_tds = 6 #fumble recovery TDs

#Pull player information into playersdf data frame
players = []
allgames = nfl.games(year)
allplayers = nfl.combine(allgames)
for p in allplayers:
    if hasattr(p.player,'gsis_id') and p.player.position in ("QB","RB","WR","TE"):
        d1 = {  "PlayerID" : p.player.gsis_id,
                "Name" : p.player.full_name,
                "Position" : p.player.position,
                "Team" : p.player.team
                }
        players.append(d1)
playersdf = pd.DataFrame(players)

#print playersdf.loc[playersdf['Position'] == "RB"]

#pull fantasy points by week for those players into statspivot data frame
stats = []
for wk in range(1,18):
    games = nfl.games(year,week=wk)
    players = nfl.combine_game_stats(games)
    for p in players:
        if hasattr(p.player,'gsis_id') and p.player.position in ("QB","RB","WR","TE"):
            d2 = {"Week" : 'Week' + str(wk),
                 "Year" : year,
                 "PlayerID" : p.player.gsis_id,
                 "Rushing Yards" : p.rushing_yds,
                 "Rushing TDs" : p.rushing_tds,
                 "Rushing Atts" : p.rushing_att,
                 "Receiving Yards" : p.receiving_yds,
                 "Receiving TDs" : p.receiving_tds,
                 "Targets" : p.receiving_tars,
                 "Receptions" : p.receiving_rec,
                 "Passing Yards" : p.passing_yds,
                 "Passing TDs" : p.passing_tds,
                 "Passing INTs" : p.passing_ints,
                 "Fumbles Lost" : p.fumbles_lost,
                 "Fumble Recovery TDs" : p.fumbles_rec_tds,
                 "2-Pt Conversions" : (p.passing_twoptm + p.rushing_twoptm + p.receiving_twoptm),
                 "Return TDs" : (p.puntret_tds + p.kickret_tds),
                 "FanPts" :   ((p.rushing_yds + p.receiving_yds) * pts_r_yds)
                            + ((p.rushing_tds + p.receiving_tds) * pts_r_tds)
                            + (p.receiving_rec * pts_r_recs)
                            + (p.rushing_att * pts_r_atts)
                            + (p.passing_yds * pts_p_yds)
                            + (p.passing_tds * pts_p_tds)
                            + (p.passing_ints * pts_p_ints)
                            + (p.fumbles_lost * pts_fumbles_lost)
                            + ((p.passing_twoptm + p.rushing_twoptm + p.receiving_twoptm) * pts_twoptm)
                            + ((p.puntret_tds + p.kickret_tds) * pts_ret_tds)
                            + (p.fumbles_rec_tds * pts_fumble_tds)
                 }
            stats.append(d2)
statsdf = pd.DataFrame(stats)
statspivot = pd.pivot_table(statsdf, values = 'FanPts', index = 'PlayerID', columns = 'Week')


#join these two tables together to get full table of players and fantasy points
joindf = statspivot.join(playersdf.set_index('PlayerID'))
joindf = joindf.fillna(0)


#add column of rank based on position for each player and week, and a flag if that was above or below certain position cutoff
for wkrnk in range (1,18):
    newcolnm = 'Week' + str(wkrnk) + 'Rank'
    colnm = 'Week' + str(wkrnk)
    newcolnmflagone = 'Week' + str(wkrnk) + 'OneFlag'
    newcolnmflagtwo = 'Week' + str(wkrnk) + 'TwoFlag'
    joindf[newcolnm] = joindf.groupby(['Position'])[colnm].rank(ascending=False)
    joindf[newcolnmflagone] = np.where(joindf[newcolnm]<=onernkcutoff+0.9,1,0)
    joindf[newcolnmflagtwo] = np.where(joindf[newcolnm]<=twornkcutoff+0.9,1,0)
    #add column of binary above/below position rank

flagcols = []
for x in range(1,18):
    onetxt = 'Week'+str(x)+'OneFlag'
    twotxt = 'Week'+str(x)+'TwoFlag'
    flagcols.append(onetxt)
    flagcols.append(twotxt)

rankcols = []
for y in range(1,18):
    ranktxt = 'Week'+str(y)+'Rank'
    rankcols.append(ranktxt)

#unpivot table above and just include binary flags
joindf = joindf.reset_index()
flagcolumns = pd.melt(joindf,id_vars = ['PlayerID'],value_vars = flagcols)
flagcolumns['Flag'] = flagcolumns['variable'].str[-7:]
flagcolumns['Week'] = flagcolumns['variable'].str[:-7]

unpivotrankcolumns = pd.melt(joindf,id_vars = ['PlayerID'],value_vars = rankcols)
unpivotrankcolumns['Week'] = unpivotrankcolumns['variable'].str[:-4]

#aggregate flags and calculate percent 1 or 2 for each player
aggdf = flagcolumns.groupby(['PlayerID','Flag'])['value'].agg(['sum','count'])
aggdf['percent'] = aggdf['sum']/aggdf['count']
aggdf['Year'] = year

finaldf = aggdf.join(playersdf.set_index('PlayerID'))

#create detailed csv for underlying data
unpivotrankcolumns = pd.melt(joindf,id_vars = ['PlayerID'],value_vars = rankcols)
unpivotrankcolumns['Week'] = unpivotrankcolumns['variable'].str[:-4]
del unpivotrankcolumns['variable']
unpivotrankcolumns.columns = ['PlayerID','Rank','Week']

flagcolumnspivot = pd.pivot_table(flagcolumns, values = 'value', index = ['PlayerID','Week'], columns = 'Flag')
flagcolumnspivot = flagcolumnspivot.reset_index()

#left join statdf (includes number of fantasy points) into unpivotrankcolumns (has ranks) on player id and week #
basedata = unpivotrankcolumns.merge(statsdf, how='left', on=['PlayerID','Week'])
basedata = basedata.merge(flagcolumnspivot, how='left', on=['PlayerID','Week'])
basedata = basedata.merge(playersdf,how='left', on='PlayerID')

#Devonta Freeman -  p.player.gsis_id == '00-0031285'
#Tevin Coleman - p.player.gsis_id == '00-0032058'
#CJ Anderson - p.player.gsis_id == '00-0029854'


finaldf.to_csv('percents.csv')
basedata.to_csv('basedata.csv')
print "SUCCESS!"
print "Saved overall percent statistics in 'percents.csv' and underlying data in 'basedata.csv' in same location as this script."

#Find stat types here: https://github.com/BurntSushi/nflgame/wiki/Stat-types
#player id = p.player.gsis_id
# rushing yards = p.rushing_yds
# rushing tds = p.rushing_tds
# receiving yards = p.receiving_yds
# receiving tds = p.receiving_tds
# passing yards = p.passing_yds
# passing tds = p.passing_tds
# interceptions = p.passing_ints
# fumbles = p.fumbles_lost
# return TD's = p.puntret_tds + p.kickret_tds
# 2-pt conversions: p.passing_twoptm + p.rushing_twoptm + p.receiving_twoptm
# Fumble recovery TD's = p.fumbles_rec_tds
