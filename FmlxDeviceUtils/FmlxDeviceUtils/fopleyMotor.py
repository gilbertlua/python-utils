import time
import math
import fopleyUtilities as fu
from functools import partial
import logging
import FmlxLogger

class CFopleyMotorModular():
    
    class MotorError(Exception):
        def __init__(self, value):
            self.value = value

        def __str__(self):
            return repr(self.value)

    def read_driver_status(self):
        return fu.decode_driver_status(self._d.read_driver_status(self._id))

    def get_encoder_position(self):
        return self.get_encoder_position_raw()/self._eng_value

    def get_encoder_position_raw(self):
        return self._d.get_encoder_position(self._id)

    def get_motor_limits(self):
        return self._d.get_motor_limits(self._id)
    
    def set_motor_limits(self,min_limit,max_limit):
        self._d.set_motor_limits(self._id,min_limit,max_limit)

    def get_motor_pos(self):
        return self.get_motor_pos_raw()/self._eng_value
        
    def get_motor_pos_raw(self):
        return self._d.get_motor_pos(self._id)['curr_pos']

    def get_motor_currents(self):   
        return self._d.get_motor_currents(self._id)

    def set_motor_currents(self,boost,travel,hold):   
        self._d.set_motor_currents(self._id,boost,travel,hold)

    def set_fol_error_config(self,is_tracking_enabled,max_fol_error):
        self._d.set_fol_error_config(self._id,is_tracking_enabled, max_fol_error)

    def get_fol_error_config(self):
        return self._d.get_fol_error_config(self._id)

    def get_encoder_correction_enable(self):
        return self._d.get_encoder_correction_enable(self._id)

    def set_encoder_correction_enable(self,enable):
        self._d.set_encoder_correction_enable(self._id,enable)

    def get_motor_enabled(self):
        return self._d.get_motor_enabled(self._id)

    def set_motor_enabled(self,enable):
        self._d.set_motor_enabled(self._id,enable)

    def move_motor_abs(self,pos,vel=None,accel=None,jerk=None):
        pos = pos*self._eng_value
        if(vel!=None):
            vel = vel*self._eng_value
        else:
            vel = self.DefaultMoveVelocity*self._eng_value
        if(accel!=None):
            accel = accel*self._eng_value
        else:
            accel = self.DefaultMoveAcc*self._eng_value
        if(jerk!=None):
            jerk = jerk*self._eng_value
        else:
            jerk = self.DefaultMoveJerk*self._eng_value
        
        stat=self._d.move_motor_abs(self._id,pos,vel,accel,jerk)
        self._logger.debug('motor {0} move abs, status : {1}'.format(self._device_name,fu.decode_motor_error(stat))) 
        self._move_done=0
        if(stat==16):
            self._move_done=1
        if(stat == 0 or stat == 16):
            self._motor_error=0 # clear fault
        else: # motor error
            self._motor_error=1
            raise CFopleyMotorModular.MotorError(fu.decode_motor_error(stat))
        return stat
            
    def move_motor_rel(self,distance,vel=None,accel=None,jerk=None):
        distance = distance*self._eng_value
        if(vel!=None):
            vel = vel*self._eng_value
        else:
            vel = self.DefaultMoveVelocity*self._eng_value
        if(accel!=None):
            accel = accel*self._eng_value
        else:
            accel = self.DefaultMoveAcc*self._eng_value
        if(jerk!=None):
            jerk = jerk*self._eng_value
        else:
            jerk = self.DefaultMoveJerk*self._eng_value
        pos = self._d.get_motor_pos(self._id)['curr_pos']
        try:
            stat=self._d.move_motor_abs(self._id,pos+distance,vel,accel,jerk)
        except TypeError:
            stat=self._d.move_motor_abs(self._id,pos+distance,vel,accel) # old API
        
        self._logger.debug('motor {0} move rel, status : {1}'.format(self._device_name,fu.decode_motor_error(stat)))

        self._move_done=0
        if(stat==16): # mecnomove
            self._move_done=1
        if(stat == 0 or stat == 16):
            self._motor_error=0 # clear fault
        else: # motor error
            self._motor_error=1
            raise CFopleyMotorModular.MotorError(fu.decode_motor_error(stat))
        return stat

    def move_motor_vel(self,forward,vel=None,accel=None,jerk=None,isContinous = False):
        if(vel!=None):
            vel = vel*self._eng_value
        else:
            vel = self.DefaultMoveVelocity*self._eng_value
        if(accel!=None):
            accel = accel*self._eng_value
        else:
            accel = self.DefaultMoveAcc*self._eng_value
        if(jerk!=None):
            jerk = jerk*self._eng_value
        else:
            jerk = self.DefaultMoveJerk*self._eng_value
        try:
            stat=self._d.move_motor_vel(self._id,forward,vel,accel,jerk,isContinous)
        except TypeError:
            stat=self._d.move_motor_vel(self._id,forward,vel,accel)
            
        self._logger.debug('motor {0} move vel, status : {1}'.format(self._device_name,fu.decode_motor_error(stat)))
        self._move_done=0
        if(stat==16):
            self._move_done=1
        if(stat == 0 or stat == 16):
            self._motor_error=0 # clear fault
        else: # motor error
            self._motor_error=1
            raise CFopleyMotorModular.MotorError(fu.decode_motor_error(stat))
        return stat
            
    def stop_motor(self,dec=None,jrk=None):
        if(dec==None):
            dec = self.DefaultStopDeceleration
        if(jrk==None):
            jrk = self.DefaultStopJerk
        try:
            stat=self._d.stop_motor(self._id,dec,jrk)
        except TypeError:
            stat=self._d.stop_motor(self._id,dec) # old API
        self._logger.debug('stop motor {0}, status : {1}'.format(self._device_name,fu.decode_motor_error(stat)))
        return stat

    def home_motor(self,flag= None , pos_edge = None ,pos_dir = None,slow_vel = None,fast_vel = None,accel = None, jerk= None):
        if(slow_vel!=None):
            slow_vel = slow_vel*self._eng_value
        else:
            slow_vel = self.DefaultHomeSlowVel * self._eng_value
        if(fast_vel!=None):
            fast_vel = fast_vel*self._eng_value
        else:
            fast_vel = self.DefaultHomeFastVelocity * self._eng_value
        if(accel !=None):
            accel = accel*self._eng_value
        else:
            accel = self.DefaultHomeAccel * self._eng_value
        if(flag==None):
            flag = self.DefaultHomeFlag
        if(pos_edge == None):
            pos_edge = self.DefaultHomePosEdge
        if(pos_dir == None):
            pos_dir = self.DefaultHomePosDir
        
        try:
            stat=self._d.home_motor(self._id,flag,pos_edge,pos_dir,slow_vel,fast_vel,accel,jerk)
        except TypeError:
            stat=self._d.home_motor(self._id,flag,pos_edge,pos_dir,slow_vel,fast_vel,accel) # old API

        self._logger.debug('motor {0} home, status : {1}'.format(self._device_name,fu.decode_motor_error(stat)))
        self._home_done=0
        if(stat==16): # mecnomove
            self._home_done=1
        if(stat == 0 or stat == 16):
            self._motor_error=0 # clear fault
        else: # motor error
            self._motor_error=1
            raise CFopleyMotorModular.MotorError(fu.decode_motor_error(stat))
        return stat

    def home(self):
        return self.home_motor(self.DefaultHomeFlag,self.DefaultHomePosEdge,self.DefaultHomePosDir,self.DefaultHomeSlowVel,self.DefaultHomeFastVelocity,self.DefaultHomeAccel,self.DefaultHomeJerk)

    def get_home_offset(self):
        return self._homing_offset

    def clear_fault(self):
        self._motor_error=0 # clear fault
        self._d.clear_motor_fault(self._id)
            
    def wait_move(self,timeout = 0):
        if(timeout==0):
            while(self._move_done==0):
                time.sleep(0.01)
            return True
        else:
            start_time = time.time()
            while(self._move_done==0):
                time.sleep(0.01)
                if((time.time() - start_time) > timeout):
                    return False
                if(self._motor_error==1):
                    self._motor_error=0 # clear fault
                    return False
            return True

    def wait_home(self,timeout = 0):
        if(timeout==0):
            while(self._home_done==0):
                time.sleep(0.01)
            return True
        else:
            start_time = time.time()
            while(self._home_done==0):
                time.sleep(0.01)
                if((time.time() - start_time) > timeout):
                    return False
                if(self._motor_error==1):
                    self._motor_error=0 # clear fault
                    return False
            return True
            
    def get_motor_status(self):
        self._logger.debug('motor',self._device_name,':',fu.decode_motor_status(self._d.get_motor_status(self._id)))

    def get_motor_status_raw(self):
        return self._d.get_motor_status(self._id)

    # motor handler -------------
    def handle_motor_error_occured(self,**kwargs):
        if(kwargs['motor_id']!=self._id):
            return
        self._motor_error = 1
        self._logger.debug('motor : {0} error : {1}'.format(self._device_name,fu.decode_motor_error(kwargs['motor_error_code'])))

    def handle_motor_move_done(self,**kwargs):
        if(kwargs['motor_id']!=self._id):
            return
        self._move_done=1
        self._logger.debug('motor : {0}, done status : {1}, pos :{2}'.format(self._device_name,fu.decode_motor_status(kwargs['status']),kwargs['position']))

    def handle_motor_home_done(self,**kwargs):
        if(kwargs['motor_id']!=self._id):
            return
        self._home_done=1
        self._homing_offset = kwargs['home_pos']
        self._logger.debug('motor : {0} homed, pos offset : {1} pos {2}'.format(self._device_name,kwargs['home_pos'],kwargs['pos']))
        
    def handle_motor_move_started(self,**kwargs):
        if(kwargs['motor_id']!=self._id):
            return
        self._logger.debug('motor : {0} started'.format(self._device_name))

    def handle_velocity_reach(self,**kwargs):
        if(kwargs['motor_id']!=self._id):
            return
        self._logger.debug('motor',self._device_name,'vel :',kwargs['velocity'])
    
    VERSION = '1.0.0'
    def __init__(self,fmlx_device,motor_id,device_name,eng_value=1,show_log=1,log_handler = None):
        self._logger = logging.getLogger('FopleyMotorModular_{0}{1}'.format(device_name,motor_id))
        self._logger.setLevel(logging.DEBUG)
        if(log_handler):
            self._logger.addHandler(log_handler)
        if(show_log):
            self._logger.addHandler(FmlxLogger.CreateConsoleHandler(logLevel=logging.DEBUG))
        self._logger.info('FopleyMotorModular version : {0}, name :{1}'.format(CFopleyMotorModular.VERSION,device_name,motor_id))
        
        self._d=fmlx_device
        self._device_name = device_name
        self._eng_value = eng_value
        self._move_done=0
        self._home_done=0
        self._motor_error=0
        self._id = motor_id
        self._save_log = False

        self._homing_offset = 0

        # event handler
        self._d.motor_error_occured+= self.handle_motor_error_occured
        self._d.motor_move_done+= self.handle_motor_move_done
        self._d.motor_home_done+= self.handle_motor_home_done
        self._d.motor_move_started+= self.handle_motor_move_started
        # self._d.on_motor_velocity_reached += self.handle_velocity_reach

        # configurable default value
        self.DefaultMoveVelocity = 1000
        self.DefaultMoveAcc = 16383
        self.DefaultMoveJerk = 65535
        self.DefaultStopDeceleration = 16383
        self.DefaultStopJerk = 65535
        self.DefaultHomeFlag = 0
        self.DefaultHomePosEdge = 1
        self.DefaultHomePosDir = 0
        self.DefaultHomeSlowVel = 50
        self.DefaultHomeFastVelocity = 100
        self.DefaultHomeAccel = 1000
        self.DefaultHomeJerk = 1000

    def set_default_home_command(self,flag,pos_edge,pos_dir,slow_vel,fast_vel,accel,jerk=65000):
        self.DefaultHomeFlag = flag
        self.DefaultHomePosEdge = pos_edge
        self.DefaultHomePosDir = pos_dir
        self.DefaultHomeSlowVel = slow_vel
        self.DefaultHomeFastVelocity = fast_vel
        self.DefaultHomeAccel = accel
        self.DefaultHomeJerk = jerk


class CFopleyMotor():

    def get_motor_pos(self,id):
        return self.get_motor_pos_raw(id)/self.__eng_value[id]
        
    def get_motor_pos_raw(self,id):
        return self.t.get_motor_pos(id)['curr_pos']

    def move_motor_abs(self,id,pos,vel=100,accel=16383,jerk=65535):
        pos = pos*self.__eng_value[id]
        vel = vel*self.__eng_value[id]
        accel = accel*self.__eng_value[id]
        jerk = jerk*self.__eng_value[id]
        if(self.__old_device==0):
            stat=self.t.move_motor_abs(id,pos,vel,accel,jerk)
        else:
            stat=self.t.move_motor_abs(id,pos,vel,accel)
        print (fu.decode_motor_error(stat))
        self.__move_done=0
        self.__move_done_mult[id]=0
        if(stat==16):
            self.__move_done=1
            self.__move_done_mult[id]=1

    def move_mult_motor_abs(self,id,pos,vel,acc,jerk=1):
        l=len(id)
        for i in range(l):
            pos[i] = pos[i]*self.__eng_value[id[i]]
            vel[i] = vel[i]*self.__eng_value[id[i]]
            acc[i] = acc[i]*self.__eng_value[id[i]]
            jerk[i] = jerk[i]*self.__eng_value[id[i]]

        stat=self.t.move_multi_motor_abs(l,id,pos,vel,acc)
        for i in range(l):
            print (id[i],fu.decode_motor_error(stat[i]))
            if(stat[i]!=0):
                self.__move_done=1
                self.__move_done_mult[id[i]]=1
            else:
                self.__move_done=0
                self.__move_done_mult[id[i]]=0

    def move_mult_motor_rel(self,id,distance,vel,acc,jerk):
        for i,j in enumerate(id):
            distance[i] = distance[i]*self.__eng_value[j]
            pos = self.get_motor_pos_raw(j)
            distance[i] = pos+distance[i]
            vel[i] = vel[i]*self.__eng_value[j]
            acc[i] = acc[i]*self.__eng_value[j]
        
        stat=self.t.move_multi_motor_abs(len(id),id,distance,vel,acc)

        for i,j in enumerate(id):
            print (j,fu.decode_motor_error(stat[i]))
            if(stat[i]!=0):
                self.__move_done=1
                self.__move_done_mult[j]=1
            else:
                self.__move_done=0
                self.__move_done_mult[j]=0

    def move_motor_rel(self,id,distance,vel=100,accel=16383,jerk=65535):
        distance = distance*self.__eng_value[id]
        jerk = jerk*self.__eng_value[id]
        vel = vel*self.__eng_value[id]
        accel = accel*self.__eng_value[id]
        pos = self.get_motor_pos_raw(id)

        if(self.__old_device==0):
            stat=self.t.move_motor_abs(id,pos+distance,vel,accel,jerk)
        else:
            stat=self.t.move_motor_abs(id,pos+distance,vel,accel)
        print (fu.decode_motor_error(stat))
        self.__move_done=0
        self.__move_done_mult[id]=0
        if(stat==16): # mecnomove
            self.__move_done=1
            self.__move_done_mult[id]=1

    def stop_motor(self,id,dec=16383,jrk=65535):
        self.t.stop_motor(id,dec,jrk)

    def home(self,id,flag,pos_edge,pos_dir,slow_vel,fast_vel,accel,jerk=1):
        slow_vel = slow_vel*self.__eng_value[id]
        fast_vel = fast_vel*self.__eng_value[id]
        accel = accel*self.__eng_value[id]
        if(self.__old_device==0):
            stat=self.t.home_motor(id,flag,pos_edge,pos_dir,slow_vel,fast_vel,accel,jerk)
        else:
            stat=self.t.home_motor(id,flag,pos_edge,pos_dir,slow_vel,fast_vel,accel)
        print (fu.decode_motor_error(stat))
        self.__home_done=0
        self.__home_done_mult[id]=0
        if(stat==16): # mecnomove
            self.__home_done=1
            self.__home_done_mult[id]=1
            
    def clear_fault(self):
        self._motor_error=0 # clear fault
        for i in range(self.__motor_count):
            self.t.clear_motor_fault(i)
            
    def wait_move(self):
        while(self.__move_done==0):
            time.sleep(0.01)

    def wait_move_mult(self,id_list):
        for i in id_list:
            while (self.__move_done_mult[i]==0):
                time.sleep(0.01)

    def wait_home(self):
        while(self.__home_done==0):
            time.sleep(0.01)

    def wait_home_mult(self,id_list):
        for i in id_list:
            while (self.__home_done_mult[i]==0):
                time.sleep(0.01)
            
    def add_queue(self,motor_id,pos,vel,acc,wait_done=1,duration=0,relative=0):
        for i,j in enumerate(motor_id):
            pos[i] = pos[i]*self.__eng_value[j]
            vel[i] = vel[i]*self.__eng_value[j]
            acc[i] = acc[i]*self.__eng_value[j]
            # print j,pos[i],vel[i],acc[i]

        # print wait_done,duration
        stat=self.t.queue_move(self.__queue_id,duration,relative,wait_done,len(motor_id),motor_id,pos,vel,acc,[0]*len(motor_id))
        print (fu.decode_motor_error(stat['error_code']),stat['remaining_count'])
        if(stat==0):
            # implement circular queue
            self.__queue_id+=1
            # self.__queue_id%=100

    def reset_move_done(self):
        self.__move_done=0
        for i in range(self.__motor_count):
            self.__move_done_mult[i]=0

    def add_queue_wait(self,duration=0):
        self.t.queue_wait_susbcribe(self.__queue_id,duration)
        self.__queue_id+=1

    def add_queue_go(self,duration=0):
        self.t.queue_publish_go(self.__queue_id,duration)
        self.__queue_id+=1

    def abort_queue(self):
        self.t.sequencer_abort()

    def clear_queue(self):
        self.t.sequencer_clear()
        self.__queue_id=0

    def start_queue(self):
        self.__queue_finish=0
        self.t.start_sequencer()

    def wait_queue(self):
        while(self.__queue_id>0):
            time.sleep(0.01)

    def wait_all_queue(self):
        while(self.__queue_finish==0):
            time.sleep(0.01)
        self.__queue_finish=0

    def get_status(self):
        for i in range(self.__motor_count):
            print ('motor',i,':',fu.decode_motor_status(self.t.get_motor_status(i)))
            
    def set_sub_addr(self,addr): 
        self.t.set_subscribe_address(addr) 

    # motor handler -------------
    def handle_motor_error_occured(self,motor_id,motor_error_code):
        if(self.__show_log):
            print (self.__device_name,'motor',motor_id, 'error :',fu.decode_motor_error(motor_error_code))
        if(self.__save_log):
            #todo implement log file save
            pass
        
    def handle_motor_move_done(self,motor_id,status,position):
        self.__move_done=1
        self.__move_done_mult[motor_id]=1
        if(self.__show_log):
            print (self.__device_name,'motor done',motor_id,' status :',fu.decode_motor_status(status),'pos :',position)
        if(self.__save_log):
            #todo implement log file save
            pass

    def handle_motor_home_done(self,motor_id,home_pos,pos):
        self.__home_done=1
        self.__home_done_mult[motor_id]=1
        if(self.__show_log):
            print (self.__device_name,'motor home',motor_id,'pos:',home_pos,'pos:',pos)
        if(self.__save_log):
            #todo implement log file save
            pass

    def handle_motor_move_started(self,motor_id):
        if(self.__show_log):
            print (self.__device_name,'motor started:',motor_id)
        if(self.__save_log):
            #todo implement log file save
            pass

    def handle_on_sequencer_item_run(self,id):
        if(self.__show_log):
            print (self.__device_name,'seq run:',id)
        if(self.__save_log):
            #todo implement log file save
            pass

    def handle_on_sequencer_item_finish(self,id):
        if(self.__queue_id>0):
            self.__queue_id-=1
        if(self.__show_log):
            print (self.__device_name,'seq item finished:',id)
        if(self.__save_log):
            #todo implement log file save
            pass

    def handle_on_sequencer_all_finish(self):
        self.__queue_finish=1
        if(self.__show_log):
            print (self.__device_name,'all seq finished')
        if(self.__save_log):
            #todo implement log file save
            pass		

    def handle_on_sequencer_fault(self,id,uncompleted_count):
        if(self.__show_log):
            print (self.__device_name,'seq fault:',id,'count:',uncompleted_count)
        if(self.__save_log):
            #todo implement log file save
            pass
        
    def __init__(self,fmlx_device,motor_count,device_name,eng_value_list,show_log=0,save_log=0,old_device=0):
        self.t=fmlx_device
        self.__device_name = device_name
        self.__motor_count = motor_count
        self.__eng_value = eng_value_list
        self.__move_done=0
        self.__move_done_mult=[0]*motor_count
        self.__home_done=0
        self.__home_done_mult=[0]*motor_count
        self.__queue_id=0
        self.__show_log=show_log
        self.__save_log=save_log
        self.__old_device=old_device
        self.__queue_finish=0

        # event handler
        self.t.motor_error_occured+= self.handle_motor_error_occured
        self.t.motor_move_done+= self.handle_motor_move_done
        self.t.motor_home_done+= self.handle_motor_home_done
        self.t.motor_move_started+= self.handle_motor_move_started
        # if(self.__old_device==0):
        #     self.t.on_sequencer_item_run += self.handle_on_sequencer_item_run
        #     self.t.on_sequencer_item_finish +=self.handle_on_sequencer_item_finish
        #     self.t.on_sequencer_all_finish += self.handle_on_sequencer_all_finish
        