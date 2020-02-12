#!/usr/bin/env python
from global_var.global_logger import logger 
import time
import random # for getMid()
import threading
import socket, errno
import os 

WAIT_AWK_MAX_TIME = 3 # sec 
MAX_RESEND_TIMES = 6 # times 
KEEPALIVE = 2 # sec ping,pong every 2 sec , 
KEPPALIVE_MAX = 4 # SEc, How long would you wait for PING,PONG, before abandon socket
SOCKET_TIMEOUT = 1 # Sec 
SERVER_SOCKET_TIMEOUT = 5 # Sec  
IS_PRINT_OUT_PING_PONG = False  

START_CHAR = '['
END_CHAR = ']'

# ------ Global Variable ---------# 
recbufList  = [] # [mid  ,  msg_type , content ]
recAwkDir = dict() # key: "MID" , value "AWK"

class SEND_AGENT(object):
    def __init__(self, bl_obj, payload, mid, qos = 1):
        self.payload  = payload 
        self.bl_obj = bl_obj
        self.mid = mid 
        self.is_awk = False
        self.qos = qos 
        #
        if qos == 1 : 
            self.send_thread = threading.Thread(target = self.send_target) 
            self.send_thread.start()
        elif qos == 0 : 
            self.send_thread = threading.Thread(target = self.send_no_trace) 
            self.send_thread.start()
        
    def send_no_trace(self) : 
        '''
        QOS = 0 
        for 'PING', 'PONG' , 'AWK'
        '''
        for i in range(MAX_RESEND_TIMES):
            if not self.bl_obj.is_connect:
                self.bl_obj.logger.info("[XBEE] Lost connection, Give up sending " + self.payload)
                return 
            try: 
                if (not IS_PRINT_OUT_PING_PONG) and (self.payload == 'PING' or self.payload == 'PONG' ):
                    pass 
                else:  
                    self.bl_obj.logger.info("[XBEE] Sending " + self.payload + "(" + self.mid + ")")
                self.bl_obj.sock.sendall( '['+self.payload+',mid'+ self.mid+']')
            except Exception as e : 
                self.bl_obj.logger.error("[XBEE] XBEE Error: " + str(e) )
                self.bl_obj.logger.error("[XBEE] Urge disconnected by send exception, when sending " + self.payload)
                self.bl_obj.is_connect = False 
                return 
            else: 
                self.is_awk = True 
                return 
        self.bl_obj.logger.error ("[XBEE] Fail to Send After trying " + str(MAX_RESEND_TIMES) + " times. Abort." )

    def send_target(self):
        '''
        QOS = 1,
        For CMD. 
        send with AWK callback , if can't received AWK, then resend it .
        '''
        global recAwkDir
        for i in range(MAX_RESEND_TIMES):
            if not self.bl_obj.is_connect:
                self.bl_obj.logger.info("[XBEE] Lost connection, Give up sending " + self.payload)
                return 
            #------ Send message -------#  # TODO 
            try: 
                if (not IS_PRINT_OUT_PING_PONG) and (self.payload == 'PING' or self.payload == 'PONG' ):
                    pass 
                else:  
                    self.bl_obj.logger.info("[XBEE] Sending " + self.payload + "(" + self.mid + ")")
                self.bl_obj.sock.sendall( '['+self.payload+',mid'+ self.mid+']')
            except Exception as e :
                self.bl_obj.logger.error("[XBEE] BluetoothError: " + str(e) )
                self.bl_obj.logger.error("[XBEE] Urge disconnected by send exception, when sending " + self.payload)
                self.bl_obj.is_connect = False 
                return 
                # self.logger.error ("[XBEE] send_target() : "+ str(e) + ". Retry " + str(i) + "/" + str(MAX_RESEND_TIMES) ) 
                # time.sleep (1)
            else: 
                t_start = time.time() 
                while time.time() - t_start < WAIT_AWK_MAX_TIME: 
                    ans = recAwkDir.pop(self.mid, "not match") # Pop out element, if exitence 
                    if ans != "not match": # Get AWK 
                        self.bl_obj.logger.info("[XBEE] Get AWK (" + self.mid + ")")
                        self.is_awk = True 
                        break
                    else: # Keep waiting 
                        pass 
                    time.sleep (0.05)
            
                if self.is_awk : 
                    return 
                else: 
                    self.bl_obj.logger.warning("[XBEE] Need to resend "+ self.payload +" (" + str(i) + "/" + str(MAX_RESEND_TIMES) + ", "+ self.mid +")")
                    time.sleep(1) # for rest 
        self.bl_obj.logger.error ("[XBEE] Fail to Send After trying " + str(MAX_RESEND_TIMES) + " times. Abort." )

class BLUE_COM(object): 
    def __init__(self, logger, host=None , port = 3 ):
        '''
        Must assign cmd_CB function before start engine
        '''
        # -------- Connection --------# 
        self.is_connect = False
        self.sock = None # Communicate sock , not server socket 
        self.recv_thread = None 
        self.engine_thread = None 
        self.is_engine_running = False  
        self.server_sock = None  # Only for Server 
        self.keepAlive_count = None 
        self.ping_count = None 
        self.host = host
        self.port = port 
        #-------- For Recevied -------# 
        self.logger = logger 
        self.BT_cmd_CB  = None 
    
    ##########################
    ###   For Server Only  ###
    ##########################
    def server_engine_start(self): 
        '''
        Must Assign cmd_CB function before start engine
        '''
        self.is_engine_running = True 
        self.server_sock=socket.socket(socket.AF_INET, socket.SOCK_STREAM)# BluetoothSocket(RFCOMM)
        self.engine_thread = threading.Thread(target = self.server_engine)
        self.engine_thread.start()

    def server_engine_stop(self):
        self.shutdown_threads()
        try: 
            self.server_sock.close()
            self.logger.info("[XBEE] Server socket close.")
            self.server_sock = None
        except: 
            self.logger.error ("[XBEE] Can't close server socket.")
    
    def server_engine (self): # ToTally Blocking 
        global recbufList
        self.server_sock.settimeout(SERVER_SOCKET_TIMEOUT)
        is_connect_last_loop = True  # TODO TODO TODO TODO  # This flag is only for logging. 
        
        time.sleep(1)
        #try:
        if True : 
            while self.is_engine_running: # Durable Server
                if self.is_connect : 
                    # ------- Check Keep alive for client  -------# 
                    if time.time() - self.keepAlive_count >= KEPPALIVE_MAX : # Give up connection
                        self.close(self.sock)
                        self.logger.warning ("[XBEE] Disconnected, because client did't send PING. (PING, PONG)")
                    # ------- Check weather something to do in recbufList ---------# 
                    if recbufList != []:
                        msg = recbufList.pop(0) # FIFO, check what I received 
                        if   msg[1] == 'DISCONNECT': # Close connection with client
                            self.close(self.sock)
                        elif msg[1] == 'PING':
                            self.logger.info("[XBEE] Get PING  ")
                        elif msg[1] == 'CMD':
                            self.logger.debug("[XBEE] Get cmd ")
                        else: 
                            self.logger.error("[XBEE] Unresconized cmd: " + msg[1]) 
                    else:
                        pass # Nothing to do. Bored server.
                    
                else: # Need to Reconnect 
                    try:
                        self.server_sock.bind((self.host, self.port)) # If client keep trying to connected with server, adress may be block. 
                        self.server_sock.listen(1) # Only accept 1 connection at a time
                    except Exception as e:
                        err_msg = "[XBEE] Exception at sock bind() : " + str(e) + ", "
                        if e.args[0] == 99:
                            err_msg += "this usually means ppp0 interface is not yet initialize."
                        if is first_reconnection: 
                            self.logger.warning(err_msg) 
                            first_reconnection = False 

                    else: 
                        try: 
                            client_sock, client_info = self.server_sock.accept() # Block for 'SERVER_SOCKET_TIMEOUT' sec.
                        except socket.error, e:
                            if finally_conneted : 
                                self.logger.info('[XBEE] Waiting Connection .... ') 
                                finally_conneted = False 
                            if e.args[0] == errno.EWOULDBLOCK or e.args[0] == 'timed out':
                                self.logger.debug('[XBEE] Still waiting for client.')
                            else: 
                                self.logger.error('[XBEE] Error at Server Engine: ' + str(e))
                        else: 
                            # Successfully Connect to client 
                            self.sock = client_sock
                            self.logger.info("[XBEE] Accepted connection from "+  str(client_info))
                            finally_conneted = True 
                            self.is_connect = True 
                            self.keepAlive_count = time.time() 
                            # Start a received thread for getting data from client socket.
                            self.recv_thread = threading.Thread(target = self.recv_engine) # , args=(self.sock,))
                            self.recv_thread.start()
                    time.sleep(1)
                time.sleep(0.1)
        #except: 
        else: 
            self.logger.error("[XBEE] Something wrong at server_engine.")
        
        self.logger.info("[XBEE] END of server_engine")
    

    ###########################
    ###   For Client Only   ###
    ###########################
    def client_engine_start(self):
        self.is_engine_running = True
        self.engine_thread = threading.Thread(target = self.client_engine)
        self.engine_thread.start()
    
    def client_engine_stop(self):
        self.client_disconnect() # Qos0 
        self.shutdown_threads()
        self.logger.info("[XBEE] client engine stop ")

    def client_engine(self):
        while self.is_engine_running: 
            if self.is_connect: 
                # ------- PING PONG -------# Keep alive 
                if time.time() - self.keepAlive_count >= KEPPALIVE_MAX : # Give up connection
                    self.close(self.sock)
                    self.logger.warning ("[XBEE] Disconnected, because KEEPAVLIE isn't response. (PING, PONG)")
                elif  time.time() - self.ping_count >= KEEPALIVE: # Only for client to send "PING"
                    self.send('PING', 0)
                    self.ping_count = time.time()
                #------- Check List --------# 
                if recbufList != []: # Something to do 
                    msg = recbufList.pop(0)
                    self.BT_cmd_CB(msg)
            else: 
                # logger.info("[client_engine] Reconnected.")
                if not self.client_connect(self.host, self.port):
                    time.sleep(1) # Sleep 1 sec for next reconnection
            time.sleep(0.1)

    def client_connect  (self, host, port = 3):
        '''
        Only for client socket 
        '''
        self.logger.info("[XBEE] connecting to " + host)
        ts = time.time()
        # Create the client socket
        self.sock=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(SOCKET_TIMEOUT) # TODO TODO TODO test 
    
        rc = self.sock.connect_ex((self.host, self.port)) # Blocking 
        if rc == 0 :  # Conncetion success
            output  = True 
            self.is_connect = True 
            self.keepAlive_count = time.time()
            self.ping_count = time.time()
            self.sock.setblocking(False) # Non-blocking 
            self.logger.info("[XBEE] connected. Spend " + str( round((time.time() - ts) * 1000 )) + "ms.")

            self.recv_thread = threading.Thread(target = self.recv_engine)# , args=(self.sock,))  # (self.sock))
            self.recv_thread.start()
        else: # Exception 
            self.logger.error("[XBEE] Not able to Connect, " + os.strerror(rc))
            output = False 
        return output 

    def client_disconnect(self): # Normally disconnect  # Only from client -> server 
        if self.is_connect: 
            self.send("DISCONNECT", 0)
        else: 
            self.logger.warning ("[XBEE] No need for disconnect, Connection already lost.")
    
    #########################
    ###   General Usage   ###
    #########################
    def add_cmd_CB (self, cmd_CB):
        self.BT_cmd_CB = cmd_CB
     
    def shutdown_threads(self):
        '''
        Include close socket 
        '''
        self.is_connect = False
        self.is_engine_running = False
        # -------------------------------# 
        self.close(self.sock)
        try:
            if self.engine_thread == None : 
                self.logger.info("[XBEE] engine_thread didn't start yet ....")
            else: 
                self.logger.info("[XBEE] Waiting engine_thread to join...")
                self.engine_thread.join(10)
        except : 
            self.logger.error("[XBEE] Fail to join engine_thread.")
        
    
    def close(self, socket): 
        self.is_connect = False  # P2P
        # -----------End recv threading --------------_# 
        try: # to close recv_threading 
            if self.recv_thread == None : 
                self.logger.info("[XBEE] recv_thread didn't start yet ....")
            else: 
                if self.recv_thread.is_alive():
                    self.logger.info ("[XBEE] waiting join recv_threading ")
                    self.recv_thread.join(5)
                self.logger.info ("[XBEE] close recv_threading")
        except : 
            self.logger.error ("[XBEE] Exception at close recv_thread.")
        
        # -----------close socket  --------------_# 
        try: 
            socket.close()
            self.logger.info("[XBEE] Socket close.")
            socket = None
        except: 
            self.logger.error ("[XBEE] Can't close socket .")
    
    def getMid(self):
        '''
        return 'AUTK', 'UROR', 'QMGT' in random
        '''
        output = "" 
        for i in range(4) : 
            output += chr(random.randint(0,25) + 65)
        return output

    def send (self, payload, qos = 1, mid = None):
        '''
        Inptu : payload need to be String 
        nonblocking send.
        return SEND_AGENT
        '''
        if mid == None : 
            mid = self.getMid()
        return SEND_AGENT(self, payload, mid, qos)

    def recv_engine(self):
        '''
        Both Server and Client need recv_engine for receiving any message.
        '''
        global recbufList, recAwkDir
        self.sock.settimeout(SOCKET_TIMEOUT)
        while self.is_connect:
            #---------RECV -----------# 
            try: 
                rec = self.sock.recv(1024) # Blocking for 1 sec. 
            except Exception as e:
                if e.args[0] == 'timed out':
                    self.logger.debug("[XBEE] recv Timeout." )
                else:
                    self.logger.error("[XBEE] Error: " + str(e) )
                    self.logger.error("[XBEE] Urge disconnected by recv exception.")
                    self.is_connect = False 
            else:
                if rec == "":
                    time.sleep(0.1)
                    continue
                
                self.logger.debug("rec: " + rec)
                is_valid = False 
                try:
                    #---------  Check start and end Char -------# 
                    if rec[0] == START_CHAR or rec[-1] == END_CHAR:
                        rec = rec[1:-1] # Del '[' and ']'
                        mid_str = rec[-8:]# ,midASDF
                        rec = rec[:-8] # Cut off mid 
                        #---------  Check MID --------# 
                        if mid_str[:4] != ',mid' or (not mid_str[4:].isupper()):
                            pass 
                        else: 
                            is_valid = True 
                    else: 
                        pass 
                except: 
                    is_valid = False 
                    self.logger.error ("[XBEE] recv_engine MID ERROR ")

                if is_valid:
                    #------- Print  ----------#  
                    if (not IS_PRINT_OUT_PING_PONG) and (rec == 'PING' or rec == 'PONG' ):
                        pass 
                    else:  
                        self.logger.info ("[XBEE] Received: " + rec )
                    #------- What to do when received msg ------# 
                    if rec == "AWK":
                        recAwkDir[mid_str[4:]] = rec
                    elif rec == "PING": # Server recv 
                        self.keepAlive_count = time.time()
                        self.send('PONG', 0, mid=mid_str[4:]) # Send the same mid with PING 
                    elif rec == "PONG":# Client recv 
                        self.keepAlive_count = time.time()
                        self.logger.info('[XBEE] Get PONG in ' + str( round((self.keepAlive_count - self.ping_count) * 1000 )) + "ms.")
                    else:
                        self.send('AWK', 0, mid = mid_str[4:])
                        if rec == "DISCONNECT":
                            recbufList.append([mid_str[4:], rec , ""])
                        else :  # CMD
                            recbufList.append([mid_str[4:], "CMD" , rec ])
                            self.BT_cmd_CB(rec)
                else: 
                    self.logger.error("[XBEE] received not valid msg.")
                # ------ Reset Flag --------# 
                rec = ""
                # End of else 
            time.sleep(0.1)
            # End of while 
