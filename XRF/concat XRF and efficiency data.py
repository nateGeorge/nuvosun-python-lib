import csv, sys, pickle, os
sys.path.append("Y:/Nate/git/nuvosun-python-lib/")
import nuvosunlib as ns
# since I have to run from the C: drive now, need to change folders into the file directory for storage files
os.chdir(os.path.dirname(os.path.realpath(__file__)))

effData = ns.import_eff_file()
print sorted(effData.keys())
exit()
newEffData = {}

# convert eff data to dict with runs as keys and web id as data

runs = []
for run in sorted(effData.keys()):
    print run
    newEffData[run] = {}
    for webID in sorted(effData[run].keys()):
        for eachDW in range(len(effData[run][webID]['DW'])):
            newEffData[run].setdefault('web ID',[]).append(webID)
        for key in effData[run][webID].keys():
            newEffData[run].setdefault(key,[]).append(effData[run][webID][key])
    
    try:
        if int(run) >= 300:
            runs.append(run)
    except Exception as e:
        print e
            
XRFdata = ns.get_XRF_data(runs)
XRFinterpedData = {}


for run in XRFdata.keys():
    XRFinterpedData[run] = {}
    for key in XRFdata[run].keys():
        XRFinterpedData[run][key] = ns.interp_to_eff(effData[run]['DW'], XRFdata[run]['DW'], XRFdata[run][key])
        

effKeys = sorted(effData[effData.keys()[0]].keys())
xrfKeys = sorted(XRFdata[XRFdata.keys()[0]].keys())
with open('XRF-eff data.csv','wb') as csvfile:
    csvwriter = csv.writer(csvfile, delimiter = ',')
    csvwriter.writerow(['substrate','web ID'] + effKeys + xrfKeys)
    for run in XRFdata.keys():
        for DWcount in range(len(XRFdata[run]['DW'])):
            csvwriter.writerow([run] + [effData[run][key] for key in effKeys] + [XRFdata[run][key] for key in xrfKeys])

