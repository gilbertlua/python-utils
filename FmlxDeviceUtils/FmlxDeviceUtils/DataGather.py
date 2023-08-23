import numpy as np
import csv
import os

class CDataGatherer():
    
    def __init__(self,NumOfData):
        self.__numOfData=NumOfData
        self.__data=[]
        self.__std=[]
        self.__avg=[]
        self.__max=[]
        self.__min=[]
        self.__delta=[]
        for i in range(self.__numOfData):
            self.__data+=[[]]
            self.__std+=[[]]
            self.__avg+=[[]]
            self.__max+=[[]]
            self.__min+=[[]]
            self.__delta+=[[]]
        
    def __del__(self):
        print 'buhbyee'
        pass

    def AddData(self,index,data):
        self.__data[index]+=[data]
        pass

    def ReadData(self,index=0):
        return self.__data[index]

    def CreateCsv(self,filename,headerString='',increment=1,isPrinting=0):
        dataCount=[]
        for i in range(self.__numOfData):
            dataCount+=[len(self.__data[i])]
        i=0
        while(increment):
            incFilename='{}{}.csv'.format(filename,i)
            if(os.path.isfile(incFilename)):
                i+=1
            else:
                break
        else:
            incFilename='{}.csv'.format(filename)
        file = open(incFilename,'w')
        file.write('no,')
        file.write(headerString)
        file.write('\n')
        dataCount=np.max(dataCount)
        for i in range(dataCount-1):
            file.write('%s,'%str(i+1)) # no
            for j in range(self.__numOfData):
                try:
                    file.write('%s,'%self.__data[j][i])
                except IndexError:
                    file.write(',')
            file.write('\n')

        for i in range(self.__numOfData):	
            self.__std[i]=np.std(self.__data[i])
            self.__avg[i]=np.average(self.__data[i])
            self.__max[i]=np.max(self.__data[i])
            self.__min[i]=np.min(self.__data[i])
            self.__delta[i]=self.__max[i]-self.__min[i]	

        file.write('standar dev,')
        for i in range(self.__numOfData):	
            file.write('%s,'%self.__std[i])
        file.write('\naverage,')
        for i in range(self.__numOfData):	
            file.write('%s,'%self.__avg[i])
        file.write('\nmax,')
        for i in range(self.__numOfData):	
            file.write('%s,'%self.__max[i])
        file.write('\nmin,')
        for i in range(self.__numOfData):	
            file.write('%s,'%self.__min[i])
        file.write('\nmax-min,')
        for i in range(self.__numOfData):	
            file.write('%s,'%self.__delta[i])
        file.close()
        
        if(isPrinting):
            print 'std :',
            for i in range(self.__numOfData):	
                print self.__std[i],
            print ''
            
            print 'avg :',
            for i in range(self.__numOfData):	
                print self.__avg[i],
            print ''

            print 'max :',
            for i in range(self.__numOfData):	
                print self.__max[i],
            print ''

            print 'min :',
            for i in range(self.__numOfData):	
                print self.__min[i],
            print ''

            print 'delta :',
            for i in range(self.__numOfData):	
                print self.__delta[i],
            print ''


