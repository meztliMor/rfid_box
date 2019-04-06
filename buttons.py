import RPi.GPIO as GPIO
import time
from multiprocessing import Process, Lock, Value
import logging
logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger("btn")

GPIO.setmode(GPIO.BOARD)

class Button(object):
    def __init__(self, pin, cb=None):
        self._pin = pin
        self._pressed = Value("b", False, lock=False)
        self._mutex = Lock()
        self._cb = cb
        GPIO.setup(self._pin, GPIO.IN)

    def start(self):
        # what does exactly GPIO.BOTH do?
        #GPIO.add_event_detect(self._pin, GPIO.RISING, callback=self.toggle, bouncetime=500)
        GPIO.add_event_detect(self._pin, GPIO.RISING, callback=self._callback, bouncetime=500)

    def _callback(self, pin):
        with self._mutex:
            self._toggle(pin)
            if self._cb is not None:
                log.debug("custom callback")
                self._cb(self._pressed.value)

    def _toggle(self, pin):
        self._pressed.value = self._pressed.value ^ True
        log.debug("toggled:{v}".format(v=self._pressed.value))
    
    def pressed(self):
        with self._mutex:
            return self._pressed.value

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


