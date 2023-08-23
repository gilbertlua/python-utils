import os
import pip
import json
from copy import deepcopy

#-----------------------------dependecy lists------------------------------------------
dep_filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), './dependencies.json')
with open(dep_filepath,'r') as dep_file:
    dep_list = json.load(dep_file)

required_deps = dep_list['general']

if os.name == 'nt':
    required_deps += dep_list['windows']
elif os.name == 'posix':
    required_deps += dep_list['unix-like']

#---------------------------dependecy processing----------------------------------------

#check if dependencies installed
installed_deplist = []
diffver_deps = []
for pkg in pip.get_installed_distributions():
    for dep in required_deps:
        dep_status = {
            'name'   : dep['name'], 
            'version': dep['version']
        }
        
        if dep_status['name'].lower() == pkg.project_name.lower():
            if dep_status['version'] != '' and dep_status['version'] != pkg.version:
                dep_status.update({'curversion' : pkg.version})
                diffver_deps.append(deepcopy(dep_status))
            
            installed_deplist.append(dep_status['name'])

missing_deps = [dep for dep in required_deps if dep['name'] not in installed_deplist]


#check wrong version dependencies
if diffver_deps:
    warntext = 'You have wrong version dependencies installed, please uninstall first:\n'
    for dep in diffver_deps:
        warntext += '- {} should be ver. {}, installed package is ver. {}\n'.format(
                        dep['name'], dep['version'], dep['curversion'])

    raise Warning(warntext)


#check if there's any missing dependencies
if not missing_deps:
    print 'All of the dependencies are already installed'
    quit()


#install missing dependencies
if os.name == 'nt': 
    #windows
    install_cmd = 'pip install'
elif os.name == 'posix':
    #unix-like
    install_cmd = 'sudo pip install'

for dep in missing_deps: 
    if dep['name'].lower() == 'pythonnet' and os.name == 'posix':
        #temporary workaround for pythonnet 2.3.0 installation bug
        print 'current pythonnet installation in Raspi is not supported due to pythonnet 2.3.0 bug'
        print 'please copy a Raspi image from SE department or'
        print 'try checking https://github.com/pythonnet/pythonnet/wiki/Installation'
    else:
        if dep['version']:
            pkg_name = ' {}=={}'.format(dep['name'], dep['version'])
        else:
            pkg_name = ' {}'.format(dep['name'])
        os.system(install_cmd + pkg_name)
