import RPi.GPIO as GPIO
import time
from multiprocessing import Process, Lock

GPIO.setmode(GPIO.BOARD)

class Button(object):
    def __init__(self, pin):
        self.mutex = Lock()
        self.pin = pin
        GPIO.setup(self.pin, GPIO.IN)
        self._pressed = False

    def toggle(self, pin):
        print "Toggle "
        with self.mutex:
            self._pressed = self._pressed ^ True
        print "Toggled " + str(self._pressed)
    
    def pressed(self):
        with self.mutex:
            return self._pressed

    def start(self):
        # what does exactly GPIO.BOTH do?
        GPIO.add_event_detect(self.pin, GPIO.RISING, callback=self.toggle, bouncetime=500)

#def setup_pins():
#    GPIO.setup(BUTTON1, GPIO.IN)
#    GPIO.setup(BUTTON2, GPIO.IN)

#def run():
#    # FIXME: add gracefull termination
#    while True:
#        if GPIO.input(BUTTON1) == GPIO.LOW:
#            print "Open"
#        else:
#            print "Close"
#        time.sleep(0.1)

def run():
    # FIXME: add gracefull termination and non-busy wait 
    while True:
        time.sleep(0.5)

def cleanup():
    print "Buttons cleanup"
    GPIO.cleanup()


if __name__ == "__main__":
    PIN1 = 16
    b1 = Button(PIN1)
    b1.start()

    #PIN2 = 18
    #b2 = Button(PIN2)
    #b2.start()
    try:
        #setup_pins()
        run()
    finally:
        # use at exit for this?
        cleanup()
#else:
#    import atexit
#    atexit.register(cleanup)
#    #FIXME: this does not handle exceptions!!!


