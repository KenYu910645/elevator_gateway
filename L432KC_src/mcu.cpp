#include "mbed.h"
#include "BufferedSerial.h"
#include <string>
#include <vector> 
#include <stdlib.h>  /*for atoi */

using std::string;

#define DEBUG 0 // switch to 1 , to print out debug message

//Serial pc(USBTX, USBRX);
BufferedSerial pc(USBTX, USBRX);
Ticker timer1;

DigitalIn IN1(PA_9);
DigitalOut OUT1(PA_10);
DigitalIn IN2(PB_4);
DigitalOut OUT2(PB_3);
DigitalIn IN3(PA_12);
DigitalOut OUT3(PB_0);
DigitalIn IN6(PA_6);
DigitalOut OUT6(PA_5);
DigitalIn IN7(PB_1);
DigitalOut OUT7(PA_8);
DigitalIn IN8(PA_4);
DigitalOut OUT8(PA_3);
DigitalIn IN9(PA_11);
DigitalOut OUT9(PB_5);
DigitalIn IN10(PA_1);
DigitalOut OUT10(PA_0);

//Dummy object
DigitalIn  NC_IN(NC);
DigitalOut NC_OUT(NC);

//NOTE!! NC is dummy index that should never be accessed.
DigitalIn  DinArr[11]  = {NC_IN,  IN1,  IN2,  IN3,  NC_IN  ,NC_IN  ,IN6,  IN7,  IN8,  IN9,  IN10};
DigitalOut DoutArr[11] = {NC_OUT, OUT1, OUT2, OUT3, NC_OUT ,NC_OUT ,OUT6, OUT7, OUT8, OUT9, OUT10};
// Global variabele
char err[] = "E"; // pass to R-pi when something wrong
bool is_completed = false; // True: string receive completed. False: Not completed yet.
bool is_valid = false; //True: string receive is in valid format, False: reset recbuf and printf err msg.
char START_CHAR = '[';
char END_CHAR = ']';
char INTERVAL_CHAR = ',';
int NUM_OF_DATA = 4;
int NUM_OF_DATA_W = 4;
int NUM_OF_DATA_R = 3;
enum REC_STATE{waiting, receiving};
REC_STATE rec_state = waiting;
string recbuf = "";

void init_IO()
{
    pc.baud(57600);
    OUT1 = 0;
    OUT2 = 0;
    OUT3 = 0;
    OUT6 = 0;
    OUT7 = 0;
    OUT8 = 0;
    OUT9 = 0;
    OUT10 = 0;
}

bool is_num(string input)
{
    const char* input_c = input.c_str();
    for (int i = 0 ; i < input.length(); i++)
    {
        if (input_c[i] - '0' > 9 or input_c[i] - '0' < 0 )
        {
            return false;
        }
    }
    return true;
}

bool is_HL(string input)
{
    if (input == "0" 
     or input == "1")
        {return true;}
    else 
        {return false;}
}
bool is_tid(string input) // Only accpect 'A' ~ 'Z'
{
    if (input.size() == 1)
    {
        if (input[0] - 'A' >= 0 and input[0] - 'A' <= 25)
        {
            return true; 
        }
    }
    return false;
}

bool is_connector(string input) // return True , if input is valid connector number.
{
    if (input == "1" 
     or input == "2"
     or input == "3"
//   or input == "4"
//   or input == "5"
     or input == "6"
     or input == "7"
     or input == "8"
     or input == "9"
     or input == "10")
        {return true;}// TODO
    else
        {return false;}
}

int main() {
    init_IO();
    while(true)
    {
        char rec = 0;
        // TODO
        if(pc.readable() > 0)
        {
            //  Get "[w,3,1,A]" "[r,A,0,T]" for serial
            //  Get one char
            rec = pc.getc();
            switch (rec_state)
            {
                case(waiting):
                    if (rec == START_CHAR){rec_state = receiving;}
                    else {;} // do nothing 
                    break;
                case(receiving):
                    if (rec == END_CHAR)// is completed 
                    {
                        is_completed = true;
                        rec_state = waiting;
                    }
                    else if (rec == START_CHAR)
                    {
                        recbuf = ""; // new cmd is come in, abondan original one.
                    }
                    else 
                    {
                        recbuf += rec;
                    }
                    break;
            }
            
            if (is_completed)
            {
                vector <string> recbufArr;
                //***************    parse data    **************//
                for (int i = 0; i < NUM_OF_DATA; i++)
                {
                  int interval_idx = recbuf.find(INTERVAL_CHAR,0);
                  if (interval_idx != string::npos) // INTERVAL find !
                  {
                    //pc.printf("get INTERVAL at : %i", interval_idx);
                    //pop out substr
                    //recbufArr[i] = recbuf.substr(0, interval_idx);// interval_idx is exclusive
                    recbufArr.push_back(recbuf.substr(0, interval_idx));
                    recbuf.erase(0,interval_idx+1);
                  }
                  else // INTERVAL NOT FOUND! Last DATA  TODO need think
                  {
                    if (recbuf == "") // nothing to parse already.
                    {
                        break;
                    }
                    else // Last Data in this package
                    {
                        //recbufArr[i] = recbuf;
                        recbufArr.push_back(recbuf);
                        break;
                    }
                  }
                }
                #if DEBUG==1
                  for (int i = 0 ; i < recbufArr.size(); i++){pc.printf(recbufArr[i].c_str()); pc.puts("\n");}
                #endif
                
                //**************    valid check     **************//
                //Data Indivisual check
                if (is_connector(recbufArr[1])) // Check valid ID
                {
                    if (recbufArr[0] == "w" and recbufArr.size() == NUM_OF_DATA_W)
                    {
                        if (is_HL(recbufArr[2]) and is_tid(recbufArr[3]))
                        {
                            is_valid = true;
                        }
                    }
                    else if (recbufArr[0] == "r" and recbufArr.size() == NUM_OF_DATA_R)
                    {
                        if (is_tid(recbufArr[2]))
                        {
                            is_valid = true;
                        }
                    }
                    else{;}
                    // if tid not exist -> not valid
                }
                
                #if DEBUG==1
                  pc.printf("is_valid: %i", is_valid); pc.puts("\n");
                #endif
                
                if (is_valid)
                {
                    //**********************   Get ID  ********************//
                    int ID = atoi(recbufArr[1].c_str());
                    
                    //*********************   Execute cmd    ********************//
                    if (recbufArr[0] == "w") // WRITE IT.
                    {
                        //notify R-pi
                        pc.printf("[G,%s]", recbufArr[3].c_str());
                        //WRITE IT
                        DoutArr[ID] = atoi(recbufArr[2].c_str());
                    }
                    else if (recbufArr[0] == "r")
                    {
                        if (DinArr[ID] == 1)
                            {pc.printf("[H,%s]", recbufArr[2].c_str());}
                        else if (DinArr[ID] == 0)
                            {pc.printf("[L,%s]", recbufArr[2].c_str());}
                        else {pc.printf(err);}
                    }
                    //else{pc.printf("[E,%s]", recbufArr[3].c_str());}//impossible to get here.
                } // end of valid
                else// TODO what if tid go south
                {
                    if (is_tid(recbufArr.back()))
                        {pc.printf("[E,%s]", recbufArr.back().c_str());}
                    else
                        {pc.printf("[E,%s]", "non");}
                }
                //******************** Reset buf and flags *********************//
                recbuf = "";
                is_completed = false;
                is_valid = false;
            }
        } // end of if(readable())
    } //end of while
}// end of main 

