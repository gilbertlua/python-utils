from bokeh.plotting import figure
from bokeh.models import LinearAxis, Range1d, HoverTool, ColumnDataSource, Legend
from bokeh.layouts import gridplot, column, row
from bokeh.models.widgets import CheckboxGroup, Div
from bokeh.io import curdoc
from bokeh.server.server import Server
from tornado import gen
from Visualizer.daq import BackgroundDaq

lineColor = ['black','firebrick','blue','red','indigo','green','gainsboro']

class VisPlotter:
    def __init__(self, callbackFunc, config, title='Plot Result',running=True,interval=0.1,logging=False):
        self._plot = []
        self.lineCnt= []
        self.dataSource = {}
        self.config = config
        self.logging = logging
        self.rollover=0
        self.text1 = Div(text='<h1 style="color:blue">{}</h1>'.format((title)), width=900, height=50)
        self.running = running
        self.callbackFunc = callbackFunc
        self.hover = HoverTool(
                tooltips=[
                    ("index", "$index"),
                    ("(x,y)", "($x, $y)")
                ]
            )
        self.tools = "pan,box_zoom,wheel_zoom,reset"
        #self.plot_options = dict( plot_height=400,plot_width=900,tools=[self.hover, self.tools])
        self.plot_options = dict(plot_height=400,tools=[self.hover, self.tools])
        self.updateValue = True
        self.doc = None
        self.source, self.pAll = self.createPlot(config)
        self.prev_y1 = 0
        self._daq= BackgroundDaq(interval,callbackFunc,self,running)

    def createPlot(self,config):            #create plot based on configurator
        for i in range(len(config)):
            p = figure(**self.plot_options, title=config[i]['axtitle'])
            plot_type = config[i]['axtype']
            axrange = config[i]['axrange']
            if plot_type==1:
                xLabel,yLabel=config[i]['axlabel']
                p.yaxis.axis_label = yLabel
                p.xaxis.axis_label = xLabel
                yrange_min, yrange_max, xrange_min, xrange_max = axrange
                p.y_range = Range1d(start=yrange_min, end=yrange_max)
            else:
                xLabel, yLabel,y2label = config[i]['axlabel']
                p.yaxis.axis_label = yLabel
                p.xaxis.axis_label = xLabel
                yrange_min, yrange_max, y2range_min,y2range_max, xrange_min, xrange_max = axrange
                p.extra_y_ranges = {"class": Range1d(start=y2range_min, end=y2range_max)}
                p.add_layout(LinearAxis(y_range_name="class", axis_label=y2label), 'right')
            line = config[i]['axline']
            lineCount = config[i]['axlinecount']
            self.rollover=xrange_max
            self.dataSource['x'+str(i)] = [0]
            for j in range(lineCount):
                self.dataSource['y'+str(i)+str(j)]=[0]
            self._plot.append(p)
            self.lineCnt.append(lineCount)
        print(self.dataSource)
        source = ColumnDataSource(data=self.dataSource)
        k=0
        allPlot=[]

        for plot in self._plot:
            lineCnt= self.lineCnt[k]
            lines=[]
            for l in range (lineCnt):
                line=plot.line(x='x'+str(k),y='y'+str(k)+str(l),source=source,color=lineColor[k+l],line_width=2,legend_label=config[k]['axline'][l])
            k+=1
            allPlot.append(plot)

        pAll = column(self._plot,sizing_mode="stretch_width")
        return source,pAll

    def bkapp(self,doc):
        layout = column(self.text1, row(self.pAll),sizing_mode="stretch_width")
        doc.title = "Fmlx Plotting"
        doc.add_root(layout)
        self.doc = doc

    def getDoc(self):
        return self.doc

    @gen.coroutine
    def update(self, val):
        newData = dict()
        if self.updateValue:
            k=0
            for i in range (len(self._plot)):
                newX = self.source.data['x'+str(i)][-1]+1
                newData['x'+str(i)] = [newX]
                for j in range(self.lineCnt[i]):
                    newY = val[k]
                    newData['y'+str(i)+str(j)] = [newY]
                    k+=1
        if self.logging==True:
            print(newData)
        self.source.stream(newData,rollover=self.rollover)



    def Start(self):
        self._daq.start()
        self.server = Server({'/': self.bkapp}, num_procs=1)
        self.server.start()
        print('Opening Bokeh application on http://localhost:5006/')

        self.server.io_loop.add_callback(self.server.show, "/")
        self.server.io_loop.start()

    def Stop(self):
        self._daq.stop()
        self.server.stop()
        self.server.io_loop.stop()