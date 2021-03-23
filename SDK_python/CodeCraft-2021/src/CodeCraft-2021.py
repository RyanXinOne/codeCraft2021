import sys
import math
import numpy as np

# redirect stdin
sys.stdin = open("training-data/training-1.txt", "r")


class DataIO:
    @staticmethod
    def read_data():
        ''' 读取数据，返回: pms, vms, requests '''

        # 读取可采购的服务器类型
        pmsNum = int(sys.stdin.readline())
        pms = {}
        for i in range(pmsNum):
            s = sys.stdin.readline().strip().lstrip("(").rstrip(")").replace(" ", "").split(",")
            pms[s[0]] = {"cpu": int(s[1]), "memory": int(s[2]), "hardCost": int(s[3]), "dailyCost": int(s[4])}
            pms[s[0]] = {"size": np.array([int(s[1]), int(s[2])], dtype=np.uint32), "cost": np.array([int(s[3]), int(s[4])], dtype=np.uint32)}

        # 读取供售卖的虚拟机类型
        vmsNum = int(sys.stdin.readline())
        vms = {}
        for i in range(vmsNum):
            s = sys.stdin.readline().strip().lstrip("(").rstrip(")").replace(" ", "").split(",")
            vms[s[0]] = {"size": np.array([int(s[1]), int(s[2])], dtype=np.uint32), "isDual": bool(int(s[3]))}

        # 读取以天为单位的用户请求序列
        days = int(sys.stdin.readline())
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

    @staticmethod
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


class Auxiliary:
    @staticmethod
    def calc_comp_res(size):
        '''计算资源综合值'''
        return size[0] ** 2 + size[1] ** 2

    @staticmethod
    def calc_comp_cost(cost, days):
        '''计算综合开销'''
        a = 1
        return cost[0] + a * days * cost[1]

    @staticmethod
    def calc_perc_util(pmId):
        '''计算某一台服务器的资源利用率'''
        pm = OWNED_PMS[pmId]
        # 计算总资源综合值
        total_size = ALL_PMS[pm["pmType"]]["size"]
        total_comp_res = Auxiliary.calc_comp_res(total_size)
        # 计算已分配资源综合值
        used_size = total_size - pm["A"] - pm["B"]
        assigned_comp_res = Auxiliary.calc_comp_res(used_size)
        # 输出利用率
        return assigned_comp_res / total_comp_res

    @staticmethod
    def sort_pms(pmIds, reverse=False):
        '''将输入服务器id按照既定策略递增/减排序，输出排序后的服务器id列表'''
        # 对每台服务器计算资源利用率
        pms = [(pmId, Auxiliary.calc_perc_util(pmId)) for pmId in pmIds]
        # 按资源利用率排序
        pms.sort(key=lambda x: x[1], reverse=reverse)
        # 输出服务器ids
        return [pm[0] for pm in pms]

    @staticmethod
    def try_assign_vm(vmId, vmType, pmId):
        '''尝试将一个虚拟机放入一个服务器，返回该操作是否成功的布尔值'''
        pm = OWNED_PMS[pmId]
        vmSize = ALL_VMS[vmType]["size"]
        # 若vm为双节点
        if ALL_VMS[vmType]["isDual"]:
            if (pm["A"] >= vmSize // 2).all() and (pm["B"] >= vmSize // 2).all():
                # 允许放入
                STOCK_VMS[vmId] = {"vmType": vmType, "pmId": pmId, "node": None}
                pm["vms"].add(vmId)
                pm["A"] -= vmSize // 2
                pm["B"] -= vmSize // 2
                return True
            else:
                return False
        # 若vm为单节点
        else:
            # 选取资源综合值较低（剩余空间较多）的节点
            node = "A" if Auxiliary.calc_comp_res(pm["A"]) >= Auxiliary.calc_comp_res(pm["B"]) else 'B'
            if (pm[node] >= vmSize).all():
                # 允许放入
                STOCK_VMS[vmId] = {"vmType": vmType, "pmId": pmId, "node": node}
                pm["vms"].add(vmId)
                pm[node] -= vmSize
                return True
            else:
                return False

    @staticmethod
    def delete_vm(vmId, vmType, pmId, node):
        '''从服务器中删除一个虚拟机'''
        pm = OWNED_PMS[pmId]
        # 从服务器的虚拟机集合中删除
        pm["vms"].remove(vmId)
        # 更新服务器剩余资源
        vmSize = ALL_VMS[vmType]["size"]
        if node is None:
            pm["A"] += vmSize // 2
            pm["B"] += vmSize // 2
        else:
            pm[node] += vmSize


def handle_delete(reqs):
    '''执行删除策略'''
    cleanup_req = []
    for vmId in reqs:
        # 判断需要删除的资源是否存在
        if vmId in STOCK_VMS:
            vm = STOCK_VMS[vmId]
            Auxiliary.delete_vm(vmId, vm["vmType"], vm["pmId"], vm["node"])
            # 从存量虚拟机中删除
            STOCK_VMS.pop(vmId)
        else:
            cleanup_req.append(vmId)
    return cleanup_req

def handle_migration():
    '''执行迁移策略'''
    constraint_num = len(STOCK_VMS) // 200
    migration_num = 0
    # 将服务器按既定策略递增排序
    pmIds = [pmId for pmId in OWNED_PMS]
    pmIds = Auxiliary.sort_pms(pmIds)
    n = len(pmIds)
    # 遍历服务器0到n-1
    for i in range(n):
        pmId = pmIds[i]
        # 遍历服务器i中的虚拟机资源
        for vmId in OWNED_PMS[pmId]["vms"]:
            vm = STOCK_VMS[vmId]
            # 遍历服务器n-1到i+1
            for j in range(n - 1, i, -1):
                backupVm = vm.copy()
                # 尝试迁移到新服务器
                isAssigned = Auxiliary.try_assign_vm(vmId, vm["vmType"], pmIds[j])
                # 若迁移成功
                if isAssigned:
                    # 从旧服务器中删除
                    Auxiliary.delete_vm(vmId, backupVm["vmType"], backupVm["pmId"], backupVm["node"])
                    migration_num += 1
                    # 检查是否达到约束限制
                    if migration_num == constraint_num:
                        return
                    # 重新排序服务器j到n-1
                    pmIds = pmIds[:j] + Auxiliary.sort_pms(pmIds[j:])
                    break

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


if __name__ == "__main__":
    # to read standard input # process # to write standard output # sys.stdout.flush()
    ALL_PMS, ALL_VMS, REQS = DataIO.read_data()

    OWNED_PMS = {}
    STOCK_VMS = {}

    for req in REQS:
        cleanup_req = handle_delete(req["del"])
        handle_migration()
        purchase_req = handle_place(req["add"])
        handle_purchase(purchase_req)
        final_cleanup(cleanup_req)

    print(OWNED_PMS)
