import os, csv, datetime, pytz, time
from dateutil.parser import parse

local = pytz.timezone("America/Los_Angeles")
utc = pytz.timezone("UTC")

cellDict = {}
dictKeys = {}
rowsToKeep = [0,1,5,6,47]

csvFile = 'Y:\\Nate\\act vision system\\cells 5-27 to 5-28 with vision on.csv'


firstRow = True
with open(csvFile,'rb') as f:
	cellReader = csv.reader(f,delimiter = ',')
	for row in cellReader:
		if not firstRow:
			for key in dictKeys.keys():
				if key == 'TimeTested':
					testTime = parse(row[dictKeys[key]])
					local_dt = local.localize(testTime, is_dst = None)
					utc_epoch = utc.localize(datetime.datetime(1970,1,1))
					epochTime = (local_dt - utc_epoch).total_seconds()
					cellDict[key].append(epochTime)
				else:
					cellDict[key].append(row[dictKeys[key]])
		else:
			for eachRow in rowsToKeep: # TimeTested, CellID, SortBin, FailBin
				cellDict[row[eachRow]] = []
				dictKeys[row[eachRow]] = eachRow
			firstRow = False
			
print dictKeys

basePath = 'Y:\FTP\Visual_Inspection\ACT02\\'
datePaths = ['150527\\','150528\\'] #['150528\\'] #
camPaths = {'right' : 'CAM1\\', 'left' : 'CAM4\\'}
camFailedCells = {}




for cam in camPaths.keys():
	camFailedCells[cam] = {}
	for date in datePaths:
		filePath = basePath + date + camPaths[cam]
		print cam
		for thing in sorted(os.listdir(filePath), key = lambda file: os.path.getmtime(filePath + file)):
			if thing[-3:] == 'bmp':
				# camTime = os.path.getmtime(filePath + thing)
				(mode, ino, dev, nlink, uid, gid, size, atime, mtime, ctime) = os.stat(filePath + thing)
				camTime = mtime
				# get TimeTested from IV tests nearest to camera picture save time and add IV data to cam info dict
				cellIndex=min(range(len(cellDict['TimeTested'])), key=lambda i: abs(cellDict['TimeTested'][i]-camTime))
				print thing, time.strftime("%d/%m/%Y %I:%M:%S %p", time.localtime(cellDict['TimeTested'][cellIndex])), ',', time.strftime("%d/%m/%Y %I:%M:%S %p", time.localtime(camTime)),',', cellIndex, camTime - cellDict['TimeTested'][cellIndex]
				
				timeDiff = camTime - cellDict['TimeTested'][cellIndex]
				if timeDiff >= 0.0:
					#print cellDict['CellID'][cellIndex]
					camFailedCells[cam][cellDict['CellID'][cellIndex]] = {}
					for key in dictKeys.keys():
						if key == 'TimeTested':
							camFailedCells[cam][cellDict['CellID'][cellIndex]]['TimeTested'] = time.strftime("%d/%m/%Y %I:%M:%S %p", time.localtime(cellDict['TimeTested'][cellIndex]))
						else:
							camFailedCells[cam][cellDict['CellID'][cellIndex]][key] = cellDict[key][cellIndex]
					camFailedCells[cam][cellDict['CellID'][cellIndex]]['camera time'] = time.strftime("%d/%m/%Y %I:%M:%S %p", time.localtime(camTime))
			
		for each in camFailedCells[cam]:
			print each
	
with open('camFailedCells.csv','wb') as f:
	failWriter = csv.writer(f, delimiter = ',')
	failWriter.writerow(['camera', 'camera file save time'] + dictKeys.keys())
	for cam in camPaths.keys():
		print camFailedCells[cam].keys()
		for cellID in sorted(camFailedCells[cam].keys(), key=lambda cellID: camFailedCells[cam][cellID]['camera time']):
			failWriter.writerow([cam,camFailedCells[cam][cellID]['camera time']] + [camFailedCells[cam][cellID][key] for key in dictKeys.keys()])

