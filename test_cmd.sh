# ev cheat list
HOST_IP=$(hostname -I)
HOST_IP=${HOST_IP%?} # delete end space
EV_HOST='http://'$HOST_IP':8080/'
alias open='curl $(echo ${EV_HOST}open)'
alias close='curl $(echo ${EV_HOST}close)'
alias enter='curl $(echo -d "robot_id=2&tid=7777.8888" ${EV_HOST}entering_done)'
alias rele='curl $(echo -d "robot_id=2&tid=7777.8888" ${EV_HOST}release)'
alias rss='curl $(echo ${EV_HOST}weixin_test)'
alias surele='curl $(echo ${EV_HOST}sudo_release)'
alias release_button='curl $(echo ${EV_HOST}release_button)'
alias precall='ppp() { curl -d "target_floor=$1" $(echo ${EV_HOST})precall;}; ppp'
alias EVReboot='EEE() { curl -d "pw=$1" $(echo ${EV_HOST})reboot;}; EEE'
alias call='ccc() { curl -d "robot_id=2&tid=7777.8888&current_floor=$1&target_floor=$2" $(echo ${EV_HOST})call;}; ccc'

# For installation testing
alias w='winput() { curl -d "key=$1&d=$2" $(echo ${EV_HOST})EVledWrite;}; winput'
alias r='rinput() { curl -d "key=$1" $(echo ${EV_HOST})EVledRead;}; rinput'

echo Cheatlist, try cmd below to test elevator:
echo -e "\033[1;33m$ open\033[0m"     : send a request to open EV door
echo -e "\033[1;33m$ close\033[0m"    : send a request to close EV door
echo -e "\033[1;33m$ enter\033[0m"    : send a request to fake AMR has entered EV
echo -e "\033[1;33m$ rele\033[0m"     : send a request to release call cmd
echo -e "\033[1;33m$ rss\033[0m"     : send Test msg to weixin
echo -e "\033[1;33m$ release_button\033[0m" : send a request to release button
echo -e "\033[1;33m$ call 1 12\033[0m": send a request to call EV, 1F to 12F, call '[current_floor] [target_floor]'
echo -e "\033[1;33m$ precall 8 \033[0m": send a request to push 8F button, precall '[target_floor]'
echo -e "\033[1;33m$ EVReboot \033[0m": send a request to reboot elevator_server 
echo -e "\033[1;33m$ r 1 \033[0m": send cmd to ST,  r '[connectorID]'
echo -e "\033[1;33m$ w 1 high \033[0m": send cmd to ST,  w '[connectorID]' '[high/low]'

