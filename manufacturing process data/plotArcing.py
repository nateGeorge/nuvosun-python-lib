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

for key in PCarc440.columns:
    if key!='DT':
        fig = plt.figure()
        ax = PCarc440.plot(kind='scatter', x = 'Down Web Pos', y = key)
        PCarc450.plot(kind='scatter', x = 'Down Web Pos', y = key, ax=ax)
        plt.show()
        fig.savefig('Y:/Nate/git/nuvosun-python-lib/manufacturing process data/' + key, edgecolor='none', bbox_inches = 'tight')
        plt.close()
        

completeTime = (datetime.now()-startTime).total_seconds()

print 'took', completeTime, 'seconds to load, or', completeTime/60, 'minutes'