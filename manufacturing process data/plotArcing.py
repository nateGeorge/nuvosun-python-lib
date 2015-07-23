import os
import pandas as pd
import pylab as plt
from datetime import datetime

startTime = datetime.now()
    
plt.style.use('dark_background')

processes = ['BE','PC','TCO']
runs = ['440','450']
runData = {}

for run in runs:
    runData.setdefault(run,{})
    for process in processes:
        runData[run][process] = pd.read_excel('C:/Users/nathan.george/Downloads/' + run + ' ' + process + ' arcing.xlsx')

loadTime = (datetime.now()-startTime).total_seconds()

print 'took', loadTime, 'seconds to load, or', loadTime/60, 'minutes'

for process in processes:
    if process == 'TCO':
        DWkey = 'Down Web Position'
    else:
        DWkey = 'Down Web Pos'
    if not os.path.exists('Y:/Nate/git/nuvosun-python-lib/manufacturing process data/' + process):
        os.mkdir('Y:/Nate/git/nuvosun-python-lib/manufacturing process data/' + process)
    for key in runData[runs[0]][process].columns:
        if key!='DT' and key!=DWkey:
            ax = pd.DataFrame.plot(runData[runs[0]][process], kind='scatter', x = DWkey, y = key, label = runs[0], linewidth = 0, c = 'red')
            pd.DataFrame.plot(runData[runs[1]][process], kind='scatter', x = DWkey, y = key, label = runs[1], ax = ax, linewidth = 0, c = 'white')
            plt.title(process + ' ' + key)
            patches, labels = ax.get_legend_handles_labels()
            ax.legend(patches, labels, loc='best')
            plt.savefig('Y:/Nate/git/nuvosun-python-lib/manufacturing process data/' + process + '/' + process + ' ' + key, edgecolor='none', bbox_inches = 'tight')
            plt.close() 
        

completeTime = (datetime.now()-startTime).total_seconds()

print 'took', completeTime, 'seconds to complete, or', completeTime/60, 'minutes'