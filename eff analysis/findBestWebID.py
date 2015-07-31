import sys, csv, os
import numpy as np
sys.path.append("Y:/Nate/git/nuvosun-python-lib/")
import nuvosunlib as nsl
# since I have to run from the C: drive now, need to change folders into the file directory for storage files
os.chdir(os.path.dirname(os.path.realpath(__file__)))

effData = nsl.import_eff_file()
webIDEffmeans = {}

print sorted(effData.keys())
for run in sorted(effData.keys()):
    for webID in sorted(effData[run].keys()):
        webIDEffmeans[np.mean(np.array(effData[run][webID]['Cell Eff Avg'],dtype='float64'))] = webID

with open('eff sorted by webIDs.csv','wb') as csvfile:
    effWr = csv.writer(csvfile, delimiter=',')
    effWr.writerow(['webID','avg eff'])
    for eff in reverse(sorted(webIDmeans.keys())): # always sorts from low to high, so need to reverse
        effWr.writerow([webIDmeans[eff],eff])