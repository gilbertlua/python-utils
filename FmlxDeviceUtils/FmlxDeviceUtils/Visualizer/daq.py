import time
from threading import Thread
import random
from functools import partial


class BackgroundDaq():
    def __init__(self, interval, callbackFunc,visualizrObj,running):
        self.val = 0
        self._counter = 0
        self._running = running
        self._callbackFunc = callbackFunc
        self._interval = interval
        self._visualCallback=visualizrObj

    def start(self):
        self._timerThread = Thread(target=self._loop)
        self._timerThread.daemon = True
        self._timerThread.start()

    def stop(self):
        if (not self._running):
            return
        self._running = False
        self._timerThread.join(1)
        if (self._timerThread.isAlive()):
            print('sampling thread timed-out on closing')

    def _loop(self):
        next_call = time.time()
        while self._running:
            self._update()
            next_call = next_call + self._interval
            sleeptime = next_call - time.time()
            if sleeptime > 0:
                time.sleep(sleeptime)
            else:
                next_call = time.time()

    def _update(self):
        tick = self._counter * (self._interval)
        try:
            values = self._callbackFunc()
        except Exception:
            self._counter = self._counter + 1
            return
        self._onUpdate(tick, *values)

    def _onUpdate(self,tick,*val):
        if self._visualCallback.doc != None:
            self._visualCallback.doc.add_next_tick_callback(partial(self._visualCallback.update, val))

