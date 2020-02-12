# AMR_Elevator
## File orientation

### Main program 
1. **elevator_server.py**
    * Main 
    * Received command from AMR.
    * To start elevator_server :  **$ sudo python elevator_server.py**
2. **param.yaml** 
    - Parameter file, should modified this file while deployment.
3. **elevator_cmd.py** 
    - Define elevator command 
4. **notify_agent.py** 
    - Send reply/notify to AMR.
5. **cmd_struct.py**   
    - Define structure of elevator_cmd 
6. **pb_interface.py**  
    - Define interface of EVB. Directly control EVB.
7. **/global_var** - 放置至資料夾的檔案如同global variable 能被任意呼叫使用
    * **global_logger.py** - logger object
    * **global_mqtt.py**   - MQTT object
    * **global_xbee.py**   - XBEE object
    * **global_param.py**  - parameter object
8. **weixin_alarm.py** 
    - publish message to weixin alarm 
9. **autoStart.sh** 
    - 開機時，會自動被/etc/rc.local 呼叫

### For testing

1.  **test_cmd.sh** 
    - **$source test_cmd.sh**
    - HTTP通訊測試用，測試按鈕定義時，建議使用此檔案來控制按鈕
2. **fake_amr_navi_center.py** 
    - **./fake_amr_navi_center.py**
    - MQTT通訊測試用，可以透過MQTT channel與電梯板通訊
3. **xbee_fake_client.py** 
    - **./xbee_fake_client.py**
    - XBEE通訊測試用，可以透過XBEE channel與電梯板通訊


4. **ev_simulator.py**
    - 電梯板模擬器 on ROS (想要使用此模擬器請看下方教學)

### Library
1. **/MQTT** 
    * **mqtt_templete.py**  
        - MQTT communication library
2. **/XBEE** 
    * **xbee_templete.py**  
        - XBEE communication library

### MCU 
1. **/L432KC_src**
    * **mcu.bin** - L432KC 的二進位檔，能直接燒錄進MCU
    * **mcu.cpp** - 上述二進位檔的src

# Usage
Execute elevator_server.py: 
```
$ sudo python elevator_server.py 
```
# Test 
### Using HTTP(curl) to test EVB
Instruction of usage will print on terminal, after execute this cmd.
```
$ source test_cmd.sh
```


### Using MQTT to test elevator_server
Create a MQTT client for testing communication.
```
$ ./fake_amr_navi_center.py
```
### Using XBEE to test EVB
Create a XBEE client for testing communication.
```
$ ./xbee_fake_client.py
```

# Deployment Setting

## Parameters instruction

1. **Commnication parameters**

    For HTTP, assgin AMR cherrypy server ip and port. 
    ```
    AMR_URI : 'http://192.168.30.139:8080/'
    ```
    For MQTT, Assign MQTT broker's IP, and AMR client name. 
    * Note that both AMR and elevator_server must connect to the same broker ip. And usually you don't have to modified elevator_server client name.
    ```
    AMR_MQTT_NAME: ["AMR250_3"]  # TODO 
    BROKER_IP: "192.168.30.101" # Office test 
    CLIENT_NAME : "elevator_server" # [DON"T MODIFIED]
    ```
    For XBEE, Fix IP , don't have to modified.
    ```
    XBEE_HOST_IP: '195.0.0.13' # P2P
    ```
2. **PB setting** 
    
    * You must modify this part after EVB installlation 
    * Define mapping from ButtonNo to ConnectorNo
    ```
    # table = {KEY:[boardNo. ConnectorNo]}s
    table:
        'close' : [1, 1]
        'open' : [1, 2]
        '1' : [1, 3] 
        '4' : [1, 9]  
        '2' : [1, 7]  
        '3' : [1, 8]
    ```
    * In elevator calling process, elevator_server must make sure elevator is arrived the floor we want. Therefore,  **floor confirmation** is nessary for calling process, if you don't want AMR finally get out elevator but with a wrong floor.
    * LED state of Floor button is monitor by elevator_server
    * When elevator_server push floor button , a timer is started.
    * Once the LED turn from 'on' to 'off', it'll trigger a process that record the time  from push button to LED trun 'off'. Then push the button again, start a timer, wait for LED turn from 'on' -> 'off'... and so on.
    * This process will only be stopped when time you record match spceify patten which define below, means floor confirmation is OK.

    ```
    FLOOR_LED_CONFIRMATION_MAX_TIME : [ 2, 2 ] # TODO 
    FLOOR_LED_CONFIRMATION_MIN_TIME : [ 0.5, 0.5 ] # TODO 
    ```

    ```
    ENABLE_VERIFY_DOOR_STATUS: False #[TODO] Shandi is True
    CLOSE_EYE_WAIT_DOOR_SEC: 3 # [TODO] This will only be use, when ENABLE_VERIFY_DOOR_STATUS is False
    ```
    * Relate to "How you manage to confirm the door is open now?"
    * ENABLE_VERIFY_DOOR_STATUS is always False, except Shandi , because its special button-door relationship.
    * CLOSE_EYE_WAIT_DOOR_SEC means how long you wait for EV from closed-door to opend-door, since the open button is pushed. 

    ``` 
    DOOR_OPEN_LIMIT_TIME: 60.0 #sec # MAX time that door can keep open, after that, timeout_release.
    ```
    * Max time that allow elevator_server keeping door open, which will make elevator LOCK by elevator_server
    ```
    WAIT_REACH_LIMIT_TIME: 300.0 
    ```
    * MAX time that wait for EV to reach assign floor.

    ```
    IS_SIMULATION: False # Switch to True if you want to simulate in ROS system
    ```
    * Simulator of elevator, base on ROS system. So you must put this hole repo into ROS working space as pkg. 
3. **Communication channels** 
    * Choose communicate channel, you can enable/disable any channel, but at least one channel should be set True.
    ```
    IS_USING_MQTT: True
    IS_USING_HTTP: True
    IS_USING_XBEE: True 
    ```
4. **weixin alarm setting**
    ```
    is_using_rss: False 
    CORP_ID: 'ww0692f024800a89da'
    CORP_SECRET: 'aKA9FsvaU02m5UH4uuYKOq3KGcud2UqXDJoaPhlzDjg'
    AGENT_ID: 1000005
    ```



## Modify udev rule 
* Must Modifiy udev rule after connecting ST32 to R-pi, let R-PI enable to identify ST32 from USB.
```
sudo vim /etc/udev/rules.d/98-st.rules
```

## ssh 
```
$ssh pi@<ip>
EX: $ssh pi@192.168.64.11 

password: odroid
```


## rc.local
Raspberry-pi 3 must add content below in **/etc/rc.local** to automatically start elevator_server.py after reboot.
```
$ sudo vim /etc/rc.local
```
Add content below to /etc/rc.local

```
exec 2> /home/pi/rc.log  # send stderr from rc.local to a log file  
exec 1>&2                  # send stdout to the same log file  
set -x                     # tell sh to display commands before execution 

(sleep 10; /home/pi/elevator_gateway/autoStart.sh) &

service ssh start

exit 0
```

# Dependency 
use sudo to install pip
```
$ sudo apt-get install python-yaml (Should use pip to install)
$ sudo su 
$ pip install cherrypy
$ pip install 

# Rasbian install cherrypy
sudo apt-get install python-cherrypy3
sudo apt-get update
sudo apt-get upgrade
```
