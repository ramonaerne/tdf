import pandas as pd
import numpy as np
import difflib

hdf = pd.HDFStore('tdf_coverage_raw.h5')
# remove old frames, then use this:
#frames = [hdf[k] for k in hdf.keys()]
frames = [hdf[hdf.keys()[2]]]

for df in frames:
    # start out by ignoring the teams
    names = df[2].values

    # the idea is to read a reference name list with all started riders (and correct names hopefully)
    csv = np.genfromtxt ('shortname_only.csv', delimiter=',', dtype="U")
    # convert to list
    refnames = [c for c in csv]

    # SIMPLE Approach 1: first idea is to ignor everything except A-Za-z and "." then we search for
    # the dot seperating name and surname (which from the data was detected most of the time). Everything
    # before the dot is the name, everything after is surname.

    filteredNames = [''.join(e for e in name if (e.isalnum() or e=='.' or e==' ')) for name in names]

    def match(name):
        matches = difflib.get_close_matches(name.upper(), refnames)
        print(name, matches)
        return matches[0] if matches else []


    matchedFiltered = [match(name) for name in filteredNames]
    matchedUnFiltered = [match(name) for name in names]

    df = pd.Series(matchedFiltered, index=df.index)
    # store TODO

hdf.close()
