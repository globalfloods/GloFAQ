# Load required libraries
import requests
import numpy as np
import matplotlib.pyplot as plt

# country = "Myanmar"
# south = 18
# north = 23
# east = 99
# west = 92

country = "Congo"
south = -6
north = 4
east = 20
west = 11
 
mask_threshold = 100

# Discharge
url_fmt = 'http://incubator.ecmwf.int/2e/rasdaman/ows?service=WCS&version=2.0.1&request=ProcessCoverages&query=for c in (%s) return encode(c[Lat(%f:%f), Long(%f:%f), forecast(%i), ensemble(%i), ansi("%s")], "csv") '

discharges = []
for forecast in range(16):
    url = url_fmt % ("discharge_forecast", south, north, west, east, forecast*24, 0, "2015-12-16T00:00:00+00:00")
    print url

    r= requests.get(url)

    r.raise_for_status()
    discharge = np.array([row.split(",") for row in r.text[1:-1].split("},{")],dtype=np.float).T

    discharge[discharge<mask_threshold] = 0

    discharges.append(discharge)

    print discharge

plt.figure()
plt.title('{}: Discharge'.format(country))
plt.imshow(discharges[0],interpolation="none")
plt.colorbar()

plt.savefig('{}-discharge.pdf'.format(country))

# Return period
url_fmt = 'http://incubator.ecmwf.int/2e/rasdaman/ows?service=WCS&version=2.0.1&request=ProcessCoverages&query=for c in (%s) return encode(c[Lat(%f:%f), Long(%f:%f)], "csv") '

url = url_fmt % ("return_level5", south, north, west, east)
print url

r = requests.get(url)

r.raise_for_status()
return_period = np.array([row.split(",") for row in r.text[1:-1].split("},{")],dtype=np.float).T/2

return_period[return_period<mask_threshold] = 0

print return_period

plt.close('all')

plt.figure()
plt.title('{}: Return period'.format(country))
plt.imshow(return_period, interpolation="none")
plt.colorbar()

plt.savefig('{}-return-period.pdf'.format(country))

plt.figure()
plt.title('{}: Discharge greater than return period'.format(country))
plt.imshow(discharges[0]>return_period,interpolation="none")
plt.colorbar()

plt.savefig('{}-discharge-greater-than-return-period-0-hrs.pdf'.format(country))

# QGIS understands this:
# http://incubator.ecmwf.int/2e/rasdaman/ows?service=WCS&version=2.0.1&request=GetCoverage&coverageId=discharge_forecast&subset=Lat(18,22)&subset=Long(92,99)&subset=ansi(%222015-08-23T00:00:00+00:00%22)&subset=forecast(0)&subset=ensemble(0)&format=application/netcdf

import overpy

api = overpy.Overpass()

# fetch all ways and nodes
result = api.query("""
    <osm-script output="xml" timeout="25">
        <union>
            <query type="node">
                <has-kv k="highway" v="primary"/>
                <bbox-query e="{0}" n="{1}" s="{2}" w="{3}"/>
            </query>
            <query type="way">
                <has-kv k="highway" v="primary"/>
                <bbox-query e="{0}" n="{1}" s="{2}" w="{3}"/>
            </query>
            <query type="relation">
                <has-kv k="highway" v="primary"/>
                <bbox-query e="{0}" n="{1}" s="{2}" w="{3}"/>
            </query>
        </union>
        <union>
            <item/>
            <recurse type="down"/>
        </union>
        <print mode="body"/>
    </osm-script>
""".format(east,north,south,west))

from shapely.geometry import LineString, box
roads = []
for way in result.ways:
    roads.append(LineString([(node.lon, node.lat) for node in way.nodes]))

delta_lat = float(north - south) / return_period.shape[0]
delta_lon = float(east - west) / return_period.shape[1]

yl,xl = return_period.shape
pixels = []
for xi in range(xl):
    pixels.append([])
    for yi in range(yl):
        west_lon = west+xi*delta_lon
        north_lat = north-yi*delta_lat
        east_lon = west+(xi+1)*delta_lon
        south_lat = north-(yi+1)*delta_lat
        pixels[-1].append(box(west_lon,south_lat,east_lon,north_lat))
        print xi,yi,west_lon,south_lat,east_lon,north_lat

pixels = np.array(pixels)

for forecast,discharge in enumerate(discharges):
    plt.figure()
    plt.title('{}: Roads likely to be flooded: Day {}'.format(country,forecast))
    plt.imshow(discharge>return_period,extent=[west,east,south,north],alpha=0.5,interpolation="none")
    plt.colorbar()
    for road in roads:
        nz_yi,nz_xi = (discharge>return_period).nonzero()
        flooded = [road.intersects(pixels[yi][xi]) for xi,yi in zip(nz_yi,nz_xi)]
        if True in flooded:
             plt.plot(*road.xy,c='r',linewidth=1)
        else:
            plt.plot(*road.xy,c='g',linewidth=1)

    plt.savefig('{}-roads-likely-to-be-flooded-day-{}.pdf'.format(country,forecast))  
    print 'Day', forecast