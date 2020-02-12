from global_var.global_logger import logger
from notify_agent import notify_agent
import time
# TODO
TOTAL_LOG_MAX_LINE = 40
TOTAL_LOG_MAX_WIDTH = 96

class cmdStruct():
    def __init__(self,type ,robot_id, tid, current_floor, target_floor):
        # AMR command 
        self.type = type
        self.robot_id = robot_id
        self.tid = tid
        self.current_floor = current_floor
        self.target_floor = target_floor
        # Global Flags (share with  cherrypy)
        self.is_release = False
        self.is_entering_done = False
        self.is_timeout_release = False
        # State change when ev is executing cmd.
        self.state = ""
        self.pre_state = ""
        self.t_into_state = 0
        self.door_state = 'unknow'
        # InState_Flags, will reset when switch state
        self.slience_counter = 0 # At wait_vacancy
        self.t_start_hit_floor = 0 # At moveing2_XXX
        self.floor_led_record  = [] # At moveing2_XXX
        # Init 
        self.na = notify_agent() # notify_agent
        #if self.type == "call":
        #    self.switch_state('wait_vacancy')
        # Total logging 
        self.total_logger = [] # ("event" , timestamped)
        self.total_logger.append(("start", time.time()))
    
    def switch_state(self, next_state):
        if self.state == "": # First state
            logger.info("[switch_state] --> " + str(next_state))
        else:
            logger.info("[switch_state] "+ str(self.state) +"("+ str(round(time.time() - self.t_into_state, 2)) +") --> "+ str(next_state))
            self.total_logger.append(("into_"+str(self.state), time.time())) 
        self.pre_state = self.state
        self.state = next_state
        self.t_into_state = time.time()
        self.reset_InState_Flags()
        self.next_state_init(next_state)
    
    def reset_InState_Flags(self): # reset_InState_Flags
        self.slience_counter = 0 # At wait_vacancy
        self.t_start_hit_floor = 0 # At moveing2_XXX
        self.floor_led_record  = [] # At moveing2_XXX
        self.na.clear() # notify_agent

    def next_state_init(self, next_state): # Optional
        if next_state == "enteringEV":
            logger.info("[enteringEV] Waiting for entering done...")
        elif next_state == "alightingEV":
            logger.info("[alightingEV] Waiting for release  ...")
    
    def generate_line (self,line_len ,brick , stuffing = "", stuffing_pos = 1):
        ### Left of stuffing
        output = ""
        for i in range(stuffing_pos-1):
            output += brick
        ### Stuffing
        output += stuffing
        ### Right of stuffing
        for i in range(line_len - len(output)):
            output += brick
        output += '\n'
        return output 

    # def generate_hollow_line (self, line_len, brick , wall_thick, stuffing, stuffing_pos):
    def generate_hollow_line (self, line_len, brick , wall_thick, stuffing):
        '''
        stuffing[] = [(stuff1 , stuff_pos1) , ( .. , .. ) , ...]
        '''

        output = ""
        for i in range(wall_thick):
            output += brick 
        for k in stuffing: 
            for i in range(k[1] - len(output) -1 ):
                output += " "
            output += k[0]
        for i in range(line_len - wall_thick - len(output) -1 ):
            output += " "
        for i in range(wall_thick):
            output += brick
        output += '\n'
        return output 

    def total_logging(self):
        msg = '\n'
        msg += self.generate_line(TOTAL_LOG_MAX_WIDTH, "=")
        msg += self.generate_line(TOTAL_LOG_MAX_WIDTH, "=", "   Mission End   "  , 40)
        msg += self.generate_line(TOTAL_LOG_MAX_WIDTH, "=")
        t_spend = round(self.total_logger[-1][1] - self.total_logger[0][1], 2)
        t_start = self.total_logger[0][1]
        msg += self.generate_hollow_line(TOTAL_LOG_MAX_WIDTH, '=',3 ,[("Robot_id :  " + str(self.robot_id), 6)] )
        msg += self.generate_hollow_line(TOTAL_LOG_MAX_WIDTH, '=',3 ,[("Floor    :  " + str(self.current_floor)+ "F --> "+ str(self.target_floor) + "F" , 6)] )
        msg += self.generate_hollow_line(TOTAL_LOG_MAX_WIDTH, '=',3 ,[("Tid      :  " + str(self.tid), 6 )] )
        msg += self.generate_hollow_line(TOTAL_LOG_MAX_WIDTH, '=',3 ,[("Start time :  " + time.strftime('%m/%d - %H:%M:%S', time.localtime(t_start)), 6)] )
        msg += self.generate_hollow_line(TOTAL_LOG_MAX_WIDTH, '=',3, [("End   time :  " + time.strftime('%m/%d - %H:%M:%S', time.localtime(self.total_logger[-1][1])) , 6)] )
        msg += self.generate_hollow_line(TOTAL_LOG_MAX_WIDTH, '=',3, [("Total time spend : " + str(t_spend) + " sec.", 6)] )
        
        #-------  Time Event List ---------# 
        msg += self.generate_line(TOTAL_LOG_MAX_WIDTH, "=")
        for i in self.total_logger: 
            msg += self.generate_hollow_line(TOTAL_LOG_MAX_WIDTH, '=',3 , [( i[0] + " :  " , 6 ) ,(str(round(i[1] - t_start,2)) + " sec", 40)] )

        '''
        history = [] # (<content>,   <line_number> ,  <Right / Left>)
        for i in self.total_logger:
            t_tmp = round( (((i[1] - t_start)/t_spend) * TOTAL_LOG_MAX_LINE),0 )
            if i[0] == "start":
                history.append((i[0], t_tmp , 'L'))
            elif i[0] == "end":
                history.append((i[0], t_tmp , 'L'))
            elif i[0][:5] == "into_":
                history.append((i[0], t_tmp , 'L'))
            elif i[0][:5] == "send_":
                history.append((i[0], t_tmp , 'R'))
            elif i[0][:7] == "notify_":
                history.append((i[0], t_tmp , 'R'))
            elif i[0][:4] == "cmd_":
                history.append((i[0], t_tmp , 'R'))
            elif i[0] == "netowork_abort":
                history.append((i[0], t_tmp , 'R'))

          
        msg += str(history) + '\n'

        msg += self.generate_line(TOTAL_LOG_MAX_WIDTH, "=")
        msg += self.generate_line(TOTAL_LOG_MAX_WIDTH, "=", "   Misson Time Line    "  , 40)
        msg += self.generate_line(TOTAL_LOG_MAX_WIDTH, "=")
        msg += self.generate_line(TOTAL_LOG_MAX_WIDTH, "=", "   State  Time Line       Notify      get cmd   "  , 19)
        ##### Start drawing 
        for i in range(TOTAL_LOG_MAX_LINE+1):
            this_line = [] # Store event that current line has to print  
            for j in history: # Find line_number
                if j[1] == i :
                    this_line.append(j)
            msg_left = "" 
            #### Left event
            for k in this_line:
                if k[2] == 'L':
                    msg_left += k[0]

            #### Center time line
            TOTAL_LOG_LEFT_WIDTH = 30
            # Add space 
            for i in range(TOTAL_LOG_LEFT_WIDTH - len(msg_left)):
                msg_left = " " + msg_left
            msg += msg_left
            msg += "    ||    "

            #### RIght event 
            for k in this_line:
                if k[2] == 'R':
                    msg += k[0]
            
            #### Next line
            msg += '\n'
        '''
        msg += self.generate_line(TOTAL_LOG_MAX_WIDTH, '=')
        logger.info(msg)
        return 
                
                
