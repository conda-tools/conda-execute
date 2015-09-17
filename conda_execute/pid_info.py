import psutil


for proc in psutil.process_iter():
    try:
        pinfo = proc.as_dict(attrs=['pid', 'name', 'create_time'])
    except psutil.NoSuchProcess:
        pass
    else:
        print(pinfo)
