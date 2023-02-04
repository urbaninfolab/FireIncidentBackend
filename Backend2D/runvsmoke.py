#
#   Licensed to the Public Domain by the Georgia Forestry Commission
#
#   Originally created by Daniel Chan - IT Programmer & Meteorologist 
#

#!/usr/bin/python
# program to run vsmoke fortran code and generate a kml file
import cgi
import cgitb
cgitb.enable()
import time
import string, sys, math
import re, glob
import subprocess
import json

#vsmokepath = '/var/www/cgi-bin'
#outputpath = '/var/www/html/maps/vsmoke/kml'

# Testing path, edit to be your own.
#vsmokepath = 'C:/Users/PC/Documents/GitHub/SmartCity/data'
#outputpath = 'C:/Users/PC/Documents/GitHub/SmartCity/data'

# This should be the release path when published live
vsmokepath = '/var/www/html/data'
outputpath = '/var/www/html/data'

#**********************************************************************
#**********************************************************************
#**********************************************************************

# define some constants
pi = math.pi

# Ellipsoid model constants (actual values here are for WGS84)
sm_a = 6378137.0
sm_b = 6356752.314
sm_EccSquared = 6.69437999013e-03

UTMScaleFactor = 0.9996


def DegToRad(deg):
    return (deg / 180.0 * math.pi)

def RadToDeg(rad):
    return (rad / math.pi * 180.0)

def ArcLengthOfMeridian(phi):
    n = (sm_a - sm_b) / (sm_a + sm_b)
    alpha = ((sm_a + sm_b) / 2.0) * (1.0 + (math.pow(n, 2.0) / 4.0) + (math.pow (n, 4.0) / 64.0))
    beta = (-3.0 * n / 2.0) + (9.0 * math.pow (n, 3.0) / 16.0) + (-3.0 * math.pow (n, 5.0) / 32.0)
    gamma = (15.0 * math.pow (n, 2.0) / 16.0) + (-15.0 * math.pow (n, 4.0) / 32.0)
    delta = (-35.0 * math.pow (n, 3.0) / 48.0) + (105.0 * math.pow (n, 5.0) / 256.0)
    epsilon = (315.0 * math.pow (n, 4.0) / 512.0)

    result = alpha * (phi + (beta * math.sin (2.0 * phi)) + (gamma * math.sin (4.0 * phi)) + (delta * math.sin (6.0 * phi)) + (epsilon * math.sin (8.0 * phi)))

    return result

def UTMCentralMeridian(zone):
    return DegToRad( -183.0 + (zone * 6.0) )

def FootpointLatitude(y):
    n = (sm_a - sm_b) / (sm_a + sm_b)
    alpha_ = ((sm_a + sm_b) / 2.0) * (1 + (math.pow (n, 2.0) / 4) + (math.pow (n, 4.0) / 64))
    y_ = y / alpha_
    beta_ = (3.0 * n / 2.0) + (-27.0 * math.pow (n, 3.0) / 32.0) + (269.0 * math.pow (n, 5.0) / 512.0)
    gamma_ = (21.0 * math.pow (n, 2.0) / 16.0) + (-55.0 * math.pow (n, 4.0) / 32.0)
    delta_ = (151.0 * math.pow (n, 3.0) / 96.0) + (-417.0 * math.pow (n, 5.0) / 128.0)
    epsilon_ = (1097.0 * math.pow (n, 4.0) / 512.0)
    result = y_ + (beta_ * math.sin (2.0 * y_)) + (gamma_ * math.sin (4.0 * y_)) + (delta_ * math.sin (6.0 * y_)) + (epsilon_ * math.sin (8.0 * y_))

    return result


'''
   /*
   * MapLatLonToXY
   *
   * Converts a latitude/longitude pair to x and y coordinates in the
   * Transverse Mercator projection.  Note that Transverse Mercator is not
   * the same as UTM; a scale factor is required to convert between them.
   *
   * Inputs:
   *    phi - Latitude of the point, in radians.
   *    lambda - Longitude of the point, in radians.
   *    lambda0 - Longitude of the central meridian to be used, in radians.
   *
   * Returns:
   *    xy - A 2-element array containing the x and y coordinates
   *         of the computed point.
   */
'''
def MapLatLonToXY(phi, lambda1, lambda0):
       ep2 = (math.pow(sm_a, 2.0) - math.pow(sm_b, 2.0)) / math.pow(sm_b, 2.0)
       nu2 = ep2 * math.pow(math.cos(phi), 2.0)
       N = math.pow(sm_a, 2.0) / (sm_b * math.sqrt(1 + nu2) )
       t = math.tan(phi)
       t2 = t * t
       tmp = (t2 * t2 * t2) - math.pow(t, 6.0)
       l = lambda1 - lambda0

       l3coef = 1.0 - t2 + nu2
       l4coef = 5.0 - t2 + 9 * nu2 + 4.0 * (nu2 * nu2)
       l5coef = 5.0 - 18.0 * t2 + (t2 * t2) + 14.0 * nu2 - 58.0 * t2 * nu2
       l6coef = 61.0 - 58.0 * t2 + (t2 * t2) + 270.0 * nu2 - 330.0 * t2 * nu2
       l7coef = 61.0 - 479.0 * t2 + 179.0 * (t2 * t2) - (t2 * t2 * t2)
       l8coef = 1385.0 - 3111.0 * t2 + 543.0 * (t2 * t2) - (t2 * t2 * t2)

       Easting = N * math.cos(phi) * l + (N / 6.0 * math.pow(math.cos(phi), 3.0) * l3coef * math.pow(l, 3.0)) +(N / 120.0 * math.pow(math.cos(phi), 5.0) * l5coef * math.pow (l, 5.0)) + (N / 5040.0 * math.pow(math.cos(phi), 7.0) * l7coef * math.pow(l, 7.0))

       Northing = ArcLengthOfMeridian (phi) + (t / 2.0 * N * math.pow(math.cos(phi), 2.0) * math.pow(l, 2.0)) + (t / 24.0 * N * math.pow(math.cos(phi), 4.0) * l4coef * math.pow(l, 4.0)) + (t / 720.0 * N * math.pow(math.cos(phi), 6.0) * l6coef * math.pow(l, 6.0)) + (t / 40320.0 * N * math.pow(math.cos(phi), 8.0) * l8coef * math.pow(l, 8.0))

       return [Easting, Northing]


'''
   /*
   * MapXYToLatLon
   *
   * Converts x and y coordinates in the Transverse Mercator projection to
   * a latitude/longitude pair.  Note that Transverse Mercator is not
   * the same as UTM; a scale factor is required to convert between them.
   *
   * Reference: Hoffmann-Wellenhof, B., Lichtenegger, H., and Collins, J.,
   *   GPS: Theory and Practice, 3rd ed.  New York: Springer-Verlag Wien, 1994.
   *
   * Inputs:
   *   x - The easting of the point, in meters.
   *   y - The northing of the point, in meters.
   *   lambda0 - Longitude of the central meridian to be used, in radians.
   *
   * returns:
   *   philambda - A 2-element containing the latitude and longitude
   *               in radians.
   * Remarks:
   *   The local variables Nf, nuf2, tf, and tf2 serve the same purpose as
   *   N, nu2, t, and t2 in MapLatLonToXY, but they are computed with respect
   *   to the footpoint latitude phif.
   *
   *   x1frac, x2frac, x2poly, x3poly, etc. are to enhance readability and
   *   to optimize computations.
   *
   */
'''
def MapXYToLatLon(x, y, lambda0):
    phif = FootpointLatitude (y)
    ep2 = (math.pow(sm_a, 2.0) - math.pow(sm_b, 2.0)) / math.pow(sm_b, 2.0)
    cf = math.cos(phif)
    nuf2 = ep2 * math.pow(cf, 2.0)
    Nf = math.pow(sm_a, 2.0) / (sm_b * math.sqrt (1 + nuf2))
    Nfpow = Nf
    tf = math.tan(phif)
    tf2 = tf * tf
    tf4 = tf2 * tf2
    x1frac = 1.0 / (Nfpow * cf)
    Nfpow *= Nf
    x2frac = tf / (2.0 * Nfpow)
    Nfpow *= Nf
    x3frac = 1.0 / (6.0 * Nfpow * cf)
    Nfpow *= Nf
    x4frac = tf / (24.0 * Nfpow)
    Nfpow *= Nf
    x5frac = 1.0 / (120.0 * Nfpow * cf)
    Nfpow *= Nf
    x6frac = tf / (720.0 * Nfpow)
    Nfpow *= Nf
    x7frac = 1.0 / (5040.0 * Nfpow * cf)
    Nfpow *= Nf
    x8frac = tf / (40320.0 * Nfpow)

    x2poly = -1.0 - nuf2
    x3poly = -1.0 - 2 * tf2 - nuf2
    x4poly = 5.0 + 3.0 * tf2 + 6.0 * nuf2 - 6.0 * tf2 * nuf2 - 3.0 * (nuf2 *nuf2) - 9.0 * tf2 * (nuf2 * nuf2)
    x5poly = 5.0 + 28.0 * tf2 + 24.0 * tf4 + 6.0 * nuf2 + 8.0 * tf2 * nuf2
    x6poly = -61.0 - 90.0 * tf2 - 45.0 * tf4 - 107.0 * nuf2 + 162.0 * tf2 * nuf2
    x7poly = -61.0 - 662.0 * tf2 - 1320.0 * tf4 - 720.0 * (tf4 * tf2)
    x8poly = 1385.0 + 3633.0 * tf2 + 4095.0 * tf4 + 1575 * (tf4 * tf2)

    latitude = phif + x2frac * x2poly * (x * x) + x4frac * x4poly * math.pow(x, 4.0) + x6frac * x6poly * math.pow(x, 6.0) + x8frac * x8poly * math.pow(x, 8.0)
    longitude = lambda0 + x1frac * x + x3frac * x3poly * math.pow(x, 3.0) + x5frac * x5poly * math.pow(x, 5.0) + x7frac * x7poly * math.pow(x, 7.0)

    return [latitude, longitude]

'''
/*
* LatLonToUTMXY
*
* Converts a latitude/longitude pair to x and y coordinates in the
* Universal Transverse Mercator projection.
*
* Inputs:
*   lat - Latitude of the point, in radians.
*   lon - Longitude of the point, in radians.
*   zone - UTM zone to be used for calculating values for x and y.
*          If zone is less than 1 or greater than 60, the routine
*          will determine the appropriate zone from the value of lon.
*
* Outputs:
*   xy - A 2-element array where the UTM x and y values will be stored.
*
* Returns:
*   The UTM zone used for calculating the values of x and y.
*
*/
'''
def LatLonToUTMXY(lat, lon):
    zone = math.floor((lon + 180.0) / 6) + 1
    x,y = MapLatLonToXY ( DegToRad(lat), DegToRad(lon), UTMCentralMeridian (zone))

    x = x * UTMScaleFactor + 500000.0
    y = y * UTMScaleFactor
    if y < 0.0:
        y += 10000000.0

    return x,y,zone


'''
/*
* UTMXYToLatLon
*
* Converts x and y coordinates in the Universal Transverse Mercator
* projection to a latitude/longitude pair.
*
* Inputs:
*   x - The easting of the point, in meters.
*   y - The northing of the point, in meters.
*   zone - The UTM zone in which the point lies.
*   southhemi - True if the point is in the southern hemisphere;
*               false otherwise.
*
* Outputs:
*   latlon - A 2-element array containing the latitude and
*            longitude of the point, in radians.
*
* Returns:
*   The function does not return a value.
*
*/
'''
def UTMXYToLatLon (x, y, zone, southhemi=False):
    x -= 500000.0
    x = x/UTMScaleFactor

    if (southhemi):
        y -= 10000000.0

    y = y / UTMScaleFactor

    cmeridian = UTMCentralMeridian(zone)
    lat, lon = MapXYToLatLon (x, y, cmeridian)
    return [RadToDeg(lat), RadToDeg(lon)]

#==============================================================

def Form2Dict(F): # Where F is a passed dictionary
    D = {}
    #F = cgi.FieldStorage()
    print(F.keys())
    for k in F.keys():
        try:
            v = int( F[k] )
        except:
            try:
                v = float( F[k]) 
            except:
                v = str( F[k] )
        D[k] = v
        print("last tried : " + D[k])
    return D

SmokeColor = '1caaaaaa'
ContoursToDraw = {39:('Moderate','ff00ffff',SmokeColor),
    89:('Unhealthy for Sensitive Groups','ff007eff',SmokeColor),
    139:('Unhealthy','ff0000ff',SmokeColor),
    352:('Very Unhealthy','ff4c0099', SmokeColor),
    527:('Hazardous','ff23007e',SmokeColor)}

class KML_File:
    "For creating KML files used for Google Earth"
    def __init__(self, filename='test.kml'):
        self.content = '''<kml xmlns=\"http://earth.google.com/kml/2.0\">
        <Document>
    <Style>
        <ListStyle>
            <listItemType>radioFolder</listItemType>
            <bgColor>00ffffff</bgColor>
        </ListStyle>
    </Style>
        '''
        self.name = filename

    def write(self):
        output=open(self.name, 'w')
        output.write(self.content)
        output.close()
    def AddStyle( self, name, LineColor='ffffffff', FillColor='ffffffff', width=2, outline=1, fill=0):
        self.content= self.content+'''<Style id="%s">
  <LineStyle>
    <color>%s</color>
    <width>%d</width>
  </LineStyle>
  <PolyStyle>
    <color>%s</color>
    <fill>%d</fill>
    <outline>%d</outline>
  </PolyStyle>
</Style>
''' %(name, LineColor, width, FillColor, fill, outline)

    def close(self):
        self.content = self.content + "</Document>\n</kml>"

    def open_folder(self, name, Open=True):
        if Open:
            self.content = self.content + "<Folder>\n<name>" + name + "</name>\n"
        else:
            self.content = self.content + '''<Folder>\n<name>%s</name>
        <Style>
            <ListStyle>
                <listItemType>checkHideChildren</listItemType>
                <bgColor>00ffffff</bgColor>
            </ListStyle>
        </Style>\n''' % name

    def close_folder(self):
        self.content = self.content + "</Folder>\n"

    def add_placemarker(self, pts, description = " ", name = " ", TurnOn=0):
        self.content = self.content +  '''<Placemark>
<description>%s</description>
<name>%s</name>
<visibility>%d</visibility><styleUrl>#%s</styleUrl>\n''' % (description, name, TurnOn, name.replace(' ',''))
        self.content = self.content + '<Polygon>\n<tessellate>1</tessellate>\n<altitudeMode>clampToGround</altitudeMode>\n<outerBoundaryIs>\n<LinearRing><coordinates>\n'
        try:
            pts.append(pts[0])
        except:
            pass
        for p in pts:
            self.content = self.content +  "%s,%s\n" % (str(p[0]),str(p[1]))
        self.content = self.content +  "</coordinates></LinearRing>\n</outerBoundaryIs>\n</Polygon>\n"
        self.content = self.content +  "</Placemark>\n"


#**********************************************************************
#**********************************************************************
#**********************************************************************

#D = Form2Dict()
# print(D)

# Sample data
#D = {'lat': 30.767735, 'lon': -97.876783, 'acres': 1, 'erate': 1.19, 'hrate': 1.77, 'mix': 2000, 'wspd': 15, 'wdir': 180, 'stclass': 1, 'frise': -0.50, 'name': '9B5927CEC83EE94F602974CA14A6FFD0569B777A'}

# Dictionary is now created extraneously and passed by generateSmokePath() in events.py
with open(outputpath + "/smokeinput.json") as jsonfile:
    D = json.load(jsonfile)

x,y,zone = LatLonToUTMXY( D['lat'], D['lon'] )

PRise = 'T'
Acres = D['acres']
ERate = D['erate'] # g/s
HRate = D['hrate'] # MW
RiseFraction = D['frise']
DayNight = 'T'
StabClass = D['stclass']  # 1-7
MixHeight = D['mix'] * 0.3048 # meters
TWindSpd = D['wspd'] * 0.44704 # m/s
TWindDir = D['wdir'] # Degrees
sigmax = 5.01
sigmay = 5.01
BckPM = 5 #D['bpm'] #5.0 # micrograms per cubic meter
UTME = x
UTMN = y
XBGN = 0
XEND = 50
XNTVL = 0.025 #10
ISOLevels = [39., 89., 139., 352., 527.]
NISO = len(ISOLevels)

name = D['name']

#write vsmoke input file
inputfile = open(vsmokepath+'/vsmkgs.ipt','w')
inputfile.write('webvsmoke\n')
inputfile.write('%s %6.1f %6.1f %6.1f %3.2f\n' %(PRise, Acres, ERate, HRate, RiseFraction))
inputfile.write('%s %d %5.1f %3.1f %4.1f %3.2f %3.2f %3.1f\n' %(DayNight, StabClass, MixHeight, TWindSpd, TWindDir, sigmax, sigmay, BckPM))
inputfile.write('%d %d %d %f %f %d\n'%(UTME,UTMN,XBGN,XEND,XNTVL,NISO))
for l in ISOLevels:
    inputfile.write('%4.1f %4.1f\n' %(l, 0.1) )
inputfile.close()

# Reminder that VSMOKE is WINDOWS-ONLY. We will have to use Wine to interface with it.    
import sys

# WINDOWS CALL
#subprocess.call("start VSMKARC.EXE", shell=True)

# LINUX (Wine) CALL
#subprocess.call("wine VSMKARC.EXE", shell=True)

try:
    result = subprocess.check_output(["wine", "VSMKARC.EXE"], shell=True) # Tack on cwd=outputpath if not working
    print(result)
except subprocess.CalledProcessError as ex:
    print ("Error Opening VSmoke:", ex.output)

potentialNew = False
#read output
f = open(vsmokepath+'/VSMKGS.OUT','r')
ds = f.readlines()
iso = []
for d in ds[35:-1]:                      # Start at line 35. I'm really unsure of all extraneous info.
    q = d.strip().split(' ')
    while q.__contains__(''):
        q.remove('')
    try:
        q.remove('*')
    except:
        pass
    try:
        while q.__contains__('-'):
            q.remove('-')
    except:
        pass
    if len(q)>2:

        # quick fix
        for i in range(5):                  # Always says "BEGIN NORTH, EAST DATA FOR" See exampleUNCUT.OUT
            q.pop(0)
        q.pop(2)   # remove the = sign
        #           q[0] is now CHIISO(
        #           q[1] is number corresponding, i.e., 1,2,3..
        q[1] = q[1][:-1] # Must cut off the enclosing )
        #           q[2] is ISOLEVEL, i.e., 39, 89, ...
        if(potentialNew):
            iso.append( [( float ( q[1].strip("\"") ), float ( q[2].strip("\"") ) )] )
    elif len(q)==2:
        potentialNew = False
        iso[-1].append( ( float ( q[0].strip("\"") ), float ( q[1].strip("\"") ) ) )
    else:
        #try:
            #iso[-1].append( iso[-1][0] )
        #except:
            #pass
        potentialNew = True
        pass
isopleths = {}
from itertools import zip_longest

for i,l in zip_longest(iso, ISOLevels):
    Pts = []
    for pt in i:
        lat,lon  = UTMXYToLatLon(pt[0], pt[1], zone)
        Pts.append( (lon,lat) )
    if(l is not None):
        isopleths[str(int(l))] = Pts
#


#write kml file
tstamp = int( time.time()*10. )
filelist = glob.glob( outputpath+'/*.kml')
for f in filelist:
    try:
        ft = int(f.split('/')[-1].split('.')[0] )
    except:
        pass
    else:
        if ft< tstamp-3600:
            #x=commands.getoutput('/bin/rm '+f)
            x=subprocess.check_output(["/bin/rm ", f])

#mykml = KML_File( outputpath+'/%d.kml' %tstamp )
import os

# Use to remove any potential KML files
#os.remove(outputpath + "/" + name + ".kml")

mykml = KML_File( outputpath+'/' + name + ".kml" )

# create styles
for k,v in ContoursToDraw.items():
    mykml.AddStyle( v[0].replace(' ',''), LineColor=v[1], FillColor=v[2])

mykml.open_folder( 'Potential Health Impacts', Open=True )
for c in ISOLevels:
    Name = str( int(c) )
    mykml.add_placemarker( isopleths[Name][1:-1], name=ContoursToDraw[int(c)][0], TurnOn=1 )
mykml.close_folder()
mykml.close()
mykml.write()

print ('Content-type: text/html \n')
#print ('"/kml/%d.kml"' % (tstamp))
print (outputpath + "/" + name + ".kml" )


