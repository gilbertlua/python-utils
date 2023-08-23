import time
import os
import sys
import fnmatch
import argparse

def search_hex():
	i=0
	filelist=[]
	listOfFiles = os.listdir('.')  
	pattern = "*.hex"  
	for entry in listOfFiles:  
		if fnmatch.fnmatch(entry, pattern):
				# i+=1
				# print i,'.',entry
				if('bootloader' in entry):
					pass
				else:
					filelist+=[entry]
	return filelist


def getPath(isLoad = True,window_title = None):
	if(sys.version_info[0] >= 3):
		import tkinter as tk
		from tkinter import filedialog
	else:
		import Tkinter as tk
		import tkFileDialog as filedialog
	root = tk.Tk()
	root.withdraw()
	if(isLoad):
		return filedialog.askopenfilename(title=window_title)
	else:
		return filedialog.asksaveasfile(title=window_title).name

# command line argument to config the plotter
parser = argparse.ArgumentParser(
    description="Formulatrix command-line plotter")
parser.add_argument('-b', '--boot_path', help="bootloader path", type=str, nargs='?')
parser.add_argument('-a', '--app_path', help="app path", type=str, nargs='?')
parser.add_argument('-f', '--flash', help="flash it using st link utility", type=int, nargs='?')

args = parser.parse_args()
if(args.boot_path == None):
	print('Input Your Bootloader File : ')
	boot_path = getPath(True,'Bootloader File')
	boot_path_quot_mark = '\"'+boot_path+'\"'
	if(not ('BOOTLOADER' in boot_path)):
		print('invalid file')
		exit()
else:
	boot_path = args.boot_path
	boot_path_quot_mark = '\"'+boot_path+'\"'
print('bootloader path : {0}'.format(boot_path_quot_mark))

if(args.app_path == None):
	print('choose your Application file : ')
	app_path = getPath(True,'Application file')
	app_path_quot_mark = '\"'+app_path+'\"'
else:
	app_path = args.app_path
	app_path_quot_mark = '\"'+app_path+'\"'
print('Application path : {0}'.format(app_path_quot_mark))

bootloader_command = 'srec_cat '+boot_path_quot_mark+' -intel ' 
application_command = app_path_quot_mark+' -intel -o '
merged_hex_file =  '\"'+app_path[0:-4]+'_BOOTLOADER.hex'+'\"'

merger_command = bootloader_command+application_command+merged_hex_file + ' -intel'

os.system(merger_command)

print('\nMerged into \"' + merged_hex_file)

if(args.flash == None):
	if(sys.version_info[0] < 3):
		do_flash = raw_input('\nWould also like to flash it into MCU? (Y/N)')
	else:
		do_flash = input('\nWould also like to flash it into MCU? (Y/N)')
else:
	if(args.flash > 0):
		do_flash = 'y'
	else:
		do_flash = 'n'
if (do_flash=='Y' or do_flash=='y'):
	flash_command="ST-LINK_CLI.exe -c SWD -p  "+ merged_hex_file + " -Rst"
	os.system(flash_command)

time.sleep(2)