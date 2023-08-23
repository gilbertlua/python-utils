from multiprocessing.connection import Listener
import threading
from pyqtgraph.Qt import QtGui, QtCore
import numpy as np
import pyqtgraph as pg
import time
from datetime import datetime
import signal
import sys
from collections import deque
from queue import Queue # for thread safe queue
import argparse

class Plotter():
    PYQT_COLOR = ['r', 'g', 'b', 'c', 'm', 'y', 'k', 'w']

    def __init__(self,line_count=1,x_limit=1000,line_names = []):
        self._line_count = line_count
        self._x_limit = x_limit
        self._app = QtGui.QApplication([])
        self._lines = [] # lines per plot
        self._line_queues = []
        self._callbacks = [] # function callback that fill the data graph
        self._dataQueue = Queue()
        self._plot = pg.plot()
        self._plot.setWindowTitle('live plot')
        self._plot.addLegend()
        self._plot.showGrid(x = True, y = True, alpha = 1)
        self._isDataUpdaterThreadRunning = False
        self._PyQttimer = QtCore.QTimer()
        self._PyQttimer.timeout.connect(self.updaterDaemon)
        self._PyQttimer.start(0)

        for j in range(self._line_count):
            self._callbacks.append([])
            self._line_queues.append(deque())
            if(len(line_names)==self._line_count):
                line_name = line_names[j]
            else:
                line_name = 'line {0}'.format(j)
            self._lines.append(self._plot.plot(pen=pg.mkPen(Plotter.PYQT_COLOR[j], width=1), name=line_name))

    def SetPlotCallback(self,line_index,callback):
        if(line_index >= self._line_count):
            raise IndexError('kakehan')
        self._callbacks[line_index] = callback

    def Start(self,interval_time = 0):
        self._interval_time = interval_time
        self._isDataUpdaterThreadRunning = True
        self._data_update_thread = threading.Thread(target=self.dataUpdateThread)
        self._data_update_thread.daemon = True
        self._data_update_thread.start() 

    def Stop(self):
        self._isDataUpdaterThreadRunning = False

    def Update(self):
        data=[]
        for callback in self._callbacks:
            data += [callback()]
        self._dataQueue.put(data)

    def dataUpdateThread(self):
        while(self._isDataUpdaterThreadRunning):
            time.sleep(self._interval_time)
            self.Update()

    def updaterDaemon(self):
        if(self._dataQueue.empty()):
            return
        datas = []
        while(not self._dataQueue.empty()):
            datas.append(self._dataQueue.get())
        # print(datas)
        for data in datas:
            i = 0
            for d,line_queue in zip(data,self._line_queues):
                if(len(line_queue) > self._x_limit):
                    line_queue.popleft()
                line_queue.append(float(d))
                xdata = np.array(list(line_queue), dtype='float64')
                self._lines[i].setData(xdata)
                i+=1

        self._app.processEvents()

if __name__ == "__main__":
    # color character op pyqtgraph
    PYQT_COLOR = ['#ff0000', '#00ff00', '#7abdff', '#00ffff', '#ff00ff', '#ffff00', '#d400ff', '#ffffff']
    BCKCOLOR = None
    # plotter default configuration
    X_LIMIT = 100 # x limit
    LINE_COUNT = 1
    GRAPH_NAME = []
    PORT_NUMBER = 4300
    SHOW_LOG = False
    AXIS_COUNT = 1
    SUB_PLOTS = []
    LINE_AXIS_INDEX = []
    LINE_AXIS_ALLIGN = []
    
    # command line argument to config the plotter
    parser = argparse.ArgumentParser(
        description="Formulatrix command-line plotter")
    # common parameter
    parser.add_argument('-s', '--showLog', help="print data send into the console", action='store_true')
    parser.add_argument('-b', '--backgroundColor', help="change background color(default black)", type=int)
    
    # for single y axis
    parser.add_argument('-x', '--xlimit', help="x data limit", type=int)
    parser.add_argument('-l','--nargs_line',help="line count per window", type=int)
    parser.add_argument('-p', '--portNumber', help="port number", type=int)
    parser.add_argument('-g','--nargs_graph_name', nargs='+',help = 'for graph name')
    
    # for multiple y axis
    parser.add_argument('-m', '--multiAxes', help="multi y axis count", type=int)
    parser.add_argument('--lineAxisIndex', help="line axis index list", nargs='+', type=int)
    parser.add_argument('--lineAxisAllign', help="line axis allign select, left(0)/right(1)", nargs='+', type=int)

    args = parser.parse_args()
    if(args.xlimit):
        X_LIMIT = args.xlimit
    if(args.nargs_line):
        LINE_COUNT = args.nargs_line
    if(args.nargs_graph_name):
        for name in args.nargs_graph_name:
            GRAPH_NAME.append(name)
    if(args.portNumber):
        PORT_NUMBER = args.portNumber
    if(args.showLog):
        SHOW_LOG = True
    if(args.multiAxes):
        AXIS_COUNT = args.multiAxes
        if(args.lineAxisIndex):
            LINE_AXIS_INDEX = []
            for lineAxisIndex in args.lineAxisIndex:
                LINE_AXIS_INDEX.append(lineAxisIndex)
        # if(args.lineAxisAllign):
        #     LINE_AXIS_ALLIGN = []
        #     for lineAxisAllign in args.lineAxisAllign:
        #         LINE_AXIS_ALLIGN.append(lineAxisAllign)
        else:
            raise Exception("Specify your line axis index!")
    if(args.backgroundColor):
        BCKCOLOR = args.backgroundColor
 

    print('FMLX Plotter')
    print('Show Log : ',SHOW_LOG)
    print('Port Number : {0}'.format(PORT_NUMBER))
    print('Plot Config, X Limit : {0}, Line Count : {1}'.format(X_LIMIT,LINE_COUNT))
        
    is_running = True
    # catch sigint to stop thread


    def signal_handler(sig, frame):
        global is_running
        print('You pressed Ctrl+C!')
        is_running = False
        sys.exit(app.exec_())
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    # thread for interprocess communication
    address = ('localhost', PORT_NUMBER)     # family is deduced to be 'AF_INET'
    listener = Listener(address)
    conn = listener.accept()
    msg_queue = deque()

    #  -------------  thread handler ------
    def thread_listerner():
        global msg_queue, is_running
        while is_running:
            message = conn.recv()
            msg_queue.append(message)

    thread_handler = threading.Thread(target=thread_listerner)
    thread_handler.daemon = True
    thread_handler.start()
    # ----------------------------------

    # plot initialization -------------------
    app = QtGui.QApplication([])
    lines = [] # lines per plot
    line_queues = []  # lines data queue per plot

    if(AXIS_COUNT<1):
        plot=pg.plot()
        plot.setWindowTitle('live plot')
        plot.addLegend()
        plot.showGrid(x = True, y = True, alpha = 1) 
        for j in range(LINE_COUNT):
            # print('wkwk',j)
            if(len(GRAPH_NAME)>0):
                graph_name = GRAPH_NAME[j]
            else:
                graph_name = 'line {0}'.format(j)
            lines.append(plot.plot(pen=pg.mkPen(PYQT_COLOR[j], width=1), name=graph_name))
            line_queues.append(deque())
    elif(AXIS_COUNT>=1):
        # https://stackoverflow.com/questions/23679159/two-y-scales-in-pyqtgraph-twinx-like
        pg.mkQApp()
        pw = pg.PlotWidget()
        pw.show()
        pw.setWindowTitle('live plot')
        pw.addLegend()
        pw.showGrid(x = True, y = True, alpha = 1)
        if(BCKCOLOR): 
            pw.setBackground(BCKCOLOR)
        plot = pw.plotItem
        if(len(GRAPH_NAME)>0):
            plot.setLabels(left=GRAPH_NAME[0])
        else:
            plot.setLabels(left='axis 0')
        plot.getAxis('left').setTextPen(PYQT_COLOR[0])
        plot.showAxis('right')
        plot.getAxis('right').setPen(pg.mkPen(width=1))
        plot.addLegend()
        for i in range(AXIS_COUNT):
            SUB_PLOTS.append(pg.ViewBox())
            if(i==0):
                plot.scene().addItem(SUB_PLOTS[-1])
                plot.getAxis('right').linkToView(SUB_PLOTS[-1])
                SUB_PLOTS[-1].setXLink(plot)
                if(len(GRAPH_NAME)==0):
                    plot.getAxis('right').setLabel('axis {0}'.format(i+1), color=PYQT_COLOR[i+1])
                    plot.getAxis('right').setTextPen(PYQT_COLOR[i+1])
                else:
                    plot.getAxis('right').setLabel(GRAPH_NAME[i+1], color=PYQT_COLOR[i+1])
                    plot.getAxis('right').setTextPen(PYQT_COLOR[i+1])
            elif(i>0):
                ## this time we need to create a new axis as well.
                axis = pg.AxisItem('right')
                plot.layout.addItem(axis, 2, 3)
                plot.scene().addItem(SUB_PLOTS[-1])
                axis.linkToView(SUB_PLOTS[-1])
                SUB_PLOTS[-1].setXLink(plot)
                if(len(GRAPH_NAME)==0):
                    axis.setLabel('axis {0}'.format(i+1), color=PYQT_COLOR[i+1])
                else:
                    axis.setLabel(GRAPH_NAME[i+1], color=PYQT_COLOR[i+1])
                axis.setPen(PYQT_COLOR[i+1])
                axis.setTextPen(PYQT_COLOR[i+1])

        for j in range(LINE_COUNT):
            if(len(GRAPH_NAME)>0):
                graph_name = GRAPH_NAME[j]
            else:
                graph_name = 'line {0}'.format(j)
            if(LINE_AXIS_INDEX[j] == 0):
                lines.append(plot.plot(name = graph_name ,pen=pg.mkPen(color = PYQT_COLOR[j], width=1)))
                line_queues.append(deque())
            elif(LINE_AXIS_INDEX[j] > 0):
                lines.append(plot.plot(name=graph_name,pen=pg.mkPen(color=PYQT_COLOR[j], width=1)))
                SUB_PLOTS[LINE_AXIS_INDEX[j]-1].addItem(lines[-1])
            line_queues.append(deque())

    def updateViews():
        global SUB_PLOTS,LINE_AXIS_INDEX
        for lineAxisIndex in LINE_AXIS_INDEX:
            if(lineAxisIndex == 0):
                continue
            SUB_PLOTS[lineAxisIndex-1].setGeometry(plot.getViewBox().sceneBoundingRect())
            SUB_PLOTS[lineAxisIndex-1].linkedViewChanged(plot.getViewBox(), SUB_PLOTS[lineAxisIndex-1].XAxis)
    
    if(AXIS_COUNT>=1):
        updateViews()
        plot.getViewBox().sigResized.connect(updateViews)

    def update():
        global X_LIMIT, LINE_COUNT, AXIS_COUNT
        global lines
        global is_running
        # start = t.time()
        
        if(len(msg_queue) == 0):
            return
        while(len(msg_queue)!=0):
            msgs = msg_queue.popleft().split()
            if('exit' in msgs):
                sys.exit(QtGui.QApplication.instance().exec_())
                sys.exit(0)
                is_running = False
            if(not 'data' in msgs):
                print('invalid header! {0}'.format(msgs[0]))
                return
            msgs = msgs[1:] # shift to next message
            if(len(msgs) != LINE_COUNT):
                print('not enough data! data : {0} must be {1}'.format(len(msgs),LINE_COUNT))
                return
            if(SHOW_LOG):
                str_date = datetime.now().strftime("%Y-%m-%d,%H:%M:%S.%f")[0:-3]
                str_data = ''.join(msgs)
                print('{0}\t{1}'.format(str_date,str_data))
            for line,line_queue,msg in zip(lines,line_queues,msgs):
                if(len(line_queue) > X_LIMIT):
                    line_queue.popleft()
                line_queue.append(float(msg))
                xdata = np.array(list(line_queue), dtype='float64')
                line.setData(xdata)
        app.processEvents()
        # print('Plotting time: {}'.format(t.time() - start))

    timer = QtCore.QTimer()
    timer.timeout.connect(update)
    timer.start(0)

    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtGui.QApplication.instance().exec_()
