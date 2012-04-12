import s3g
import serial
import time

r = s3g.Replicator()
r.stream = serial.Serial('/dev/tty.usbserial-A600eosi', 115200)

while True:
  r.Move([1000,0,0,0,0], 500)
  time.sleep(1)
  while r.stream.inWaiting() > 0:
    print ord(r.stream.read())

  r.Move([1000,1000,0,0,0], 500)
  time.sleep(1)
  while r.stream.inWaiting() > 0:
    print ord(r.stream.read())

  r.Move([0,1000,0,0,0], 500)
  time.sleep(1)
  while r.stream.inWaiting() > 0:
    print ord(r.stream.read())

  r.Move([0,0,0,0,0], 500)
  time.sleep(1)
  while r.stream.inWaiting() > 0:
    print ord(r.stream.read())
