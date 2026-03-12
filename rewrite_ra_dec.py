from datetime import datetime, timedelta, timezone
import json
import numpy as np
import os
from pathlib import Path
import sys

# Import necessary classes/modules
sys.path.append("src/")
from observation import ObservationProcessor

class PostProcessObservation(ObservationProcessor):
    # Initialize observation with corresponding parameters
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def processresults(self, current_time, coordinates, json_rfile, PLOTTING_PARAM):
        # print('DEBUG {}'.format(coordinates))
        self.time = current_time
        COORD_CLASS = self.getCoordinates(self.time, **coordinates)
        if False:
            print('DEBUG: {: 05.1f} {: 6.1f} {} {: 05.1f} {: 05.1f} {: 6.1f} {: 05.1f}'.format(
                coordinates['altitude'], coordinates['azimuth'],
                self.RAHr,
                self.RA, self.DEC, self.GAL_LON, self.GAL_LAT))
        else:
            print('data_{}.json RA: {} DEC: {}'.format(self.filetagname, self.RAHr, self.DEC))

        self.freqs = np.array(json_rfile['Data']['Frequency list'], dtype = float)
        self.blank_data = np.array(json_rfile['Data']['Blank spectrum'], dtype = float)
        self.h_line_data = np.array(json_rfile['Data']['H-line spectrum'], dtype = float)
        self.SNR_spectrum = np.array(json_rfile['Data']['SNR Spectrum'], dtype = float)

        self.analyzeData(COORD_CLASS)
        self.plotData(**PLOTTING_PARAM)
        user_params = {
                "SDR": json_rfile['Observation parameters']['SDR'],
                "DSP": json_rfile['Observation parameters']['DSP'],
                "Observer": coordinates,
                "Observation": json_rfile['Observation parameters']['Observation']
            }
        self.writeDatafile(**user_params)

class Reader(object):
    def __init__(self):
        self._to_read = None
        self._end = False
        self._generator = None

    def open(self, to_read):
        self._to_read = to_read
        self._end = False
        self._generator = iter(self)
        return self._generator

    def close(self):
        self._end = True
        try:
            next(self._generator)
        except StopIteration:
            pass
        finally:
            self._generator = None

        self._to_read = None

class FolderReader(Reader):
    def __iter__(self):
        walk_path = self._to_read['rootpath']

        for (root, dirs, files) in os.walk(walk_path):
            #dir = dirs[0] if 0 < len(dirs) else 'none'
            #file = files[0] if 0 < len(files) else 'none'
            #print('find_in_tree', root, dir, file)
            #print('find_in_tree', root, dirs, files)
            if self._end:
                print('ending')
                break

            if 'filespec' in self._to_read:
                files = sorted(files)
                for filenm in files:
                    if filenm in self._to_read['skiplist']:
                        continue

                    if '.#' in filenm:
                        continue

                    if self._to_read['filespec'] in filenm:
                        ind_path = {}
                        ind_path['path'] = root
                        ind_path['name'] = filenm
                        #print('DEBUG: {}'.format(ind_path))
                        yield ind_path

                    if self._end:
                        print('ending')
                        break

class ObsPar:
    def __init__(self):
        self._data = {}
        self._name = None

    @property
    def data(self):
        return self._data

    @property
    def name(self):
        return self._name

    @property
    def isEmpty(self):
        return len(self.data) < 1

    def init(self, name, default):
        if len(self.data):
            self.save()

        self._name = name
        self._load(default)

    def _load(self, j):
        if isinstance(j, dict):
            for k, v in j.items():
                if k == 'seq' and isinstance(j[k], list):
                    # build the list of observations from scratch each time
                    # this list helps create the skiplist if it is required
                    self.data[k] = []
                else:
                    self.data[k] = v

    def load(self):
        try:
            with open(self.name, 'r') as fh:
                d = fh.read(60000)
                j = json.loads(d)
        except:
            j = self.data

        self._load(j)

        return True

    def save(self):
        if self.name is None:
            return

        with open(self.name, 'w') as fh:
            io = {}
            for k in self.data.keys():
                io[k] = self.data[k]

            #if DEBUG: print(io)
            fh.write( json.dumps( io , indent = 4) )

def testing():
    dt = datetime.now(timezone.utc)
    dtstr = '{}'.format(dt)
    time = ''.join(dt.isoformat().split('-'))
    time = ''.join(time.split(':'))
    time = time.split('.')[0]
    print('Time is: {}'.format(dtstr))
    print('Time is: {}'.format(time))
    dt = datetime.now(timezone.utc)
    then = datetime.strptime(dtstr, '%Y-%m-%d %H:%M:%S.%f%z')
    print('time taken is: {}'.format(dt - then))

    json_file = {
                'Time': str(then),
            }

    stime = ''.join(then.isoformat().split('-'))
    stime = ''.join(stime.split(':'))
    stime = stime.split('.')[0]
    with open('Spectrums/data_{}.json'.format(stime), 'w') as file:
        json.dump(json_file, file, indent = 4)

    with open('Spectrums/data_{}.json'.format(stime), 'r') as file:
        json_rfile = json.load(file)

    dt = datetime.now(timezone.utc)
    then = datetime.strptime(json_rfile['Time'], '%Y-%m-%d %H:%M:%S.%f%z')
    print('time taken is: {}'.format(dt - then))

def copyfiles():
    print('Renaming files in data(ra={self.RA},dec={self.DEC}).json format')
    filespec = {'rootpath': 'Spectrums', 'filespec': ').json', 'skiplist': []}
    reader = FolderReader()
    context = reader.open(filespec)
    for item in context:
        # print('DEBUG: convert: {}'.format(item))
        with open('{}/{}'.format(item['path'], item['name']), 'r') as file:
            json_rfile = json.load(file)

        if 'Observation results' in json_rfile:
            print('DEBUG: {}'.format(json_rfile['Observation results']['Time']))
            current_time = datetime.strptime(json_rfile['Observation results']['Time'], '%Y-%m-%d %H:%M:%S.%f%z')

            stime = ''.join(current_time.isoformat().split('-'))
            stime = ''.join(stime.split(':'))
            stime = stime.split('.')[0]
            with open('Spectrums/data_{}.json'.format(stime), 'w') as file:
                json.dump(json_rfile, file, indent = 4)

def createobspecname(item):
    names = item['name'].split('.')
    base = names[0]

    return '{}/{}_seq.json'.format(item['path'], base)

def readnxtobspec(obspec, obspecs, seqname, group):
    group += 1

    if len(obspecs) < group + 1:
        group -= 1

    # save a copy of the observation sequence specification for future reference
    obspec.init(seqname, obspecs[group])
    obspec.load()

    return group

def processfiles(filespec, obspecs, observation_class, PLOTTING_PARAM):
    group = -1
    obspec = ObsPar()
    observation = {}

    deltatime = 0.
    reader = FolderReader()
    context = reader.open(filespec)
    previous_time = None
    for item in context:
        # print('DEBUG: convert: {}'.format(item))
        with open('{}/{}'.format(item['path'], item['name']), 'r') as file:
            json_rfile = json.load(file)

        if 'Observation results' in json_rfile:
            # print('DEBUG: {}'.format(json_rfile['Observation results']['Time']))
            current_time = datetime.strptime(json_rfile['Observation results']['Time'], '%Y-%m-%d %H:%M:%S.%f%z')
            if not previous_time is None:
                deltatime = (current_time - previous_time).total_seconds()
                #print('DEBUG {} time taken is: {}'.format(item['name'], deltatime))
            #else:
            #    print('DEBUG {}'.format(item['name']))

            seqname = createobspecname(item)
            if Path(seqname).is_file() or obspec.isEmpty or obspec.data['deltatimethresh'] < deltatime:
                print('{} deltatime: {:.0f}s'.format(item['name'], deltatime))
                group = readnxtobspec(obspec, obspecs, seqname, group)
                observation['azimuth'] = obspec.data['azimuth']
                observation['altitude'] = obspec.data['altitude']

            observation['latitude'] = json_rfile['Observation parameters']['Observer']['latitude']
            observation['longitude'] = json_rfile['Observation parameters']['Observer']['longitude']
            observation['elevation'] = json_rfile['Observation parameters']['Observer']['elevation']
            observation['azimuth'] = observation['azimuth']
            observation['altitude'] = observation['altitude']

            if not item['name'] in obspec.data['seq']:
                obspec.data['seq'].append(item['name'])

            observation_class.processresults(current_time, observation, json_rfile, PLOTTING_PARAM)

            observation['azimuth'] += obspec.data['azdelta']
            observation['altitude'] += obspec.data['aldelta']
            previous_time = current_time

    obspec.save()

def postprocessfiles():
    print('Processing samples taken at fixed times with regular manual movement between samples')
    print('setting interval to approx 0.15 degrees will result in 6 second pause between samples')
    path = 'config.json'
    config = open(path, 'r')
    parsed_config = json.load(config)

    OBSERVER_PARAM = parsed_config["observer"]
    PLOTTING_PARAM = parsed_config["plotting"]
    OBSERVATION_PARAM = parsed_config["observation"]

    Observation = PostProcessObservation(**OBSERVATION_PARAM)

    filespec = {'rootpath': 'Spectrums', 'filespec': '.json',
                'skiplist': []}

    # Provide a one time only default sequence spec
    # Note this is overridden by the data_xxxx_seq.json file if it exists
    # if multiple sequences appear in the same folder then create
    # an entry for each sequence here (or delete files from the folder)
    obspecs = [{'deltatimethresh': 1000.,
                'azimuth': OBSERVER_PARAM['azimuth'],
                'altitude': OBSERVER_PARAM['altitude'],
                'azdelta': OBSERVATION_PARAM['degree_interval'],
                'aldelta': 0.,
                'seq': []}]

    processfiles(filespec, obspecs, Observation, PLOTTING_PARAM)

    print(obspecs)

if __name__ == "__main__":
    print('WARNING: this script will modify the RA and DEC values of the observations')
    if True:
        postprocessfiles()
    else:
        copyfiles()
