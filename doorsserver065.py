#!/usr/bin/env python
"""
     in 0.61
        -restucture listener to be simpler while loop in a separate thread to try to prevent the memory leak.
     in version 0.62:
        -(still needs work) persistent opensince[] by outputing it frequently as json to a file in /etc/
        -ignore disabled (negative) pins when loading.
        
    todo in 0.64:
        -ssl
    Todo in version 0.7:
        -log in
        -admin backend (allow mutiple users with different permisions)
        -admin frontend (web interface to add/remove users and their permsions)
        -change config from web interface


"""

import urllib.request, http.server, http.cookies
import time, os, sys, smtplib, json
from time import sleep
import pifacedigitalio, datetime, cgi
startup=True
warnat={}
opensince={}
verbose=0
isdaemon=0
debug=False
session_data={}
filebase=os.path.basename(__file__)
#dlf="/var/log/doors4.log"
import argparse
parser = argparse.ArgumentParser()
parser.add_argument('-v','--verbose',help="verbose logging/output",action='store_true')
parser.add_argument('-f','--configfile', help='specify a JSON formated file to retrive configuration from',default ='/home/pi/doors.json')
parser.add_argument('-d','--daemon',help='direct errors and output to log files', action='store_true')
parser.add_argument('-i','--insecure',help='do not use ssl', action='store_true', default=False)
parser.add_argument('-n','--newtoken',help='generate a new token', action='store_true', default=False)
parser.add_argument('-p','--port',help='specify what port to listen on for http requests', type=int, default=8880 )
parser.add_argument('-l','--logfile', help='specify the log path and file name prefix',default ='/var/log/'+filebase)
args=parser.parse_args()
try:
    doorstates=open(args.logfile+".states","r")
    doorstatesjson=json.loads(doorstates.read())
    doorstates.close()
except:
    doorstatesjson={'states':{},'since':{}}
doorstates=open(args.logfile+".states","w",1)

if not args.insecure:
    from socketserver import BaseServer
    import ssl

"""
    writes events to log and sets/clears message to remind of
    doors being left open
    
"""
import urllib.parse
def door_oc(event):
    
    """
        event trigger can be a bit buggy, so we'll wait a fraction
        of a second, then confirm the input still matches up.
        Also verify event is valid (direction is 0 or 1 only)
    """
    if debug:print(event)
    sleep(0.08)
    if event['direction'] >1:
        if args.verbose: print("warning - unknown direction:",event['direction'], " full event:\n",event,"\nprevious event ignored.\n",file=doorlog)
    elif piface.input_pins[event['pin']].value==event['direction']:
        if args.verbose: print("warning - event direction does not make sense with current pin state. full event:\n",event,"\nprevious event ignored.\n",file=doorlog)
    else:
        if args.verbose:
            print(event,file=doorlog)
        dt=str(datetime.datetime.now())
        if (event['pin'] in doorsjson['garageclose']):
            actions=["closed","opening"]
        elif (event['pin'] in doorsjson['garageopen']):
            actions=['open','closing']
        else:
            actions=["closed","opened"]
       
        doorlog.write( doorsjson['doors'][str(event['pin'])]+" door was "+actions[event['direction']]+" at "+ dt + "\r\n")
        
        """ set time for door warning """
        global warnat, opensince, doorstatesjson
        opensince[event['pin']]=int(time.time())
        if (event['pin'] in doorsjson['warnings'])&(int(doorsjson['warntime']>1)):
            
            
            if (event['direction']):
                warnat[event['pin']]=int(time.time())+int(doorsjson['warntime'])
                
                if args.verbose:
                    print ('time.time=',time.time(),'\nwarntime=',doorsjson['warntime'], "\nwarnat=", warnat[event['pin']],"("+time.asctime( time.localtime(warnat[event['pin']]) )+")\n",file=doorlog)
            else:
                if args.verbose:
                    print("warnat ",event['pin']," canceled.\n",file=doorlog)
               
                warnat[event['pin']]=0
    doorstatesjson['states'][event['pin']]=event['direction']
    doorstatesjson['since'][event['pin']]=int(time.time())
    doorstates.seek(0)
    doorstates.write(json.dumps(doorstatesjson))
                
activepins=[]
def mainstuff():
    global piface, warnat, opensince #garagepins, doors, garagewarnmail, garagewarntime, warnat, smtpinfo,

    #listener = pifacedigitalio.InputEventListener(chip=piface)
    ii=0
    if debug:print (doorstatesjson)
    for i in doorsjson['doors']:
        if int(i) < 0:
            pass
        else:
            
            t=pinListener()
            t.fn=door_oc
            try:
                t.value=int(not bool(doorstatesjson['states'][str(i)]))
                opensince[int(i)]=doorstatesjson['since'][str(i)]
            except KeyError as e:
                if args.verbose:print ("exception while tring to load previous states for ",i, e)
                #sleep(4)
                t.value=0
                opensince[int(i)]=int(time.time())
            
            t.pin=i
            t.start()
            
            del(t)
            ii=ii+1
            
    for i in doorsjson['warnings']:
        warnat[i]=0
    
    while 1:
        
        if (str(int(time.time())).endswith('1') ) and debug: print (resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1000,'k ram')
        for x in doorsjson['warnings']:
                if ((warnat[x]<time.time())) and (warnat[x]>1):
                    if debug:
                        print('(warnat[x]=',warnat[x],")<time.time()(",time.time(),")")
                    if args.verbose:
                        print ("x=",x," warnat[x]=",warnat[x],"\n Sending warning message for "+doorsjson['doors'][str(x)]+" . Repeating at",time.asctime( time.localtime(warnat[x]) ),"\n",file=doorlog)
                    warnat[x]=int(time.time())+int(doorsjson['warntime'])
                    server = smtplib.SMTP(doorsjson['emaillogin']['server'],doorsjson['emaillogin']['port'])
                    if doorsjson['emaillogin']['say_ehlo']:
                        server.ehlo()
                    if doorsjson['emaillogin']['starttls']:
                        server.starttls()
                    server.login(doorsjson['emaillogin']['userid'],doorsjson['emaillogin']['password'])
                    message=doorsjson['warnmessage']
                    if message.count:
                        message=message.replace('%t',str(round((time.time()-opensince[x])/60,1))+" minutes")
                        message=message.replace('%d',doorsjson['doors'][str(x)])
                        if args.insecure:
                            proto="http://"
                        else:
                            proto='https://'
                        if 'domain' in doorsjson:
                            if 'token' in doorsjson:
                                tok="/?t="+doorsjson['token']
                            else:
                                tok=""
                            message=message.replace('%u',proto+doorsjson['domain']+":"+str(args.port)+tok)
                    else:
                        message=doorsjson['doors'][str(x)]+" has been open at least "+ str(round((time.time()-opensince[x])/60,1))+" minutes!"
                    server.sendmail(doorsjson['emaillogin']['email'],doorsjson["warnemail"],message)
                    server.close
        sleep(0.5)

piface = pifacedigitalio.PiFaceDigital()

doorsjson={}
conf_notes=''
def load_config(fn):
    global doorsjson, conf_notes
    doorsjson={}
    if len(fn)==0:
        fn="/home/pi/doors.json"
    doorconf=open(fn,"r")
    doorsjson=json.loads(doorconf.read())
    doorconf.close()
    conf_notes=doorsjson['____notes____']
    del(doorsjson['____notes____'])
    if 'debug' in doorsjson:
        if bool(doorsjson['debug']):debug=True
    if ('token' not in doorsjson) or args.newtoken:
        import hashlib
        doorsjson['token']=hashlib.sha224(bytes(str(time.time())+str(len(doorsjson)),'UTF-8')).hexdigest()

class myHandler(http.server.SimpleHTTPRequestHandler):
    #Handler for the GET requests
    def cookies(self):
        tcookies={}
        if 'Cookie' in self.headers:
            
            cookies_list=self.headers['Cookie'].split('; ')
            for cookie in cookies_list:
                key, val =cookie.split('=')
                tcookies[key]=val
        return tcookies
    def do_GET(self):
        tempp=self.path.split('?')
        self.path=tempp[0]
        get={}
        fget={}
        if len(tempp)>1:
            fget=urllib.parse.parse_qs(tempp[1])
            query=tempp[1].split('&')

            for q in query:
                key, val = q.split('=')
                get[key]=val
                
        if debug:print(self.path)
        if debug:print(fget)
        if 'token' in self.cookies():
            if self.cookies()['token']==doorsjson['token']:#'2b61d43c54d8b395e9424c3906261431':
                loggedin=True
            else:
                loggedin=False
        else:
            loggedin=False
        
        if 't' in fget:
            if debug:print ("t is in fget and =",fget['t'][0])
            if debug:print('expecting token=',doorsjson['token'])
            if fget['t'][0]==doorsjson['token']:#'2b61d43c54d8b395e9424c3906261431':
                token=True
                loggedin=True
                if debug:print('token=',token)
            else:
                token=False
        else:
            token=False            
        sendReply=False
        #loggedin=True
        cookies={}
        if 'Cookie' in self.headers:
            cookies_list=self.headers['Cookie'].split('; ')
            for cookie in cookies_list:
                key, val =cookie.split('=')
                cookies[key]=val
        if debug:print (self.path)
        
        if debug: print("path being used is:", self.path,"\nloggedin is", loggedin)
        if self.path=="/":
            if debug: print('path is root')
            global opensince
            c=http.cookies.SimpleCookie()
            c['pi']="hello"
            if token:
                if debug: print('token is still true')
                c['token']=doorsjson['token']#'2b61d43c54d8b395e9424c3906261431'
                c['token']['expires']=6*30*24*60*60
            if args.verbose:
                print (self.headers, file=sys.stdout)
                #print(self.headers['Cookie'])
            cookies={}
            #if 'Cookie' in self.headers:
            #    cookies_list=self.headers['Cookie'].split('; ')
            #    for cookie in cookies_list:
            #        key, val =cookie.split('=')
            #        cookies[key]=val
            #if debug:print (self.path)
            #if 'token' in self.cookies():
            #    if self.cookies()['token']=='2b61d43c54d8b395e9424c3906261431':
            #        loggedin=True
            #    else:
            #        loggedin=False
            #else:
            #    loggedin=False
            
            if loggedin:        
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.wfile.write(bytes(str(c)+"\n", 'UTF-8'))
                self.end_headers()
                #self.wfile.write(bytes('heyQt\n', "UTF-8"))
                #self.wfile.write(bytes(str(cookies), "UTF-8"))
                self.wfile.write(bytes((open('top.html').read()),"UTF-8"))
                for pin in doorsjson['doors']:
                    if int(pin) <0:
                        pass
                    else:
                        actions=["open","closed"]
                        openclosestate=actions[int(piface.input_pins[int(pin)].value)]
                        if (openclosestate=="open") :
                            if int(pin) in doorsjson['garageclose']:
                                try:
                                    if (doorsjson['garageopen'][doorsjson['garageclose'].index(int(pin))]>-1):
                                        openpin=doorsjson['garageopen'][doorsjson['garageclose'].index(int(pin))]
                                        if (piface.input_pins[openpin].value==0):
                                            openclosestate='partialy open'
                                            img='partopengaragedoor.jpg'
                                        else:
                                            img="opengaragedoor.jpg"
                                    else:
                                        img='opengaragedoor.jpg'
                                except (ValueError, IndexError) as e:
                                    repr(e)
                                    img='opengaragedoor.jpg'
                            else:
                                img='opendoor.jpg'
                        else:
                            if int(pin) in doorsjson['garageclose']:
                                img='closedgaragedoor.jpg'
                            else:
                                img='closeddoor.jpg'
                        
                            
                        if int(pin) in doorsjson['garageclose']:
                            self.wfile.write(bytes('<li>                        <img style="cursor: pointer;" onclick="toggle_garage('+pin+');" id="'+pin+'-img" src="'+img+'" />                        <h3>'+doorsjson['doors'][pin]+' Door is <span class="status" id="'+pin+'-stat">'+openclosestate+'</span>                        </h3>                        <p id="time'+pin+'">since '+time.asctime( time.localtime(opensince[int(pin)]))+'</p></li>',"UTF-8"))
                        elif int(pin) in doorsjson['garageopen']:
                            pass
                            #print ("pass pin",pin)
                        else:
                            if debug:print (opensince)
                            self.wfile.write(bytes('<li>\n                        <img  id="'+pin+'-img" src="'+img+'" />\n                        <h3>'+doorsjson['doors'][pin]+' Door is <span class="status" id="'+pin+'-stat">'+openclosestate+'</span></h3>\n                        <p id="time'+pin+'">since '+time.asctime( time.localtime(opensince[int(pin)]))+'</p>\n                    </li>',"UTF-8"))
                self.wfile.write(bytes(__file__+(open('bot.html').read()+str(opensince)),"UTF-8"))
                sendReply=False
                """
                    end of default page (for authorized users)
                """
            else:
                """
                    todo: add a login form here
                """
                    
                pass
        elif self.path=="/alldoors":
            #
            #"""
            #    check for login first
            #"""
            #if 'token' in self.cookies():
            #    if self.cookies()['token']=='2b61d43c54d8b395e9424c3906261431':
            #        loggedin=True
            #    else:
            #        loggedin=False
            #else:
            #    loggedin=False
            #        
            if loggedin: #logged in
                self.send_response(200)
                self.send_header('Content-type','text/html')
                self.end_headers()
                outputjson={'state':{},'gstate':{},'time':{}, 'ram':str(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1000)+'k ram'}
                for pin in doorsjson['doors']:
                    if (int(pin)<0) or (int(pin) in doorsjson['garageopen']):
                        pass
                    else:
                        if debug: print (outputjson,opensince,pin)
                        outputjson['time'][pin]='since '+time.asctime( time.localtime(opensince[int(pin)]))
                        if int(pin) in doorsjson['garageclose']:
                            if piface.input_pins[int(pin)].value==1:
                                outputjson['gstate'][pin]=1
                            else:
                                try:
                                    openpin=doorsjson['garageopen'][doorsjson['garageclose'].index(int(pin))]
                                    if openpin>-1:
                                        if piface.input_pins[openpin].value==0:
                                            outputjson['gstate'][pin]=2
                                        else:
                                            outputjson['gstate'][pin]=0
                                    else:
                                        outputjson['gstate'][pin]=0
                                except ArithmeticError as e: #(IndexError, ValueError)
                                    repr(e)
                                    outputjson['gstate'][pin]=0
                        else:
                            #print('not in either garage list')
                            outputjson['state'][pin]=piface.input_pins[int(pin)].value
                self.wfile.write(bytes(json.dumps(outputjson),"UTF-8"))
            
            sendReply=False
        
        elif self.path=='/shutdown/full':
            if loggedin:
                exit(0)
        
        elif self.path=="/reload":
            #if 'token' in self.cookies():
            #    if self.cookies()['token']=='2b61d43c54d8b395e9424c3906261431':
            #        loggedin=True
            #    else:
            #        loggedin=False
            #else:
            #    loggedin=False
            #        
            if loggedin:
                load_config(args.configfile)
                self.send_response(200)
                self.send_header('Location','/')
                self.end_headers()
        elif self.path=="/config":
            #if 'token' in self.cookies():
            #    if self.cookies()['token']=='2b61d43c54d8b395e9424c3906261431':
            #        loggedin=True
            #    else:
            #        loggedin=False
            #else:
            #    loggedin=False
            #        
            if loggedin: #logged in
                self.send_response(200)
                self.send_header('Content-type','text/html')
                self.end_headers()
                self.wfile.write(bytes('<form action="setconf">',"UTF-8"))
                aa=0
                for door in doorsjson['doors']:
                    if int(door)<0:
                        disabled=''
                        pin = str(0-int(door))
                    else:
                        disabled='checked'
                        pin=door
                    self.wfile.write(bytes('<input  name="enable'+str(aa)+'"  type="checkbox" '+disabled+' /><input type="number" name="pin'+str(aa)+'" value="'+pin+'" min="0" max="7"/>'+"="+'<input  name="name'+str(aa)+'" value="'+str(doorsjson['doors'][door]+'" />'+"<br />"),"UTF-8"))
                    aa+=1
                self.wfile.write(bytes('<input type="submit"></form>',"UTF-8"))
        elif self.path=="/setconf":
            if loggedin:
                enables=[]
                names={}
                pins={}
                for forminput in fget.keys():
                    if forminput.startswith('pin'):
                        pins[forminput[-1:]]=get[forminput]
                    elif forminput.startswith('enable'):
                        enables.append(forminput[-1:])
                    elif forminput.startswith('name'):
                        names[forminput[-1:]]=urllib.parse.unquote(get[forminput])
                if debug:
                    print("pins[]=",pins,"\nenables=",enables,"names=",names)
                for key,pin in pins.items():
                    if not((pin in doorsjson['doors']) or (str(0-int(pin)) in doorsjson['doors'])):
                        if key in enables:
                            # todo:activate listener for pin
                            doorsjson['doors'][str((pin))]=names[key]
                        else:
                            doorsjson['doors'][str(0-int(pin))]=names[key]
                    elif (pin) in doorsjson['doors']:
                        if not key in enables:
                            activepins.remove(pin)
                            del(doorsjson['doors'][pin])
                            doorsjson['doors'][str(0-int(pin))]=names[key]
                        else:
                            doorsjson['doors'][str((pin))]=names[key]
                    else:
                        if not key in enables:
                            doorsjson['doors'][str(0-int(pin))]=names[key]
                        else:
                            # todo: activate listener for pin
                            del(doorsjson['doors'][str(0-int(pin))])
                            doorsjson['doors'][str((pin))]=names[key]
                
                djf=open( args.configfile,'w')
                djf.write(json.dumps(doorsjson,indent=4, separators=(',', ': ')))
                load_config(args.configfile)
                # todo: stop/start threads for new disabled/enabled pins
    
        elif self.path.startswith("/click/"):
            #if 'token' in self.cookies():
            #    if self.cookies()['token']=='2b61d43c54d8b395e9424c3906261431':
            #        loggedin=True
            #    else:
            #        loggedin=False
            #else:
            #    loggedin=False
            #        
            if loggedin:
            #if 1: #logged in
                pin=self.path[-1:]
                if debug:print (pin)
                relay=doorsjson['garagerelay'][doorsjson['garageclose'].index(int(pin))]
                if 1: #check for matching relay pin #(int(pin) in doorsjson['garageclose']) and doorsjson['garagerelay'].count>doorsjson['garageclose'].index(int(pin)):
                    relay=doorsjson['garagerelay'][0]
                    piface.output_pins[relay].turn_on()
                    sleep (0.3)
                    piface.output_pins[relay].turn_off()
                self.send_response(200)
                self.send_header('Content-type','text/html')
                self.end_headers()
                self.wfile.write(bytes('ok',"UTF-8"))
        elif self.path=='/log':
            f = open(args.logfile+".log", mode='rb')
            if debug:print (f)
            data=f.read()
            if debug:print (len(data))
            self.send_response(200)
            self.send_header('Content-type',"text/plain")
            self.end_headers()
            self.wfile.write(data)
            f.close()
        elif self.path=='/serverlog':
            f = open(args.logfile+".server", mode='rb')
            if debug:print (f)
            data=f.read()
            if debug:print (len(data))
            self.send_response(200)
            self.send_header('Content-type',"text/plain")
            self.end_headers()
            self.wfile.write(data)
            f.close()
        elif self.path=='/errlog':
            f = open(args.logfile+".err", mode='rb')
            if debug:print (f)
            data=f.read()
            if debug:print (len(data))
            self.send_response(200)
            self.send_header('Content-type',"text/plain")
            self.end_headers()
            self.wfile.write(data)
            f.close()
        elif self.path.endswith(".manifest"):
            mimetype='text/cache-manifest'
            sendReply = True
        elif self.path.endswith(".html"):
            mimetype='text/html'
            sendReply = True
        elif self.path.endswith(".jpg"):
            mimetype='image/jpg'
            sendReply = True
        elif self.path.endswith(".gif"):
            mimetype='image/gif'
            sendReply = True
        elif self.path.endswith(".js"):
            mimetype='application/javascript'
            sendReply = True
        elif self.path.endswith(".css"):
            mimetype='text/css'
            sendReply = True
        elif self.path.endswith(".png"):
            mimetype='image/png'
            sendReply = True
        
        if sendReply == True:  
                #Open the static file requested and send it
                f = open('/home/pi/python.d' + self.path, mode='rb')
                if debug:print (f)
                data=f.read()
                if debug:print (len(data))
                self.send_response(200)
                self.send_header('Content-type',mimetype)
                self.end_headers()
                self.wfile.write(data)
                f.close()
        else:
            #"".endswith
            pass
    def log_message(self, format, *args):
        if isdaemon:
            serverlog.write("%s - - [%s] %s\n" %
                     (self.address_string(),
                      self.log_date_time_string(),
                      format%args))
        else:
            sys.stderr.write("%s - - [%s] %s\n" %
                     (self.address_string(),
                      self.log_date_time_string(),
                      format%args))
load_config(args.configfile)                
import threading, resource
runServer=True
class serverthread(threading.Thread):
    def run(self):
        global runServer
        while runServer:
            try:           
                server = http.server.HTTPServer(('', args.port), myHandler)
                print ('Starting httpserver on port ' , args.port)
                if not args.insecure:
                    server.socket = ssl.wrap_socket (server.socket, certfile='/etc/ssl/localcerts/doorsserver065.cer', keyfile="/etc/ssl/localcerts/doorsserver065.key", server_side=True)
                server.serve_forever()
            
            except KeyboardInterrupt:
                print ('Keyboard Interupt')
                runServer=False
            except Exception as e:
                print(e,file=sys.stderr)
                try:
                    server.server_close()
                    print ('server was stopped at '+ time.asctime( time.localtime(time.time()))+' automatically due to error.')
                except Exception as e:
                    print (e,"\n'server_close()' failed at "+time.asctime( time.localtime(time.time()))+".",file=sys.stderr)
                finally:
                    try:
                        server = http.server.HTTPServer(('', args.port), myHandler)
                        if not args.insecure:server.socket = ssl.wrap_socket (server.socket, certfile='/etc/ssl/localcerts/doorsserver065.cer', keyfile="/etc/ssl/localcerts/doorsserver065.key", server_side=True)

                        print ('Starting httpserver on port ' , args.port," at ", time.asctime( time.localtime(time.time())))

                        server.serve_forever()
                    except KeyboardInterrupt:
                        print ('Keyboard Interupt')
                        runServer=False
class pinListener(threading.Thread):
    
    #def __init__(self, pin, fn ):
     #   self.pin=pin
      #  self.value=piface.input_pins[int(self.pin)].value
    def run(self):
        global activepins
        activepins.append(self.pin)
        while self.pin in activepins:
            self.newval=piface.input_pins[int(self.pin)].value
            if self.newval==self.value:
                pass
            else:
                self.value=self.newval
                self.fn(dict({'pin':int(self.pin), 'direction': int(not bool(self.value)), 'value': int(self.value)}))
            sleep(0.1)
    
os.chdir(os.path.dirname(os.path.abspath(__file__)))
if debug:print (os.getcwd())
serve=serverthread()
serve.start()


if debug: print('doorstatesjson=',doorstatesjson)
if args.daemon:
    
    doorlog = open(args.logfile+".log", "a",1)
    sys.stderr=open(args.logfile+".err","a",1)
    sys.stdout=open(args.logfile+".log","a",1)
    serverlog=open(args.logfile+".server","a",1)
    #sys.stdin.close()
    #context = daemon.DaemonContext()
    #context.files_preserve = [doorconf,doorlog]
    isdaemon=1
    print(time.asctime( time.localtime(time.time()))," daemon starting up...",file=doorlog)
    print(time.asctime( time.localtime(time.time()))," daemon starting up...",file=sys.stderr)
    if args.verbose:
        print(json.dumps(doorsjson,indent=4,sort_keys=True,separators=(',',':')),file=doorlog)
    #with daemon.DaemonContext():
    #with context:
    mainstuff()
else:
    doorlog=sys.stdout
    if args.verbose:
        print(json.dumps(doorsjson,indent=4,sort_keys=True))
    try:
        mainstuff()
    except KeyboardInterrupt:
        doorstates.close()

