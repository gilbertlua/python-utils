class PlotConfig():
    def __init__(self):
        self._plotCount = 0
        self._plot = []


    def add_plot(self,title,linecount,line_name,dual_y, x_label,y_label, y_range, x_range,y_label_ext=''):
        newline = {}
        newline['axtitle'] = title
        if dual_y:
            newline['axtype'] = 2
            newline['axrange'] = y_range[0], y_range[1], y_range[2],y_range[3], x_range[0],x_range[1]
            newline['axlabel'] = x_label, y_label,y_label_ext
        else:
            newline['axtype'] = 1
            newline['axrange'] = y_range[0], y_range[1], x_range[0],x_range[1]
            newline['axlabel']= x_label,y_label
        lineName=[]
        for i in range(linecount):
            lineName.append(line_name[i])
        newline['axline'] = lineName
        newline['axlinecount']=linecount
        self._plot.append(newline)

    def plot(self):
        return self._plot
