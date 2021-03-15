import sys
import math
# import numpy as np

# redirect stdin
sys.stdin = open("training-data/training-1.txt", "r")

def read_data():
    ''' 读取数据，返回: {"pms": PMS, "vms": VMS, "reqs": REQUESTS} '''

    # 可以采购的服务器类型数量: int[1, 100]
    PMS_NUM = int(sys.stdin.readline())
    # 服务器:
    # [{"pmType": 型号,
    #   "cpu": CPU核数,
    #   "memory": 内存大小,
    #   "hardCost": 硬件成本,
    #   "dailyCost": 每日能耗成本}
    # , ...]
    PMS = []
    for i in range(PMS_NUM):
        s = sys.stdin.readline().strip().lstrip("(").rstrip(")").replace(" ", "").split(",")
        PMS.append({"pmType": s[0], "cpu": int(s[1]), "memory": int(s[2]), "hardCost": int(s[3]), "dailyCost": int(s[4])})

    # 售卖的虚拟机类型数量: int[1, 1000]
    VMS_NUM = int(sys.stdin.readline())
    # 虚拟机:
    # [{"vmType": 型号,
    #   "cpu": CPU核数,
    #   "memory": 内存大小,
    #   "isDual": 是否双节点部署}
    # , ...]
    VMS = []
    for i in range(VMS_NUM):
        s = sys.stdin.readline().strip().lstrip("(").rstrip(")").replace(" ", "").split(",")
        VMS.append({"vmType": s[0], "cpu": int(s[1]), "memory": int(s[2]), "isDual": bool(int(s[3]))})

    # 请求天数: int[1, 1000]
    DAYS = int(sys.stdin.readline())
    # 每天的用户请求序列: (总请求数<10**5)
    # [{"num": 当天请求数,
    #   "reqs": [{"command": "add"/"del",
    #                 "vmType": 虚拟机型号(del无此项),
    #                 "vmId": 虚拟机id}
    #               , ...]
    #  }
    # , ...]
    REQUESTS = []
    for i in range(DAYS):
        dailyReq = {}
        dailyReq["num"] = int(sys.stdin.readline())
        dailyReq["reqs"] = []
        for j in range(dailyReq["num"]):
            s = sys.stdin.readline().strip().lstrip("(").rstrip(")").replace(" ", "").split(",")
            if s[0] == "add":
                dailyReq["reqs"].append({"command": s[0], "vmType": s[1], "vmId": s[2]})
            else:
                dailyReq["reqs"].append({"command": s[0], "vmId": s[1]})
        REQUESTS.append(dailyReq)

    DATA = {"pms": PMS, "vms": VMS, "reqs": REQUESTS}
    return DATA


def output(expansion, migration, decision):
    ''' 
    输入参数: 每一天的决策信息，列表
    [{
        "expansion": [{"pmType": 服务器型号, "num": 购买数量}, ...],
        "migration": [{"vmId": 虚拟机ID, "pmId": 目的服务器ID, "node": 目的服务器节点(可选)}, ...],
        "decision": [{"pmId": 服务器ID, "node": 部署节点(可选)}, ...]
     }, ...]
    '''
    pass


data = read_data()
print(data)

if __name__ == "__main__":
    # to read standard input # process # to write standard output # sys.stdout.flush()
    pass
