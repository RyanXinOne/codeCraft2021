import sys

DEBUG = True

if DEBUG:
    import time
    # redirect stdin/stdout
    sys.stdin = open("training-data/training-2.txt", "r")
    sys.stdout = open("output.txt", "w")

# settings
MAX_ITERATIONS = 10000
MAX_MIGRATION = 30
PLACEMENT_RELAX = 8

class VectorCalc:
    @staticmethod
    def add(a, b):
        return [a[0] + b[0], a[1] + b[1]]
    
    @staticmethod
    def minus(a, b):
        return [a[0] - b[0], a[1] - b[1]]

    @staticmethod
    def div2(a):
        return [a[0] // 2, a[1] // 2]
    
    @staticmethod
    def ge(a, b):
        return a[0] >= b[0] and a[1] >= b[1]


class DataIO:
    @staticmethod
    def read_data():
        ''' 读取数据，返回: pms, vms, requests, days '''

        # 读取可采购的服务器类型
        pmsNum = int(sys.stdin.readline())
        pms = {}
        for i in range(pmsNum):
            s = sys.stdin.readline().strip().lstrip("(").rstrip(")").replace(" ", "").split(",")
            pms[s[0]] = {"cpu": int(s[1]), "memory": int(s[2]), "hardCost": int(s[3]), "dailyCost": int(s[4])}
            pms[s[0]] = {"size": [int(s[1]), int(s[2])], "cost": [int(s[3]), int(s[4])]}

        # 读取供售卖的虚拟机类型
        vmsNum = int(sys.stdin.readline())
        vms = {}
        for i in range(vmsNum):
            s = sys.stdin.readline().strip().lstrip("(").rstrip(")").replace(" ", "").split(",")
            vms[s[0]] = {"size": [int(s[1]), int(s[2])], "isDual": bool(int(s[3]))}

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

        return pms, vms, requests, days

    @staticmethod
    def write_output_day(purchased, migration, placement):
        ''' 
        输入参数: 一天的决策信息
            "purchased": [(服务器型号, 购买数量), ...]
            "migration": [(虚拟机ID, 目的服务器ID, 目的服务器节点(可选)), ...]
            "placement": [(服务器ID, 部署节点(可选)), ...]
        '''
        purchase_num = len(purchased)
        sys.stdout.write("(purchase, " + str(purchase_num) + ")\n")
        for i in range(purchase_num):
            sys.stdout.write("(" + purchased[i][0] + ", " + str(purchased[i][1]) + ")\n")
        
        migration_num = len(migration)
        sys.stdout.write("(migration, " + str(migration_num) + ")\n")
        for i in range(migration_num):
            info = migration[i]
            sys.stdout.write("(" + info[0])
            for item in info[1:]:
                sys.stdout.write(", " + str(item))
            sys.stdout.write(")\n")
        
        for i in range(len(placement)):
            info = placement[i]
            sys.stdout.write("(" + str(info[0]))
            for item in info[1:]:
                sys.stdout.write(", " + item)
            sys.stdout.write(")\n")

    @staticmethod
    def generate_output(purchased, migrated_vmIds, add_reqs):
        '''生成需要的输出格式'''
        migration = []
        for vmId in migrated_vmIds:
            vm = STOCK_VMS[vmId]
            info = [vmId, vm["pmId"]]
            if vm["node"]:
                info.append(vm["node"])
            migration.append(tuple(info))
        
        placement = []
        for req in add_reqs:
            vmId = req[0]
            vm = STOCK_VMS[vmId]
            info = [vm["pmId"]]
            if vm["node"]:
                info.append(vm["node"])
            placement.append(tuple(info))
        
        DataIO.write_output_day(purchased, migration, placement)


class Auxiliary:
    @staticmethod
    def calc_comp_res(size):
        '''计算资源综合值'''
        return size[0] ** 2 + size[1] ** 2

    @staticmethod
    def calc_perc_util(pmId):
        '''计算某一台服务器的资源利用率'''
        pm = OWNED_PMS[pmId]
        # 计算总资源综合值
        total_size = ALL_PMS[pm["pmType"]]["size"]
        total_comp_res = Auxiliary.calc_comp_res(total_size)
        # 计算已分配资源综合值
        used_size = VectorCalc.minus(total_size, VectorCalc.add(pm["A"], pm["B"]))
        assigned_comp_res = Auxiliary.calc_comp_res(used_size)
        # 输出利用率
        return assigned_comp_res / total_comp_res

    @staticmethod
    def calc_comp_cost(pmType, days):
        '''计算综合开销'''
        a = 1
        cost = ALL_PMS[pmType]["cost"]
        return cost[0] + a * days * cost[1]

    @staticmethod
    def calc_total_size(reqs):
        '''计算输入虚拟机列表的总所需资源（均分入两个节点中）'''
        containerA = [0, 0]
        containerB = [0, 0]
        vmNodeInfo = {}
        # 遍历虚拟机
        for req in reqs:
            vmId = req[0]
            vmType = req[1]
            vmSize = ALL_VMS[vmType]["size"]
            # 判断单双节点
            if ALL_VMS[vmType]["isDual"]:
                containerA = VectorCalc.add(containerA, VectorCalc.div2(vmSize))
                containerB = VectorCalc.add(containerB, VectorCalc.div2(vmSize))
                vmNodeInfo[vmId] = None
            else:
                # 将虚拟机放入负载较小的节点
                if Auxiliary.calc_comp_res(containerA) <= Auxiliary.calc_comp_res(containerB):
                    containerA = VectorCalc.add(containerA, vmSize)
                    vmNodeInfo[vmId] = "A"
                else:
                    containerB = VectorCalc.add(containerB, vmSize)
                    vmNodeInfo[vmId] = "B"
        return containerA, containerB, vmNodeInfo

    @staticmethod
    def sort_pms_by_percUtil(pmIds, reverse=False):
        '''将输入服务器id按照资源利用率递增/减排序，输出排序后的服务器id列表'''
        # 对每台服务器计算资源利用率
        pms = [(pmId, Auxiliary.calc_perc_util(pmId)) for pmId in pmIds]
        # 按资源利用率排序
        pms.sort(key=lambda x: x[1], reverse=reverse)
        # 输出服务器ids
        return [pm[0] for pm in pms]

    @staticmethod
    def sort_pms_by_compCost(pmTypes, days, reverse=False):
        '''将输入服务器类型按照资源利用率递增/减排序，输出排序后的服务器类型列表'''
        # 对每台服务器计算综合开销
        pms = [(pmType, Auxiliary.calc_comp_cost(pmType, days)) for pmType in pmTypes]
        # 按综合开销排序
        pms.sort(key=lambda x: x[1], reverse=reverse)
        # 输出服务器ids
        return [pm[0] for pm in pms]

    @staticmethod
    def sort_reqs_by_compRes(reqs, reverse=False):
        '''按综合资源值排序虚拟机请求'''
        rs = [(req, Auxiliary.calc_comp_res(ALL_VMS[req[1]]["size"])) for req in reqs]
        # 按综合资源排序
        rs.sort(key=lambda x: x[1], reverse=reverse)
        # 输出服务器ids
        return [req[0] for req in rs]

    @staticmethod
    def try_assign_vm(vmId, vmType, pmId):
        '''尝试将一个虚拟机放入一个服务器，返回该操作是否成功的布尔值'''
        pm = OWNED_PMS[pmId]
        vmSize = ALL_VMS[vmType]["size"]
        # 若vm为双节点
        if ALL_VMS[vmType]["isDual"]:
            if VectorCalc.ge(pm["A"], VectorCalc.div2(vmSize)) and VectorCalc.ge(pm["B"], VectorCalc.div2(vmSize)):
                # 允许放入
                STOCK_VMS[vmId] = {"vmType": vmType, "pmId": pmId, "node": None}
                pm["vms"].add(vmId)
                pm["A"] = VectorCalc.minus(pm["A"], VectorCalc.div2(vmSize))
                pm["B"] = VectorCalc.minus(pm["B"], VectorCalc.div2(vmSize))
                return True
            else:
                return False
        # 若vm为单节点
        else:
            # 选取资源综合值较低的节点
            nodeSize = VectorCalc.div2(ALL_PMS[pm["pmType"]]["size"])
            sizeA = VectorCalc.minus(nodeSize, pm["A"])
            sizeB = VectorCalc.minus(nodeSize, pm["B"])
            node = "A" if Auxiliary.calc_comp_res(sizeA) <= Auxiliary.calc_comp_res(sizeB) else 'B'
            if VectorCalc.ge(pm[node], vmSize):
                # 允许放入
                STOCK_VMS[vmId] = {"vmType": vmType, "pmId": pmId, "node": node}
                pm["vms"].add(vmId)
                pm[node] = VectorCalc.minus(pm[node], vmSize)
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
            pm["A"] = VectorCalc.add(pm["A"], VectorCalc.div2(vmSize))
            pm["B"] = VectorCalc.add(pm["B"], VectorCalc.div2(vmSize))
        else:
            pm[node] = VectorCalc.add(pm[node], vmSize)


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
    '''执行迁移策略，输出经过迁移的虚拟机id'''
    constraint_num = min(MAX_MIGRATION, len(STOCK_VMS) // 200)
    migration_num = 0
    migrated = []
    # 将服务器按既定策略递增排序
    length = len(OWNED_PMS)
    pmIds = list(range(length))
    pmIds = Auxiliary.sort_pms_by_percUtil(pmIds)
    # 遍历服务器0到n-1
    for i in range(length):
        pmId = pmIds[i]
        # 遍历服务器i中的虚拟机资源
        for vmId in OWNED_PMS[pmId]["vms"].copy():
            vm = STOCK_VMS[vmId]
            # 遍历服务器n-1到i+1
            for j in range(length - 1, i, -1):
                # 尝试迁移到新服务器
                isAssigned = Auxiliary.try_assign_vm(vmId, vm["vmType"], pmIds[j])
                # 若迁移成功
                if isAssigned:
                    # 从旧服务器中删除
                    Auxiliary.delete_vm(vmId, vm["vmType"], vm["pmId"], vm["node"])
                    migrated.append(vmId)
                    migration_num += 1
                    # 检查是否达到约束限制
                    if migration_num == constraint_num:
                        return migrated
                    # 重新排序服务器j到n-1
                    pmIds = pmIds[:j] + Auxiliary.sort_pms_by_percUtil(pmIds[j:])
                    break
            else:
                # 优化：若无法迁移，则不能使该服务器达到空闲，不再尝试继续迁移
                break
    return migrated

def handle_place(reqs):
    '''执行放置策略'''
    purchase_req = []
    pmIds = list(range(len(OWNED_PMS)))
    # 将服务器按既定策略递减排序
    pmIds = Auxiliary.sort_pms_by_percUtil(pmIds, reverse=True)
    # 将请求按大小递增排序
    reqs = Auxiliary.sort_reqs_by_compRes(reqs)
    # 遍历到达的服务器索引
    n = 0
    length = len(pmIds)
    # 遍历输入的增添请求
    for i, req in enumerate(reqs):
        if i >= MAX_ITERATIONS:
            purchase_req += reqs[i:]
            break
        vmId = req[0]
        vmType = req[1]
        # 遍历服务器
        for j in range(n, length):
            pmId = pmIds[j]
            # 尝试放置请求
            isAssigned = Auxiliary.try_assign_vm(vmId, vmType, pmId)
            # 若放置成功
            if isAssigned:
                # 重新排序服务器0到i
                pmIds = Auxiliary.sort_pms_by_percUtil(pmIds[: j + 1], reverse=True) + pmIds[j + 1 :]
                n = max(j - PLACEMENT_RELAX, 0)
                break
        else:
            # 记录放不下的请求
            purchase_req += reqs[i:]
            break
    return purchase_req

def pre_purchase(reqs, leftDays, pmTypes):
    '''计算需要购买的服务器'''
    purchase_pms = []
    vmIds = [req[0] for req in reqs]
    # 计算总所需资源
    totalA, totalB, vmNodeInfo = Auxiliary.calc_total_size(reqs)
    # 遍历可选购服务器
    for pmType in pmTypes:
        #判断该服务器能否装下所有请求
        nodeSize = VectorCalc.div2(ALL_PMS[pmType]["size"])
        if VectorCalc.ge(nodeSize, totalA) and VectorCalc.ge(nodeSize, totalB):
            # 购买该服务器并分配所有请求
            purchase_pms.append({"pmType": pmType, "vms": set(vmIds), "A": VectorCalc.minus(nodeSize, totalA), "B": VectorCalc.minus(nodeSize, totalB)})
            break
    else:
        # 二分请求，递归购买
        n = len(reqs)
        vmNodeInfo = {}
        tmp_pms, tmp_vms = pre_purchase(reqs[: n // 2], leftDays, pmTypes)
        purchase_pms += tmp_pms
        vmNodeInfo.update(tmp_vms)
        tmp_pms, tmp_vms = pre_purchase(reqs[n // 2 :], leftDays, pmTypes)
        purchase_pms += tmp_pms
        vmNodeInfo.update(tmp_vms)

    return purchase_pms, vmNodeInfo
    
def handle_purchase(reqs, leftDays):
    '''执行购买，更新拥有服务器和存量虚拟机，返回购买信息'''
    vmTypeInfo = dict(reqs)
    # 将可选购服务器按综合开销递增排序
    pmTypes = [pmType for pmType in ALL_PMS]
    pmTypes = Auxiliary.sort_pms_by_compCost(pmTypes, leftDays)
    # 计算购买需求
    purchase_pms, vmNodeInfo = pre_purchase(reqs, leftDays, pmTypes)
    # 将需要购买的服务器按照类型排序
    purchase_pms.sort(key=lambda x: x["pmType"])
    # 保存购买的服务器类型和数量
    types = []
    type_num = {}
    # 放置服务器和虚拟机
    pmId = len(OWNED_PMS)
    for pm in purchase_pms:
        if pm["pmType"] not in type_num:
            types.append(pm["pmType"])
        type_num[pm["pmType"]] = type_num.get(pm["pmType"], 0) + 1
        OWNED_PMS.append(pm)
        # 加入存量虚拟机
        for vmId in pm["vms"]:
            STOCK_VMS[vmId] = {"vmType": vmTypeInfo[vmId], "pmId": pmId, "node": vmNodeInfo[vmId]}
        pmId += 1
    
    return [(t, type_num[t]) for t in types]
    

def final_cleanup(reqs):
    '''执行最后清理'''
    for vmId in reqs:
        vm = STOCK_VMS[vmId]
        Auxiliary.delete_vm(vmId, vm["vmType"], vm["pmId"], vm["node"])
        # 从存量虚拟机中删除
        STOCK_VMS.pop(vmId)


if __name__ == "__main__":
    # to read standard input # process # to write standard output # sys.stdout.flush()
    if DEBUG:
        start_time = time.time()
    
    ALL_PMS, ALL_VMS, REQS, all_days = DataIO.read_data()

    OWNED_PMS = []
    STOCK_VMS = {}

    for d, req in enumerate(REQS):
        sys.stderr.write(str(d) + "\n")
        # daily operation
        cleanup_req = handle_delete(req["del"])
        migrated_vmIds = handle_migration()
        purchase_req = handle_place(req["add"])
        purchased = handle_purchase(purchase_req, all_days - d)
        final_cleanup(cleanup_req)

        # daily output
        DataIO.generate_output(purchased, migrated_vmIds, req["add"])

    sys.stdout.flush()

    if DEBUG:
        end_time = time.time()
        sys.stderr.write("time cost: " + str(end_time - start_time) + "\n")
