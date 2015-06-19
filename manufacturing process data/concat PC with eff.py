import csv, sys, pickle, os
sys.path.append("Y:/Nate/git/nuvosun-python-lib/")
import nuvosunlib as ns
# since I have to run from the C: drive now, need to change folders into the file directory for storage files
os.chdir(os.path.dirname(os.path.realpath(__file__)))

effData = ns.import_eff_file()

runs = ['446']

allPCdata = {}
cleanedPCdata = {}
OESrunDate = {}
OESdata = {}

for run in runs:
	
	allPCdata[run]={}
	os.chdir('Y:/Nate/combining databases/mc02 after 399')
	for f in iglob('*.csv'):
		if re.search(str(run),f) and not re.search('concatd',f):
			file = f
			DWstart = 0.0
			DWend = float(f[20:23])
			print 'DWend', DWend
			print f
	reader = csv.DictReader(open(file))
	dateCounter = 0 # used to grab date from middle of run, for importing OES data (labeled by date)
	for row in reader:
		for column, value in row.iteritems():
			allPCdata[run].setdefault(column, []).append(value)
			if column == 'DT':
				allPCdata[run].setdefault('epoch seconds', []).append((parse(value)-datetime.datetime(1970,1,1)).total_seconds()) # get seconds since epoch from DT for OES interpolation
				dateCounter += 1
				if dateCounter == 120: #once we are sufficiently in the run and have the correct date for sure
					OESrunDate[run] = value[0:2] + '-' + value[3:5] + '-' + value[6:9] #don't know why it's buggy, for year should be value[8:10]...no idea
	#os.chdir('..')
	# trim data to DW range
	cleanedPCdata[run] = {}
	for key in allPCdata[run].keys():
		cleanedPCdata[run][key]=[]
	count = 0
	for eachDW in allPCdata[run]['XRF 1 Down Web Pos']:
		eachDW = float(eachDW)
		if eachDW>DWstart and eachDW<DWend:
			for key in allPCdata[run].keys():
				cleanedPCdata[run][key].append(allPCdata[run][key][count])
		count+=1
	#add substrate label to data
	cleanedPCdata[run]['substrate']=[]
	for each in range(len(cleanedPCdata[run]['XRF 1 Down Web Pos'])):
		cleanedPCdata[run]['substrate'].append(str(run))
	del allPCdata[run]
    
