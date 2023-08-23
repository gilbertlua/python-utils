try:
    import tkinter as Tk # python 2
    import tkinter.ttk
except ModuleNotFoundError:
    import tkinter as Tk # python 3
import os
class simple_terminal_view():
    def __init__(self, root, controller):
        self.frame = Tk.Frame(root)
        self.controller = controller
        #self.printer=printer
        #self.printer.update=self.update
        self.controller.update=self.update
        self.controller.addCommand=self.addCommand
        self.controller.clearFrame=self.clearFrame
        self.controller.createField=self.createField
        self.controller.createComboBoxField=self.createComboBoxField
        self.controller.updateDiscription=self.updateDiscription
        top=self.frame.winfo_toplevel()
        self.frame.grid(padx=15, pady=15,sticky=Tk.N+Tk.S+Tk.E+Tk.W)
        top.rowconfigure(0, weight=1)
        top.rowconfigure(1, weight=10)
        top.columnconfigure(0, weight=1)
        top.columnconfigure(1, weight=5)
        self.frame.rowconfigure(1, weight=1)
        self.frame.columnconfigure(0, weight=1)
        self.frame.columnconfigure(1, weight=1)
        self.frame.pack(side=Tk.LEFT, fill=Tk.BOTH, expand=1)
        self.arrowImage=Tk.PhotoImage(file = os.path.join(os.path.dirname(os.path.abspath(__file__)),"img/arrow.gif")) 
        self.CreateWidgets()
        self.cmdindex=0
        self.logLineNo=0        
        self.entries = []
    def update(self,message):
        print("update call")      
        self.pythonTextBox.insert(Tk.INSERT, "%s\n"%message)
    def updateDiscription(self,message,cmd):    
        self.selectedCmdLabel.config(text=str(cmd))  
        self.discriptionBox.config(text=str(message))  
        
    def createMinimalCmdFrame(self):    
        self.cmdLabel = Tk.Label(self.cmdFrame, text="Command:")
        self.cmdLabel.grid(row=0, column=0, sticky=Tk.W)
        self.selectedCmdLabel = Tk.Label(self.cmdFrame)
        self.selectedCmdLabel.grid(row=1, column=0, sticky=Tk.W)
        self.cmdWrite = Tk.Button(self.cmdFrame, text="Write",image = self.arrowImage,command=lambda :self.controller.WriteSelectedCommand(self.collect_entries()))
        self.cmdWrite.grid(row=5, column=4, sticky=Tk.W)
        self.cmdSendBtn = Tk.Button(self.cmdFrame, text="Execute",command=self.execute)
        self.cmdSendBtn.grid(row=6, column=4, sticky=Tk.W)
        #self.cmdSendBtn.bind('<Button-1>', lambda x: self.controller.executeSelectedCommand())
    def execute(self):
    
        print((self.collect_entries()))
    def collect_entries(self):
        return [{name: entry.get()} for name, entry in self.entries]
    def callback(self):
        print(self.collect_entries())
    def createComboBoxField(self,labelName):
        fieldFrame=Tk.Frame(self.cmdFrame)
        fieldFrame.grid(padx=5, pady=5,row=2+self.fieldidx, column=0, columnspan=1, rowspan=1 ,sticky=Tk.N+Tk.W+Tk.S+Tk.E)
        fieldFrame.columnconfigure(1, weight=1)
        fieldFrame.columnconfigure(0, weight=1)
        label = Tk.Label(fieldFrame, text=labelName)
        label.grid(row=0, column=0, sticky=Tk.W)
        selection = Tk.StringVar() 
        selection_values = ['True',' False']
        selection.set(selection_values[1]) # this sets the Combobox to the first element of the list
        combobox = tkinter.ttk.Combobox(fieldFrame, width = 27,  values=selection_values, textvariable=selection) 
        combobox.grid(row=0, column=2, sticky=Tk.W)

        self.fieldidx=self.fieldidx+1
        self.entries.append((labelName, combobox))
    def createField(self, labelName):
        fieldFrame=Tk.Frame(self.cmdFrame)
        fieldFrame.grid(padx=5, pady=5,row=2+self.fieldidx, column=0, columnspan=1, rowspan=1 ,sticky=Tk.N+Tk.W+Tk.S+Tk.E)
        fieldFrame.columnconfigure(1, weight=1)
        fieldFrame.columnconfigure(0, weight=1)
        label = Tk.Label(fieldFrame, text=labelName)
        label.grid(row=0, column=0, sticky=Tk.W)
        textbox = Tk.Entry(fieldFrame, width = 30)
        textbox.grid(row=0, column=2, sticky=Tk.W)
        self.fieldidx=self.fieldidx+1
        self.entries.append((labelName, textbox))
        
    def clearFrame(self):
        self.fieldidx=0
        self.entries = []
        for widget in self.cmdFrame.winfo_children():
                widget.destroy()
        self.createMinimalCmdFrame()
    def addCommand(self,command):
        self.commands_list_box.insert(self.cmdindex,command)
        self.cmdindex=self.cmdindex+1
    def commandlistonClick(self,event):
        currentSelection=self.commands_list_box.curselection()
        print(currentSelection)
        selected=self.commands_list_box.get(currentSelection)
        print(selected)
        self.controller.selected(selected)
    def CreateWidgets(self):
        self.statusbar=Tk.Frame(self.frame)
        self.statusbar.grid(padx=15, pady=15,row=2, column=0, columnspan=3, rowspan=1 ,sticky=Tk.N+Tk.W+Tk.S+Tk.E)
        #self.statusbar.rowconfigure(0, weight=1)
        self.statusbar.rowconfigure(1, weight=1)
        self.statusbar.columnconfigure(0, weight=1)
                
        self.StatusbarLabel = Tk.Label(self.statusbar, text="StatusBar :")
        self.StatusbarLabel.grid(row=0, column=0, sticky=Tk.W)
        
        scrollbarV = Tk.Scrollbar(self.statusbar, orient=Tk.VERTICAL)
        scrollbarH = Tk.Scrollbar(self.statusbar, orient=Tk.HORIZONTAL)        
        self.log_list_box = Tk.Listbox(self.statusbar, selectmode=Tk.BROWSE
                                , yscrollcommand=scrollbarV.set
                                , xscrollcommand=scrollbarH.set
                                , relief=Tk.SUNKEN)
        self.log_list_box.grid(row=1, column=0,sticky=Tk.N+Tk.W+Tk.S+Tk.E)
        
        self.commandFrame=Tk.Frame(self.frame)
        self.commandFrame.grid(padx=15, pady=15,row=0, column=0, columnspan=1, rowspan=2 ,sticky=Tk.N+Tk.W+Tk.S+Tk.E)
        #self.commandFrame.rowconfigure(0, weight=1)
        self.commandFrame.rowconfigure(1, weight=1)
        self.commandFrame.columnconfigure(0, weight=1)
        
        self.listCommandLabel = Tk.Label(self.commandFrame, text="Available Command:")
        self.listCommandLabel.grid(row=0, column=0, sticky=Tk.W)
        
        scrollbarV = Tk.Scrollbar(self.commandFrame, orient=Tk.VERTICAL)
        scrollbarH = Tk.Scrollbar(self.commandFrame, orient=Tk.HORIZONTAL)
        self.commands_list_box = Tk.Listbox(self.commandFrame, selectmode=Tk.BROWSE
                                , yscrollcommand=scrollbarV.set
                                , xscrollcommand=scrollbarH.set
                                , relief=Tk.SUNKEN)
        self.commands_list_box.grid(row=1, column=0,sticky=Tk.N+Tk.W+Tk.S+Tk.E)
        
        self.commands_list_box.bind('<ButtonRelease-1>', self.commandlistonClick)
        
        self.pythonFrame=Tk.Frame(self.frame)
        self.pythonFrame.grid(padx=15, pady=15,row=0, column=2, columnspan=1, rowspan=2 ,sticky=Tk.N+Tk.W+Tk.S+Tk.E)
        #self.pythonFrame.rowconfigure(0, weight=1)
        self.pythonFrame.rowconfigure(1, weight=1)
        self.pythonFrame.columnconfigure(0, weight=1)
        
        self.pythonLabel = Tk.Label(self.pythonFrame, text="Python:")
        self.pythonLabel.grid(row=0, column=0, sticky=Tk.W)
        self.pythonTextBox = Tk.Text(self.pythonFrame)
        self.pythonTextBox.grid(row=1, column=0,sticky=Tk.N+Tk.W+Tk.S+Tk.E)

        self.cmdFrame=Tk.Frame(self.frame)
        self.cmdFrame.grid(padx=15, pady=15,row=0, column=1, columnspan=1, rowspan=1 ,sticky=Tk.N+Tk.W+Tk.S+Tk.E)
        #self.pythonFrame.rowconfigure(0, weight=1)
        #self.cmdFrame.rowconfigure(1, weight=1)
        #self.cmdFrame.columnconfigure(0, weight=0)
        self.createMinimalCmdFrame()
        self.discriptionFrame=Tk.Frame(self.frame)
        self.discriptionFrame.grid(padx=15, pady=15,row=1, column=1, columnspan=1, rowspan=1 ,sticky=Tk.N+Tk.W+Tk.S+Tk.E)
        
        self.discriptionLabel = Tk.Label(self.discriptionFrame, text="Discription:")
        self.discriptionLabel.grid(row=0, column=0, sticky=Tk.W)
        self.discriptionBox = Tk.Label(self.discriptionFrame,wraplength=250,justify=Tk.LEFT)
        self.discriptionBox.grid(row=1, column=0,sticky=Tk.N+Tk.W+Tk.S+Tk.E)
        