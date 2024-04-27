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
    if progress == 0:
        info(job_title)
    if progress == length - 1:
        print("") 
    if length != 0:        
        progress = int((progress * 100) / length)
    else:
        progress = 100
    print(" %d%%" % progress,end=" ",flush=True)


def concatenate_elements(arr):  
    # 使用join方法将数组元素拼接成字符串  
    str_elements = ', '.join(map(str, arr))  
    # 如果数组长度超过20，则在拼接的字符串的第20个元素后添加"...and so on"  
    if len(arr) > 20:  
        # 使用字符串切片和格式化字符串来拼接结果  
        str_elements = f"{', '.join(map(str, arr[:20]))}...and so on"  
    return str_elements      