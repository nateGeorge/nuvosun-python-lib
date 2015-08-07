''' TO DO:
add data to mongoDB database instead of csv
a. add other folders in, PC, reactor, BE
b. detect new files and add them to DB
c. for TCO analysis:
    1. add integration of Na on the interfaces of the layers, detect Na peaks and integrate them
    2. add integration of CIGS divided into 4 sections
    3. add cumulative integration of everything
    4. add integration boundaries for the 2 sections of Cd, detect slope change in Cd for boundary
'''

import csv, os, re, time, sys, pickle, psutil, gc
import numpy as np
import matplotlib.pyplot as plt
from scipy.integrate import simps # this line isn't working for me from the Y: drive
import pandas as pd
sys.path.append("Y:/Nate/git/nuvosun-python-lib/")
import nuvosunlib as nsl
import sqlite3 as sql

# since I have to run from the C: drive now, need to change folders into the file directory for storage files
os.chdir(os.path.dirname(os.path.realpath(__file__))) 

############# GENERAL OPTIONS
logProcessing = False
savePlots = False
keepRecordsOfStats = False
debuggingMode = True
saveFileInfo = True
runCutoff = 286
# plotting options
plt.style.use('ggplot')
plotBy = 'X'
savePlotsPath = 'Y:/Characterization/GDOES/processed data/plots of processed files/'
baseFileSavePath = 'Y:/Characterization/GDOES/processed data/lists of processed files/'

############ SOME CONSTANTS
# quality of measurement, noted in file name
goodIndicators = ['ok','good','very good','great','ok noisy','question','questionable'] 
badIndicators = ['noisy','bad','spikes','weird']
sumReString = '' # string for re (regular expression) for searching for quality label in filename

for indicator in goodIndicators + badIndicators:
    sumReString += '(' + indicator + ')|'
sumReString = sumReString[:-1]

startTime = time.time() # for tracking how long the program takes to run

ReliRunsDict = nsl.getReliRunsDict() # a dictionary of good/bad reli runs with fields: ['bake time'] = '12h', ['SC result'] = 'bad', ['SC TTF'] = 1200

def parse_file_details(sumReString):
    """Returns dictionary of files with their paths, modified time, and quality of the sample as 
    indicated by the summary file (....sum.jy).
    
    :param sumReString: string for searching the ...sum.jy files to find quality of the 
    sample (i.e. good, bad, weird)
    returns :
    dict fileDict with keys ['mTime','filePath','burn quality']
    
    """
    print 'getting new files'
    totalFileSize = 0
    earliestRunTime = 9999999999.0 # for finding the earliest run there was, time since epoch now is roughly 1430000000.0, so this should be greater than that
    fileDict = {}
    for root, dirs, files in os.walk(GDOESfolders[folder]['path']):
        for file in files:
            if re.search('BE', file) or re.search('Glass', file):
                print 'skipping file', file, 'becasue had \'BE\' or \'Glass\' in it'
                continue
            sys.stdout.write('.') # prints a period for every file, if watching it run via terminal, it is showing progress is happening
                
            if file.endswith('.jy') and not re.search('sum', file):
                # get the burn quality for the file, based on the note in the filename of the summary file 
                # in the sum.jy file, the quality is denoted as bad, ok, good, very good, etc(in array goodIndicators + badIndicators)
                burnQuality = 'N/A'
                sumFileFound = ''
                for sumFile in files:
                    # if the path of the data file and sumfile aren't the same, skip that sum file
                    if os.path.dirname(os.path.realpath(file)) != os.path.dirname(os.path.realpath(sumFile)):
                        continue
                    if re.search(file[:-3], sumFile) and re.search('sum', sumFile):
                        sumFileFound = sumFile
                        if re.search('sumReString',sumFile,re.IGNORECASE):
                            burnQuality = re.search('sumReString',sumFile,re.IGNORECASE).group(0)
                            break
                
                filePath = root + '/' + file
                fileMtime = os.path.getmtime(filePath)
                
                if debuggingMode:
                    # for checking how far back in time the data goes
                    if fileMtime < earliestRunTime:
                        earliestRunTime = fileMtime
                    totalFileSize += os.path.getsize(filePath)

                if logProcessing:
                    print 'found new GDOES file:', file
                    print 'at location', filePath
                
                # a few of the files are summary files, but are not labeled a such in the filename (no 'sum' in the filename).
                # this checks the first few lines to see if the word 'summary' is in there, indicating it's a summary file
                GDOESfile = open(filePath, 'rb')
                summaryFile = False
                for line in range(10): # scan first ten lines to see if it is an integration/summary file, not a data file
                    firstLine = GDOESfile.readline()
                    if re.search('Summary',firstLine, re.IGNORECASE):
                        summaryFile = True
                # adds the file to the file list for later processing
                if not summaryFile:
                    fileDict[file] = {}
                    fileDict[file]['filePath'] = filePath
                    fileDict[file]['mtime'] = fileMtime
                    fileDict[file]['burn quality'] = burnQuality
    return fileDict

def parse_run_details_andSave(dictOfFiles, GDOESfolders):
    """Return a dictionary of files with classification details of cells and GDOES measurements 
    from scanning paths/filenames in dictOfFiles.
    Saved details of runs in .pkl files (python pickle files)

    :param dictOfFiles: A dictionary of the form ``dictOfFiles[file]['filePath'] = path_to_file``.
    path_to_file includes the filename.
    :rtype: A dictionary of the form ``returnedRunData[file]['substrate']`` with keys: substrate, DW, 
    CW, baked, sample number, bake time, pressure, power, cell number, and keys from dictOfFiles
    """
    # scan filenames and paths of the files for details such as substrate, DW/CW positions, baketime, GDOES pressure/power
    # takes an input of a dictionary of files, 
    returnedRunData = {}
    for file in dictOfFiles.keys():
        if logProcessing:
            print 'processing:', dictOfFiles[file]
        # get substrate number
        if  re.search('S0*(\d\d\d)',dictOfFiles[file]['filePath'],re.IGNORECASE):
            runNumber = re.search('S0*(\d\d\d)',dictOfFiles[file]['filePath'],re.IGNORECASE).group(1)#\s+([dw\d+]*)\s+([cw\d\d])-.*', file)
        else:
            continue
            print 'skipping file because no substrate label found!', file
        # get DW position
        if re.search('dw\s*(\d\.*\d*)', file, re.IGNORECASE):
            dwPos = re.search('dw\s*(\d+\.*\d*)', file, re.IGNORECASE).group(1)
        else:
            dwPos = 'unknown'
        # CW position
        if re.search('cw\s*(\d+)', file, re.IGNORECASE):
            cwPos = re.search('cw\s*(\d+)', file, re.IGNORECASE).group(1)
        else:
            cwPos = 'unknown'
        # if indication of bake with baketime in file, get it, otherwise assume 12h bake
        if re.search('nb', file) or re.search('no bake', file):
            baked = 'no bake'
        else:
            baked = 'baked'
            if re.search('m', file):
                bakeTime = re.search('(\d*)\s*m', file).group(1) + 'm'
            elif re.search('h', file):
                bakeTime = re.search('(\d*)\s*h', file).group(1) + 'h'
            else:
                bakeTime = '12h'

        # burn number; sometimes samples are taken on the same cell a few centimeters apart, they are denoted by a '-4' or other digit
        # as a sample number
        if re.search('-\s*\d', file):
            sampleNumber = re.search('-\s*(\d+)', file).group(1)
        elif re.search('#\s*\d', file):
            sampleNumber = re.search('#\s*(\d+)', file).group(1)
        elif re.search('burn\s*\d', file):
            sampleNumber = re.search('burn\s*(\d+)', file).group(1)
        else:
            sampleNumber = 'N/A'
        # pressure setting of GDOES measurement, can be in filename or path
        if re.search('Pa', dictOfFiles[file]['filePath']):
            pressure = re.search('(\d*)\s*k*Pa', dictOfFiles[file]['filePath'], re.IGNORECASE).group(1)
        else:
            pressure = 'unknown'
        # GDOES power setting, can be in filename or path
        if re.search('(\d+)\s*W', dictOfFiles[file]['filePath'],re.IGNORECASE):
            power = re.search('(\d+)\s*W', dictOfFiles[file]['filePath'], re.IGNORECASE).group(1) + 'W'
        else:
            power = 'unknown'
        # cell barcode number
        if re.search('\d\d\d\d\d\d', file):
            cellNumber = re.search('\d\d\d\d\d\d+', file).group(0)
        else:
            cellNumber = 'unknown'
        # run date
        '''
        runDateFound = False
        for year in ['15','16','17']:
            if re.search('\d\d\d\d' + year, dictOfFiles[file]['filePath']):
                runDate = re.search('\d\d\d\d' + year, dictOfFiles[file]['filePath']).group(0)
                runData = datetime.strftime(runData, '%m%d%y')
                runDateFound = True
            elif not runDateFound and year == '17':
                runDate = datetime.fromtimestamp(dictOfFiles[file]['mtime'])
        '''
        
        ################# populate runData dict with parsed parameters from path and file
        returnedRunData[file] = {}
        # if the file was from a calibration, label it as such
        # latest 350 data file that was not a calibration standard was at mtime = 1426206383.0390635
        if runNumber == '350' and dictOfFiles[file]['mtime']>1426206384.0:
            returnedRunData[file]['calibration'] = 'true'
        else:
            returnedRunData[file]['calibration'] = 'false'
        
        returnedRunData[file]['modified time'] = dictOfFiles[file]['mtime']
        returnedRunData[file]['substrate'] = runNumber
        returnedRunData[file]['DW'] = dwPos
        returnedRunData[file]['CW'] = cwPos
        returnedRunData[file]['baked'] = baked
        returnedRunData[file]['sample number'] = sampleNumber
        returnedRunData[file]['bake time'] = bakeTime
        returnedRunData[file]['pressure'] = pressure
        returnedRunData[file]['power'] = power
        returnedRunData[file]['cell number'] = cellNumber
        for key in dictOfFiles[file].keys():
            returnedRunData[file][key] = dictOfFiles[file][key]
        if logProcessing:
            print returnedRunData[file]
            
    if saveFileInfo:
        GDOESfolders[folder]['latestMtime'] = os.path.getmtime(GDOESfolders[folder]['path'])
        runDatapkl = open(baseFileSavePath + 'runData-' + folder + '.pkl','wb')
        fileDictpkl = open(baseFileSavePath + 'fileDict-' + folder + '.pkl','wb')
        foldersPkl = open(baseFileSavePath + 'GDOESfolderList.pkl','wb')
        pickle.dump(runData, runDatapkl)
        pickle.dump(dictOfFiles, fileDictpkl)
        pickle.dump(GDOESfolders, foldersPkl)
        runDatapkl.close()
        fileDictpkl.close()
        foldersPkl.close()
    
    return returnedRunData

def check_if_folders_uptodate(GDOESfolders):
    if os.path.isfile(baseFileSavePath + 'GDOESfolderList.pkl'):
        GDOESfolders = pickle.load(open(baseFileSavePath + 'GDOESfolderList.pkl','rb'))
        fileWasThere = True
    else:
        for folder in GDOESfolders.keys():
            GDOESfolders[folder]['latestMtime'] = os.path.getmtime(GDOESfolders[folder]['path'])
        if saveFileInfo:
            pickle.dump(GDOESfolders, open(baseFileSavePath + 'GDOESfolderList.pkl','wb'))
        fileWasThere = False
    return fileWasThere, GDOESfolders

def load_file_details():
    print 'loading file data from pickle files'
    with open(baseFileSavePath + 'runData-' + folder + '.pkl','rb') as tf:
        runData = pickle.load(tf)
    with open(baseFileSavePath + 'fileDict-' + folder + '.pkl','rb') as tf:
        fileDict = pickle.load(tf)
    with open(baseFileSavePath + 'allGDOESdataKeys-'+folder,'rb') as wf:
        allGDOESdataKeys = pickle.load(wf)
    with open(baseFileSavePath + 'allGDOESIntegrationKeys-'+folder,'rb') as wf:
        allGDOESIntegrationKeys = pickle.load(wf)
    with open(baseFileSavePath + 'GDOESkeyDict-'+folder,'rb') as wf:
         GDOESkeyDict = pickle.load(wf)
    with open(baseFileSavePath + 'labelsNotInElementDict-'+folder,'rb') as wf:
        labelsNotInElementDict = pickle.load(wf)
    return runData, fileDict, allGDOESdataKeys, allGDOESIntegrationKeys, GDOESkeyDict, labelsNotInElementDict

def parse_GDOES_row_labels_andSaveData(runData):
    '''Parse GDOES data files to get elements and wavelengths of measurement, so we know 
    The row labels are different in many files (30+ formats) and some files are missing them.
    First, we get the labels from files where the wavelength of measurement is specified at the top of the file.
    Then we use that information to parse other files without these labels at the top.'''
    allGDOESdata = {}
    allGDOESdataAlignedByCIGS = {}
    dataStartIndex = {}
    PCStartIndex = {}
    PCEndIndex = {}
    dataEndIndex = {}
    borderTimes = {}
    borderIndices = {}
    allGDOESdataIntegration = {}
    allGDOESdataKeys = []
    allGDOESIntegrationKeys = ['In in ITO','In in CIGS','Na in TCO','Cd in CIGS','Se in CIGS','Na in CIGS','Na in TCO+CIGS','Na below CIGS','Se in CIGS','Se in MoSe2','Se in MoSe2','Na in MoSe2','Na in Mo']
    allElementDict = {}
    GDOESformats = []
    elementDicts = []
    labelRowFormats = {}
    filesWithFormats = {}
    fileCounter = 0
    RowFormatCounter = 0
    filesWithoutElementDict = []
    labelsNotInElementDict = []
    GDOESkeyDict = {}
    # if we want to take a look at how the files are being parsed by parse_file_details(), make debuggingMode = True
    if debuggingMode:
        sumf = open(baseFileSavePath + folder + ' sum file list.csv','wb')
        sumWriter = csv.writer(sumf, delimiter = ',')
        sumWriter.writerow([key for key in runData[runData.keys()[0]]])
    
    for file in sorted(runData.keys()):
        if debuggingMode:
            sumWriter.writerow([runData[file][key] for key in runData[runData.keys()[0]]])
        
        GDOESkeyDict[file] = {}
        if 'csvFile' in globals():
            csvFile.close()
        '''if int(runData[file]['substrate']) < runCutoff:
            print 'skipping',file,'because substrate',runData[file]['substrate'],'under', runCutoff
            continue'''

        csvFile = open(fileDict[file]['filePath'], 'rb')

        GDOEScsv = csv.reader(csvFile, delimiter = '\t')

        elementDict = {}
        elDict = []
        labels = []
        ratioLabels = []
        foundSe = False
        for row in GDOEScsv:
            if len(row)>0 and row[0] == 'X':
                if not elementDict:
                    filesWithoutElementDict.append(file)
                    break
                templabels = [x for x in row]
                ratiosStarted = False
                for label in templabels:
                    if not re.search('/Fi',label) and label != 'P g':
                        if ratiosStarted:
                            print file
                            print label, 'came after /Fi started'
                            exit()
                        labels.append(label)
                    if re.search('/Fi',label):
                        ratiosStarted = True
                        ratioLabels.append(label)
                labelRow = row
                fiRow = []
                labelCount = -1
                for label in labels:
                    labelCount += 1
                    labelInd = labels.index(label)
                    if label in elementDict.keys() and label != '*Vrf' and label != 'Vrf':  
                        GDOESkeyDict[file][elementDict[label]] = {}
                        if re.search('^\*.',label): # if there is a star at the beginning, like *Cu
                            GDOESkeyDict[file][elementDict[label]]['mult'] = 1.0
                            GDOESkeyDict[file][elementDict[label]]['pos'] = labelCount
                            GDOESkeyDict[file][elementDict[label]]['rawlabel'] = label
                            labels[labelInd] = elementDict[label]
                        elif re.search('\*(\d.*)',label): # if there is a multiplication of the signal, like Se*150
                            GDOESkeyDict[file][elementDict[label]]['mult'] = 1/float(re.search('\*(\d.*)',label).group(1))
                            GDOESkeyDict[file][elementDict[label]]['pos'] = labelCount
                            GDOESkeyDict[file][elementDict[label]]['rawlabel'] = label
                            labels[labelInd] = elementDict[label]
                        elif re.search('/(\d.*)',label): # if there is a division of the signal, like Mo/500
                            GDOESkeyDict[file][elementDict[label]]['mult'] = float(re.search('/(\d.*)',label).group(1))
                            GDOESkeyDict[file][elementDict[label]]['pos'] = labelCount
                            GDOESkeyDict[file][elementDict[label]]['rawlabel'] = label
                            labels[labelInd] = elementDict[label]
                        else:
                            GDOESkeyDict[file][elementDict[label]]['mult'] = 1.0
                            GDOESkeyDict[file][elementDict[label]]['pos'] = labelCount
                            GDOESkeyDict[file][elementDict[label]]['rawlabel'] = label
                            labels[labelInd] = elementDict[label]
                        fiRow.append(elementDict[label] + '/Fi')
                    elif label == '*Vrf':
                        GDOESkeyDict[file]['Vrf'] = {}
                        GDOESkeyDict[file]['Vrf']['mult'] = 1.0
                        GDOESkeyDict[file]['Vrf']['pos'] = labelCount
                        GDOESkeyDict[file]['Vrf']['rawlabel'] = label
                        labels[labelInd] = 'Vrf'
                    elif label[:2] == 'Fi':
                        GDOESkeyDict[file]['Fi'] = {}
                        if label == 'Fi':
                            GDOESkeyDict[file]['Fi']['mult'] = 1.0
                            GDOESkeyDict[file]['Fi']['pos'] = labelCount
                            GDOESkeyDict[file]['Fi']['rawlabel'] = label
                        else:
                            GDOESkeyDict[file]['Fi']['mult'] = 1/float(re.search('Fi\*(\d+)',label).group(1))
                            GDOESkeyDict[file]['Fi']['pos'] = labelCount
                            GDOESkeyDict[file]['Fi']['rawlabel'] = label
                    else:
                        GDOESkeyDict[file][label] = {}
                        GDOESkeyDict[file][label]['mult'] = 1.0
                        GDOESkeyDict[file][label]['pos'] = labelCount
                        GDOESkeyDict[file][label]['rawlabel'] = label
                        labelsNotInElementDict = set(labelsNotInElementDict) | set([label])
                        
                break # stop going through the rows if we hit the labels
            elif len(row)>0 and len(row[1])>0:
                isElementDict = True
                elementDict[row[0]] = row[1]#[-3:] # row[1] is the element followed by a space, then the wavelength of observation by OES; row[0] is the label in the file headings
                elDict.append(row[1])
        print 'loaded ', file
        if not elementDict: # if doesn't have an element dict, skip for now
            continue
        fileCounter += 1
        if labelRow not in GDOESformats:
            GDOESformats.append(labelRow)
            filesWithFormats[','.join(sorted(labelRow))] = []
        filesWithFormats[','.join(sorted(labelRow))].append(file)
        if elDict not in elementDicts:
            elementDicts.append(elDict)

        labels = labels + fiRow

        labelKeys = [label for label in labels]
        for key in labelKeys:
            for mvaKey in mvaKeys:
                if re.search(mvaKey,key):
                    labels.append(key + ' mva20')

        allGDOESdataKeys = set(labels) | set(allGDOESdataKeys)
        allGDOESIntegrationKeys = set(labels) | set(allGDOESIntegrationKeys)
        allElementDict.update(elementDict)

    for element in allElementDict.keys():
        if not re.search('Se',element):
            if re.search('^\*',element):
                if element[1:] not in allElementDict.keys():
                    allElementDict[element[1:]] = allElementDict[element]
            if re.search('/Fi',element):
                if element[:-3] not in allElementDict.keys():
                    allElementDict[element[:-3]] = allElementDict[element]
    
    allElementDict['Se'] = 'Se 207'
    print allElementDict
    
    del allElementDict['Vrf']
    del allElementDict['*Vrf']
    
    #sys.stdout = open('test.txt','wb')
    #print allElementDict

    labelsNotInElementDict = list(labelsNotInElementDict) + ['Fi']
    elementDict = allElementDict
    print sorted(elementDict)
    
    for file in filesWithoutElementDict:
        print file
        if 'csvFile' in globals():
            csvFile.close()
        '''if int(runData[file]['substrate']) < runCutoff:
            print 'skipping',file,'because substrate',runData[file]['substrate'],'under', runCutoff
            continue'''

        csvFile = open(fileDict[file]['filePath'], 'rb')

        GDOEScsv = csv.reader(csvFile, delimiter = '\t')

        labels = []
        foundSe = False
        for row in GDOEScsv:
            #print row
            if len(row)>0 and row[0] == 'X':
                templabels = [x for x in row]
                ratiosStarted = False
                for label in templabels:
                    if not re.search('/Fi',label) and label != 'P g':
                        if ratiosStarted:
                            print file
                            print label, 'came after /Fi started'
                            exit()
                        labels.append(label)
                        if re.search('Se',label):
                            foundSe = True
                    if re.search('/Fi',label):
                        ratiosStarted = True
                        if not foundSe and re.search('Se/Fi',label): # some files have Se/Fi but not Se...go figure
                            GDOESkeyDict[file]['Se 207'] = {}
                            GDOESkeyDict[file]['Se 207']['pos'] = templabels.index(label)
                            GDOESkeyDict[file]['Se 207']['rawlabel'] = label
                            GDOESkeyDict[file]['Se 207']['mult'] = 1.0
                    ##  TODO: add something for catching files with Se/Fi but not Se in them...if re.search
                labelRow = row
                fiRow = []
                labelCount = -1
                for label in labels:
                    labelCount += 1
                    labelInd = labels.index(label)
                    if label not in labelsNotInElementDict and not re.search('Fi',label) and label != '*Vrf' and label != 'Vrf':
                        if re.search('^\*.',label): # if star at the beginning, like *Cu
                            tempLab = re.search('\*(.*)',label).group(1)
                            GDOESkeyDict[file][elementDict[tempLab]] = {}
                            GDOESkeyDict[file][elementDict[tempLab]]['mult'] = 1.0
                            GDOESkeyDict[file][elementDict[tempLab]]['pos'] = labelCount
                            GDOESkeyDict[file][elementDict[tempLab]]['rawlabel'] = label
                            labels[labelInd] = elementDict[re.search('^\*(.*)',label).group(1)]
                        elif re.search('\*(\d.*)',label): # if multiplication, like Cu*150
                            tempLab = re.search('(.*)\*(\d.*)',label).group(1)
                            GDOESkeyDict[file][elementDict[tempLab]] = {}
                            GDOESkeyDict[file][elementDict[tempLab]]['mult'] = 1/float(re.search('\*(\d.*)',label).group(1))
                            GDOESkeyDict[file][elementDict[tempLab]]['pos'] = labelCount
                            GDOESkeyDict[file][elementDict[tempLab]]['rawlabel'] = label
                            labels[labelInd] = elementDict[tempLab]
                        elif re.search('/(\d.*)',label): # if division, like Cu/150
                            tempLab = re.search('(.*)/(\d.*)',label).group(1)
                            GDOESkeyDict[file][elementDict[tempLab]] = {}
                            GDOESkeyDict[file][elementDict[tempLab]]['mult'] = float(re.search('/(\d.*)',label).group(1))
                            GDOESkeyDict[file][elementDict[tempLab]]['pos'] = labelCount
                            GDOESkeyDict[file][elementDict[tempLab]]['rawlabel'] = label
                            labels[labelInd] = elementDict[re.search('(.*)/(\d.*)',label).group(1)]
                        else:
                            labels[labelInd] = elementDict[label]
                            GDOESkeyDict[file][elementDict[label]] = {}
                            GDOESkeyDict[file][elementDict[label]]['mult'] = 1.0
                            GDOESkeyDict[file][elementDict[label]]['pos'] = labelCount
                            GDOESkeyDict[file][elementDict[label]]['rawlabel'] = label
                        fiRow.append(elementDict[re.search('\S*', labels[labelInd]).group(0)] + '/Fi')
                    elif label == '*Vrf':
                        GDOESkeyDict[file]['Vrf'] = {}
                        GDOESkeyDict[file]['Vrf']['mult'] = 1.0
                        GDOESkeyDict[file]['Vrf']['pos'] = labelCount
                        GDOESkeyDict[file]['Vrf']['rawlabel'] = label
                        labels[labelInd] = 'Vrf'
                    elif label[:2] == 'Fi':
                        if debuggingMode:
                            print '**********'
                            print '**********'
                            print '**********'
                            print '**********'
                            print 'found Fi. raw label:', label
                        GDOESkeyDict[file]['Fi'] = {}
                        if label == 'Fi':
                            if debuggingMode:
                                print 'just plain Fi'
                            GDOESkeyDict[file]['Fi']['mult'] = 1.0
                            GDOESkeyDict[file]['Fi']['pos'] = labelCount
                            GDOESkeyDict[file]['Fi']['rawlabel'] = label
                        else:
                            if debuggingMode:
                                print 'Fi with multiplier:', 1/float(re.search('Fi\*(\d+)',label).group(1))
                            GDOESkeyDict[file]['Fi']['mult'] = 1/float(re.search('Fi\*(\d+)',label).group(1))
                            GDOESkeyDict[file]['Fi']['pos'] = labelCount
                            GDOESkeyDict[file]['Fi']['rawlabel'] = label
                    else:
                        GDOESkeyDict[file][label] = {}
                        GDOESkeyDict[file][label]['mult'] = 1.0
                        GDOESkeyDict[file][label]['pos'] = labelCount
                        GDOESkeyDict[file][label]['rawlabel'] = label
                break # stop going through the rows if we hit the labels
        print 'loaded ', file
        
        #### these are for keeping some stats on the number of different formats
        fileCounter += 1
        if labelRow not in GDOESformats:
            GDOESformats.append(labelRow)
            filesWithFormats[','.join(sorted(labelRow))] = []
        filesWithFormats[','.join(sorted(labelRow))].append(file)
        if elDict not in elementDicts:
            elementDicts.append(elDict)

        labels = labels + fiRow

        labelKeys = [label for label in labels]
        for key in labelKeys:
            for mvaKey in mvaKeys:
                if re.search(mvaKey,key):
                    labels.append(key + ' mva20')
        
        allGDOESdataKeys = set(labels) | set(allGDOESdataKeys)
        allGDOESIntegrationKeys = set(labels) | set(allGDOESIntegrationKeys)
        
    if debuggingMode:
        with open(baseFileSavePath + 'output.txt','w') as f:
            sys.stdout = f
            print len(GDOESformats),'number of different file formats'
            print len(elementDicts),'number of element dicts'
            print fileCounter,'number of different files'
            
            print 'gdoeskeys'
            print ''
            for each in sorted(allGDOESdataKeys):
                print each
            print ''
            print 'integral keys'
            print ''
            for each in sorted(allGDOESIntegrationKeys):
                print each

            print 'element dict'
            print ''
            print allElementDict

            print 'earliest run time:', time.localtime(earliestRunTime)
            print 'total file size:', totalFileSize

    if saveFileInfo:
        with open(baseFileSavePath + 'allGDOESdataKeys-'+folder,'wb') as wf:
            pickle.dump(allGDOESdataKeys,wf)
        with open(baseFileSavePath + 'allGDOESIntegrationKeys-'+folder,'wb') as wf:
            pickle.dump(allGDOESIntegrationKeys,wf)
        with open(baseFileSavePath + 'GDOESkeyDict-'+folder,'wb') as wf:
            pickle.dump(GDOESkeyDict,wf)
        with open(baseFileSavePath + 'labelsNotInElementDict-'+folder,'wb') as wf:
            pickle.dump(labelsNotInElementDict,wf)
        
    # writes GDOESkeyDict to csv file
    if debuggingMode:
        someKeys = ['mult','pos','rawlabel']
        with open(baseFileSavePath + 'GDOESKEYDICT.CSV','wb') as csvf:
            keyWriter = csv.writer(csvf,delimiter=',')
            keyWriter.writerow(['substrate','file'] + [key for key in sorted(allGDOESdataKeys)])
            for file in GDOESkeyDict.keys():
                rowToWrite = [runData[file],file]
                for element in sorted(allGDOESdataKeys):
                    try:
                        rowToWrite.append([GDOESkeyDict[file][element][key] for key in someKeys])
                    except KeyError:
                        rowToWrite.append(['N/A' for key in someKeys])
                keyWriter.writerow(rowToWrite)

    if logProcessing:
        outf = open(baseFileSavePath + 'GDOESoutlog.txt','a')
        sys.stdout=outf
    
    endTime = time.time()
    print 'took', endTime - startTime, 'seconds'
    print 'or', (endTime - startTime)/60, 'minutes'
    return

def write_GDOES_data():
    for file in sorted(allGDOESdata.keys()):
        print 'saving data for file ', file
        for count in range(len(allGDOESdata[file]['X'])):
            rawGDOEStoWrite = []
            for key in sorted(allGDOESdataKeys):
                try:
                    rawGDOEStoWrite.append(allGDOESdata[file][key][count])
                except KeyError:
                    rawGDOEStoWrite.append(0.0)
            rawIntegratedGDOEStoWrite = []
            for key in sorted(allGDOESIntegrationKeys):
                try:
                    rawIntegratedGDOEStoWrite.append(allGDOESdataIntegration[file][key])
                except KeyError:
                    rawIntegratedGDOEStoWrite.append(0.0)
            dataWriter.writerow(rawGDOEStoWrite + [runData[file][key] for key in runDataLabels] + [file,folder])
            if runData[file]['substrate'] in ReliRunsDict.keys():
                ReliDataWriter.writerow(rawGDOEStoWrite + [runData[file][key] for key in runDataLabels] + [file,folder] + [ReliRunsDict[runData[file]['substrate']][key] for key in ReliKeys])
        for key in borderLabels:
            try:
                rawIntegratedGDOEStoWrite.append(borderTimes[file][key])
            except KeyError:
                rawIntegratedGDOEStoWrite.append(0.0)
        integrationWriter.writerow(rawIntegratedGDOEStoWrite + [runData[file][key] for key in runDataLabels] + [file,folder])
        if runData[file]['substrate'] in ReliRunsDict.keys():
            ReliIntegrationWriter.writerow(rawIntegratedGDOEStoWrite + [runData[file][key] for key in runDataLabels] + [file,folder] + [ReliRunsDict[runData[file]['substrate']][key] for key in ReliKeys])
        filesSaved.append(file)
    
    if saveFileInfo:
        with open('GDOES files saved - ' + folder, 'wb') as wf:
            pickle.dump(filesSaved,wf)
    
    return
 
######################################################################################
# the process starts here

mvaKeys = ['Se','Cu 325/Fi','Mo 317/Fi','Fe 386/Fi'] # keys to take moving averages of

runData = {}
runDataLabels = ['substrate', 'DW', 'CW', 'baked', 'bake time', 'pressure', 'power', 'cell number', 'sample number']

basePath = 'Y:/Characterization/GDOES/'
GDOESfolders = {}
GDOESfolders['TCO'] = {}
GDOESfolders['TCO']['path'] = basePath + 'TCO/'
GDOESfolders['PC'] = {}
GDOESfolders['PC']['path'] = basePath + 'PC/'

if logProcessing:
    outf = open(baseFileSavePath + 'GDOESoutlog.txt', 'w')
    sys.stdout = outf
    sys.stderr = (open(baseFileSavePath + 'GDOESerrlog.txt', 'w'))

folderListExists, GDOESfolders = check_if_folders_uptodate(GDOESfolders)

for folder in GDOESfolders.keys():
    # if no change in files since last checked (modified time of overall folder is the same), load saved list of them
    if folderListExists and GDOESfolders[folder]['latestMtime'] == os.path.getmtime(GDOESfolders[folder]['path']):
        runData, fileDict, allGDOESdataKeys, allGDOESIntegrationKeys, GDOESkeyDict, labelsNotInElementDict = load_file_details()
    else:        
        fileDict = parse_file_details(sumReString)
        runData = parse_run_details_andSave(fileDict, GDOESfolders)
        parse_GDOES_row_labels_andSaveData(runData)

        '''it was having trouble parsing all the file info then going straight
           into loading the files.  For now have to run the script twice'''
        continue
        exit()
        
    ##############################
    # write initial header line to csv file
    ReliKeys = sorted(ReliRunsDict['304'].keys())

    dataWriter = csv.writer(open(baseFileSavePath + 'all GDOES data.csv', 'wb'),delimiter = ',')
    ReliDataWriter = csv.writer(open(baseFileSavePath + 'all GDOES data - with reli labels.csv', 'wb'),delimiter = ',')

    otherXs = ['X by CIGS top','X by MoSe2 top','X by Mo top','X by Fe top']
    allGDOESdataKeys = list(allGDOESdataKeys)
    for anX in otherXs:
        allGDOESdataKeys.append(anX)

    dataWriter.writerow(sorted(list(allGDOESdataKeys)) + runDataLabels + ['file name','after process step',])
    ReliDataWriter.writerow(sorted(list(allGDOESdataKeys)) + runDataLabels + ['file name','after process step'] + ReliKeys)

    intLabels = sorted(allGDOESIntegrationKeys)
    borderLabels = ['CIGS start','MoSe start','Mo start','Fe start']

    integrationWriter = csv.writer(open(baseFileSavePath + 'all GDOES integration data.csv','wb'), delimiter = ',')
    integrationWriter.writerow(intLabels + borderLabels + runDataLabels + ['file name','after process step'])

    ReliIntegrationWriter = csv.writer(open(baseFileSavePath + 'all GDOES integration data - with reli labels.csv','wb'), delimiter = ',')

    ReliIntegrationWriter.writerow(intLabels + borderLabels + runDataLabels + ['file name','after process step'] + ReliKeys)

    pid = os.getpid()
    #######################################
    # collect data here
    allGDOESdata = {}
    borderTimes = {}
    allGDOESdataIntegration = {}
    filesSaved = []
    totalFiles = len(runData)
    fileCount = 0
    for file in sorted(runData.keys()):
        if logProcessing:
            outf = open(baseFileSavePath + 'GDOESoutlog.txt','a')
            sys.stdout=outf
        if int(runData[file]['substrate']) < runCutoff:
            print 'skipping',file,'because substrate',runData[file]['substrate'],'under', runCutoff
            continue
        if 'Se 207' not in GDOESkeyDict[file].keys():
            print 'skipping', file, 'because doesn\'t have Se key in it'
            continue # skip files with no Se in them (have it only as Se/Fi), such as C438266_S285_PRF-1.jy
        fileCount += 1
        print '% done:', float(fileCount)/totalFiles
        py = psutil.Process(pid)
        memoryUse = py.memory_info()[0]/2.**30
        print memoryUse
        if memoryUse > 1.0: # if memory use is over 1GB, write data so we don't crash the program
            print 'writing data to free up memory'
            write_GDOES_data()
            del allGDOESdata
            del allGDOESdataIntegration
            del borderTimes
            allGDOESdata = {}
            allGDOESdataIntegration = {}
            borderTimes = {}
            gc.collect()

        print file
        if 'Fi' not in GDOESkeyDict[file].keys(): # need to adjust code to deal with no Fi...will take significant work
            continue
        if 'csvFile' in globals():
                csvFile.close()

        allGDOESdataIntegration[file] = {}
        borderTimes[file] = {}
        allGDOESdata[file] = {}
        dataStarted = False
        plasmaOn = False
        setScrapTime = False
        timeOffset = 0
        scrapTime = 2.0 # time to cut off from beginning of measurement, in s

        csvFile = open(fileDict[file]['filePath'], 'rb')
        GDOEScsv = csv.reader(csvFile, delimiter = '\t')
        for row in GDOEScsv:
            if dataStarted:
                Fi = float(row[GDOESkeyDict[file]['Fi']['pos']]) * GDOESkeyDict[file]['Fi']['mult']
                if not plasmaOn and Fi > 2.0:# line up by plasma turning on
                    timeOffset = float(row[0])
                    plasmaOn = True
                elif not plasmaOn:
                    continue

                if (float(row[GDOESkeyDict[file]['X']['pos']]) - timeOffset) < scrapTime: # don't use first 2 seconds
                    continue
                elif not setScrapTime:
                    setScrapTime = True
                    subScrapTime = float(row[GDOESkeyDict[file]['X']['pos']]) - timeOffset # set time subtraction so first point of X is 0

                for label in GDOESkeyDict[file].keys():
                    if Fi < 0.2: #sometimes plasma shut off for end of measurement
                        continue
                    if label in allGDOESdata[file].keys():
                        if label == 'X':
                            allGDOESdata[file]['X'].append(float(row[GDOESkeyDict[file]['X']['pos']]) - timeOffset - subScrapTime) # make time 0 when plasma turns on
                        elif GDOESkeyDict[file]['Se 207']['rawlabel'] == 'Se/Fi':
                            allGDOESdata[file][label].append(float(row[GDOESkeyDict[file][label]['pos']]) * Fi)
                        else:
                            allGDOESdata[file][label].append(float(row[GDOESkeyDict[file][label]['pos']]) * GDOESkeyDict[file][label]['mult'])
                    else:
                        if label == 'X':
                            allGDOESdata[file]['X'] = [float(row[GDOESkeyDict[file]['X']['pos']]) - timeOffset - subScrapTime] # make time 0 when plasma turns on
                        elif GDOESkeyDict[file]['Se 207']['rawlabel'] == 'Se/Fi':
                            allGDOESdata[file][label] = [float(row[GDOESkeyDict[file][label]['pos']]) * Fi]
                        else:
                            allGDOESdata[file][label] = [float(row[GDOESkeyDict[file][label]['pos']]) * GDOESkeyDict[file][label]['mult']]
            else:
                if len(row)>0 and row[0] == 'X':
                    dataStarted = True
        print 'loaded ', file

        if not plasmaOn:
            print 'skipping file becasue plasma never turned on'
            del allGDOESdata[file]
            continue

        if (max(allGDOESdata[file]['X'])-min(allGDOESdata[file]['X'])) < 50:
            print 'skipping file because total time of run is:', (max(allGDOESdata[file]['X'])-min(allGDOESdata[file]['X']))
            del allGDOESdata[file]
            continue
        '''if GDOESdata.keys() == []:
            print 'skipping run',file,'because GDOESdata is empty'
            continue'''


        '''plotKeys = ['In/Fi','Zn/Fi','Cd/Fi','Cu/Fi','Mo/Fi','Fe/Fi','Na/Fi']

        for plotKey in plotKeys:
            if plotKey not in GDOESdata.keys():
                element = key[:2]
                for key in GDOESdata.keys():
                    if re.search(element,key):
                        if re.search(element + '\*\d+',key):
                            multiplier = re.search(element + '\*(\d+)',key).group(1)
                            GDOESdata[element] = np.array(GDOESdata[key],dtype = 'float64') / multiplier
                            GDOESdata[plotKey] = np.divide(np.array(GDOESdata[element],dtype = 'float64'), np.array(GDOESdata['Fi'], dtype = 'float64'))
                        elif re.search(element,key):
                            GDOESdata[plotKey] = np.divide(np.array(GDOESdata[key],dtype = 'float64'),np.array(GDOESdata['Fi'], dtype = 'float64'))

            if 'Cu/Fi' not in GDOESdata.keys():
                for key in GDOESdata.keys():
                    if re.search('Cu',key):
                        GDOESdata['Cu/Fi'] = np.divide(np.array(GDOESdata[key],dtype = 'float64'),np.array(GDOESdata['Fi'], dtype = 'float64'))
            if 'In/Fi' not in GDOESdata.keys():
                for key in GDOESdata.keys():
                    if re.search('In',key):
                        GDOESdata['In/Fi'] = np.divide(np.array(GDOESdata[key],dtype = 'float64'),np.array(GDOESdata['Fi'],dtype = 'float64'))
            if 'Ga/Fi' not in GDOESdata.keys():
                for key in GDOESdata.keys():
                    if re.search('Ga',key):
                        GDOESdata['Ga/Fi'] = np.divide(np.array(GDOESdata[key],dtype = 'float64'),np.array(GDOESdata['Fi'],dtype = 'float64'))

        if 'Se2/Fi2' not in GDOESdata.keys():
            if isElementDict:
                for wl in elementDict.keys():
                    if wl == '207':
                        GDOESdata['Se2/Fi2'] = GDOESdata[elementDict[wl]]
                        del GDOESdata[elementDict[wl]]
            elif 'Se/Fi' in GDOESdata.keys():
                GDOESdata['Se2/Fi2'] = GDOESdata['Se/Fi']
                del GDOESdata['Se/Fi']
            elif 'Se' in GDOESdata.keys():
                GDOESdata['Se2/Fi2'] = np.array(GDOESdata['Se']) / np.array(GDOESdata['Fi'])'''

        for key in allGDOESdata[file].keys():
            allGDOESdata[file][key] = np.array(allGDOESdata[file][key], dtype = 'float64')

        for key in allGDOESdata[file].keys():
            if key not in labelsNotInElementDict:
                allGDOESdata[file][key + '/Fi'] = np.divide(allGDOESdata[file][key],allGDOESdata[file]['Fi'])

        for key in allGDOESdata[file].keys():
            for mvaKey in mvaKeys:
                if re.search(mvaKey,key):
                    forwardMVA = pd.rolling_mean(allGDOESdata[file][key],5)
                    reverseMVA = pd.rolling_mean(allGDOESdata[file][key][::-1],5)
                    MVA20 = (forwardMVA + reverseMVA[::-1])/2
                    allGDOESdata[file][key + ' mva20'] = MVA20
                    allGDOESdata[file][key + ' mva20'][np.isnan(allGDOESdata[file][key + ' mva20'])] = 0

        # from 384 DW 182 CW 46, ex situ
        CuMultiplier = 0.663324546134
        InMultiplier = 14.0202014032
        GaMultiplier = 7.7784824715

        allGDOESdata[file]['Cu3'] = []
        allGDOESdata[file]['Cu %'] = allGDOESdata[file]['Cu 325/Fi'] / CuMultiplier
        allGDOESdata[file]['In %'] = allGDOESdata[file]['In 451/Fi'] / InMultiplier
        allGDOESdata[file]['Ga %'] = allGDOESdata[file]['Ga 417/Fi'] / GaMultiplier
        allGDOESdata[file]['Cu+In+Ga %'] = allGDOESdata[file]['Cu %'] + allGDOESdata[file]['In %'] + allGDOESdata[file]['Ga %']

        hitCigs = False
        hitMoSe = False
        hitMo = False
        hitFe = False
        hitFeBack = False

        CIGSstartIndex = len(allGDOESdata[file]['X'])-5
        MoSestartIndex = len(allGDOESdata[file]['X'])-4
        MostartIndex = len(allGDOESdata[file]['X'])-3
        FestartIndex = len(allGDOESdata[file]['X'])-2
        FeBackstartIndex = len(allGDOESdata[file]['X'])-1 # by default set this to last element of the array(s)

        for count in range(len(allGDOESdata[file]['X'])):
            allGDOESdata[file]['Cu3'].append((allGDOESdata[file]['Cu 325/Fi'][count] / CuMultiplier) / ((allGDOESdata[file]['In 451/Fi'][count] / InMultiplier) + (allGDOESdata[file]['Ga 417/Fi'][count] / GaMultiplier)))

        for count in range(len(allGDOESdata[file]['X'])-21):
            if not hitCigs and allGDOESdata[file]['X'][count]>3: # if no copper observed yet (i.e. not in the CIGS layer)
                if allGDOESdata[file]['Cu 325/Fi mva20'][count] > 0.02 and allGDOESdata[file]['X'][count] > 4.0:
                    CIGSstartTimeOffset = allGDOESdata[file]['X'][count]
                    CIGSstartIndex = count
                    hitCigs = True

            if hitCigs and not hitMoSe:
                if allGDOESdata[file]['Mo 317/Fi mva20'][count] > 0.05 and count > CIGSstartIndex + 5:#0.0015:
                    MoSestartTimeOffset = allGDOESdata[file]['X'][count]
                    MoSestartIndex = count
                    hitMoSe = True

            if not hitFe:
                if allGDOESdata[file]['Fe 386/Fi mva20'][count] > 0.05 and count > MoSestartIndex + 5:#0.0015:
                    FestartTimeOffset = allGDOESdata[file]['X'][count]
                    FestartIndex = count
                    hitFe = True

            if hitFe and not hitFeBack:
                if allGDOESdata[file]['Mo 317/Fi mva20'][count] < 0.05 and allGDOESdata[file]['Fe 386/Fi mva20'][count] > 0.2 and count > FestartIndex + 5:#0.0015:
                    FeBackstartTimeOffset = allGDOESdata[file]['X'][count]
                    FeBackstartIndex = count
                    hitFeBack = True

        if not hitMo:
            MostartIndex = list(allGDOESdata[file]['Mo 317/Fi mva20']).index(max(allGDOESdata[file]['Mo 317/Fi mva20']))
            MostartTimeOffset = allGDOESdata[file]['X'][MostartIndex]
            if MostartIndex<=MoSestartIndex:
                hitMo = False
            else:
                hitMo = True
                for count in range(len(allGDOESdata[file]['X']) - 21):
                    if not hitFe:
                        if allGDOESdata[file]['Fe 386/Fi mva20'][count] > 0.05 and count > MostartIndex + 1:#0.0015:
                            FestartTimeOffset = allGDOESdata[file]['X'][count]
                            FestartIndex = count
                            hitFe = True
                    if hitFe and not hitFeBack:
                        if allGDOESdata[file]['Mo 317/Fi mva20'][count] < 0.05 and allGDOESdata[file]['Fe 386/Fi mva20'][count] > 0.2 and count > FestartIndex + 5:#0.0015:
                            FeBackstartTimeOffset = allGDOESdata[file]['X'][count]
                            FeBackstartIndex = count
                            hitFeBack = True
        if hitFeBack:
            for key in allGDOESdata[file].keys():
                allGDOESdata[file][key] = allGDOESdata[file][key][:FeBackstartIndex] # trim off data where it is only the Fe substrate
            # if any of the indices are beyond the array length after trimming, reset to default values

        if FestartIndex >= FeBackstartIndex:
            FestartIndex = len(allGDOESdata[file]['X'])-2
            hitFe = False
        if MostartIndex >= FeBackstartIndex or MostartIndex >= FestartIndex:
            MostartIndex = len(allGDOESdata[file]['X'])-3
            hitMo = False
        if MoSestartIndex >= FeBackstartIndex or MoSestartIndex >= MostartIndex or MoSestartIndex >= FestartIndex:
            MoSestartIndex = len(allGDOESdata[file]['X'])-4
            hitMoSe = False
        if CIGSstartIndex >= FeBackstartIndex or CIGSstartIndex >= MoSestartIndex or CIGSstartIndex >= MostartIndex or CIGSstartIndex >= FestartIndex:
            hitCigs = False
            CIGSstartIndex = len(allGDOESdata[file]['X'])-5

        print CIGSstartIndex, MoSestartIndex, MostartIndex, FestartIndex, FeBackstartIndex

        #borderIndices[file] = {}
        '''borderIndices[file]['CIGSstartIndex'] = CIGSstartIndex
        borderIndices[file]['CIGSendIndex'] = CIGSendIndex
        borderIndices[file]['MoSestartIndex'] = MoSestartIndex
        borderIndices[file]['MostartIndex'] = MostartIndex
        borderIndices[file]['FestartIndex'] = FestartIndex'''

        if hitCigs:
            borderTimes[file]['CIGS start'] = allGDOESdata[file]['X'][CIGSstartIndex]
            allGDOESdata[file]['X by CIGS top'] = []
            if hitMoSe:
                borderTimes[file]['MoSe start'] = allGDOESdata[file]['X'][MoSestartIndex]
                allGDOESdata[file]['X by MoSe2 top'] = []
                if hitMo:
                    borderTimes[file]['Mo start'] = allGDOESdata[file]['X'][MostartIndex]
                    allGDOESdata[file]['X by Mo top'] = []
                    if hitFe:
                        borderTimes[file]['Fe start'] = allGDOESdata[file]['X'][FestartIndex]
                        allGDOESdata[file]['X by Fe top'] = []

        if hitCigs:
            allGDOESdata[file]['X by CIGS top'] = allGDOESdata[file]['X'] - CIGSstartTimeOffset
            if hitMoSe:
                allGDOESdata[file]['X by MoSe2 top'] = allGDOESdata[file]['X'] - MoSestartTimeOffset
                if hitMo:
                    allGDOESdata[file]['X by Mo top'] = allGDOESdata[file]['X'] - MostartTimeOffset
                    if hitFe:
                        allGDOESdata[file]['X by Fe top'] = allGDOESdata[file]['X'] - FestartTimeOffset


        for key in allGDOESdata[file].keys():
            if not re.search('X', key):
                allGDOESdataIntegration[file][key] = simps(allGDOESdata[file][key],allGDOESdata[file]['X'])

        if hitCigs:
            allGDOESdataIntegration[file]['In in ITO'] = simps(allGDOESdata[file]['In 451/Fi'][:CIGSstartIndex],allGDOESdata[file]['X'][:CIGSstartIndex])
            allGDOESdataIntegration[file]['In in CIGS'] = simps(allGDOESdata[file]['In 451/Fi'][CIGSstartIndex:],allGDOESdata[file]['X'][CIGSstartIndex:])
            allGDOESdataIntegration[file]['Na in TCO'] = simps(allGDOESdata[file]['Na 590/Fi'][:CIGSstartIndex],allGDOESdata[file]['X'][:CIGSstartIndex])
            allGDOESdataIntegration[file]['Cd in CIGS'] = simps(allGDOESdata[file]['Cd 229/Fi'][CIGSstartIndex:],allGDOESdata[file]['X'][CIGSstartIndex:])
            if hitMoSe:
                allGDOESdataIntegration[file]['Se in CIGS'] = simps(allGDOESdata[file]['Se 207/Fi'][CIGSstartIndex:MoSestartIndex],allGDOESdata[file]['X'][CIGSstartIndex:MoSestartIndex])
                allGDOESdataIntegration[file]['Na in CIGS'] = simps(allGDOESdata[file]['Na 590/Fi'][CIGSstartIndex:MoSestartIndex],allGDOESdata[file]['X'][CIGSstartIndex:MoSestartIndex])
                allGDOESdataIntegration[file]['Na in TCO+CIGS'] = simps(allGDOESdata[file]['Na 590/Fi'][:MoSestartIndex],allGDOESdata[file]['X'][:MoSestartIndex])
                allGDOESdataIntegration[file]['Na below CIGS'] = simps(allGDOESdata[file]['Na 590/Fi'][MoSestartIndex:],allGDOESdata[file]['X'][MoSestartIndex:])
                allGDOESdataIntegration[file]['Se in CIGS'] = simps(allGDOESdata[file]['Se 207/Fi'][CIGSstartIndex:MoSestartIndex],allGDOESdata[file]['X'][CIGSstartIndex:MoSestartIndex])
                allGDOESdataIntegration[file]['Se in MoSe2'] = simps(allGDOESdata[file]['Se 207/Fi'][MoSestartIndex:],allGDOESdata[file]['X'][MoSestartIndex:])
                if hitMo:
                    allGDOESdataIntegration[file]['Se in MoSe2'] = simps(allGDOESdata[file]['Se 207/Fi'][MoSestartIndex:MostartIndex],allGDOESdata[file]['X'][MoSestartIndex:MostartIndex])
                    allGDOESdataIntegration[file]['Na in MoSe2'] = simps(allGDOESdata[file]['Na 590/Fi'][MoSestartIndex:MostartIndex],allGDOESdata[file]['X'][MoSestartIndex:MostartIndex])
                    allGDOESdataIntegration[file]['Na in Mo'] = simps(allGDOESdata[file]['Na 590/Fi'][MostartIndex:],allGDOESdata[file]['X'][MostartIndex:])

        # plot GDOES data, only works for TCO full stack data
        if savePlots and folder == 'TCO':
            f, (ax1, ax2, ax3, ax4, ax5, ax6, ax7, ax8, ax9) = plt.subplots(9, sharex = True)
            ax = ['ax' + str(each) for each in range(1,10)]

            ax1.plot(allGDOESdata[file][plotBy], allGDOESdata[file]['In 451/Fi'])
            ax2.plot(allGDOESdata[file][plotBy], allGDOESdata[file]['Zn 335/Fi'])
            ax3.plot(allGDOESdata[file][plotBy], allGDOESdata[file]['Cd 229/Fi'])
            ax4.plot(allGDOESdata[file][plotBy], allGDOESdata[file]['Cu 325/Fi'])
            ax4.plot(allGDOESdata[file][plotBy], allGDOESdata[file]['Cu 325/Fi mva20'])
            ax5.plot(allGDOESdata[file][plotBy], allGDOESdata[file]['Mo 317/Fi'])
            ax5.plot(allGDOESdata[file][plotBy], allGDOESdata[file]['Mo 317/Fi mva20'])
            ax6.plot(allGDOESdata[file][plotBy], allGDOESdata[file]['Fe 386/Fi'])
            ax6.plot(allGDOESdata[file][plotBy], allGDOESdata[file]['Fe 386/Fi mva20'])
            ax7.plot(allGDOESdata[file][plotBy], allGDOESdata[file]['Se 207/Fi'])
            ax7.plot(allGDOESdata[file][plotBy], allGDOESdata[file]['Se 207/Fi mva20'])
            ax8.plot(allGDOESdata[file][plotBy], allGDOESdata[file]['Na 590/Fi'])
            ax9.plot(allGDOESdata[file][plotBy], allGDOESdata[file]['Fi'])
            if hitCigs:
                ax1.axvline(borderTimes[file]['CIGS start'])
                if hitMoSe:
                    ax5.axvline(borderTimes[file]['MoSe start'])
                    if hitMo:
                        ax5.axvline(borderTimes[file]['Mo start'])
                        if hitFe:
                            ax6.axvline(borderTimes[file]['Fe start'])
                            if hitFeBack:
                                ax6.axvline(FeBackstartTimeOffset)
            ax1.set_ylabel('In')
            ax2.set_ylabel('Zn')
            ax3.set_ylabel('Cd')
            ax4.set_ylabel('Cu')
            ax5.set_ylabel('Mo')
            ax6.set_ylabel('Fe')
            ax7.set_ylabel('Se 207')
            ax8.set_ylabel('Na')
            ax9.set_ylabel('Fi')
            ax8.set_xlabel(plotBy)

            plt.tight_layout()
            figure = plt.gcf() # get current figure
            figure.set_size_inches(12, 8)
            figure.subplots_adjust(hspace = 0.01)
            figure.suptitle(runData[file]['substrate'] + ', ' + file + ', signals normalized by Fi')
            for a in ax:
                plt.setp(eval(a).get_yticklabels()[-1], visible=False)

            plt.savefig(savePlotsPath + 'plots/' + file[:-3] + '.png', facecolor = 'w')
            plt.close()
        if logProcessing:
            outf.close()

write_GDOES_data()
endTime = time.time()

print 'took', endTime - startTime, 'seconds'
print 'or', (endTime - startTime)/60, 'minutes'