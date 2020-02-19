import time
import yaml
import serial
from global_var.global_logger import logger
from global_var.global_param import REC_TIMEOUT, IS_VERBOSE, table, IS_SIMULATION,BROKER_IP
if IS_SIMULATION:
    import posix_ipc
# Data receiving
START_CHAR = '['
END_CHAR = ']'
INTERVAL_CHAR = ','
NUM_OF_DATA = 2  # [<data>, <tid>], ex: [G,H]
waiting   = 0
receiving = 1

class PB_interface_simu():
    '''
    This interface is for elevator simulation only.
    '''
    def __init__(self):
        self.mq_recv = posix_ipc.MessageQueue('/simu_IPC_reply', posix_ipc.O_CREAT)
        self.mq_recv.block = False # non-blocking recv , send
        self.mq_send = posix_ipc.MessageQueue('/simu_IPC_cmd'  , posix_ipc.O_CREAT)
        self.mq_send.block = False # non-blocking recv , send
    
    def EVledWrite(self, key, d, retryTime=3):
        if d=="high":
            sendBuff = "w " + str(key) + " 1"
        elif d=="low":
            sendBuff = "w " + str(key) + " 0"
        try:
            self.mq_send.send(sendBuff, priority = 9)
        except posix_ipc.BusyError: # queue full
            pass 
        return 'G'
    def EVledRead(self, key, retryTime=3):
        try : 
            self.mq_send.send("r " + str(key), priority = 9)
        except posix_ipc.BusyError: # queue full
            return -1 # Error queue full 
        # Wait for answer for 1 sec. 
        t_start_wait = time.time()
        while time.time()  - t_start_wait < 1: # 1 sec 
            try:
                r = self.mq_recv.receive()
            except posix_ipc.BusyError:
                pass # queue empty, keep waiting
            else: # Get msg
                return int(r[0])
        return -1 # Error , timeout 

class PB_interface():
    def __init__(self):
        # TODO You must modified this after installation.
        # dev connection, change <device path> when installing, Should set udev-rules accordingly.
        EV_board1 = serial.Serial('/dev/EV_board1',57600,timeout= 0.5)
        #EV_board2 = serial.Serial('/dev/EV_board2',57600,timeout= 0.5)
        #EV_board3 = serial.Serial('/dev/EV_board3',9600,timeout= 0.5)
        #Port
        self.device_table={ 1 : EV_board1
                    #2 : EV_board2,
                    #3 : EV_board3 
                    }
        self.tid_counter = 0
    def EVledWrite(self, key, d, retryTime=3):
        '''
        Send IO write cmd to ST_board
        Input:
            key: ConnectorID
            d : 'high' or 'low'
            retryTime : How many time to re-send command when ST_board reject cmd.
        '''
        board = table[key][0]
        device = self.device_table[board]
        ID = table[key][1] # Connector ID
        sendBuff = "[w," + str(ID)
        
        if d=="high":
            sendBuff += ",1,"
        elif d=="low":
            sendBuff += ",0,"
        
        # Test time spend
        tStart = time.time()
        for i in range(retryTime):
            tid = self.getTid()
            send = sendBuff + tid + "]"
            device.write(send) # SendBuff should be "[w,1,0,A]", "[w,10,1,B]" ...etc.
        
            # Test time spend
            respond = self.waitAnswer(device,tid) # Could be only 'H', 'L', 'E'
            if respond == 'G':
                break
            else: # Got an 'E' or -1(timeout), need to resend command 
                logger.warning("[EVledWrite] GOT an ERROR from ST_board, retry"+ str(i+1)+ "th time.")
        tEnd = time.time()
        if IS_VERBOSE: # TODO SUPER_VERBOSE?????
            logger.debug("[EVledWrite]"+"Board:"+ board + "send:"+ send+ "respond:"+ respond+ "deltaT(sec):"+ str(tEnd - tStart))
        else:
            pass
        return respond

    def EVledRead(self, key, retryTime=3):
        '''
        Send IO read cmd to ST_board, And wait for ST answer.
        Input:
            key: Connector ID
            retryTime: How many times to resend command when ST 
        Output:
            Return 1 : ev_led is on
            Return 0 : ev_led is off
            Return -1 : Error
        '''
        board = table[key][0]
        device = self.device_table[board]
        ID = table[key][1] # Connector ID
        tStart = time.time()
        for i in range(retryTime):
        
            tid = self.getTid()
            sendBuff = "[r," + str(ID) + "," + tid + "]"
            try:
                device.write(sendBuff) #blocking by default
            except:
                logger.error("[EVledWrite] write fail!")
                continue
            # Test time spend
            respond = self.waitAnswer(device,tid) # Could be only 'H', 'L', 'E'
            
            if respond == 'H' or respond == 'L':
                break
            else: # "'E', -1 (timeout) mean error", Need to resend
                logger.warning("[EVledRead] GOT an ERROR from ST_board, retry"+ str(i+1)+ "th time.")
        tEnd = time.time()
        # Testing msg
        if IS_VERBOSE: # TODO super verbose
            logger.debug("[GPIO read ]"+" Board:"+ board + " ID:" +ID+ "send:"+sendBuff+ " H/L:" + respond+ "deltaT(sec)"+ str(tEnd - tStart))
        ##### Return msg  ### NOTE THAT, H/L are inverted.
        if respond == "H":
            return 0 # LED is off, But GPIO is high
        elif respond == 'L':
            return 1 # LED is on , But GPIO is low.
        else:
            return -1 # although retry many time, still can get proper answer.

    def is_ans(self, input):
        '''
        check is valid answer for ST_board
        input:
            First element of answer
        Output:
            return T/F
        '''
        if input=="G" or input=="E" or input=="H" or input=="L":
            return True
        else:
            return False

    def getTid(self):
        '''
        return A(65)~Z(90) in sequence
        '''
        # global tid_counter
        if self.tid_counter >= 26: # Reset counter
            self.tid_counter = 0
        #output = chr(65 + (tid_counter/26)) + chr(65 + tid_counter%26) # AA, AB, AC
        output = chr(65 + self.tid_counter)
        self.tid_counter += 1
        return output

    def waitAnswer(self, device ,tid):
        '''
        Wait answer from ST_board(tid must match) and parse it, can't block exceed REC_TIMEOUT
        Input: 
            tid : which tid you are expecting for response.
        Output:
            return -1 : timeout
            return ans(str) from ST_board : H , L , G, E
        Note: this function is called by EVLedRead() and EvledWrite()

        '''
        # receiving package for GPIORead
        rec_state = waiting
        recbuf = ""
        rec_timeout_counter = 0
        
        tStartWait = time.time()
        while time.time() - tStartWait < REC_TIMEOUT: # ~= 0.1 sec
            is_completed = False
            is_valid = False
            if device.inWaiting() != 0: # Wait for ST_board answer, Should be '[H]' or '[L]'
                try: # 
                    rec = device.read() # Read one byte # blocking for 0.5sec(define by configuration)
                except:
                    logger.error("[EVwaitAnswer] read fail")
                    continue
                    #print "rec = ", rec
                #receive ST_board answer
                if rec_state == waiting:
                    if rec==START_CHAR:
                        rec_state = receiving
                elif rec_state == receiving:
                    if rec == END_CHAR:# is_completed
                        rec_state = waiting
                        is_completed = True
                    elif rec == START_CHAR:
                        recbuf = ""
                    else:
                        recbuf += rec
                else:
                    pass
            if is_completed:
                #print "recbuf:", recbuf
                ##################### Parse Data
                recbufArr = list()
                for i in range(NUM_OF_DATA):
                    interval_idx = recbuf.find(INTERVAL_CHAR)
                    if interval_idx != -1: # found a interval char
                        recbufArr.append(recbuf[:interval_idx])
                        recbuf = recbuf[interval_idx+1:]
                    else: # interval not found, Last data?
                        if recbuf == "":
                            pass
                        else:
                            recbufArr.append(recbuf)
                ##################### Valid check
                if len(recbufArr) == 2:
                    if self.is_ans(recbufArr[0]) and recbufArr[1] == tid: # if tid is not match keep while.
                        is_valid = True
                ##################### return respond
                if __debug__:
                    #print "recbufArr: ", recbufArr
                    pass
                if is_valid:
                    return recbufArr[0]
            # End of is_completed
            rec_timeout_counter += 1
            time.sleep(0.001) #TODO test#sleep 1ms, check device for every 1ms
            # End of while
        return -1
