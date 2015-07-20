'''
to do:
find if 600 in MR recipe, sort according to MR temp

get days of week for each run, check for trend


'''


import re, time, csv, glob, os, sys
import matplotlib.colors as colors
import matplotlib.cm as cmx
import numpy as np
import pandas as pd
import pylab as plt
import traceback as tb
from datetime import datetime
from openpyxl import load_workbook
sys.path.append("Y:/Nate/git/nuvosun-python-lib/")
import nuvosunlib as nsl
# since I have to run from the C: drive now, need to change folders into the file directory for storage files
os.chdir(os.path.dirname(os.path.realpath(__file__)))

normFitstoData={}
linearFitstoData={} #dict of substrates, with linear fit to [eff,voc,jsc,ff,rs,rsh] [0:5]
residuals={}

allEffData = nsl.effData_by_substrate(nsl.import_eff_file(effCutoff = 11.1, substrateRange = [400,500]))
baseBaseDir = 'Y:/TASK FORCE - Performance drift/eff drift fits'
baseDir = baseBaseDir + '/new as of july 2015'

basePath = baseDir + '/organized by substrate/'
basePathCW = baseDir + '/by CW/organized by substrate/'
basePath2 = baseDir + '/organized by IV parameter/'
basePath2CW = baseDir + '/by CW/organized by IV parameter/'
basePath3 = baseDir + '/organized by IV parameter/normalized'
basePath3CW = baseDir + '/organized by IV parameter/normalized'

for each in [baseBaseDir, baseDir, baseDir + '/by CW/',basePath,basePathCW]:
    if not os.path.exists(each):
            os.mkdir(each)

for eachPath in [basePath2,basePath3,basePath2CW,basePath3CW]:
    if not os.path.exists(eachPath):
        os.mkdir(eachPath)
    for each in ['eff','voc','jsc','ff','rs','rsh']:
        if not os.path.exists(eachPath + each + '/'):
            os.mkdir(eachPath + each + '/')

labels = ['PC Tool','BE Recipe', 'BC Recipe', 'PC Recipe', 'Se Recipe', 'TCO Recipe', 'Cds Recipe', 'Substrate Lot']
dateKeys = ['BC Run','BE Run','SE Run','PC Run','CDS Run','TCO Run']
effDataKeys = ['Cell Eff Avg','Cell Voc Avg','Cell Jsc Avg','Cell FF Avg','Cell Rs Avg','Cell Rsh Avg']

# make dict of CW values and colors for plotting by using a color gradient
CWs = [0.05, 0.12, 0.2, 0.29, 0.37, 0.46, 0.54, 0.63, 0.71, 0.8, 0.88]
numCWs = len(CWs)
CWcolorDict = {}
gist = plt.get_cmap('gist_ncar') 
cNorm  = colors.Normalize(vmin=0, vmax=(numCWs-1))
scalarMap = cmx.ScalarMappable(norm=cNorm, cmap=gist)
for each in range(numCWs):
	colorVal = scalarMap.to_rgba(each)
	CWcolorDict[CWs[each]] = colorVal


allCW = []
daysOfWeek = []
subList = []
subDetails = {}
maxYmult = 1.1
minYmult = 0.9
binnedEff = {}
binnedEffCW = {}

for substrate in allEffData.keys():
    print substrate
    if substrate in [429,437,446]:
        print 'skipping ', substrate
        continue
    try:
        # get indices where DW is at cutoffs, for removing start and end of runs where startup issues complicate data
        DWstartIndex = min(range(len(allEffData[substrate]['DW'])), key=lambda i: abs(allEffData[substrate]['DW'][i]-40))
        DWendIndex = min(range(len(allEffData[substrate]['DW'])), key=lambda i: abs(allEffData[substrate]['DW'][i]-(allEffData[substrate]['DW'][-1]-20)))
        currentData = {}
        tempData = {}
        currentData['DW'] = allEffData[substrate]['DW'][DWstartIndex:DWendIndex]
        if len(currentData['DW']) > 10 and max(allEffData[substrate]['DW']) >= 50 and (max(allEffData[substrate]['DW']) - min(allEffData[substrate]['DW'])) >= 50 and (max(currentData['DW']) - min(currentData['DW'])) >= 25:
            pass
        else:
            print 'skipping substrate', substrate, 'because run is too short.  DW range:', min(allEffData[substrate]['DW']), ':', max(allEffData[substrate]['DW'])
            continue
        
        
        for key in allEffData[substrate].keys():
            tempData[key] = allEffData[substrate][key][DWstartIndex:DWendIndex]
        
        currentDW = []
        currentEff = []
        currentVoc = []
        currentJsc = []
        currentFF = []
        currentRs = []
        currentRsh = []
        currentDataByCW = {}
        noPOR = True
        for each in range(len(tempData[key])):
            index = each + DWstartIndex
            # only select POR runs
            # POR setup after 
            if allEffData[substrate]['BE Recipe'][index] == 'Ti15M15M15@500nm' and allEffData[substrate]['BC Recipe'][index] == '2x Mo' and allEffData[substrate]['PC Recipe'][index] in ['5&6,20.25,1.3Na,85Cu', '5&6,20.25,1.3Na,84Cu'] and allEffData[substrate]['Se Recipe'][index] == 'P335C6001mV3.5/88' and allEffData[substrate]['Cds Recipe'][index] == '1.7SP 1.4SP' and allEffData[substrate]['TCO Recipe'][index] == 'Higher O2 flow':
                noPOR = False
                # append lists for fit to overall data
                currentDW.append(tempData['DW'][each])
                currentEff.append(tempData['Cell Eff Avg'][each])
                currentVoc.append(tempData['Cell Voc Avg'][each])
                currentJsc.append(tempData['Cell Jsc Avg'][each])
                currentFF.append(tempData['Cell FF Avg'][each])
                currentRs.append(tempData['Cell Rs Avg'][each])
                currentRsh.append(tempData['Cell Rsh Avg'][each])
                
                # populate data by CW dict
                currentCW = allEffData[substrate]['CW'][each]
                currentDataByCW.setdefault(currentCW,{})
                for key in effDataKeys + ['DW']:
                    currentDataByCW[currentCW].setdefault(key,[]).append(tempData[key][each])
                
                if substrate not in subDetails.keys():
                    subDetails[substrate] = [allEffData[substrate][key][index] for key in labels] + [datetime.strftime(datetime.strptime(allEffData[substrate][key][index][:-2],'%y%m%d'),'%d-%m-%Y') for key in dateKeys]
        if noPOR:
            continue
        currentCWs = sorted(currentDataByCW.keys())
        print currentCWs
        
        # get average of eff from each 10m section, all CWs
        df = pd.DataFrame({'DW':currentDW,'Eff':currentEff})
        bins = np.linspace(df.DW.min(), df.DW.max(), (df.DW.max() - df.DW.min())/10)
        DWgroups = df.groupby(np.digitize(df.DW, bins))
        middleDWs = [(a+b)/2 for a,b in zip(DWgroups.min().DW,DWgroups.max().DW)]
        avgEffs = [each for each in df.mean().Eff]
        minDWs = [each for each in df.min().DW]
        maxDWs = [each for each in df.max().DW]
        binnedEff.setdefault(substrate,{})
        for each in range(len(middleDWs)):
            binnedEff[substrate]['Eff'] = avgEffs[each]
            binnedEff[substrate]['avg DW'] = middleDWs[each]
            binnedEff[subDetails]['min DW'] = minDWs[each]
            binnedEff[subDetails]['max DW'] = maxDWs[each]
            binnedEff[subDetails]['CW'] = 'all CWs'
        
        plt.scatter(middleDWs, DWgroups.mean().Eff)
        plt.title(str(substrate)+' mean efficiency every 10m, all CWs (' + sorted(currentDataByCW.keys()) + ')')
        plt.savefig(basePathCW+str(substrate)+'/binned DWs all CWs/'+str(substrate)+' 10m mean Eff.jpg')
        plt.savefig(basePath2CW+'/binned DWs/eff'+str(substrate)+' 10m mean Eff.jpg')
        plt.close()
        
        # avg eff from each 10m section, each CW
        for eachCW in sorted(currentDataByCW.keys()):
            df = pd.DataFrame({'DW':currentDataByCW[eachCW]['DW'],'Eff':currentDataByCW[eachCW]['Cell Eff Avg']})
            bins = np.linspace(df.DW.min(), df.DW.max(), (df.DW.max() - df.DW.min())/10)
            DWgroups = df.groupby(np.digitize(df.DW, bins))
            middleDWs = [(a+b)/2 for a,b in zip(DWgroups.min().DW + DWgroups.max().DW)]
            plt.scatter(middleDWs, DWgroups.mean().Eff, label = eachCW, color = CWcolorDict[eachCW])
            avgEffs = [each for each in df.mean().Eff]
            minDWs = [each for each in df.min().DW]
            maxDWs = [each for each in df.max().DW]
            binnedEff.setdefault(substrate,{})
            for each in range(len(minDWs)):
                binnedEffCW[substrate]['Eff'] = avgEffs[each]
                binnedEffCW[substrate]['avg DW'] = middleDWs[each]
                binnedEffCW[subDetails]['min DW'] = minDWs[each]
                binnedEffCW[subDetails]['max DW'] = maxDWs[each]
                binnedEffCW[subDetails]['CW'] = maxDWs[each]
                
        plt.title(str(substrate)+' mean efficiency every 10m')
        plt.savefig(basePathCW+str(substrate)+'/'+str(substrate)+' 10m mean Eff, individual CWs.jpg')
        plt.savefig(basePath2CW+'binned DWs/'+str(substrate)+' 10m mean Eff, individual CWs.jpg')
        plt.close()
        
        allCW = set(allCW) | set(currentDataByCW.keys())
        maxDW=max(currentDW)
        minDW=min(currentDW)
        if abs(maxDW-minDW) < 10.0:
            continue
        subDetails[substrate] = subDetails[substrate] + [minDW, maxDW]
        
        # calculate fits to data
        
        effFitsbyCW = {}
        effSlopesbyCW = {}
        for CW in currentCWs:
            effFitsbyCW.setdefault(CW,np.polyfit(currentDataByCW[CW]['DW'],currentDataByCW[CW]['Cell Eff Avg'],1,full=True))
            effSlopesbyCW.setdefault(CW,(np.poly1d(effFitsbyCW[CW][0])(maxDW)-np.poly1d(effFitsbyCW[CW][0])(minDW))/(maxDW-minDW))
        
        effFit=np.polyfit(currentDW,currentEff,1,full=True)
        effSlope=(np.poly1d(effFit[0])(maxDW)-np.poly1d(effFit[0])(minDW))/(maxDW-minDW)
        
        vocFit=np.polyfit(currentDW,currentVoc,1,full=True)
        vocSlope=(np.poly1d(vocFit[0])(maxDW)-np.poly1d(vocFit[0])(minDW))/(maxDW-minDW)
        
        jscFit=np.polyfit(currentDW,currentJsc,1,full=True)
        jscSlope=(np.poly1d(jscFit[0])(maxDW)-np.poly1d(jscFit[0])(minDW))/(maxDW-minDW)
        
        ffFit=np.polyfit(currentDW,currentFF,1,full=True)
        ffSlope=(np.poly1d(ffFit[0])(maxDW)-np.poly1d(ffFit[0])(minDW))/(maxDW-minDW)
        
        rsFit=np.polyfit(currentDW,currentRs,1,full=True)
        rsSlope=(np.poly1d(rsFit[0])(maxDW)-np.poly1d(rsFit[0])(minDW))/(maxDW-minDW)
        
        rshFit=np.polyfit(currentDW,currentRsh,1,full=True)
        rshSlope=(np.poly1d(rshFit[0])(maxDW)-np.poly1d(rshFit[0])(minDW))/(maxDW-minDW)
        
        linearFitstoData[substrate]=[effSlope,vocSlope,jscSlope,ffSlope,rsSlope,rshSlope]
        normFitstoData[substrate]=[100*effSlope/np.average(currentEff),100*vocSlope/np.average(currentVoc),100*jscSlope/np.average(currentJsc),100*ffSlope/np.average(currentFF),100*rsSlope/np.average(currentRs),100*rshSlope/np.average(currentRsh)]
        residuals[substrate]=[np.sum(effFit[1]),np.sum(vocFit[1]),np.sum(jscFit[1]),np.sum(ffFit[1]),np.sum(rsFit[1]),np.sum(rshFit[1])]

        # plot raw data and fits
        
        savedir=basePath+str(substrate)+'/'
        if not os.path.exists(savedir): os.makedirs(savedir)
        
        for CW in sorted(currentCWs):
            print CW
            plt.scatter(currentDataByCW[CW]['DW'],currentDataByCW[CW]['Cell Eff Avg'],c = CWcolorDict[CW],label = CW)
        plt.plot([minDW,maxDW],[np.poly1d(effFit[0])(minDW),np.poly1d(effFit[0])(maxDW)],color='red',linewidth=3)
        plt.legend()
        ymax=max([np.poly1d(effFit[0])(minDW),np.poly1d(effFit[0])(maxDW)])*maxYmult
        ymin=min([np.poly1d(effFit[0])(minDW),np.poly1d(effFit[0])(maxDW)])*minYmult
        plt.ylim([ymin,ymax])
        plt.title(str(substrate)+' eff fit')
        plt.savefig(basePath+str(substrate)+'/'+str(substrate)+' eff fit.jpg')
        plt.savefig(basePath2+'eff/'+str(substrate)+' eff fit.jpg')
        plt.close()
        
        plt.scatter(currentDW,currentVoc)
        plt.plot([minDW,maxDW],[np.poly1d(vocFit[0])(minDW),np.poly1d(vocFit[0])(maxDW)],color='red',linewidth=3)
        ymax=max([np.poly1d(vocFit[0])(minDW),np.poly1d(vocFit[0])(maxDW)])*maxYmult
        ymin=min([np.poly1d(vocFit[0])(minDW),np.poly1d(vocFit[0])(maxDW)])*minYmult
        plt.ylim([ymin,ymax])
        plt.title(str(substrate)+' voc fit')
        plt.savefig(basePath+str(substrate)+'/'+str(substrate)+' voc fit.jpg')
        plt.savefig(basePath2+'voc/'+str(substrate)+' voc fit.jpg')
        plt.close()
        
        plt.scatter(currentDW,currentJsc)
        plt.plot([minDW,maxDW],[np.poly1d(jscFit[0])(minDW),np.poly1d(jscFit[0])(maxDW)],color='red',linewidth=3)
        ymax=max([np.poly1d(jscFit[0])(minDW),np.poly1d(jscFit[0])(maxDW)])*maxYmult
        ymin=min([np.poly1d(jscFit[0])(minDW),np.poly1d(jscFit[0])(maxDW)])*minYmult
        plt.ylim([ymin,ymax])
        plt.title(str(substrate)+' jsc fit')
        plt.savefig(basePath+str(substrate)+'/'+str(substrate)+' jsc fit.jpg')
        plt.savefig(basePath2+'jsc/'+str(substrate)+' jsc fit.jpg')
        plt.close()
        
        plt.scatter(currentDW,currentFF)
        plt.plot([minDW,maxDW],[np.poly1d(ffFit[0])(minDW),np.poly1d(ffFit[0])(maxDW)],color='red',linewidth=3)
        ymax=max([np.poly1d(ffFit[0])(minDW),np.poly1d(ffFit[0])(maxDW)])*maxYmult
        ymin=min([np.poly1d(ffFit[0])(minDW),np.poly1d(ffFit[0])(maxDW)])*minYmult
        plt.ylim([ymin,ymax])
        plt.title(str(substrate)+' ff fit')
        plt.savefig(basePath+str(substrate)+'/'+str(substrate)+' ff fit.jpg')
        plt.savefig(basePath2+'ff/'+str(substrate)+' ff fit.jpg')
        plt.close()
        
        plt.scatter(currentDW,currentRs)
        plt.plot([minDW,maxDW],[np.poly1d(rsFit[0])(minDW),np.poly1d(rsFit[0])(maxDW)],color='red',linewidth=3)
        ymax=max([np.poly1d(rsFit[0])(minDW),np.poly1d(rsFit[0])(maxDW)])*maxYmult
        ymin=min([np.poly1d(rsFit[0])(minDW),np.poly1d(rsFit[0])(maxDW)])*minYmult
        plt.ylim([ymin,ymax])
        plt.title(str(substrate)+' rs fit')
        plt.savefig(basePath+str(substrate)+'/'+str(substrate)+' rs fit.jpg')
        plt.savefig(basePath2+'rs/'+str(substrate)+' rs fit.jpg')
        plt.close()
        
        plt.scatter(currentDW,currentRsh)
        plt.plot([minDW,maxDW],[np.poly1d(rshFit[0])(minDW),np.poly1d(rshFit[0])(maxDW)],color='red',linewidth=3)
        ymax=max([np.poly1d(rshFit[0])(minDW),np.poly1d(rshFit[0])(maxDW)])*maxYmult
        ymin=min([np.poly1d(rshFit[0])(minDW),np.poly1d(rshFit[0])(maxDW)])*minYmult
        plt.ylim([ymin,ymax])
        plt.title(str(substrate)+' rsh fit')
        plt.savefig(basePath+str(substrate)+'/'+str(substrate)+' rsh fit.jpg')
        plt.savefig(basePath2+'rsh/'+str(substrate)+' rsh fit.jpg')
        plt.close()
        
        
        #normalized plots
        ymaxnorm=max([np.poly1d(effFit[0])(minDW),np.poly1d(effFit[0])(maxDW)])
        plt.scatter(currentDW,currentEff/ymaxnorm)
        plt.plot([minDW,maxDW],[np.poly1d(effFit[0])(minDW)/ymaxnorm,np.poly1d(effFit[0])(maxDW)/ymaxnorm],color='red',linewidth=3)
        ymax=max([np.poly1d(effFit[0])(minDW)/ymaxnorm,np.poly1d(effFit[0])(maxDW)/ymaxnorm])*maxYmult
        ymin=min([np.poly1d(effFit[0])(minDW)/ymaxnorm,np.poly1d(effFit[0])(maxDW)/ymaxnorm])*minYmult
        plt.ylim([ymin,ymax])
        plt.title(str(substrate)+' norm eff fit')
        plt.savefig(basePath+str(substrate)+'/'+str(substrate)+' eff fit - norm.jpg')
        plt.savefig(basePath3+'eff/'+str(substrate)+' eff fit - norm.jpg')
        plt.close()
        
        
        ymaxnorm=max([np.poly1d(vocFit[0])(minDW),np.poly1d(vocFit[0])(maxDW)])
        plt.scatter(currentDW,currentVoc/ymaxnorm)
        plt.plot([minDW,maxDW],[np.poly1d(vocFit[0])(minDW)/ymaxnorm,np.poly1d(vocFit[0])(maxDW)/ymaxnorm],color='red',linewidth=3)
        ymax=max([np.poly1d(vocFit[0])(minDW)/ymaxnorm,np.poly1d(vocFit[0])(maxDW)/ymaxnorm])*maxYmult
        ymin=min([np.poly1d(vocFit[0])(minDW)/ymaxnorm,np.poly1d(vocFit[0])(maxDW)/ymaxnorm])*minYmult
        plt.ylim([ymin,ymax])
        plt.title(str(substrate)+' norm voc fit')
        plt.savefig(basePath+str(substrate)+'/'+str(substrate)+' voc fit - norm.jpg')
        plt.savefig(basePath3+'voc/'+str(substrate)+' voc fit - norm.jpg')
        plt.close()
        
        ymaxnorm=max([np.poly1d(jscFit[0])(minDW),np.poly1d(jscFit[0])(maxDW)])
        plt.scatter(currentDW,currentJsc/ymaxnorm)
        plt.plot([minDW,maxDW],[np.poly1d(jscFit[0])(minDW)/ymaxnorm,np.poly1d(jscFit[0])(maxDW)/ymaxnorm],color='red',linewidth=3)
        ymax=max([np.poly1d(jscFit[0])(minDW)/ymaxnorm,np.poly1d(jscFit[0])(maxDW)/ymaxnorm])*maxYmult
        ymin=min([np.poly1d(jscFit[0])(minDW)/ymaxnorm,np.poly1d(jscFit[0])(maxDW)/ymaxnorm])*minYmult
        plt.ylim([ymin,ymax])
        plt.title(str(substrate)+' norm jsc fit')
        plt.savefig(basePath+str(substrate)+'/'+str(substrate)+' jsc fit - norm.jpg')
        plt.savefig(basePath3+'jsc/'+str(substrate)+' jsc fit - norm.jpg')
        plt.close()
        
        ymaxnorm=max([np.poly1d(ffFit[0])(minDW),np.poly1d(ffFit[0])(maxDW)/ymaxnorm])
        plt.scatter(currentDW,currentFF/ymaxnorm)
        plt.plot([minDW,maxDW],[np.poly1d(ffFit[0])(minDW)/ymaxnorm,np.poly1d(ffFit[0])(maxDW)/ymaxnorm],color='red',linewidth=3)
        ymax=max([np.poly1d(ffFit[0])(minDW)/ymaxnorm,np.poly1d(ffFit[0])(maxDW)/ymaxnorm])*maxYmult
        ymin=min([np.poly1d(ffFit[0])(minDW)/ymaxnorm,np.poly1d(ffFit[0])(maxDW)/ymaxnorm])*minYmult
        plt.ylim([ymin,ymax])
        plt.title(str(substrate)+' norm ff fit')
        plt.savefig(basePath+str(substrate)+'/'+str(substrate)+' ff fit - norm.jpg')
        plt.savefig(basePath3+'ff/'+str(substrate)+' ff fit - norm.jpg')
        plt.close()
        
        ymaxnorm=max([np.poly1d(rsFit[0])(minDW),np.poly1d(rsFit[0])(maxDW)])
        plt.scatter(currentDW,currentRs/ymaxnorm)
        plt.plot([minDW,maxDW],[np.poly1d(rsFit[0])(minDW)/ymaxnorm,np.poly1d(rsFit[0])(maxDW)/ymaxnorm],color='red',linewidth=3)
        ymax=max([np.poly1d(rsFit[0])(minDW)/ymaxnorm,np.poly1d(rsFit[0])(maxDW)/ymaxnorm])*maxYmult
        ymin=min([np.poly1d(rsFit[0])(minDW)/ymaxnorm,np.poly1d(rsFit[0])(maxDW)/ymaxnorm])*minYmult
        plt.ylim([ymin,ymax])
        plt.title(str(substrate)+' norm rs fit')
        plt.savefig(basePath+str(substrate)+'/'+str(substrate)+' rs fit - norm.jpg')
        plt.savefig(basePath3+'rs/'+str(substrate)+' rs fit - norm.jpg')
        plt.close()
        
        ymaxnorm=max([np.poly1d(rshFit[0])(minDW),np.poly1d(rshFit[0])(maxDW)])
        plt.scatter(currentDW,currentRsh/ymaxnorm)
        plt.plot([minDW,maxDW],[np.poly1d(rshFit[0])(minDW)/ymaxnorm,np.poly1d(rshFit[0])(maxDW)/ymaxnorm],color='red',linewidth=3)
        ymax=max([np.poly1d(rshFit[0])(minDW)/ymaxnorm,np.poly1d(rshFit[0])(maxDW)/ymaxnorm])*maxYmult
        ymin=min([np.poly1d(rshFit[0])(minDW)/ymaxnorm,np.poly1d(rshFit[0])(maxDW)/ymaxnorm])*minYmult
        plt.ylim([ymin,ymax])
        plt.title(str(substrate)+' norm rsh fit')
        plt.savefig(basePath+str(substrate)+'/'+str(substrate)+' rsh fit - norm.jpg')
        plt.savefig(basePath3+'rsh/'+str(substrate)+' rsh fit - norm.jpg')
        plt.close()
        
        subList.append(substrate)
    except Exception as e:
        print sys.exc_info()
        print tb.print_tb(sys.exc_info()[2])
        
sortedsubstratelist=sorted(subList)

with open('Y:/TASK FORCE - Performance drift/eff drift fits/new as of july 2015/all runs sorted and with drifts.csv', 'wb') as csvfile:
    spamwriter = csv.writer(csvfile, delimiter=',', quoting=csv.QUOTE_MINIMAL)
    spamwriter.writerow(['substrate'] + labels + dateKeys + ['min DW', 'max DW'] + ['eff slope','voc slope','jsc slope','ff slope','rs slope','rsh slope']+['norm eff slope','norm voc slope','norm jsc slope','norm ff slope','norm rs slope','norm rsh slope','eff residuals','voc residuals','jsc residuals','ff residuals','rs residuals','rsh residuals'])
    for each in sortedsubstratelist:
        try:
            spamwriter.writerow([each] + [subDetails[each][pos] for pos in range(len(subDetails[each]))] + linearFitstoData[each] + normFitstoData[each] + residuals[each])
        except KeyError:
            pass

allCW = sorted(list(allCW))
print allCW

with open('Y:/TASK FORCE - Performance drift/eff drift fits/new as of july 2015/binnedEff','wb') as csvFile:
    binnedEffCsv = csv.writer(csvFile, delimiter=',')
    binnedEffCsv.writerow(['substrate'] + [key for key in sorted(binnedEffCW[substrate].keys())])
    for subs in sorted(binnedEff.keys()):
        binnedEffCsv.writerow(subs + [binnedEff[subs][key] for key in sorted(binnedEff[subs].keys())])
    for subs in sorted(binnedEffCW.keys()):
        binnedEffCsv.writerow(subs + [binnedEffCW[subs][key] for key in sorted(binnedEff[subs].keys())])
exit()

with open('eff sorted by tool and POR, MR600.csv', 'wb') as csvfile:
    spamwriter = csv.writer(csvfile, delimiter=',')
    spamwriter.writerow(labelrow+['PC/BE tool','run length','VendorName', 'VendorLot','RollNumber','run type'])
    for substrate in substrate_list:
        print substrate
        substrate=str(substrate)
        if not isinstance(alldata[substrate],list):
            alldata[substrate]=alldata[substrate].tolist()
        if int(substrate) in [x[0] for x in porMC01runs] or int(substrate) in [x[0] for x in porMC02runs]:
            for datarow in alldata[substrate]:
                spamwriter.writerow(datarow+allrundata[substrate]+['POR'])
        elif int(substrate) in [x[0] for x in mr600MC01runs] or int(substrate) in [x[0] for x in mr600MC02runs]:
            for datarow in alldata[substrate]:
                spamwriter.writerow(datarow+allrundata[substrate]+['MR600'])
        
            
            
