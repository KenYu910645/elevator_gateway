import requests
import json
import time
import datetime
from global_var.global_param import CORP_ID, CORP_SECRET, AGENT_ID

corp_id = CORP_ID
corp_secret = CORP_SECRET
agent_id = AGENT_ID

# Setting access_token log file
file_path = '/tmp/access_token.log'

# Access token, use it when the saved token became invalid.
def get_access_token():
    get_token_url = 'https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid=%s&corpsecret=%s' % (corp_id, corp_secret)
    # print(get_token_url)
    r = requests.get(get_token_url)
    request_json = r.json()
    this_access_token = request_json['access_token']
    r.close()
    # Write the token into file
    try:
        f = open(file_path, 'w+')
        f.write(this_access_token)
        f.close()
    except Exception as e:
        print(e)

    # Return the access_token
    return this_access_token


class WXAlarm:
    def __init__(self):
        self.access_token = get_access_token()

    def get_access_token_from_file(self):
        try:
            f = open(file_path, 'r+')
            this_access_token = f.read()
            f.close()
            return this_access_token
        except Exception as e:
            print(e)

    def sent(self, content):
        flag = True
        ts = time.time()
        st = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
        message = str(st) + " elevator_server : "
        message += content
        while (flag):
            try:
                send_message_url = 'https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token=%s' % self.access_token
                message_params = {
                    "touser": '@all',
                    "msgtype": "text",
                    "agentid": agent_id,
                    "text": {
                        "content": message
                    },
                    "safe": 0
                }
                r = requests.post(send_message_url, data=json.dumps(message_params))
                # print('post success %s ' % r.text)

                # Determine whether sending is successful or not. If not, execute exception function.
                request_json = r.json()
                errmsg = request_json['errmsg']
                if errmsg != 'ok': raise
                # If it's successful , change the flag.
                flag = False
            except Exception as e:
                print(e)
                self.access_token = get_access_token()


# weixin logger 
alarm = WXAlarm()
