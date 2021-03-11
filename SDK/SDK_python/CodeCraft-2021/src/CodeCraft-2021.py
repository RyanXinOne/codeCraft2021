import sys

# redirect stdin
sys.stdin = open("training-data/training-1.txt", "r")

def read_data():
    ''' 读取数据，返回: {"servers": SERVERS, "vms": VMS, "requests": REQUESTS} '''

    # 可以采购的服务器类型数量: int[1, 100]
    SERVERS_NUM = int(sys.stdin.readline())
    # 服务器:
    # [{"servertype": 型号,
    #   "cpu": CPU核数,
    #   "memory": 内存大小,
    #   "hardCost": 硬件成本,
    #   "dailyCost": 每日能耗成本}
    # , ...]
    SERVERS = []
    for i in range(SERVERS_NUM):
        s = sys.stdin.readline().strip().lstrip("(").rstrip(")").replace(" ", "").split(",")
        SERVERS.append({"servertype": s[0], "cpu": int(s[1]), "memory": int(s[2]), "hardCost": int(s[3]), "dailyCost": int(s[4])})

    # 售卖的虚拟机类型数量: int[1, 1000]
    VMS_NUM = int(sys.stdin.readline())
    # 虚拟机:
    # [{"vmtype": 型号,
    #   "cpu": CPU核数,
    #   "memory": 内存大小,
    #   "isDual": 是否双节点部署}
    # , ...]
    VMS = []
    for i in range(VMS_NUM):
        s = sys.stdin.readline().strip().lstrip("(").rstrip(")").replace(" ", "").split(",")
        VMS.append({"vmtype": s[0], "cpu": int(s[1]), "memory": int(s[2]), "isDual": bool(int(s[3]))})

    # 请求天数: int[1, 1000]
    DAYS = int(sys.stdin.readline())
    # 每天的用户请求序列: (总请求数<10**5)
    # [{"num": 当天请求数,
    #   "requests": [{"command": "add"/"del",
    #                 "vmtype": 虚拟机型号(del无此项),
    #                 "vmid": 虚拟机id}
    #               , ...]
    #  }
    # , ...]
    REQUESTS = []
    for i in range(DAYS):
        dailyReq = {}
        dailyReq["num"] = int(sys.stdin.readline())
        dailyReq["requests"] = []
        for j in range(dailyReq["num"]):
            s = sys.stdin.readline().strip().lstrip("(").rstrip(")").replace(" ", "").split(",")
            if s[0] == "add":
                dailyReq["requests"].append({"command": s[0], "vmtype": s[1], "vmid": s[2]})
            else:
                dailyReq["requests"].append({"command": s[0], "vmid": s[1]})
        REQUESTS.append(dailyReq)

    DATA = {"servers": SERVERS, "vms": VMS, "requests": REQUESTS}
    return DATA


def output(expansion, migration, decision):
    ''' 
    输入参数: 每一天的决策信息，列表
    [{
        "expansion": [{"servertype": 服务器型号, "num": 购买数量}, ...],
        "migration": [{"vmid": 虚拟机ID, "serverid": 目的服务器ID, "node": 目的服务器节点(可选)}, ...],
        "decision": [{"serverid": 服务器ID, "node": 部署节点(可选)}, ...]
     }, ...]
    '''
    pass


data = read_data()
print(data)

if __name__ == "__main__":
    # to read standard input # process # to write standard output # sys.stdout.flush()
    pass
