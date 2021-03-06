#!/usr/bin/env python3.8

import os,sys
from random import randint
import requests
from PIL import Image
from io import BytesIO
import configparser
import mercantile
import instapy_cli
import logging
logging.basicConfig(level=logging.INFO)

instaconfig = configparser.ConfigParser()
instaconfig.read('/storage/projects/instaortho/instagram.ini')

def spreadRange(value,spread=5):
    return range(value-int(spread/2), value+int(spread/2)+1)

tmspath = "https://maps.nj.gov/arcgis/rest/services/Basemap/Orthos_Natural_2015_NJ_WM/MapServer/WMTS/tile/1.0.0/Basemap_Orthos_Natural_2015_NJ_WM/default/default028mm/{z}/{y}/{x}"

zoom = 18
tmsbounds = (76050,97939,77260,100252)

newx = randint(tmsbounds[0],tmsbounds[2])
newy = randint(tmsbounds[1],tmsbounds[3])

latlng = mercantile.ul(newx,newy,zoom)
description = "Near {lat:.4f}, {lng:.4f}".format(lat=latlng.lat,lng=latlng.lng)
logging.debug(description)

post = Image.new("RGB", (256*5,256*5))
postiter = [0,0]

for x in spreadRange(newx):
    postiter[1]=0
    for y in spreadRange(newy):
        r = requests.get(tmspath.format(z=zoom,y=y,x=x))
        logging.debug(r.status_code, tmspath.format(z=zoom,y=y,x=x))
        onetile = Image.open(BytesIO(r.content)) 
        if not onetile.getbbox():
            logging.error("Empty tile encountered. Quitting.")
            sys.exit(2)
        post.paste(onetile,
            (256*postiter[0], 256*postiter[1],
            (256*postiter[0])+256, (256*postiter[1])+256 ))
        logging.debug(postiter)
        postiter[1] += 1
    postiter[0] += 1
post.save('photo.jpg')

with instapy_cli.client(instaconfig['DEFAULT']['username'],
          instaconfig['DEFAULT']['password']) as cli:
    cli.upload('photo.jpg', description) 
os.remove('photo.jpg')
