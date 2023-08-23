import math

# fopley motor pos reach timer calculation
def pos_reach_calc(event_pos,current_pos,target_pos,vel,acc):
	distance = abs(target_pos-current_pos)
	# print 'dist',distance
	event_distance = abs(event_pos-current_pos)
	# print 'evt dist',event_distance
	# time needed to reach that max velocity
	t_vel_max=1.0*vel/acc
	# print 't vmax',t_vel_max
	# position when the vel reach max
	p_vel_max=0.5*acc*(t_vel_max**2)
	# print 'p vmax',p_vel_max
	# make the profile start from 0
	target_pos -= current_pos
	event_pos -= current_pos
	current_pos = 0
	
	# if reverse make it positive
	if(target_pos<current_pos):
		# print 'reversed'
		target_pos*=-1
		event_pos*=-1
	# print 'pos list:',current_pos,event_pos,target_pos

	# can it reach max vel with the current profile?
	# if yes then it is a trapezoidal
	t_result=0
	if(abs(distance)>=p_vel_max):
		square_max_pos=distance-p_vel_max
		# print 'sqr maxpos',square_max_pos
		# is it still inside the first triangle?
		if(event_distance<=p_vel_max):
			# print '0'
			t_result = math.sqrt(2.0*event_distance/acc)
		# is it inside the square
		elif(event_distance<=square_max_pos):
			# print '1' 	
			square_distance = event_pos - p_vel_max
			# print 'sqr dist',square_distance
			t_square = square_distance / vel
			t_result = t_vel_max + t_square 
			# print 't r',t_result
		# is it inside the second triangle?
		elif(event_distance<=distance):
			# print '2'
			square_distance = target_pos - p_vel_max
			t_square = square_distance / vel
			# solving quadratic equation
			a = -0.5 * acc
			b = vel
			c = -1*(event_pos - square_distance)
			d = math.sqrt((b**2)-4*a*c)
			root_pos = (-1.0*b + d) / (2.0*a)
			root_neg = (-1.0*b - d) / (2.0*a)
			# print root_pos,root_neg,d
			t_result = t_vel_max + t_square + min(root_pos,root_neg)
		else:
			return False
	#if not then it is a triangle
	else:
		t_max=math.sqrt(2.0*distance/acc)
		v_max = 0.5*t_max*acc
		# time needed to reach event pos
		t = math.sqrt(2.0*event_pos/acc)
		# if it's inside the first triangle
		if(t<(0.5*t_max)):
			# print '3'
			t_result = t
		# if it's on the second triangle
		else:
			# print '4'
			# solving quadratic equation
			a = -0.5 * acc
			b = v_max
			c = -1*(event_pos - (distance/2.0))
			d = math.sqrt((b**2)-4*a*c)
			root_pos = (-1.0*b + d) / (2.0*a)
			root_neg = (-1.0*b - d) / (2.0*a)
			# print root_pos,root_neg,d
			t_result = 0.5*t_max+ min(root_pos,root_neg)

	return t_result * 1000

#status code decoder--------------------------------------
def decode_motor_status(motor_status):
	if(motor_status==0):
		return "no error"
	else:
		string_array_status=[
		"scNone ",
		"scMoving ",
		"scHoming ",
		"scHomed ",
		"scLowerLimit ",
		"scUpperLimit ",
		"scOverCurrent ",
		"scAborted ",
		"scFolErrorIdle ",
		"scFolErrorMoving ",
		"scEncoderError ",
		"scDisabled ",
		"scEmergencyStop ",
		"scHardBrake ",
		"scDriverFault ",
		"scStalled"
		]
		string_status=""
		for i in range(len(string_array_status)):
			if( (motor_status>>i) & 1):
				string_status+=string_array_status[i+1]
	return string_status
		
def decode_motor_error(motor_error_code):
	string_array_status=[
	"mecNone ",
	"mecInvalidID ",
	"mecLowerLimit ",
	"mecUpperLimit ",
	"mecIllegalPos ",
	"mecIllegalVel ",
	"mecIllegalAcc ",
	"mecAborted ",
	"mecFolErrorIdle ",
	"mecFolErrorMoving ",
	"mecEncoderError ",
	"mecDisabled ",
	"mecHoming ",
	"mecEmergencyStop ",
	"mecHardBrake ",
	"mecDriverFault ",
	"mecNoMove ",
	"mecMoveNotSupported ",
	"mecIllegalJrk ",
	"mecStalled "
	]
	if(motor_error_code<len(string_array_status)):
		return string_array_status[motor_error_code]
	else:
		return "unknown error"

def decode_driver_status(drv_status):
	if(drv_status == 0):
		return 'none'
	string_array_status=[
	'dsc_driverError',
	'dsc_uv_cp',
	'dsc_olb ',
	'dsc_ola',
	'dsc_s2gb',
	'dsc_s2ga',
	'dsc_otpw',
	'dsc_ot', 
	'dsc_s2vsb',
	'dsc_s2vsa'
	]
	return_string = ''
	for enum,status in enumerate(string_array_status):
		if(drv_status & 1<<enum):
			return_string+='{0},'.format(status)

	return return_string