#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ---------------------

# --- utilities
import json, sys, cPickle, os, operator, types
from random import randint, shuffle, choice, random
from time import sleep, asctime
from glob import glob
from os import makedirs, path
# --- twitter Stuff
import twitter, twython
from twitter.oauth import write_token_file, read_token_file
from twitter.oauth_dance import oauth_dance
# --- ML stuff

from unidecode import unidecode

from tools import Metanalyzer
M = Metanalyzer()
# --- serial Stuff
#import serial
#ser = serial.Serial('/dev/ttyUSB0', 9600)
# --- preprocessing Stuff 

# --- OSC Stuff
import OSC
#import pifacedigitalio as pf

global oscClient
oscClient = OSC.OSCClient()
oscClient.connect(('127.0.0.1', 9009))              # connect oscClient to localhost:9009 (processing)

global oscClient_ari
oscClient_ari = SOC.OSCClient()
oscClient_ari.connect(('192.168.1.182', 9090))     # connect oscClient_ari (Arinoise)
global gestu

class App:                                          # this app acts as server, so listen incoming msgs on this pc ip
    def __init__(self,ip,port):
        self._ip=ip
        self._port=port
        #self.r1 = pf.Relay(0)
        #self.r2 = pf.Relay(1)
        #pf.init()
        self.server = OSC.OSCServer( ( self._ip, self._port) )
        self.server.addMsgHandler( "/gesto", self.callback_gesto )
        #self.server.addMsgHandler( "/tweet", self.user_callback )
        #self.server.addMsgHandler( "/quit", self.quit_callback )
        self.server.timeout = 0
        self.server.handle_timeout = types.MethodType(self.handle_timeout, self.server)

        self.run = True
        print ("[OSCtweet]: up & running")
        while self.run:
            sleep(0.01)
            self.each_frame()  
            self.server.close()


    def callback_gesto(self, path, tags, args, source):
        #print path,
        cmnd = OSC.OSCMessage("/gesto")
        # arg0 es un int [1, 4]
        a0 = args[0]-1
        global gestu
        gestu = a0
        cmnd.append(a0)
        # arg1 es un int [0, 100)
        a1 = args[1]
        cmnd.append(a1)
        # arg2 es un string
        a2 = args[2]
        cmnd.append(a2)
        print cmnd
        oscClient.send(cmnd)
        global kws
        kws = palabras_emotivas[a0]
        global keyword
        keyword = ' OR '.join(kws)
        print 'keyword:', keyword
        do_the_trick()

    def user_callback(self,path, tags, args, source):
        print path
        for a in args:
            print a
        # callback code here

    def quit_callback(self,path, tags, args, source):
        self.run = False

    def handle_timeout(self,server):
        self.timed_out = True 

    def each_frame(self):
        self.server.timed_out = False
        while not self.server.timed_out:
            self.server.handle_request()

#   ----------      -------------       ------------      -------------

def dual_login(app_data, user_data):
    """
    login, oauthdance and creates .credential file for specified user
    """
    APP_NAME = app_data['AN']
    CONSUMER_KEY = app_data['CK']
    CONSUMER_SECRET = app_data['CS']
    CREDENTIAL = '.'+user_data['UN']+'.credential'

    try:
        (oauth_token, oauth_token_secret) = twitter.oauth.read_token_file(CREDENTIAL)
        print '[Load]: %s' % CREDENTIAL,
    except IOError, e:
        (oauth_token, oauth_token_secret) = twitter.oauth_dance(APP_NAME, CONSUMER_KEY, CONSUMER_SECRET)
        twitter.oauth.write_token_file(CREDENTIAL, oauth_token, oauth_token_secret)
        print '[Save:] %s' % CREDENTIAL,
    api = twitter.Twitter(domain='api.twitter.com', api_version='1.1',
        auth=twitter.oauth.OAuth(oauth_token, oauth_token_secret, CONSUMER_KEY, CONSUMER_SECRET))
    api2 = twython.Twython(CONSUMER_KEY, CONSUMER_SECRET, oauth_token, oauth_token_secret)
    return api, api2

def do_log():
    # login
    global api01, api02
    print '[API_STATE]: ',
    api01, api02 = dual_login(app_data, user_data)
    print '=ok='
    return

def do_fetch(dot_A=0):
    """
    fetch all available tweets with given keyword since dot_A (max_id in past fetch)
    """
    ftw_meta={}
    ftw_stat=[]
    samples_db=[]
    past_dot=0
    try: #to get some tweets
        timestamp = asctime()
        fetched_tws = api01.search.tweets(q=keyword, since_id=dot_A, count=8)
        #fetched_tws = api01.search.tweets(q=keyword, since_id=dot_A, count=100, geocode='19.4341667,-99.1386111,1000km')
        ftw_stat, ftw_meta = fetched_tws['statuses'], fetched_tws['search_metadata']
        alive=True
        dot_B = ftw_meta['max_id']              #present
        dot_C = ftw_stat[-1]['id']              #min_id in pack
        samples_db.extend(ftw_stat)
    except: #abort, wait, retry
        print '\n No hay nuevos tweets... <<'+asctime()+'>> ||| \n'
        ftw_meta['count']=0
        alive = False
        dot_B=dot_A #if exception ocurrs
        #sleep(60)
        #continue
    #if theres more
    """
    if ( (ftw_meta['count']==100) and (dot_A!=0) ):
        while(ftw_meta['count']>3 and dot_C!=past_dot):
            try:
                past_dot = dot_C # remember before overwriting
                fetched_tws = api01.search.tweets(q=keyword, since_id=dot_A, max_id=dot_C, count=100)
                #fetched_tws = api01.search.tweets(q=keyword, since_id=dot_A, max_id=dot_C, count=100, geocode='19.4341667,-99.1386111,1000km')
                ftw_stat, ftw_meta = fetched_tws['statuses'], fetched_tws['search_metadata']
                dot_C = ftw_stat[-1]['id']      #min_id
                samples_db.extend(ftw_stat)
            except:
                ftw_meta['count']=0
                break
    """
    if (alive):
        samples_db.reverse()
        print "[%s]" % timestamp
        #print '\n Fetched at <<'+timestamp+'>> ||| \n ----------------------------------------------\n'
    #return texts in db
    samples_txt = [s['text'].lower() for s in samples_db]
    return dot_B, samples_db


#   ----------      -------------       ------------      -------------


def do_the_trick():
    print "\n\t-->> [Collecting]"
    global dot
    global samples
    dot, samples = do_fetch()
    if len(samples)>0:
        print "\n\t-->> [Playing]:"
    for ind_s, s in enumerate(samples):
        print "\n<.%s.>" % s['text']
        #threat msg for spacing and tokenizing
        for j,k in enumerate(kws):
            if unidecode(k).lower() in unidecode(s['text']).lower():                
                
                newTweet = M.tweetmetanalyze(unidecode(s['text']))
                ste = newTweet
                print "U:", ste

                #here, send osc
                try:
                    cmnd = OSC.OSCMessage("/tweet")
                    cmnd.append(ste)
                    cmnd.append(ind_s)
                    oscClient.send(cmnd)

                    cmnd = OSC.OSCMessage("/palabra")
                    cmnd.append(categorias_emotivas[gesto_to_class[k]])
                    cmnd.append(gesto_to_inten[k])
                    oscClient_ari.send(cmnd)

                except:
                    print '\n\tAquí le falló\n\t'
        sleep(randint(1,5))

if __name__ == '__main__':
    # lists
    categorias_emotivas = ['alegria', 'ira', 'tristeza', 'miedo']
    palabras_emotivas = [['sonreir', 'felicidad', 'feliz', 'risa', 'reir', 'carcajada'],
                    ['disgusto', 'frustracion', 'colera', 'furia'],
                    ['pesimismo', 'desamparo', 'llanto','dolor'],
                    ['alerta', 'nervioso', 'ansiedad', 'aterrorizado', 'psicosis']]
    gestures = ['sonreir', 'feliz', 'risa', 'carcajada',
                    'disgusto', 'frustracion', 'colera', 'furia',
                    'pesimismo', 'desamparo', 'llanto','dolor',
                    'alerta', 'nervioso', 'ansiedad', 'aterrorizado']
    gesto_to_class = {'sonreir':0, 'felicidad':0, 'feliz':0, 'risa':0, 'reir':0, 'carcajada':0, 
                    'disgusto':1, 'frustracion':1, 'colera':1, 'furia':1,
                    'pesimismo':2, 'desamparo':2, 'dolor':2, 'llanto':2,
                    'alerta':3, 'nervioso':3, 'ansiedad':3, 'aterrorizado':3, 'psicosis':3}
    gesto_to_inten = {'sonreir':0, 'felicidad':1, 'feliz':1, 'risa':2, 'reir':2, 'carcajada':3, 
                    'disgusto':0, 'frustracion':1, 'colera':2, 'furia':3,
                    'pesimismo':0, 'desamparo':1, 'dolor':2, 'llanto':3,
                    'alerta':0, 'nervioso':1, 'ansiedad':2, 'aterrorizado':3, 'psicosis':3}
    # login, check path
    app_data, user_data = cPickle.load(open('.teleTex.dat','r'))
    
    # read arguments
    if len(sys.argv)>1:
        keyword=" ".join(sys.argv[1:])
    else:
        keyword =  "alameda";
    
    # init and log
    timestep = 10
    dot = 0
    do_log()
    
    #check OSC
    #app = App("192.168.1.234",9000)        #mon for receive
    app = App("127.0.0.1",9029)             #for local use (python send_gesto)