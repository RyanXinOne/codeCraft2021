import sys
import math
# import numpy as np

# redirect stdin
sys.stdin = open("training-data/training-1.txt", "r")

def read_data():
    ''' 读取数据，返回: pms, vms, requests '''

    # 可以采购的服务器类型数量: int[1, 100]
    pmsNum = int(sys.stdin.readline())
    # 服务器:
    # pms = {服务器型号:
    #   {"cpu": CPU核数,
    #    "memory": 内存大小,
    #    "hardCost": 硬件成本,
    #    "dailyCost": 每日能耗成本}
    # , ...}
    pms = {}
    for i in range(pmsNum):
        s = sys.stdin.readline().strip().lstrip("(").rstrip(")").replace(" ", "").split(",")
        pms[s[0]] = {"cpu": int(s[1]), "memory": int(s[2]), "hardCost": int(s[3]), "dailyCost": int(s[4])}

    # 售卖的虚拟机类型数量: int[1, 1000]
    vmsNum = int(sys.stdin.readline())
    # 虚拟机:
    # vms = {虚拟机型号:
    #  {"cpu": CPU核数,
    #   "memory": 内存大小,
    #   "isDual": 是否双节点部署}
    # , ...}
    vms = {}
    for i in range(vmsNum):
        s = sys.stdin.readline().strip().lstrip("(").rstrip(")").replace(" ", "").split(",")
        vms[s[0]] = {"cpu": int(s[1]), "memory": int(s[2]), "isDual": bool(int(s[3]))}

    # 请求天数: int[1, 1000]
    days = int(sys.stdin.readline())
    # 每天的用户请求序列: (总请求数<10**5)
    # requests = [
    #  {"add": [(虚拟机id, 虚拟机型号), ...],
    #   "del": [虚拟机id, ...]
    #  }
    # , ...]
    requests = []
    for i in range(days):
        reqsNum = int(sys.stdin.readline())
        dailyReq = {}
        dailyReq["add"] = []
        dailyReq["del"] = []
        for j in range(reqsNum):
            s = sys.stdin.readline().strip().lstrip("(").rstrip(")").replace(" ", "").split(",")
            if s[0] == "add":
                dailyReq["add"].append((s[2], s[1]))
            else:
                dailyReq["del"].append(s[1])
        requests.append(dailyReq)

    return pms, vms, requests

def write_output(expansion, migration, decision):
    ''' 
    输入参数: 每一天的决策信息，列表
    [{
        "expansion": [{"pmType": 服务器型号, "num": 购买数量}, ...],
        "migration": [{"vmId": 虚拟机ID, "pmId": 目的服务器ID, "node": 目的服务器节点(可选)}, ...],
        "decision": [{"pmId": 服务器ID, "node": 部署节点(可选)}, ...]
     }, ...]
    '''
    pass

def calc_comp_res(cpu, memory):
    '''计算资源综合值'''
    return cpu ** 2 + memory ** 2

def calc_comp_cost(hardCost, dailyCost, days):
    '''计算综合开销'''
    a = 1
    return hardCost + a * days * dailyCost

def calc_perc_util(comp1, comp2):
    '''计算资源利用率'''
    return comp1 / comp2

def handle_delete(reqs):
    '''执行删除策略'''
    cleanup_req = []
    for vmId in reqs:
        # 判断需要删除的资源是否存在
        if vmId in ASSIGNED_VMS.keys():
            pmId = ASSIGNED_VMS[vmId]["pmId"]
            node = ASSIGNED_VMS[vmId]["node"]
            # 从服务器中删除
            OWNED_PMS[pmId][node].remove(vmId)
            # 从虚拟机中删除
            ASSIGNED_VMS.pop(vmId)
        else:
            cleanup_req.append(vmId)
    return cleanup_req

def handle_migration():
    '''执行迁移策略'''
    pass

def handle_place(reqs):
    '''执行放置策略'''
    pass

def handle_purchase(reqs):
    '''执行购买策略'''
    pass
    bought_pms = {}
    OWNED_PMS.update(bought_pms)

def final_cleanup(reqs):
    '''执行最后清理'''
    pass


ALL_PMS, ALL_VMS, REQS = read_data()

# 已拥有服务器
# OWNED_PMS = {服务器id:
#   {"pmType": 服务器型号,
#    "A": [虚拟机id, ...],
#    "B": [虚拟机id, ...],
#    "d": [虚拟机id, ...]}
# , ...}
OWNED_PMS = {}
# 已分配虚拟机
# ASSIGNED_VMS = {虚拟机id:
#   {"pmId": 所在服务器id,
#    "node": 所在服务器节点("A"/"B"/"d")}
# , ...}
ASSIGNED_VMS = {}
for req in REQS:
    cleanup_req = handle_delete(req["del"])
    handle_migration()
    purchase_req = handle_place(req["add"])
    handle_purchase(purchase_req)
    final_cleanup(cleanup_req)

print(OWNED_PMS)


if __name__ == "__main__":
    # to read standard input # process # to write standard output # sys.stdout.flush()
    pass
