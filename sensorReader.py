import os, time, urllib2, httplib, csv, sys
import RPi.GPIO as GPIO

from Adafruit_CharLCD import Adafruit_CharLCD

lcd = Adafruit_CharLCD()
lcd.clear()
lcd.message("      EUPRY\n     MONITOR")

os.system('sudo modprobe w1-gpio')
os.system('sudo modprobe w1-therm')
time.sleep(10) # wait to give the 1-wire software time to find the connected sensors

GPIO.setmode(GPIO.BCM)
# Set led pin as out, and turn it of.

GPIO.setup(14, GPIO.OUT)    # Pin for alarm-LED
GPIO.setup(14, GPIO.LOW)
GPIO.setup(11, GPIO.OUT)    # Pin for Door alarm LED
GPIO.setup(11, GPIO.LOW)
GPIO.setup(9, GPIO.OUT)     # Pin for Power alarm LED
GPIO.setup(9, GPIO.LOW)
GPIO.setup(10, GPIO.OUT)    # Pin for Network-LED
GPIO.setup(10, GPIO.LOW)
#GPIO.setup(15, GPIO.OUT)    # Pin for SCREEN-LED
#GPIO.setup(15, GPIO.HIGH)
GPIO.setup(18, GPIO.OUT)    # Pin for Piezo

# Set optocoupler pin as in, where high readings means that a external power source is available.
GPIO.setup(8, GPIO.IN)      # Pin for Opto-coupler reading
GPIO.setup(7, GPIO.IN)      # Pin for door sensor reading

base_dir = '/sys/bus/w1/devices'


def get_settings():
    result = urllib2.urlopen("http://localhost/emoncms/raspberrypi/get.json")
    result = result.readline()
    result = result[1:-1].split(',')
    settings = {}
    for s in result:
        s = csv.reader([s], delimiter=':').next()
        settings[s[0]] = s[1].replace("\\", "")
    return settings


def get_device_address():
    f = open(base_dir + '/w1_bus_master1/w1_master_slaves', 'r');
    devices = f.readlines()
    f.close()
    return devices


def read_temp_raw(sensorAddress):
    device_file = base_dir + '/' + sensorAddress + '/w1_slave'
    if os.path.exists(device_file):
        f = open(device_file, 'r')
        lines = f.readlines()
        f.close()
        return lines
    return False


def read_temp(sensorAddress):
    lines = read_temp_raw(sensorAddress)

    if lines == False or lines[0].strip()[-3:] != 'YES':
        return False

    equals_pos = lines[1].find('t=')
    if lines[1][equals_pos + 2:-2] == '8500':
        return False

    return lines[1][equals_pos + 2:-2]


def updateLCD(values, devices):
    if max(values) > 800:
        temp = "ALARM %+2.2f\n" % (float(max(values)) / 100)
        index = values.index(max(values))
        mes = devices[index] + temp
    elif min(values) < 200:
        temp = "ALARM %+2.2f\n" % (float(min(values)) / 100)
        index = values.index(min(values))
        mes = devices[index] + temp
    else:
        mes = "Cur. Max:%+2.2f\n" % (float(max(values)) / 100)
        temp = "Cur. Min:%+2.2f" % (float(min(values)) / 100)
        mes += temp

    lcd.clear()
    lcd.message(mes)


def pin_reader(pin):
    reading = 0
    for i in range(100):
        reading += GPIO.input(pin)
        time.sleep(0.01)
    if reading == 100:
        return 1
    return 0


settings = get_settings()
lastDataPush = time.time()
pushFreq = 60 * 5 # Data push to database in seconds

while True:
    devices = get_device_address()
    data = ""

    values = list()
    dev = list()


    for address in devices:
        val = read_temp(address[:-1])
        if val != False:
            dev.append(address)
            values.append(int(val))
            data += address[:-1] + ":" + val + ","

    door = pin_reader(7)
    power = pin_reader(8)

    if values:
        if door == 0:
            updateLCD(values, dev)
        else:
            lcd.clear()
            lcd.message("      DOOR\n      OPEN")

        if min(values) < 200 or max(values) > 800:
            GPIO.output(14, GPIO.HIGH)
            os.system('sh /home/pi/UNICEF_VACCINE_MONITOR/piezo_alarm.sh &')
            pushFreq = 60 * 2
        else:
            GPIO.output(14, GPIO.LOW)
            pushFreq = 60 * 5

    else:
        GPIO.output(14, GPIO.LOW)
        lcd.clear()
        lcd.message("    AWAITING\n  MEASUREMENTS")


    if time.time() - lastDataPush > pushFreq:
        
        data += ("power-source:" + str(power) + ",")

        data += ("door:" + str(door))

        url1 = "http://localhost/emoncms/input/post.json?json={" + data + "}&apikey=" + settings['apikey']

        url2 = settings['remoteprotocol'] + settings['remotedomain'] + settings[
            'remotepath'] + "/input/post.json?json={" + data + "}&apikey=" + settings['remoteapikey']

        try:
            urllib2.urlopen(url1)
        except:
            print "Cannot connect to localhost!"

        try:
            urllib2.urlopen(url2)
            GPIO.output(10, GPIO.LOW)
        except:
            print "No connection to the internet!"
            lcd.clear()
            lcd.message("  NO INTERNET\n   CONNECTION")
            GPIO.output(10, GPIO.HIGH)

        lastDataPush = time.time()

    if door == 1:
        GPIO.output(11, GPIO.HIGH)

    else:
        GPIO.output(11, GPIO.LOW)
    
   # if GPIO.input(8) == 0:
	#GPIO.output(9, GPIO.HIGH)
	

    #else:
	#GPIO.output(9, GPIO.LOW)
	    

    time.sleep(15)
