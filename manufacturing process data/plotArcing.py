import pandas as pd
import pylab as plt
from datetime import datetime

startTime = datetime.now()
    
plt.style.use('dark_background')

PCarc440 = pd.read_excel('C:/Users/nathan.george/Downloads/440 PC arcing.xlsx')
PCarc450 = pd.read_excel('C:/Users/nathan.george/Downloads/450 PC arcing.xlsx')
BEarc440 = pd.read_excel('C:/Users/nathan.george/Downloads/440 BE arcing.xlsx')
BEarc450 = pd.read_excel('C:/Users/nathan.george/Downloads/450 BE arcing.xlsx')

loadTime = (datetime.now()-startTime).total_seconds()

print 'took', loadTime, 'seconds to load, or', loadTime/60, 'minutes'

for process in ['BE','PC']:
    for key in eval(process + 'arc440').columns:
        if key!='DT' and key!='Down Web Pos':
            ax = pd.DataFrame.plot(eval(process + 'arc440'), kind='scatter', x = 'Down Web Pos', y = key, label = '440', linewidth = 0, c = 'red')
            pd.DataFrame.plot(eval(process + 'arc450'), kind='scatter', x = 'Down Web Pos', y = key, label = '450', ax = ax, linewidth = 0, c = 'white')
            patches, labels = ax.get_legend_handles_labels()
            ax.legend(patches, labels, loc='best')
            plt.savefig('Y:/Nate/git/nuvosun-python-lib/manufacturing process data/' + process + '/' + key, edgecolor='none', bbox_inches = 'tight')
            plt.close()
        

completeTime = (datetime.now()-startTime).total_seconds()

print 'took', completeTime, 'seconds to load, or', completeTime/60, 'minutes'