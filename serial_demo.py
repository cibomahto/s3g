import s3g
import serial
import time
import optparse


parser = optparse.OptionParser()
parser.add_option("-p", "--port", dest="portname",
                  help="serial port (ex: /dev/ttyUSB0)", default="/dev/ttyACM0")
(options, args) = parser.parse_args()


r = s3g.Replicator()
r.file = serial.Serial(options.portname, 115200)

while True:
  r.Move([1000,0,0,0,0], 500)
  time.sleep(1)
  while r.file.inWaiting() > 0:
    print ord(r.file.read())

  r.Move([1000,1000,0,0,0], 500)
  time.sleep(1)
  while r.file.inWaiting() > 0:
    print ord(r.file.read())

  r.Move([0,1000,0,0,0], 500)
  time.sleep(1)
  while r.file.inWaiting() > 0:
    print ord(r.file.read())

  r.Move([0,0,0,0,0], 500)
  time.sleep(1)
  while r.file.inWaiting() > 0:
    print ord(r.file.read())


