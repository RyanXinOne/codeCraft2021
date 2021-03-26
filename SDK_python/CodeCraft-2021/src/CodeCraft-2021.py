import sys

DEBUG = True

if DEBUG:
    import time
    dataset_no = 2
    # redirect stdin/stdout
    sys.stdin = open("training-data/training-"+str(dataset_no)+".txt", "r")
    sys.stdout = open("output"+str(dataset_no)+".txt", "w")

# settings
MAX_MIGRATION = 200
MAX_FAIL_MIGRATION = 25
MIGRATION_GAP = 10
MIGRATION_RELAX_SIZE = 2
PLACEMENT_RELAX_SIZE = 300
ALPHA = 0.8


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
    def read_configure():
        ''' 读取配置数据，返回: pms, vms, days '''
        # 读取可采购的服务器类型
        pmsNum = int(sys.stdin.readline())
        pms = {}
        for i in range(pmsNum):
            s = sys.stdin.readline().strip().lstrip("(").rstrip(")").replace(" ", "").split(",")
            pms[s[0]] = {"size": [int(s[1]), int(s[2])], "cost": [int(s[3]), int(s[4])]}

        # 读取供售卖的虚拟机类型
        vmsNum = int(sys.stdin.readline())
        vms = {}
        for i in range(vmsNum):
            s = sys.stdin.readline().strip().lstrip("(").rstrip(")").replace(" ", "").split(",")
            vms[s[0]] = {"size": [int(s[1]), int(s[2])], "isDual": bool(int(s[3]))}

        # 读取请求天数
        days = int(sys.stdin.readline())

        return pms, vms, days

    @staticmethod
    def read_requests_day():
        '''读取一天的请求'''
        reqsNum = int(sys.stdin.readline())
        dailyReq = {}
        dailyReq["add"] = []
        dailyReq["del"] = set()
        for j in range(reqsNum):
            s = sys.stdin.readline().strip().lstrip("(").rstrip(")").replace(" ", "").split(",")
            if s[0] == "add":
                dailyReq["add"].append((s[2], s[1]))
            else:
                dailyReq["del"].add(s[1])
        return dailyReq

    @staticmethod
    def write_output_day(purchased, migration, placement):
        ''' 输出到标准输出流
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
    def generate_output_day(purchased, migrated_vmIds, add_reqs):
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
    def sort_pms_by_percUtil(reverse=False):
        '''将输入服务器id按照资源利用率递增/减排序，输出排序后的服务器id列表'''
        def calc_perc_util(pm):
            '''计算某一台服务器的资源利用率'''
            # 计算总资源综合值
            total_size = ALL_PMS[pm["pmType"]]["size"]
            total_comp_res = Auxiliary.calc_comp_res(total_size)
            # 计算已分配资源综合值
            used_size = VectorCalc.minus(total_size, VectorCalc.add(pm["A"], pm["B"]))
            assigned_comp_res = Auxiliary.calc_comp_res(used_size)
            # 输出利用率
            return assigned_comp_res / total_comp_res

        # 对每台服务器计算资源利用率
        pmIds_w_pu = [(pmId, calc_perc_util(pm)) for pmId, pm in enumerate(OWNED_PMS)]
        # 按资源利用率排序
        pmIds_w_pu.sort(key=lambda x: x[1], reverse=reverse)
        # 输出服务器id和对应percUtil
        return pmIds_w_pu

    @staticmethod
    def sort_pms_by_serverLoad(reverse=False):
        '''将输入服务器id按照服务器负载递增/减排序，输出排序后的服务器id列表'''      
        def calc_server_load(pm):
            '''计算某一台服务器的当前负载'''
            used_size = VectorCalc.minus(ALL_PMS[pm["pmType"]]["size"], VectorCalc.add(pm["A"], pm["B"]))
            return Auxiliary.calc_comp_res(used_size)

        # 对每台服务器计算服务器负载
        pmIds_w_sl = [(pmId, calc_server_load(pm)) for pmId, pm in enumerate(OWNED_PMS)]
        # 排序
        pmIds_w_sl.sort(key=lambda x: x[1], reverse=reverse)
        # 输出服务器id和对应负载
        return pmIds_w_sl

    @staticmethod
    def sort_pms_by_absCapacity(reverse=False):
        '''将输入服务器id按照绝对容积递增/减排序，输出排序后的服务器id列表'''
        def calc_absolute_capacity(pm):
            '''计算某一服务器的绝对容积'''
            totalSize = ALL_PMS[pm["pmType"]]["size"]
            return Auxiliary.calc_comp_res(totalSize)

        # 对每台服务器计算服务器绝对容积
        pmIds_w_absc = [(pmId, calc_absolute_capacity(pm)) for pmId, pm in enumerate(OWNED_PMS)]
        # 排序
        pmIds_w_absc.sort(key=lambda x: x[1], reverse=reverse)
        # 输出服务器id和对应容积
        return pmIds_w_absc

    @staticmethod
    def sort_pms_by_compCost(days, reverse=False):
        '''将输入服务器类型按照资源利用率递增/减排序，输出排序后的服务器类型列表'''
        def calc_comp_cost(pmType, days):
            '''计算综合开销'''
            cost = ALL_PMS[pmType]["cost"]
            return cost[0] + ALPHA * days * cost[1]

        # 对每台服务器计算综合开销
        pmTypes_w_compCost = [(pmType, calc_comp_cost(pmType, days)) for pmType in ALL_PMS]
        # 按综合开销排序
        pmTypes_w_compCost.sort(key=lambda x: x[1], reverse=reverse)
        # 输出服务器类型列表
        return [item[0] for item in pmTypes_w_compCost]

    @staticmethod
    def sort_vms_by_compRes(vmIds, reverse=False):
        '''按综合资源值排序虚拟机id'''
        vmIds_w_compRes = [(vmId, Auxiliary.calc_comp_res(ALL_VMS[STOCK_VMS[vmId]["vmType"]]["size"])) for vmId in vmIds]
        # 按综合资源排序
        vmIds_w_compRes.sort(key=lambda x: x[1], reverse=reverse)
        # 输出虚拟机ids
        return vmIds_w_compRes

    @staticmethod
    def sort_reqs_by_compRes(reqs, reverse=False):
        '''按综合资源值排序虚拟机请求'''
        reqs_w_compRes = [(req, Auxiliary.calc_comp_res(ALL_VMS[req[1]]["size"])) for req in reqs]
        # 按综合资源排序
        reqs_w_compRes.sort(key=lambda x: x[1], reverse=reverse)
        # 输出服务器ids
        return reqs_w_compRes

    @staticmethod
    def insert_pmId_by_measure(item, pmIds_w_measure):
        '''根据既定策略插入服务器id，原列表需为递增序列'''
        length = len(pmIds_w_measure)
        if length == 0:
            return [item]
        median = length // 2

        if item[1] == pmIds_w_measure[median][1]:
            pmIds_w_measure.insert(median, item)
            return pmIds_w_measure
        elif item[1] < pmIds_w_measure[median][1]:
            return Auxiliary.insert_pmId_by_measure(item, pmIds_w_measure[:median]) + pmIds_w_measure[median:]
        else:
            return pmIds_w_measure[:median + 1] + Auxiliary.insert_pmId_by_measure(item, pmIds_w_measure[median + 1:])

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


def handle_migration(delReqs):
    '''执行迁移策略。输出经过迁移的虚拟机id'''
    constraint_num = min(MAX_MIGRATION, len(STOCK_VMS) // 200)
    migration_num = 0
    fail_migration_num = 0
    migrated = set()
    # 将服务器按既定策略递增排序
    length = len(OWNED_PMS)
    pmIds_w_measure = Auxiliary.sort_pms_by_serverLoad()
    # 检查约束限制
    if constraint_num == 0:
        return migrated
    # 遍历服务器0到n-1
    for i in range(length):
        # 升序排序服务器i中的虚拟机资源
        vmIds_w_compRes = Auxiliary.sort_vms_by_compRes(OWNED_PMS[pmIds_w_measure[i][0]]["vms"])
        n = length - 1
        # 遍历服务器i中的虚拟机资源
        for item in vmIds_w_compRes:
            vmId = item[0]
            # 跳过将要被删除的资源
            if vmId in delReqs:
                continue
            vm = STOCK_VMS[vmId]
            # 遍历服务器n-1到i+1
            for j in range(n, i + MIGRATION_GAP, -1):
                pmId = pmIds_w_measure[j][0]
                # 尝试迁移到新服务器
                isAssigned = Auxiliary.try_assign_vm(vmId, vm["vmType"], pmId)
                # 若迁移成功
                if isAssigned:
                    # 从旧服务器中删除
                    Auxiliary.delete_vm(vmId, vm["vmType"], vm["pmId"], vm["node"])
                    migrated.add(vmId)
                    # 检查是否达到约束限制
                    migration_num += 1
                    if migration_num == constraint_num:
                        return migrated
                    n = min(j + MIGRATION_RELAX_SIZE, length - 1)
                    break
            else:
                # 优化：若无法迁移，则不能使该服务器达到空闲，不再尝试继续迁移
                fail_migration_num += 1
                if fail_migration_num == MAX_FAIL_MIGRATION:
                    return migrated
                break
    return migrated

def handle_placement(reqs):
    '''执行放置策略'''
    purchase_req = []
    length = len(OWNED_PMS)
    # 将请求按大小递增排序
    reqs_w_compRes = Auxiliary.sort_reqs_by_compRes(reqs)
    # 将服务器递增排序
    pmIds_w_measure = Auxiliary.sort_pms_by_serverLoad()
    # 记录到达的服务器索引
    n = length - 1
    # 遍历输入的增添请求
    for item in reqs_w_compRes:
        vmId, vmType = item[0]
        # 倒序遍历服务器
        for j in range(n, -1, -1):
            pmId = pmIds_w_measure[j][0]
            # 尝试放置请求
            isAssigned = Auxiliary.try_assign_vm(vmId, vmType, pmId)
            # 若放置成功
            if isAssigned:
                n = min(j + PLACEMENT_RELAX_SIZE, length - 1)
                break
        else:
            # 记录放不下的请求
            purchase_req.append((vmId, vmType))
            n = min(PLACEMENT_RELAX_SIZE, length - 1)
    return purchase_req

def handle_purchase(reqs, leftDays):
    '''执行购买，更新拥有服务器和存量虚拟机，返回购买信息'''

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

    def calc_requirement(reqs, leftDays, pmTypes):
        '''计算需要购买的服务器'''
        purchase_pms = []
        vmIds = [req[0] for req in reqs]
        # 计算总所需资源
        totalA, totalB, vmNodeInfo = calc_total_size(reqs)
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
            tmp_pms, tmp_vms = calc_requirement(reqs[: n // 2], leftDays, pmTypes)
            purchase_pms += tmp_pms
            vmNodeInfo.update(tmp_vms)
            tmp_pms, tmp_vms = calc_requirement(reqs[n // 2 :], leftDays, pmTypes)
            purchase_pms += tmp_pms
            vmNodeInfo.update(tmp_vms)

        return purchase_pms, vmNodeInfo

    vmTypeInfo = dict(reqs)
    # 将可选购服务器按综合开销递增排序
    pmTypes = Auxiliary.sort_pms_by_compCost(leftDays)
    # 计算购买需求
    purchase_pms, vmNodeInfo = calc_requirement(reqs, leftDays, pmTypes)
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

def handle_delete(reqs):
    '''执行删除'''
    for vmId in reqs:
        vm = STOCK_VMS[vmId]
        Auxiliary.delete_vm(vmId, vm["vmType"], vm["pmId"], vm["node"])
        # 从存量虚拟机中删除
        STOCK_VMS.pop(vmId)

if __name__ == "__main__":
    # to read standard input # process # to write standard output # sys.stdout.flush()
    if DEBUG:
        start_time = time.time()
        migration_time = placement_time = purchasing_time = 0
        total_cost = 0
    
    ALL_PMS, ALL_VMS, days = DataIO.read_configure()
    OWNED_PMS = []
    STOCK_VMS = {}

    for d in range(days):
        if DEBUG:
            sys.stderr.write(str(d + 1) + "/" + str(days) + "\n")
        # read daily requests
        req = DataIO.read_requests_day()
        # daily operation
        if DEBUG:
            timeStamp1 = time.time()
        migrated_vmIds = handle_migration(req["del"])
        if DEBUG:
            timeStamp2 = time.time()
            migration_time += (timeStamp2 - timeStamp1)
        purchase_req = handle_placement(req["add"])
        if DEBUG:
            timeStamp1 = time.time()
            placement_time += (timeStamp1 - timeStamp2)
        purchased = handle_purchase(purchase_req, days - d)
        if DEBUG:
            timeStamp2 = time.time()
            purchasing_time += (timeStamp2 - timeStamp1)
        handle_delete(req["del"])
        # daily output
        DataIO.generate_output_day(purchased, migrated_vmIds, req["add"])
        if DEBUG:
            # 计算购买成本
            for pmType, num in purchased:
                total_cost += ALL_PMS[pmType]["cost"][0] * num
            # 计算运维成本
            for pm in OWNED_PMS:
                if pm["vms"]:
                    total_cost += ALL_PMS[pm["pmType"]]["cost"][1]

    sys.stdout.flush()

    if DEBUG:
        end_time = time.time()
        sys.stderr.write("total cost: " + str(total_cost) + "\n")
        sys.stderr.write("total time: " + str(end_time - start_time) + "\n")
        sys.stderr.write("migration time: " + str(migration_time) + "\n")
        sys.stderr.write("placement time: " + str(placement_time) + "\n")
        sys.stderr.write("purchasing time: " + str(purchasing_time) + "\n")
