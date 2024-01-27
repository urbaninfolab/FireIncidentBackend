import re
import shutil
from time import sleep
import pandas as pd
import json
import sys
import requests
import xmltodict
from datetime import date, datetime
from datetime import timedelta
import numpy
import requests
import os
import uuid
import urllib.parse
from urllib.parse import urlencode, urljoin, urlparse,  quote_plus
import xmltojson
import math
import subprocess
from bs4 import BeautifulSoup
from urllib.request import urlopen
from shapely.geometry import shape, GeometryCollection, Point
import geopandas as gpd

import ssl
ssl._create_default_https_context = ssl._create_unverified_context


def csvToJSON(csv_url, file_name):
    data = pd.read_csv(csv_url)
    result = data.to_json(orient="records")
    parsed = json.loads(result)
    formatted_result = json.dumps(parsed, indent=4)

    json_file = open(file_name, "w")
    json_file.write(formatted_result)
    json_file.close()

def getWeatherAPI(url):
    
    response = requests.get(url, timeout=20)
    print(url)
    retries = 0
    while(response.status_code != 200 and retries < 5):
        # Strange weather.gov error, where .gov hasn't constructed the hourly data yet.
        print("Error: " + str(response.status_code))
        sleep(3)
        response = requests.get(url)
        retries += 1
    api = response.json()
    hourlyApiUrl = api['properties']['forecastHourly']
    response =  requests.get(hourlyApiUrl + "/", timeout=20)

    retries = 0
    while(response.status_code != 200 and retries < 5):
        # Strange weather.gov error, where .gov hasn't constructed the hourly data yet.
        print("Error: " + str(response.status_code))
        sleep(3)
        response =  requests.get(hourlyApiUrl + "/", timeout=20)
        retries += 1
    hourlyData = response.json()
    print(response.status_code)
    hourlyData1 = hourlyData['properties']['periods'][0]

    return hourlyData1



# Converts other city formats into the Austin Format
# Just pass the proper variables
def dataConverter(cityName,listOfFires,keyOfTitle,keyOfAddress,customCoordinateConversion=None):

    cityacronynm = ''.join([c for c in cityName if c.isupper()])
    
    # Make an Austin-format dictionary
    dict = {}
    dict["rss"] = {}
    dict["rss"]["channel"] = {}
    dict["rss"]["channel"]["item"] = []

    # For every element in their list, get the proper data
    for fire in listOfFires:
        currentdict = {}
        currentdict["title"] = fire[keyOfTitle]
        
        # If a Fire Department provides accurate GIS, use it
        if(customCoordinateConversion != None):
            currentdict["link"] = customCoordinateConversion(fire, currentdict)
        # Otherwise, we need to geolocate the coordinates on our own
        else: 
            print("Use OpenStreetMaps")

        # Plug in the rest of the data
        currentdict["guid"] = {}
        currentdict["guid"]["@isPermaLink"] = "false"
        
        # Add unique GUID dependent on coords
        longNLatString = currentdict["link"].replace('http://maps.google.com/maps?q=', '')
        currentdict["guid"]["#text"] = longNLatString  #  uuid.uuid4().hex

        # Get time. If time not given, generate time.
        time = ""
        if("Time" in fire):
            time = fire["Time"]
        else:
            # Get current time of Central Time Zone (Chicago)
            time = (datetime.utcnow() - timedelta(hours=5)).strftime('%H:%M:%S')

        # Future- check if time given, update time.
        currentdict["description"] = fire[keyOfAddress] + " | " + cityacronynm + "FD" + " | " + time

        # date in the format of DAY, DD MONTH YYYY HH:MM:SS CDT
        currentdict["pubDate"] = (datetime.utcnow() - timedelta(hours=5)).strftime('%a, %d %b %Y ')
        currentdict["pubDate"] += time + ' CDT'
        #currentdict["pubDate"] = str(date.today())     


        dict["rss"]["channel"]["item"].append(currentdict)


    # Delete duplicate fire entries if given (thank you Dallas.)
    new_d = []
    guidList = []
    for x in dict["rss"]["channel"]["item"]:
        if x["guid"]["#text"] not in guidList:
            new_d.append(x)
            guidList.append(x["guid"]["#text"])

    dict["rss"]["channel"]["item"] = new_d

    # Write data to a file for the city
    today = date.today()
    filename = str(today) + "-FireMap" + cityName + ".json"



    checkDuplicates(dict,filename)


# A nuclear option to download a webpage as JSON, just in case database access is not provided.
def convertHTMLtoJSON(url):

    # Headers to mimic the browser
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 \
        (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'
    }
    
    # Get the page through get() method
    html_response = requests.get(url=url, headers = headers, timeout=20)
    
    # Convert HTML to JSON
    html = html_response.text
    
    #soup = BeautifulSoup(html_response.text,'lxml')
    #print(soup)
    #table = soup.find(lambda tag: tag.name=='table' and tag.has_attr('class') and tag['class']=="infoTable") 
    #table = soup.find(attrs={"class" : "infoTable"})
    #rows = table.findAll(lambda tag: tag.name=='tr')

    #print(rows)
    #print(html)
    #import xml.etree.ElementTree as ET
    #xmlstr = ET.tostring(html, encoding='utf-8', method='xml')

    #html = html.replace('<!DOCTYPE HTML PUBLIC \"-\/\/W3C\/\/DTD HTML 4.01 Transitional\/\/EN\">\r\n<html>\r\n<head>\r\n<title>City of El Paso Traffic Incidents &amp; Alerts<\/title>\r\n<meta http-equiv=\"Content-Type\" content=\"text\/html; charset=iso-8859-1\">\r\n<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\r\n<link rel=\"stylesheet\" type=\"text\/css\" href=\"style.css\">\r\n<\/head>', '')
    #html = "<html> <body>" + html
    json_ = xmltojson.parse(html)

    json_data = json.loads(json_)

    return json_data


# Checks for duplicate fire points to deactivate or add new fires

# Keep in mind that different Fire Departments may deactivate in different ways,
# putting a "time ended", putting the entry in a different color, or deleting it.

def checkDuplicates(data_dict,filename):
    # generate the object using json.dumps()
    # corresponding to json data
    json_data = json.dumps(data_dict)
    json_data = json.loads(json_data)

    # Edge case- if the file doesnt exist yet, create an empty one
    if not os.path.exists(filename):
        with open(filename, 'w') as f:
            emptydict = {}
            emptydict['rss'] = {}
            emptydict['rss']['channel'] = {} 
            emptydict['rss']['channel']['item'] = []
            json.dump(emptydict, f)
            
    try:
        cityName = filename.split("-FireMap")[1].split(".json")[0]

        date = filename.split("-")[0:3]
        date = [x for x in date]
        directory = "../fire/api/v1/" + ("Austin" if cityName == "" else cityName) + "/" + str(date[0]) + "/" + str(date[1]) + "/" + str(date[2])
        if not os.path.exists(directory):
            os.makedirs(directory)
        shutil.copy(filename, directory + "/FireMap.json")
    except:
        print("Error copying file")

    # check if we have new data point
    if 'item' in json_data['rss']['channel']:
        # check if the new data point is duplicate
        try:
            with open(filename, 'r') as json_file:
                # print(json_data['rss']['channel'])
                new_data = json_data['rss']['channel']['item']
                # check if new data is array or json object
                if(not isinstance(new_data, list)):
                    new_data = [new_data]
                existing_data = json.load(json_file)
                existing_data = existing_data['rss']['channel']['item']
                # check if existing data is array or json object
                if(not isinstance(existing_data, list)):
                    existing_data = [existing_data]
                # update status of existing dp in database
                for index, dp_exist in enumerate(existing_data):
                    guid_text_exist = dp_exist['guid']['#text']
                    # loop through new dp
                    for dp in new_data:
                        guid_text = dp['guid']['#text']
                        # check if unique id exist in database
                        if guid_text_exist == guid_text:
                            # update active status
                            dp_exist['active_status'] = "yes"
                            # create smoke path for active fire
                            print(dp_exist["link"])
                            try:
                                generateSmokePath(dp_exist,guid_text)
                            except Exception as e:
                                print("Error generating smoke path:" + str(e))
                            break
                        else:
                            dp_exist['active_status'] = "no"

                # add new dp
                for dp in new_data:
                    guid_text = dp['guid']['#text']
                    append_flag = True
                    for index, dp_exist in enumerate(existing_data):
                        guid_text_exist = dp_exist['guid']['#text']
                        if guid_text_exist == guid_text:
                            append_flag = False
                            break
                    # add new dp to list
                    if append_flag:
                        dp['active_status'] = "yes"
                        existing_data.append(dp)
                        # create smoke path for active fire
                        try:
                            generateSmokePath(dp,guid_text)
                        except Exception as e:
                            print("Error generating smoke path:" + str(e))
                json_data['rss']['channel']['item'] = existing_data
        except Exception as e:
            print('has error when open json')
            print(e)
            print("Error on line {}".format(sys.exc_info()[-1].tb_lineno))
            pass

        # print(json_data)

        # Write the json data to output
        # json file
        with open(filename, "w") as json_file:
            json_data = json.dumps(json_data)
            json_file.write(json_data)
            json_file.close()
        try:
            shutil.copy(filename, directory + "/FireMap.json")
        except:
            print("Error copying file")


        


windDirections = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
angles = [0, 25, 45, 65, 90, 115, 135, 155, 180, 205, 225, 245, 270, 295, 315, 335]

def generateSmokePathOld(dp, guid_text):
    # TODO- Standardize values for different types of fires
    # Also, should regenerate smoke map for long-lasting fire? Larger smoke trail? Wind direction?
    D = {}
    link = dp['link']
    longNLatString = link.replace('http://maps.google.com/maps?q=', '')
    longNLatArray = longNLatString.split(',')
    for x in longNLatArray:
        x = float(x)
    D["lat"] = float(longNLatArray[0]);       # Longitude
    D["lon"] = float(longNLatArray[1]);       # Latitude
    D["acres"] =            1;       # Acres
    D["erate"] = 2.39       # Emission Rate
    D["hrate"] = 2.59       # Heat Release Rate
    D["mix"] =     2000; # Mixing Height
    # Need to make a call to Weather Data API to get wind speed, direction here.
    hourlyData1 = getWeatherAPI('https://api.weather.gov/points/' + longNLatString)
    D["wspd"] = int(hourlyData1['windSpeed'].split(' ')[0])       # Wind Speed
    index = windDirections.index(hourlyData1['windDirection'])
    angle = angles[index]
    D["wdir"] =       angle; # Wind Direction
    D["stclass"] =      1; # Duration 
    D["frise"] =    -0.50; # Plume Rise Fraction
    D["name"] =     guid_text; # File name refers to unique GUID of each fire.
    data_str = json.dumps(D)
    with open('smokeinput.json', 'w', encoding="utf8") as f:
        f.write(data_str)

    subprocess.call("python3 runvsmoke.py", shell=True)

    #exec(open("./runvsmoke.py").read()) # Runs VSmoke for one hour forecast dict

    # Emission Rate is calculated by Fuel Moisture, % consumed, and the emission factor.
    # I've used the default values and calculated the respective rates for 1, 2, and 3 hours.
    # Default: Fuel Moisture: Dry, % Consumed: 70, PM 2.5 Emission Factor: 27
    # 
    # function updateEmissions() {
    #   var area = parseFloat(document.getElementById("acres").value);
    #   var duration = parseFloat(document.getElementById("duration").value);
    #   var tf = parseFloat(document.getElementById("load").value);
    #   var pc = parseFloat(document.getElementById("consumed").value);
    #   var ef = parseFloat(document.getElementById("factor").value);
    #   var er = area *tf*(pc/100.0)*ef/duration/7.92;
    #   var te = (area *tf*(pc/100.0)*ef/2.2)*1.e9;
    #   document.getElementById("erate").value = er;
    #   document.getElementById("hrate").value = 29.302*area *tf*(pc/100.0)/duration/7.92;
    #   document.getElementById("totale").value = te.toPrecision(4);
    # }
    # 
    #  

    D["name"] =     guid_text + "2"; # File name refers to unique GUID of each fire.
    D["erate"] =   1.19;             
    D["hrate"] =    1.77; 
    data_str = json.dumps(D)
    with open('smokeinput.json', 'w', encoding="utf8") as f:
        f.write(data_str)
    subprocess.call("python3 runvsmoke.py", shell=True)

    #exec(open("./runvsmoke.py").read()) # Runs VSmoke for two hour forecast

    D["name"] =     guid_text + "3"; # File name refers to unique GUID of each fire.
    D["erate"] = 0.80
    D["hrate"] = 0.86
    data_str = json.dumps(D)
    with open('smokeinput.json', 'w', encoding="utf8") as f:
        f.write(data_str)
    subprocess.call("python3 runvsmoke.py", shell=True)

    #exec(open("./runvsmoke.py").read()) # Runs VSmoke for three hour forecast
    
def generateSmokePath(dp, guid_text):

    #http://weather.gfc.state.ga.us/googlevsmoke/cgi-bin/runvsmoke.py?lat=32.58581561097687&lon=-83.64056152343748&acres=1&erate=1.19&hrate=1.77&mix=2000&wspd=10&wdir=0.1&stclass=2&frise=-0.50
    D = {}
    link = dp['link']
    longNLatString = link.replace('http://maps.google.com/maps?q=', '')
    longNLatArray = longNLatString.split(',')
    for x in longNLatArray:
        x = float(x)
    D["lat"] = float(longNLatArray[0])       # Longitude
    D["lon"] = float(longNLatArray[1])       # Latitude
    D["acres"] =            1       # Acres
    D["erate"] = 2.39       # Emission Rate
    D["hrate"] = 2.59       # Heat Release Rate
    D["mix"] =     2000 # Mixing Height
    # Need to make a call to Weather Data API to get wind speed, direction here.
    hourlyData1 = getWeatherAPI('https://api.weather.gov/points/' + longNLatString)
    D["wspd"] = int(hourlyData1['windSpeed'].split(' ')[0])       # Wind Speed
    index = windDirections.index(hourlyData1['windDirection'])
    angle = angles[index]
    D["wdir"] =       angle # Wind Direction
    D["stclass"] =      1 # Duration 
    D["frise"] =    -0.50 # Plume Rise Fraction

    #print("Failed on one")

    # 0.5 hours
    # 4.7727272727272725
    # 5.179646464646464

    D["erate"] =  4.7727272727272725         
    D["hrate"] =  5.179646464646464

    dictToURL(D, "", longNLatString)
 
    #print("Failed on two")

    # 1.5 hours
    #http://weather.gfc.state.ga.us/googlevsmoke/cgi-bin/runvsmoke.py?lat=32.58581561097687&lon=-83.64056152343748&acres=1&erate=1.5909090909090908&hrate=1.7265488215488214&mix=2000&wspd=10&wdir=0.1&stclass=2&frise=-0.50

    # 1.5909090909090908
    # 1.7265488215488214

    D["erate"] =   1.5909090909090908         
    D["hrate"] =   1.7265488215488214

    dictToURL(D, 2, longNLatString)

    #print("Failed on three")

    # 2.5 hours
    # http://weather.gfc.state.ga.us/googlevsmoke/cgi-bin/runvsmoke.py?lat=32.58581561097687&lon=-83.64056152343748&acres=1&erate=0.9545454545454545&hrate=1.0359292929292927&mix=2000&wspd=10&wdir=0.1&stclass=2&frise=-0.50

# http://weather.gfc.state.ga.us/googlevsmoke/cgi-bin/runvsmoke.py?lat=32.58581561097687&lon=-83.64056152343748&acres=1&erate=1.0375494071146245&hrate=1.126010101010101&mix=2000&wspd=10&wdir=0.1&stclass=2&frise=-0.50

    # 0.9545454545454545
    # 1.0359292929292927

    D["erate"] = 1.5375494071146245
    D["hrate"] = 1.0359292929292927

    dictToURL(D, 3, longNLatString)



def dictToURL(D, num, longNLatString):
    queryURL = "https://weather.gfc.state.ga.us/googlevsmoke/cgi-bin/runvsmoke.py?"
    queryURL += "lat=" + str(D["lat"])
    queryURL += "&lon=" + str(D["lon"])
    queryURL += "&acres=" + str(D["acres"])
    queryURL += "&erate=" + str(D["erate"])
    queryURL += "&hrate=" + str(D["hrate"])
    queryURL += "&mix=" + str(D["mix"])
    queryURL += "&wspd=" + str(D["wspd"])
    queryURL += "&wdir=" + str(D["wdir"])
    queryURL += "&stclass=" + str(D["stclass"])
    queryURL += "&frise=" + str(D["frise"])
    response = requests.get(queryURL, timeout=20)
    text = response.text.replace('"', '')
    text = text[0:text.rfind("kml")+3]
    url = "https://weather.gfc.state.ga.us" + text
    response = requests.get(url, timeout=20)
    with open(longNLatString + ".kml" + str(num),'wb') as output_file:
        output_file.write(response.content)



typename = sys.argv[1]
if typename == "events":
    events_csv_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRYFcMiNeH5BnTdJkkR-o0Yq4inRWN4bbwain2o0Zv3RWn5LiIOiTevxTlVQOn5K7GNzzaU7qLK--Ai/pub?output=csv"
    csvToJSON(events_csv_url, "events.json")
elif typename == "projects":
    project_csv_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSHTkqHi3_lXKhsMNwcnNmxvgEjPXAJf0yPRoq7IprnHY1o1_8pSfvJpgbiTDnOGvFdccezwxkkOZzn/pub?output=csv"
    csvToJSON(project_csv_url, "projects.json")
elif typename == "researchGroups":
    research_group_csv_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQAfLyT5YB_cXD5dhHOSwxNp_O6D4xFXBTSJb0r1VT002bkdTvU43SkebVgtOrQ2XGXJ0ws4IpatfJJ/pub?output=csv"
    csvToJSON(research_group_csv_url, "researchGroups.json")
elif typename == "people":
    research_group_csv_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS-J4Szapnw_e5VuZlxedLNUr0UypBQ5NWs50V-8SkC1uQuf8CYWYBVEYMceRygs6_611aldtJXHLBo/pub?output=csv"
    csvToJSON(research_group_csv_url, "people.json")
elif typename == "notification":
    notification_csv_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSHNTsjEaYkySRiIPL5LVZdxbYSPk679Jl0_ERphQVrW_Gub1YRkzbfy5JVzUQ054TCzB3vGrUdnNIV/pub?output=csv"
    csvToJSON(notification_csv_url, "notification.json")
elif typename == "fireRisk":
    # Average and keep fire risk data

    df = gpd.read_file('firerisk.shp.zip')

    cities = {
        '' : '48453',  # Austin
        'Dallas' : '48113',
        'Houston' : '48201',
        'SanAntonio' : '48311',
        'SanDiego' : '48405',
        'Seattle' : '98101',
        'ElPaso' : '48503',   
    }

    averageFires = {}

    for city in cities:

        dict = []
        fires = 0
        fireAverage = 0

        try:

            # Read in all the fire coordinates of today
            today = date.today()
            filename = str(today) + "-FireMap" + city + ".json"
            with open(filename, 'r') as json_file:
                all_data = json.load(json_file)
                existing_data = all_data['rss']['channel']['item']
                for index, dp_exist in enumerate(existing_data):
                    coordinates = all_data['rss']['channel']['item'][index]['link'].replace("http://maps.google.com/maps?q=","").split(',')
                    coords = [float(coordinates[0]), float(coordinates[1])]
                    dict.append(coords) 
            
            # Determine fire coordinate tract and add
            dd = df.loc[df.ctid.str.startswith(cities[city], na=False)]

            #Coordinates are backwards
            for point in dict:
                point = Point(point[1], point[0])
                for index, poi in dd.iterrows():
                    polygon = df.iloc[[index]]['geometry']
                    if polygon.contains(point).bool():
                        df.at[index,'numFires'] += 1
                        fires += 1
                        print(str(fires) + " / " + str(len(dict)) + " fires in " + city)
            
            fireAverage = dd['numFires'].mean()
            print("Average fire count in " + city + ": " + str(fireAverage))

            averageFires[city] = fireAverage

        except Exception as e: 
            print(e)
            print("File not found")
            continue

    df.to_file(filename='firerisk.shp.zip', driver='ESRI Shapefile')

    with open('AverageFire.json', 'w') as outfile:
        json.dump(averageFires, outfile)

    print("Done")

elif typename == "fireMap":

    # API: https://www.austintexas.gov/fact/fact_rss.cfm
    # response = requests.get("https://www.austintexas.gov/fact/fact_rss.cfm", timeout=20)
    # City updated to services endpoint, without telling us..? 
    response = requests.get("https://services.austintexas.gov/fact/fact_rss.cfm", timeout=20) 
    with open('fireMap.xml', 'wb') as f:
        f.write(response.content)

    # convert xml to json
    with open("fireMap.xml") as xml_file:
        today = date.today()
        filename = str(today) + "-FireMap.json"

        data_dict = xmltodict.parse(xml_file.read())
        xml_file.close()

        # generate the object using json.dumps()
        # corresponding to json data
        json_data = json.dumps(data_dict)
        json_data = json.loads(json_data)

        # Edge case- if the file doesnt exist yet, create an empty one
        if not os.path.exists(filename):
            with open(filename, 'w') as f:
                emptydict = {}
                emptydict['rss'] = {}
                emptydict['rss']['channel'] = {} 
                emptydict['rss']['channel']['item'] = []
                json.dump(emptydict, f)

        # check if we have new data point
        if 'item' in json_data['rss']['channel']:
            # check if the new data point is duplicate
            try:
                with open(filename, 'r') as json_file:
                    # print(json_data['rss']['channel'])
                    new_data = json_data['rss']['channel']['item']
                    # check if new data is array or json object
                    if(not isinstance(new_data, list)):
                        new_data = [new_data]
                    existing_data = json.load(json_file)
                    existing_data = existing_data['rss']['channel']['item']
                    # check if existing data is array or json object
                    if(not isinstance(existing_data, list)):
                        existing_data = [existing_data]
                    # update status of existing dp in database
                    for index, dp_exist in enumerate(existing_data):
                        guid_text_exist = dp_exist['guid']['#text']
                        # loop through new dp
                        for dp in new_data:
                            guid_text = dp['guid']['#text']
                            # check if unique id exist in database
                            if guid_text_exist == guid_text:
                                # update active status
                                dp_exist['active_status'] = "yes"
                                # create smoke path for active fire
                                generateSmokePath(dp_exist,guid_text)
                                break
                            else:
                                dp_exist['active_status'] = "no"

                    # add new dp
                    for dp in new_data:
                        guid_text = dp['guid']['#text']
                        append_flag = True
                        for index, dp_exist in enumerate(existing_data):
                            guid_text_exist = dp_exist['guid']['#text']
                            if guid_text_exist == guid_text:
                                append_flag = False
                                break
                        # add new dp to list
                        if append_flag:
                            dp['active_status'] = "yes"
                            existing_data.append(dp)
                            # create smoke path for active fire
                            generateSmokePath(dp,guid_text)
                    json_data['rss']['channel']['item'] = existing_data
            except Exception as e:
                print('has error when open json')
                print(e)
                print("Error on line {}".format(sys.exc_info()[-1].tb_lineno))
                pass

            # print(json_data)

            # Write the json data to output
            # json file
            with open(filename, "w") as json_file:
                json_data = json.dumps(json_data)
                json_file.write(json_data)
                json_file.close()

elif typename == "fireMap_deactive":
    today = date.today()
    yesterday = today - timedelta(days=1)

    filename = str(yesterday) + "-FireMap.json"
    json_data = {}

    with open(filename, 'r') as json_file:
        all_data = json.load(json_file)
        existing_data = all_data['rss']['channel']['item']
        for index, dp_exist in enumerate(existing_data):
            all_data['rss']['channel']['item'][index]['active_status'] = "no"
            # ensure deletion of daily KML files
            path = "/var/www/html/data/" + dp_exist['guid']['#text'] + ".kml"
            if(os.path.isfile(path)):
                os.remove(path)
        json_data = all_data

    with open(filename, "w") as json_file:
        json_data = json.dumps(json_data)
        json_file.write(json_data)
        json_file.close()

elif typename == "fireMapDallas":   # DALLAS FIRE RETRIEVAL

    response = requests.get("https://vgov.dallascityhall.com/data/dfr-active-calls.txt", timeout=20)
    response.encoding = 'utf-16'

    json_data = json.loads(response.text)

    fireArray = []

    # Extract fire data for Dallas
    for item in json_data:
        if("fire" in item["CD"].lower() or "burning" in item["CD"].lower()):
            fireArray.append(item)

    # Custom Coordinates for Dallas
    def customCoordinateFunc(fire, currentdict):

        address = fire["Address"].replace(" ", "%20")
        address = address.replace("/","|")

        # Must geolocate the coordinates of the given Dallas Address using Dallas servers--  
        response = requests.get("https://egis.dallascityhall.com/arcgis/rest/services/Crm_public/CrmDallasStreetsLocator/GeocodeServer/findAddressCandidates?outFields=*&maxLocations=1&outSR=4326&searchExtent=&f=pjson&Single+Line+Input=" + address, timeout=20)
        json_data = json.loads(response.text)

        # print("https://egis.dallascityhall.com/arcgis/rest/services/Crm_public/CrmDallasStreetsLocator/GeocodeServer/findAddressCandidates?outFields=*&maxLocations=1&outSR=4326&searchExtent=&f=pjson&Single+Line+Input=" + address )

        # print(response.url)
        x = str(json_data["candidates"][0]["location"]["x"])
        y = str(json_data["candidates"][0]["location"]["y"])
        lat = x[:x.index(".")+7]
        lon = y[:y.index(".")+7]
        print("hi")

        return "http://maps.google.com/maps?q=" + lon + "," + lat

    dataConverter("Dallas",fireArray,"CD","Address", customCoordinateFunc)

elif typename == "fireMapHouston":
    response = requests.get("https://mycity2.houstontx.gov/pubgis01/rest/services/HEC/HEC_Active_Incidents/MapServer/0/query?f=json&cacheHint=true&resultOffset=0&resultRecordCount=200&where=1%3D1&orderByFields=CALL_TIME%20DESC&outFields=*&returnGeometry=false&spatialRel=esriSpatialRelIntersects", timeout=20)
    response.encoding = 'utf-8'

    json_data = json.loads(response.text)
    fireArray = []

    # Extract fire data for Houston
    for item in json_data["features"]:
        if("fire" in item["attributes"]["IncidentType"].lower() or "burning" in item["attributes"]["IncidentType"].lower()):
            fireArray.append(item["attributes"])

    # Custom Coordinates for Houston
    def customCoordinateFunc(fire, currentdict):

        # Side fix, just for Houston, address are usually given as Cross Streets
        if(fire["CrossStreet"] != ""):
            fire["IncidentType"] += " / " + fire["CrossStreet"]

        lon = str(fire["LATITUDE"])
        lat = str(fire["LONGITUDE"])

        return "http://maps.google.com/maps?q=" + lon + "," + lat

    dataConverter("Houston",fireArray,"IncidentType","Address", customCoordinateFunc)
    
elif typename == "fireMapSanAntonio":
    
    # HTML to Json, as database access is not provided
    json_data = convertHTMLtoJSON("https://webapp3.sanantonio.gov/activefire/Fire.aspx")

    json_data = json_data["html"]["body"]["form"]["table"]["tr"][3]["td"]["div"]["div"]["table"]["tr"]
    json_data.pop(0)

    fireArray = []

    for item in json_data:
        if("fire" in item["td"][2].lower() or "burning" in item["td"][2].lower()):

            time = item["td"][1]["#text"]
            type = item["td"][2]
            location = item["td"][3]["a"]["@href"]
            address = item["td"][3]["a"]["#text"]

            # Makeshift dictionary objects
            dictObj = {}
            dictObj["Address"] = address
            dictObj["Location"] = location
            dictObj["IncidentType"] = type

            fireArray.append(dictObj)

    # Custom Coordinates for San Antonio
    def customCoordinateFunc(fire, currentdict):

        lat = "0"
        lon = "0"

        try:
            # Google Maps Reverse Geolocation Code
            r = requests.get(fire["Location"], timeout=20)
            scrapestring = "<meta content=\"https://maps.google.com/maps/api/staticmap?center="
            index = r.text.index(scrapestring)
            index += len(scrapestring)
            lon = r.text[index : r.text.index(".",index) + 7]
            lat = r.text[r.text.index("%2C") + 3 : r.text.index(".",r.text.index("%2C")) + 7 ]
        except:
            try:
                # Nomatim Reverse Geolocation Code
                r = requests.get("https://nominatim.openstreetmap.org/search?q=" + fire["Address"].replace("/","&") + ",San Antonio,Texas&format=json", timeout=20)
                lon = r.json()[0]["lat"]
                lon = lon[:lon.index(".") + 7]
                lat = r.json()[0]["lon"]
                lat = lat[:lat.index(".") + 7]
            except:
                # Skip this fire, don't ruin entire file if can't be geocoded correctly.
                pass


        return "http://maps.google.com/maps?q=" + lon + "," + lat

    dataConverter("SanAntonio",fireArray,"IncidentType","Address", customCoordinateFunc)

elif typename == "fireMapElPaso":

    json_data = []

    url= 'http://legacy.elpasotexas.gov/traffic'
    openurl=urlopen(url)
    soup = BeautifulSoup(openurl.read(),features="lxml")
    for tr in soup.findAll('tr', {"class": "resultRows"}):
        array =  tr.findAll('td')
        try:
            array1 =  array[3].findAll('a')

            json_item = {}
            #json_item["Time"] =  (array[0].text)
            json_item["streetAddress"] =  (array1[0].text)
            json_item["subTypeFull"] = array[3].find(text=True, recursive=False).replace('\n','').replace('\t','').replace('\r','')
            json_item["Location"] = (array1[0].get("href"))
            json_data.append(json_item)

        except Exception as e:
            print(e) 
            pass

    fireArray = []

    # Extract fire data for ElPaso
    for item in json_data:
        if("fire" in item["subTypeFull"].lower() or "burning" in item["subTypeFull"].lower()):
            # New dict
            dictObj = {}
            dictObj["Address"] = item["streetAddress"]
            dictObj["IncidentType"] = item["subTypeFull"]
            dictObj["Location"] = item["Location"]
            fireArray.append(dictObj)

    # Custom Coordinates for San Antonio
    def customCoordinateFunc(fire, currentdict):

        lon = "0"
        lat = "0"

        try:
            # Google Maps Reverse Geolocation Code
            r = requests.get(fire["Location"], timeout=20)
            scrapestring = "<meta content=\"https://maps.google.com/maps/api/staticmap?center="
            index = r.text.index(scrapestring)
            index += len(scrapestring)
            lon = r.text[index : r.text.index(".",index) + 7]
            lat = r.text[r.text.index("%2C") + 3 : r.text.index(".",r.text.index("%2C")) + 7 ]
        except:
            try:
                # Nomatim Reverse Geolocation Code
                r = requests.get("https://nominatim.openstreetmap.org/search?q=" + fire["Address"].replace("/","&") + ",El Paso,Texas&format=json", timeout=20)
                lon = r.json()[0]["lat"]
                lon = lon[:lon.index(".") + 7]
                lat = r.json()[0]["lon"]
                lat = lat[:lat.index(".") + 7]
            except:
                # Skip this fire, don't ruin entire file if can't be geocoded correctly.
                pass


        return "http://maps.google.com/maps?q=" + lon + "," + lat


    dataConverter("ElPaso",fireArray,"IncidentType","Address", customCoordinateFunc)


elif typename == "fireMapOklahomaCity":

    url = "https://data.okc.gov/services/portal/api/map/layers/Emergency%20Responses"
    #headers = {
    #    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 15_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.4 YaBrowser/22.7.2.662 Mobile/15E148 Safari/604.1',
    #    'Accept': 'application/vnd.github.v3.text-match+json'
    #}
    # session = IncapSession()
    # response = session.get(url)  # url is not blocked by incapsula
    # #response = requests.get(url,headers=headers)
    # response.encoding = 'utf-8'

    # print(response.text)

    # json_data = json.loads(response.text)
    # fireArray = []

    # # Extract fire data for OKC
    # for item in json_data["Features"]:
    #     if("fire" in item["Attributes"][2].lower() or "burning" in item["Attributes"][2].lower()):
    #         # New dict
    #         dictObj = {}
    #         dictObj["Address"] = item["Attributes"][0]
    #         dictObj["IncidentType"] = item["Attributes"][2]
    #         dictObj["LATITUDE"] = item["Geometry"]["latitude"]
    #         dictObj["LONGITUDE"] = item["Geometry"]["longitude"]
    #         fireArray.append(dictObj)

    # # Custom Coordinates for OKC
    # def customCoordinateFunc(fire, currentdict):

    #     lon = str(fire["LATITUDE"])
    #     lat = str(fire["LONGITUDE"])

    #     return "http://maps.google.com/maps?q=" + lon + "," + lat

    # dataConverter("OklahomaCity",fireArray,"IncidentType","Address", customCoordinateFunc)

elif typename == "fireMapLosAngeles":
    
    # Download XML, conv to JSON 

    # https://www.lafd.org/alerts-rss.xml

    #response = requests.get("https://www.lafd.org/alerts-rss.xml")
    #response.encoding = 'utf-8'

    response = convertHTMLtoJSON("https://www.lafd.org/alerts-rss.xml")

    fireArray = []

    for item in response["rss"]["channel"]["item"]:
        LArray = item["description"].split(";")
        if("fire" in LArray[0].lower() or "burning" in LArray[0].lower()):
            dictObj = {}
            dictObj["Address"] = LArray[3]
            dictObj["IncidentType"] = LArray[0]
            latlng = requests.head(LArray[4].split('"')[1::2][0]).headers['location'].replace("https://www.google.com/maps/search/?api=1&query=",'')
            # if latlng contains @
            if "@" in latlng:
                latlng = latlng.split("@")[1]
            latlng = latlng.split(",")
            dictObj["LATITUDE"] = latlng[0]
            dictObj["LONGITUDE"] = latlng[1]
            fireArray.append(dictObj)
    
    # Custom Coordinates for LA
    def customCoordinateFunc(fire, currentdict):

        lon = str(fire["LATITUDE"])
        lat = str(fire["LONGITUDE"])

        return "http://maps.google.com/maps?q=" + lon + "," + lat

    dataConverter("LosAngeles",fireArray,"IncidentType","Address", customCoordinateFunc)

elif typename == "fireMapChicago":
    
    response = requests.get("https://smartcity.tacc.utexas.edu/cgi-bin/onetomany.py?nodes=3&n1=60&n1d=200&n2=30&n2d=300&n3=90&n3d=500&V=60&L=50&gap=5&rtime=360", timeout=20)
    print(response.text)
    #request = requests.get("https://data.cityofchicago.org/api/views/xzkq-xp2w/rows.json?accessType=DOWNLOAD")

    #print requests.head("http://"+i).headers['location']

elif typename == "fireMapRiverside":

    response = requests.get("https://rvcfire.org/feed/feed/incidents", timeout=20)
    response.encoding = 'utf-8'

    json_data = json.loads(response.text)
    fireArray = []

    # Extract fire data for OKC
    for item in json_data:
        if("fire" in item["subTypeFull"].lower() or "burning" in item["subTypeFull"].lower()):
            # New dict
            dictObj = {}
            dictObj["Address"] = item["streetAddress"]
            dictObj["IncidentType"] = item["subTypeFull"]
            hey = item["eventMessage"].split(",")
            dictObj["LATITUDE"] = hey[5]
            dictObj["LONGITUDE"] = hey[4]
            fireArray.append(dictObj)

    # Custom Coordinates for OKC
    def customCoordinateFunc(fire, currentdict):

        lon = str(fire["LATITUDE"])
        lat = str(fire["LONGITUDE"])

        return "http://maps.google.com/maps?q=" + lon + "," + lat

    dataConverter("Riverside",fireArray,"IncidentType","Address", customCoordinateFunc)

elif typename == "fireMapSeattle":

    #response = requests.get("https://www.sandiegofires.org/api/v1/incidents")

    #response = convertHTMLtoJSON("http://www2.seattle.gov/fire/realtime911/getRecsForDatePub.asp?action=Today&incDate=&rad1=des")

    #print(response)

    json_data = []

    url= 'http://www2.seattle.gov/fire/realtime911/getRecsForDatePub.asp?action=Today&incDate=&rad1=des'
    openurl=urlopen(url)
    soup = BeautifulSoup(openurl.read(),features="lxml")
    for tr in soup.findAll('tr', {"id": re.compile('^row')}):
        array =  tr.findAll('td')
        try:
            json_item = {}
            json_item["Time"] =  (array[0].text)
            json_item["streetAddress"] =  (array[4].text)
            json_item["subTypeFull"] = (array[5].text)
            json_data.append(json_item)
        except: 
            pass

    fireArray = []

    # Extract fire data for SanDiego
    for item in json_data:
        if("fire" in item["subTypeFull"].lower() or "burning" in item["subTypeFull"].lower()):
            # New dict
            dictObj = {}
            dictObj["Address"] = item["streetAddress"]
            dictObj["IncidentType"] = item["subTypeFull"]
            fireArray.append(dictObj)


    # Custom Coordinates for San Antonio
    def customCoordinateFunc(fire, currentdict):

        lat = "0"
        lon = "0"

        try:
            # Google Maps Reverse Geolocation Code
            r = requests.get("https://www.google.com/maps?q=" + fire["Address"] + ",Seattle,Washington", timeout=20)
            scrapestring = "<meta content=\"https://maps.google.com/maps/api/staticmap?center="
            index = r.text.index(scrapestring)
            index += len(scrapestring)
            lon = r.text[index : r.text.index(".",index) + 7]
            lat = r.text[r.text.index("%2C") + 3 : r.text.index(".",r.text.index("%2C")) + 7 ]
        except:
            try:
                # Nomatim Reverse Geolocation Code
                r = requests.get("https://nominatim.openstreetmap.org/search?q=" + fire["Address"].replace("/","&") + ",Seattle,Washington&format=json", timeout=20)
                lon = r.json()[0]["lat"]
                lon = lon[:lon.index(".") + 7]
                lat = r.json()[0]["lon"]
                lat = lat[:lat.index(".") + 7]
            except:
                # Skip this fire, don't ruin entire file if can't be geocoded correctly.
                pass


        return "http://maps.google.com/maps?q=" + lon + "," + lat


    dataConverter("SanDiego",fireArray,"IncidentType","Address", customCoordinateFunc)

elif typename == "fireMapSanDiego":

    json_data = []

    # https://webmaps.sandiego.gov/arcgis/rest/services/SDFR/FireMap_Incidents/FeatureServer/0/query?f=json&returnGeometry=true&spatialRel=esriSpatialRelIntersects&geometry=%7B%22xmin%22%3A-08041991.5141392%2C%22ymin%22%3A1845088.2708794475%2C%22xmax%22%3A-14032207.57451871%2C%22ymax%22%3A4054872.2104999367%2C%22spatialReference%22%3A%7B%22wkid%22%3A102100%7D%7D&geometryType=esriGeometryEnvelope&inSR=102100&outFields=*&outSR=102100&resultType=tile

    response = requests.get("https://webmaps.sandiego.gov/arcgis/rest/services/SDFR/FireMap_Incidents/FeatureServer/0/query?f=json&returnGeometry=true&spatialRel=esriSpatialRelIntersects&geometry=%7B%22xmin%22%3A-08041991.5141392%2C%22ymin%22%3A1845088.2708794475%2C%22xmax%22%3A-14032207.57451871%2C%22ymax%22%3A4054872.2104999367%2C%22spatialReference%22%3A%7B%22wkid%22%3A102100%7D%7D&geometryType=esriGeometryEnvelope&inSR=102100&outFields=*&outSR=102100&resultType=tile", timeout=20)
    response.encoding = 'utf-8'

    json_data = json.loads(response.text)

    fireArray = []

    # Extract fire data for San Diego
    for item in json_data["features"]:
        if("fire" in item["attributes"]["PriorityDescription"].lower() or "burning" in item["attributes"]["PriorityDescription"].lower()):
            dictObj = {}
            dictObj["Address"] = item["attributes"]["Address"]
            dictObj["IncidentType"] = item["attributes"]["PriorityDescription"]
            dictObj["LATITUDE"] = item["attributes"]["Latitude"]
            dictObj["LONGITUDE"] = item["attributes"]["Longitude"]
            fireArray.append(dictObj)

    # Custom Coordinates for San Diego
    def customCoordinateFunc(fire, currentdict):
            
            lon = str(fire["LATITUDE"])
            lat = str(fire["LONGITUDE"])
    
            return "http://maps.google.com/maps?q=" + lon + "," + lat

    dataConverter("Seattle",fireArray,"IncidentType","Address", customCoordinateFunc)

elif typename == "fireMapMiami":

    response = requests.get("https://www.miamidade.gov/firecad/calls_include.asp", timeout=20)
    response.encoding = 'utf-8'

    #print(response.text)
   
    json_data = []

    #url= 'https://www.miamidade.gov/firecad/calls_include.asp'
    #openurl=urlopen(url)
    soup = BeautifulSoup(response.text,features="lxml")

    # Find fire data for Miami
    for tr in soup.findAll('tr', {"height": "20"}):
        array =  tr.findAll('td')
        try:
            json_item = {}
            json_item["Time"] =  (array[0].text)
            json_item["streetAddress"] =  (array[3].text)
            json_item["subTypeFull"] = (array[2].text)
            json_data.append(json_item)
        except: 
            pass

    fireArray = []

    # Extract fire data for Miami
    for item in json_data:
        if("fire" in item["subTypeFull"].lower() or "burning" in item["subTypeFull"].lower()):
            # New dict
            dictObj = {}
            dictObj["Address"] = item["streetAddress"]
            dictObj["IncidentType"] = item["subTypeFull"]
            # convert time to central time
            dictObj["Time"] = (datetime.strptime(item["Time"].replace(" ",""), '%H:%M:%S') - timedelta(hours=1)).strftime('%H:%M:%S')
            #dictObj["Location"] = item["Location"]
            fireArray.append(dictObj)

    # Custom Coordinates for San Antonio
    def customCoordinateFunc(fire, currentdict):

        lat = "0"
        lon = "0"

        try:
            # Google Maps Reverse Geolocation Code
            r = requests.get("https://www.google.com/maps?q=" + fire["Address"] + ",Miami,Florida", timeout=20)
            scrapestring = "<meta content=\"https://maps.google.com/maps/api/staticmap?center="
            index = r.text.index(scrapestring)
            index += len(scrapestring)
            lon = r.text[index : r.text.index(".",index) + 7]
            lat = r.text[r.text.index("%2C") + 3 : r.text.index(".",r.text.index("%2C")) + 7 ]
        except:
            try:
                # Nomatim Reverse Geolocation Code
                r = requests.get("https://nominatim.openstreetmap.org/search?q=" + fire["Address"].replace("/","&") + ",Miami,Florida&format=json", timeout=20)
                lon = r.json()[0]["lat"]
                lon = lon[:lon.index(".") + 7]
                lat = r.json()[0]["lon"]
                lat = lat[:lat.index(".") + 7]
            except:
                # Skip this fire, don't ruin entire file if can't be geocoded correctly.
                pass


        return "http://maps.google.com/maps?q=" + lon + "," + lat


    dataConverter("Miami",fireArray,"IncidentType","Address", customCoordinateFunc)


elif typename == "fireMapOrlando":

    response = requests.get("https://www1.cityoforlando.net/opd/activecalls/activecadfire.xml", timeout=20)
    response.encoding = 'utf-8'

    #print(response.text)
   
    json_data = []

    # Extract fire data for Orlando, using XML
    soup = BeautifulSoup(response.text,features="lxml")

    for item in soup.findAll('call'):
        try: 
            json_item = {}
            time =  (item.find('date').text).split(" ")[1]
            json_item["Time"] = datetime.strptime(time, '%H:%M').strftime('%H:%M:%S')
            json_item["streetAddress"] =  (item.find('location').text)
            json_item["subTypeFull"] = (item.find('desc').text)
            json_data.append(json_item)
        except:
            pass

    fireArray = []

    # Extract fire data for Miami
    for item in json_data:
        if("fire" in item["subTypeFull"].lower() or "burning" in item["subTypeFull"].lower()):
            # New dict
            dictObj = {}
            dictObj["Address"] = item["streetAddress"]
            dictObj["IncidentType"] = item["subTypeFull"]
            # convert time to central time
            dictObj["Time"] = (datetime.strptime(item["Time"].replace(" ",""), '%H:%M:%S') - timedelta(hours=1)).strftime('%H:%M:%S')
            #dictObj["Location"] = item["Location"]
            fireArray.append(dictObj)

    # Custom Coordinates for San Antonio
    def customCoordinateFunc(fire, currentdict):

        lat = "0"
        lon = "0"

        try:
            # Google Maps Reverse Geolocation Code
            r = requests.get("https://www.google.com/maps?q=" + fire["Address"] + ",Orlando,Florida", timeout=20)
            scrapestring = "<meta content=\"https://maps.google.com/maps/api/staticmap?center="
            index = r.text.index(scrapestring)
            index += len(scrapestring)
            lon = r.text[index : r.text.index(".",index) + 7]
            lat = r.text[r.text.index("%2C") + 3 : r.text.index(".",r.text.index("%2C")) + 7 ]
        except:
            try:
                # Nomatim Reverse Geolocation Code
                r = requests.get("https://nominatim.openstreetmap.org/search?q=" + fire["Address"].replace("/","&") + ",Orlando,Florida&format=json", timeout=20)
                lon = r.json()[0]["lat"]
                lon = lon[:lon.index(".") + 7]
                lat = r.json()[0]["lon"]
                lat = lat[:lat.index(".") + 7]
            except:
                # Skip this fire, don't ruin entire file if can't be geocoded correctly.
                pass


        return "http://maps.google.com/maps?q=" + lon + "," + lat


    dataConverter("Orlando",fireArray,"IncidentType","Address", customCoordinateFunc)


elif typename == "fireMapPortland":

    response = requests.get("https://www.portlandoregon.gov/fire/apps/calls/incidents_map.cfm", timeout=20)
    response.encoding = 'utf-8'

    #print(response.text)
   
    json_data = []

    # Extract fire data for Orlando, using XML
    soup = BeautifulSoup(response.text,features="lxml")

    for item in soup.findAll('dl'):
        array = item.findAll('dd')
        try:
            json_item = {}
            time =  (array[4].text).split(" ")[1]
            json_item["Time"] = datetime.strptime(time, '%H:%M:%S').strftime('%H:%M:%S')
            json_item["streetAddress"] =  (array[2].text)
            json_item["subTypeFull"] = (array[1].text)
            json_data.append(json_item)
        except:
            pass

    fireArray = []

    # Extract fire data for Miami
    for item in json_data:
        if("fire" in item["subTypeFull"].lower() or "burning" in item["subTypeFull"].lower()):
            # New dict
            dictObj = {}
            dictObj["Address"] = item["streetAddress"]
            # get rid of last 3 characters, as Portland cities end in ",Port "
            dictObj["Address"] = item["streetAddress"][:-6]
            dictObj["IncidentType"] = item["subTypeFull"]
            # convert time to central time
            dictObj["Time"] = (datetime.strptime(item["Time"].replace(" ",""), '%H:%M:%S') + timedelta(hours=2)).strftime('%H:%M:%S')
            #dictObj["Location"] = item["Location"]
            fireArray.append(dictObj)

    # Custom Coordinates for San Antonio
    def customCoordinateFunc(fire, currentdict):

        lat = "0"
        lon = "0"

        try:    
            # Google Maps Reverse Geolocation Code
            r = requests.get("https://www.google.com/maps?q=" + fire["Address"] + ",Portland,Oregon", timeout=20)
            scrapestring = "<meta content=\"https://maps.google.com/maps/api/staticmap?center="
            index = r.text.index(scrapestring)
            index += len(scrapestring)
            lon = r.text[index : r.text.index(".",index) + 7]
            lat = r.text[r.text.index("%2C") + 3 : r.text.index(".",r.text.index("%2C")) + 7 ]
        except:
            try:
                # Nomatim Reverse Geolocation Code
                r = requests.get("https://nominatim.openstreetmap.org/search?q=" + fire["Address"].replace("/","&") + ",Portland,Oregon&format=json", timeout=20)
                lon = r.json()[0]["lat"]
                lon = lon[:lon.index(".") + 7]
                lat = r.json()[0]["lon"]
                lat = lat[:lat.index(".") + 7]
            except:
                # Skip this fire, don't ruin entire file if can't be geocoded correctly.
                pass

        return "http://maps.google.com/maps?q=" + lon + "," + lat


    dataConverter("Portland",fireArray,"IncidentType","Address", customCoordinateFunc)


elif typename == "fireMapMilwaukee":

    response = requests.get("https://itmdapps.milwaukee.gov/MFDCallData/", timeout=20)
    response.encoding = 'utf-8'

    json_data = []

    # Extract fire data for Milwaukee
    soup = BeautifulSoup(response.text,features="lxml")

    for item in soup.findAll('tr'):
        array = item.findAll('td')
        try:
            json_item = {}
            time =  (array[1].text).split(" ")[1]
            json_item["Time"] = datetime.strptime(time, '%H:%M:%S').strftime('%H:%M:%S')
            json_item["streetAddress"] =  (array[2].text)
            json_item["subTypeFull"] = (array[4].text)
            json_data.append(json_item)
        except:
            pass

    fireArray = []

    # Extract fire data for Miami
    for item in json_data:
        if("fire" in item["subTypeFull"].lower() or "burning" in item["subTypeFull"].lower()):
            # New dict
            dictObj = {}
            dictObj["Address"] = item["streetAddress"]
            dictObj["IncidentType"] = item["subTypeFull"]
            # convert time to central time
            dictObj["Time"] = (datetime.strptime(item["Time"].replace(" ",""), '%H:%M:%S') ).strftime('%H:%M:%S')
            #dictObj["Location"] = item["Location"]
            fireArray.append(dictObj)

    # Custom Coordinates for San Antonio
    def customCoordinateFunc(fire, currentdict):

        lon = "0"
        lat = "0"

        try: 
            # Google Maps Reverse Geolocation Code
            r = requests.get("https://www.google.com/maps?q=" + fire["Address"] + ",Milwaukee,Wisconsin", timeout=20)
            scrapestring = "<meta content=\"https://maps.google.com/maps/api/staticmap?center="
            index = r.text.index(scrapestring)
            index += len(scrapestring)
            lon = r.text[index : r.text.index(".",index) + 7]
            lat = r.text[r.text.index("%2C") + 3 : r.text.index(".",r.text.index("%2C")) + 7 ]
        except:
            try:
                # Nomatim Reverse Geolocation Code
                r = requests.get("https://nominatim.openstreetmap.org/search?q=" + fire["Address"].replace("/","&") + ",Milwaukee,Wisconsin&format=json", timeout=20)
                lon = r.json()[0]["lat"]
                lon = lon[:lon.index(".") + 7]
                lat = r.json()[0]["lon"]
                lat = lat[:lat.index(".") + 7]
            except:
                # Skip this fire, don't ruin entire file if can't be geocoded correctly.
                pass



        return "http://maps.google.com/maps?q=" + lon + "," + lat


    dataConverter("Milwaukee",fireArray,"IncidentType","Address", customCoordinateFunc)

elif typename == "fireMapOrangeCounty":

    response = requests.get("https://davnit.net/esmap/data/call_log.json", timeout=20)
    response.encoding = 'utf-8'

    json_data = []

    # Extract fire data for Orange County
    json_data1 = response.json()["calls"]

    for item in json_data1:
        array = json_data1[item]
        try:
            json_item = {}
            time =  (array[3]).split(" ")[1]
            json_item["Time"] = datetime.strptime(time, '%H:%M:%S').strftime('%H:%M:%S')
            json_item["streetAddress"] =  (array[2])
            json_item["subTypeFull"] = (array[1])
            json_data.append(json_item)
        except:
            pass

    #print(json_data)

    fireArray = []

    # Extract fire data for Orange County
    for item in json_data:
        if("fire" in item["subTypeFull"].lower() or "burning" in item["subTypeFull"].lower()):
            # New dict
            dictObj = {}
            dictObj["Address"] = item["streetAddress"]
            dictObj["IncidentType"] = item["subTypeFull"]
            # convert time to central time
            dictObj["Time"] = (datetime.strptime(item["Time"].replace(" ",""), '%H:%M:%S') - timedelta(hours=1)).strftime('%H:%M:%S')
            #dictObj["Location"] = item["Location"]
            fireArray.append(dictObj)

    #print(fireArray)

    def customCoordinateFunc(fire, currentdict):

        lon = "0"
        lat = "0"

        try: 
            # Google Maps Reverse Geolocation Code
            r = requests.get("https://www.google.com/maps?q=" + fire["Address"] + ",Orange County,Florida", timeout=20)
            scrapestring = "<meta content=\"https://maps.google.com/maps/api/staticmap?center="
            index = r.text.index(scrapestring)
            index += len(scrapestring)
            lon = r.text[index : r.text.index(".",index) + 7]
            lat = r.text[r.text.index("%2C") + 3 : r.text.index(".",r.text.index("%2C")) + 7 ]
        except:
            try:
                # Nomatim Reverse Geolocation Code
                r = requests.get("https://nominatim.openstreetmap.org/search?q=" + fire["Address"].replace("/","&") + ",Orange County,Florida&format=json", timeout=20)
                lon = r.json()[0]["lat"]
                lon = lon[:lon.index(".") + 7]
                lat = r.json()[0]["lon"]
                lat = lat[:lat.index(".") + 7]
            except:
                # Skip this fire, don't ruin entire file if can't be geocoded correctly.
                pass



        return "http://maps.google.com/maps?q=" + lon + "," + lat


    dataConverter("OrangeCounty",fireArray,"IncidentType","Address", customCoordinateFunc)

elif typename == "fireMapPhoenix":

    # Phoenix has misconfigured their website- can't verify SSL certificate
    response = requests.get("http://htms.phoenix.gov/publicweb/",  verify=False, timeout=20)
    response.encoding = 'utf-8'

    json_data = []

    # Extract fire data for Phoenix
    soup = BeautifulSoup(response.text,features="lxml")

    for item in soup.findAll('tr', attrs={'class': 'MonitorRow'}):
        array = item.findAll('td')
        try:
            json_item = {}
            json_item["streetAddress"] =  (array[1].text)
            json_item["subTypeFull"] = "Fire"
            json_data.append(json_item)
        except:
            pass

    fireArray = []

    # Extract fire data for Miami
    for item in json_data:
        if("fire" in item["subTypeFull"].lower() or "burning" in item["subTypeFull"].lower()):
            # New dict
            dictObj = {}
            dictObj["Address"] = item["streetAddress"]
            dictObj["IncidentType"] = item["subTypeFull"]
            # convert time to central time
            #dictObj["Time"] = (datetime.strptime(item["Time"].replace(" ",""), '%H:%M:%S') ).strftime('%H:%M:%S')
            #dictObj["Location"] = item["Location"]
            fireArray.append(dictObj)

    # Custom Coordinates for San Antonio
    def customCoordinateFunc(fire, currentdict):

        lon = "0"
        lat = "0"

        try: 
            # Google Maps Reverse Geolocation Code
            r = requests.get("https://www.google.com/maps?q=" + fire["Address"] + ",Phoenix,Arizona", timeout=20)
            scrapestring = "<meta content=\"https://maps.google.com/maps/api/staticmap?center="
            index = r.text.index(scrapestring)
            index += len(scrapestring)
            lon = r.text[index : r.text.index(".",index) + 7]
            lat = r.text[r.text.index("%2C") + 3 : r.text.index(".",r.text.index("%2C")) + 7 ]
        except:
            try:
                # Nomatim Reverse Geolocation Code
                r = requests.get("https://nominatim.openstreetmap.org/search?q=" + fire["Address"].replace("/","&") + ",Phoenix,Arizona&format=json", timeout=20)
                lon = r.json()[0]["lat"]
                lon = lon[:lon.index(".") + 7]
                lat = r.json()[0]["lon"]
                lat = lat[:lat.index(".") + 7]
            except:
                # Skip this fire, don't ruin entire file if can't be geocoded correctly.
                pass



        return "http://maps.google.com/maps?q=" + lon + "," + lat


    dataConverter("Phoenix",fireArray,"IncidentType","Address", customCoordinateFunc)


elif typename == "fireMapPinellasCounty":

    response = requests.get("https://www.pinellascounty.org/911/activity.json", timeout=20)
    response.encoding = 'utf-8-sig'

    json_data = []

    # Extract fire data for Pinellas County
    json_data1 = response.json()["CallInfo"]

    for array in json_data1:
        try:
            json_item = {}
            time =  (array["Received"])
            json_item["Time"] = datetime.strptime(time, '%H:%M:%S').strftime('%H:%M:%S')
            json_item["Lat"] = (array["Lat"])
            json_item["Lon"] = (array["Lon"])
            json_item["streetAddress"] =  (array["Grid"])
            # Instead of using Grid, need to reverse geocode to get address
            
            json_item["subTypeFull"] = (array["Type"])
            json_data.append(json_item)
        except:
            pass


    fireArray = []

    # Extract fire data for Pinellas County
    for item in json_data:
        if("fire" in item["subTypeFull"].lower() or "burning" in item["subTypeFull"].lower()):
            # New dict
            dictObj = {}
            dictObj["Address"] = item["streetAddress"]
            dictObj["IncidentType"] = item["subTypeFull"]
            dictObj["LATITUDE"] = item["Lat"]
            dictObj["LONGITUDE"] = item["Lon"]
            # convert time to central time
            dictObj["Time"] = (datetime.strptime(item["Time"].replace(" ",""), '%H:%M:%S') - timedelta(hours=1)).strftime('%H:%M:%S')
            fireArray.append(dictObj)

    # Custom Coordinates for San Antonio
    def customCoordinateFunc(fire, currentdict):

        lon = fire["LATITUDE"]
        lat = fire["LONGITUDE"]

        # convert to 6 decimal places
        lon = lon[:lon.index(".") + 7]
        lat = lat[:lat.index(".") + 7]

        return "http://maps.google.com/maps?q=" + lon + "," + lat


    dataConverter("PinellasCounty",fireArray,"IncidentType","Address", customCoordinateFunc)


