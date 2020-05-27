#!/usr/bin/env python3

import os,sys
from random import randint
import requests
import ujson as json
from PIL import Image
from io import BytesIO
import configparser
import mercantile
import logging

if len(sys.argv) == 2 and str(sys.argv[1]).upper() == 'DEBUG':
    logging.basicConfig(level=logging.DEBUG)
else:
    logging.basicConfig(level=logging.INFO)

instaconfig = configparser.ConfigParser()
instaconfig.read(os.path.join(os.getcwd(),'instagram.ini'))

from time import sleep
import subprocess
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys

def spreadRange(value,spread=5):
    return range(value-int(spread/2), value+int(spread/2)+1)

def applescriptType(path):
    ascript = """
activate application "Chrome"

tell application "System Events" to keystroke "/{0}"

delay 1
tell application "System Events" to key code 76

delay 1
tell application "System Events" to key code 76
""".format(path).encode()

    osa = subprocess.Popen(['osascript', '-'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    osa.communicate(ascript)

def savePhoto(filename="photo.jpg"):
    tmspath = "https://maps.nj.gov/arcgis/rest/services/Basemap/Orthos_Natural_2015_NJ_WM/MapServer/WMTS/tile/1.0.0/Basemap_Orthos_Natural_2015_NJ_WM/default/default028mm/{z}/{y}/{x}"

    zoom = 18
    tmsbounds = (76050,97939,77260,100252)

    newx = randint(tmsbounds[0],tmsbounds[2])
    newy = randint(tmsbounds[1],tmsbounds[3])

    latlng = mercantile.ul(newx,newy,zoom)
    
    description = reverseGeocode(latlng.lng, latlng.lat)
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
                return None
            post.paste(onetile,
                (256*postiter[0], 256*postiter[1],
                (256*postiter[0])+256, (256*postiter[1])+256 ))
            logging.debug(postiter)
            postiter[1] += 1
        postiter[0] += 1
    post.save(filename)
    return description

def reverseGeocode(x, y):
    url = "https://geo.nj.gov/arcgis/rest/services/Tasks/Addr_NJ_cascade/GeocodeServer/reverseGeocode?location=%7B+%22x%22%3A+{x}%2C+%22y%22%3A+{y}%2C+%22spatialReference%22%3A+%7B+%22wkid%22%3A+4326+%7D+%7D&distance=100&langCode=&locationType=&featureTypes=&outSR=4326&returnIntersection=false&f=pjson".format(x=x,y=y)
    logging.debug(x, y, url)
    try: 
        d = requests.get(url)
        j = json.loads(d.text)
        if j.get("address").get("ZIP"):
            t = "Near {0}. #{1} #{2}".format(j.get("address").get("City"), j.get("address").get("ZIP"), j.get("address").get("City").lower().replace(" ", "") )
        else:
            t = "Near {0}. #{1}".format(j.get("address").get("City"), j.get("address").get("City").lower().replace(" ", "") )
        return t
    except Exception as e:
        logging.error(e)
        return "Near {lat:.4f}, {lng:.4f}".format(lat=y,lng=x)

class FakeBrowser(object):
    def __init__(self, username, password):
        mobile_emulation = { "deviceName": "Nexus 5" }
        opts = webdriver.ChromeOptions()
        opts.add_experimental_option("mobileEmulation", mobile_emulation)
        self.driver = webdriver.Chrome('/usr/local/bin/chromedriver', options=opts)

        self.driver.get("https://www.instagram.com/")
        sleep(2)
        login_button = self.driver.find_element_by_xpath("//button[contains(text(),'Log In')]")
        login_button.click()
        sleep(2)
        username_input = self.driver.find_element_by_xpath("//input[@name='username']")
        username_input.send_keys( username )
        password_input = self.driver.find_element_by_xpath("//input[@name='password']")
        password_input.send_keys( password )
        password_input.submit()

    def close_reactivated(self):
        try:
            sleep(2)
            not_now_btn = self.driver.find_element_by_xpath("//a[contains(text(),'Not Now')]")
            not_now_btn.click()
            logging.debug("Closed notification (Not Now link)")
            sleep(1)
        except:
            logging.debug("Failed to find Not Now link")

    def close_notification(self):
        try: 
            sleep(2)
            close_noti_btn = self.driver.find_element_by_xpath("//button[contains(text(),'Not Now')]")
            close_noti_btn.click()
            sleep(1)
            logging.debug("Closed notification (Not Now button)")
        except:
            logging.debug("Failed to close notification")

    def close_add_to_home(self):
        try:
            sleep(3) 
            close_addHome_btn = self.driver.find_element_by_xpath("//button[contains(text(),'Cancel')]")
            close_addHome_btn.click()
            sleep(1)
            logging.debug("Closed notification (Cancel button)")
        except:
            logging.debug("Failed to close Add Home")

    def postPhoto(self, description=""):
        new_post_btn = self.driver.find_element_by_xpath("//div[@role='menuitem']").click()
        sleep(1.5)
        
#        uploadfile = self.driver.find_element_by_xpath("//input[@type='file'][@accept='image/jpeg']")
#        uploadfile.sendkeys( os.path.join(os.getcwd(), 'photo.jpg'))
        applescriptType( os.path.join(os.getcwd(), 'photo.jpg'))
#        uploadfile.submit()
        sleep(2)

        next_btn = self.driver.find_element_by_xpath("//button[contains(text(),'Next')]").click()
        sleep(1.5)

        caption_field = self.driver.find_element_by_xpath("//textarea[@aria-label='Write a caption…']")
        caption_field.send_keys(description)

        share_btn = self.driver.find_element_by_xpath("//button[contains(text(),'Share')]").click()
        sleep(25)

    def __del__(self):
        logging.info("Waiting 20 seconds before closing session.")
        sleep(20)
        self.driver.quit()

if __name__ == '__main__':
    description = savePhoto()
    if description:
        logging.info( os.path.join(os.getcwd(), 'photo.jpg') )
        logging.info(description)
        #sys.exit(2)
        try:
            fb = FakeBrowser(instaconfig['DEFAULT']['username'], instaconfig['DEFAULT']['password'])
            fb.close_reactivated()
            fb.close_notification()
            fb.close_add_to_home()
            fb.postPhoto(description)
            sleep(25)
        except Exception as e:
            logging.error(e)
            sys.exit(2)

