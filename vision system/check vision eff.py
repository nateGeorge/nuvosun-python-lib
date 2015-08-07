import pandas as pd
import pylab as plt
from datetime import datetime
import time, os
from dateutil import parser

plt.style.use('dark_background')

effData = pd.read_excel('C:/Users/nathan.george/Downloads/vision tape test eff.xlsx')

cells = effData[effData.duplicated(subset = 'CellID') | effData.duplicated(subset = 'CellID', take_last = True)].groupby('CellID')

plotKeys = ['Efficiency','Voc','Jsc','FF','Rs','Rsh']

tapeNoTapeDiff2 = []
tapeNoTapeDiff1 = []
cellNames = []

for name, group in cells:
    print name
    Effs = [e for e in group.Efficiency]
    print [t for t in group.TimeTested]
    print Effs
    tapeNoTapeDiff2.append(Effs[2]-Effs[0])
    tapeNoTapeDiff1.append(Effs[1]-Effs[0])
    cellNames.append(name)
    for key in plotKeys:
        #print group.columns
        #print group.TimeTested
        times = group.TimeTested
        keyData = group[key]
        #print keyData
        plt.scatter([(t-datetime(1970,1,1)).total_seconds() for t in times], [d for d in keyData])
        ax = plt.gca()
        ax.get_yaxis().get_major_formatter().set_useOffset(False)
        plt.title(name + ' ' + key)
        plt.xlabel('time since epoch')
        plt.ylabel(key)
        if not os.path.exists('Y:/Nate/act vision system/check tape effect/' + key):
            os.mkdir('Y:/Nate/act vision system/check tape effect/' + key)
        plt.savefig('Y:/Nate/act vision system/check tape effect/' + key + '/' + name + ' ' + key,edgecolor='none', bbox_inches = 'tight')
        #plt.show()
        plt.close()
       
plt.scatter(range(len(cellNames)),tapeNoTapeDiff1, label = 'black tape', color = 'white')
plt.scatter(range(len(cellNames)),tapeNoTapeDiff2, label = 'red and yellow tape', color = 'red')
ax = plt.gca()
ax.set(xticks=range(len(cellNames)), xticklabels=cellNames)
plt.xlabel('efficiency without tape minus eff with tape')
plt.legend(loc='best')
locs, labels = plt.xticks()
plt.setp(labels, rotation=90)
plt.show()
plt.savefig('Y:/Nate/act vision system/check tape effect/eff diff summary', edgecolor='none', bbox_inches = 'tight')