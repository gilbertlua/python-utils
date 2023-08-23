from Visualizer.daq import BackgroundDaq
from Visualizer.configurator import PlotConfig
from Visualizer.plotter import VisPlotter
import random


def genSample():
    num1 = random.uniform(2.1,2.4)
    num2 = random.uniform(-3, -5)
    num3 = random.uniform(-2,-3)
    num4 = random.uniform(0,-2)
    return [num1,num2,num3,num4]

config = PlotConfig()
config.add_plot('Plotting Test',2,['Sensor 1','Sensor 2'],0,'Time','Current',[-5,5,-10,10],[0,500])
config.add_plot('Ext Y',2,['Source 1','Source 2'],1,'Time','Volt',[-5,5,-10,10],[0,500])
visualizr = VisPlotter(genSample,config.plot(),"Test",True,0.0001,True)
visualizr.Start()
