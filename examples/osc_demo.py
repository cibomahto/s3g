
# To use this example without installing s3g, we need this hack:
import os, sys
lib_path = os.path.abspath('../')
sys.path.append(lib_path)

import s3g
import serial
import time
import optparse
import OSC
import threading

"""
Control an s3g device (Makerbot, etc) using osc!

Requires these modules:
* pySerial: http://pypi.python.org/pypi/pyserial
* pyOSC: https://trac.v2.nl/wiki/pyOSC
"""

parser = optparse.OptionParser()
parser.add_option("-s", "--serialport", dest="serialportname",
                  help="serial port (ex: /dev/ttyUSB0)", default="/dev/ttyACM0")
parser.add_option("-p", "--oscport", dest="oscport",
                  help="OSC port to listen on", default="10000")
(options, args) = parser.parse_args()


print "here!"
r = s3g.Replicator()
print "here!"
r.file = serial.Serial(options.serialportname, 115200)
print "here!"

r.velocity = 1600

def velocity_handler(addr, tags, stuff, source):
    """
    Allow an external program to modify the movement rate
    """
    print stuff[0]
    r.velocity = stuff[0]

def move_handler(addr, tags, stuff, source):
    #print addr, tags, stuff, source
    print r.velocity

    #target = [stuff[0], stuff[1], stuff[2], stuff[3], stuff[4]]
    #velocity = stuff[5]
    x = (1 - stuff[0]) * 3000
    y = stuff[1] * 3000

    target = [x, y, 0, 0, 0]
    r.Move(target, r.velocity)

    while r.file.inWaiting() > 0:
      r.file.read()
      #print ord(r.file.read())

print "starting server"
s = OSC.OSCServer(('127.0.0.1', int(options.oscport)))
s.addDefaultHandlers()
s.addMsgHandler("/move", move_handler)
s.addMsgHandler("/velocity", velocity_handler)
st = threading.Thread(target=s.serve_forever)
st.start()

try:
    while True:
        time.sleep(0.1)        
except KeyboardInterrupt:
    exit(1)
    pass

s.close()
st.join()
