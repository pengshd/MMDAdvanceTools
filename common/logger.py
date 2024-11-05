from datetime import datetime

swtitch = True
debug_switch = False


def info(str, end="\n", flush=False):
    if swtitch:
        formatted_datetime = (
            "[" + datetime.now().strftime("%H:%M:%S.%f")[:-3] + " INFO]"
        )
        print_str = formatted_datetime + str
        if str.startswith("\r"):
            print_str = str[0] + formatted_datetime + str[1:]
        print(print_str, end=end, flush=flush)


def debug(str, end="\n", flush=False):
    if debug_switch:
        # formatted_datetime = "["+datetime.now().strftime('%H:%M:%S.%f')[:-3]+" DEBUG]"
        formatted_datetime = ""
        print(formatted_datetime + str, end=end, flush=flush)
    pass


class ProgressBar:

    progress = 0
    length = 0
    job_title = ""

    def __init__(self, job_title, length):
        self.length = length
        self.job_title = job_title

    def show_progress_bar(self):
        percent = 0
        self.progress += 1
        if self.length != 0:
            percent = int((self.progress * 100) / self.length)
        else:
            percent = 100
        if self.progress == 1:
            info(f"{self.job_title}, progress = 0%, all steps = {self.length}")
        else:
            info(
                f"\r{self.job_title}, progress = {percent}%, step = {self.progress}",
                end="",
            )
        if self.progress == self.length:
            print("")


def concatenate_elements(arr):
    # 使用join方法将数组元素拼接成字符串
    str_elements = ", ".join(map(str, arr))
    # 如果数组长度超过20，则在拼接的字符串的第20个元素后添加"...and so on"
    if len(arr) > 20:
        # 使用字符串切片和格式化字符串来拼接结果
        str_elements = f"{', '.join(map(str, arr[:20]))}...and so on"
    return str_elements
