from datetime import datetime
import sys

def info(str,end = "\n",flush = False):
    formatted_datetime = "["+datetime.now().strftime('%H:%M:%S.%f')[:-3]+" INFO]"
    print(formatted_datetime+str,end=end,flush=flush)

def debug(str,end = "\n",flush = False):
    # formatted_datetime = "["+datetime.now().strftime('%H:%M:%S.%f')[:-3]+" DEBUG]"
    # print(formatted_datetime+str,end=end,flush=flush)
    pass

def show_progress_bar(job_title, progress, length):
    if length != 0:        
        progress = int((progress * 100) / length)
    else:
        progress = 100
    formatted_datetime = "["+datetime.now().strftime('%H:%M:%S.%f')[:-3]+" INFO]"    
    sys.stdout.write("\r  " + formatted_datetime + job_title + " %d%%" % progress)
    sys.stdout.flush()