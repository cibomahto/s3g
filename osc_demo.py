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

def move_handler(addr, tags, stuff, source):
    print addr, tags, stuff, source

    #target = [stuff[0], stuff[1], stuff[2], stuff[3], stuff[4]]
    #velocity = stuff[5]
    x = (1 - stuff[0]) * 3000
    y = stuff[1] * 3000

    target = [x, y, 0, 0, 0]
    velocity = 400
    r.Move(target, velocity)
    return

print "starting server"
s = OSC.OSCServer(('192.168.1.162', int(options.oscport)))
s.addDefaultHandlers()
s.addMsgHandler("/move", move_handler)
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
