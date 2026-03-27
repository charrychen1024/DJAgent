#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import csv
import json
import os
import random
import string
from datetime import datetime, timedelta

class DataGenerator:
    def __init__(self, config=None):
        self.config = config or {
            "num_users": 22,  # 2+2+5+5+5+5
            "num_risk_data": 1000,
            "base_dir": os.path.dirname(os.path.abspath(__file__))
        }
        
        # 预定义数据
        self.product_types = ["零担", "整车", "合同物流"]
        self.cargo_types = ["电子产品", "服装", "食品", "建材", "化工品"]
        self.abnormal_types = [
            "重量异常", "超时派送", "未及时签收", "货物损坏", 
            "运费异常", "虚假签收", "路线异常", "包装破损"
        ]
        self.risk_levels = ["低", "中", "高"]
        self.delivery_statuses = ["已签收", "派送中", "已退回"]
        
        # 创建必要的目录
        self._create_directories()
        
    def _create_directories(self):
        """创建数据存储目录"""
        directories = [
            os.path.join(self.config["base_dir"], "data"),
            os.path.join(self.config["base_dir"], "data", "feedback"),
            os.path.join(self.config["base_dir"], "uploads")
        ]
        
        for dir_path in directories:
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)
                print(f"Created directory: {dir_path}")
    
    def _generate_random_date(self, start_date, end_date):
        """生成随机日期"""
        days = (end_date - start_date).days
        random_days = random.randint(0, days)
        random_seconds = random.randint(0, 86400)
        return start_date + timedelta(days=random_days, seconds=random_seconds)
    
    def _generate_random_time(self):
        """生成随机时间字符串"""
        return f"{random.randint(0,23):02d}:{random.randint(0,59):02d}"
    
    def generate_users(self):
        """生成用户数据"""
        user_file = os.path.join(self.config["base_dir"], "data", "users.csv")
        users = []
        
        # 风控业务人员：2名业务负责人 + 2名普通分析人员
        users.append(["001", "王经理", "业务负责人", "风控部", ""])
        users.append(["002", "李总监", "业务负责人", "风控部", ""])
        users.append(["003", "张分析", "普通分析人员", "风控部", ""])
        users.append(["004", "赵分析", "普通分析人员", "风控部", ""])
        
        # 一线操作人员：快递小哥5名
        for i in range(5, 10):
            user_id = f"{i:03d}"
            username = f"{self._get_random_name()}快递"
            role = "一线操作人员"
            department = "快递部"
            employee_id = f"EMP_{user_id}"
            users.append([user_id, username, role, department, employee_id])
            
        # 一线操作人员：销售5名
        for i in range(10, 15):
            user_id = f"{i:03d}"
            username = f"{self._get_random_name()}销售"
            role = "一线操作人员"
            department = "销售部"
            employee_id = f"EMP_{user_id}"
            users.append([user_id, username, role, department, employee_id])
            
        # 一线操作人员：财务对账人5名
        for i in range(15, 20):
            user_id = f"{i:03d}"
            username = f"{self._get_random_name()}财务"
            role = "一线操作人员"
            department = "财务部"
            employee_id = f"EMP_{user_id}"
            users.append([user_id, username, role, department, employee_id])
            
        # 一线操作人员：网点负责人5名
        for i in range(20, 25):
            user_id = f"{i:03d}"
            username = f"{self._get_random_name()}网点"
            role = "一线操作人员"
            department = "物流部"
            employee_id = f"EMP_{user_id}"
            users.append([user_id, username, role, department, employee_id])
        
        with open(user_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["user_id", "username", "role", "department", "employee_id"])
            writer.writerows(users)
            
        print(f"Generated {len(users)} users")
        
    def _get_random_name(self):
        """生成随机中文姓名"""
        surnames = ["张", "李", "王", "赵", "刘", "陈", "杨", "黄", "周", "吴"]
        names = ["伟", "芳", "娜", "秀英", "敏", "静", "丽", "强", "磊", "洋"]
        return random.choice(surnames) + random.choice(names)
    
    def generate_risk_data(self):
        """生成风险数据（物流运单数据）"""
        # 只生成一个risk_data_001.csv文件，包含1000条记录
        risk_file = os.path.join(self.config["base_dir"], "data", "risk_data_001.csv")
        risk_records = []
        
        for j in range(self.config["num_risk_data"]):
            waybill_number = f"WLYD{random.randint(1000000, 9999999)}"
            start_place = f"{random.choice(['上海', '北京', '广州', '深圳', '杭州', '南京'])}{random.choice(['浦东新区', '朝阳区', '天河区', '南山区', '余杭区', '鼓楼区'])}"
            end_place = f"{random.choice(['上海', '北京', '广州', '深圳', '杭州', '南京'])}{random.choice(['浦东新区', '朝阳区', '天河区', '南山区', '余杭区', '鼓楼区'])}"
            collector_name = self._get_random_name()
            collector_id = f"EMP_{random.randint(1, 100):03d}"
            customer_name = f"{self._get_random_name()}贸易公司"
            supplier_name = "顺丰速运"  # 统一为顺丰速运
            cargo_type = random.choice(self.cargo_types)
            product_type = random.choice(self.product_types)
            weight = f"{random.randint(1, 5000)}kg"
            volume = f"{random.randint(1, 1000) / 100:.2f}m³"
            shipping_amount = f"{random.randint(100, 5000)}元"
            settlement_amount = f"{random.randint(90, 4800)}元"
            delivery_time = f"{random.randint(2025, 2026)}-{random.randint(1,12):02d}-{random.randint(1,28):02d} {self._generate_random_time()}"
            collection_time = f"{random.randint(2025, 2026)}-{random.randint(1,12):02d}-{random.randint(1,28):02d} {self._generate_random_time()}"
            delivery_time = f"{random.randint(2025, 2026)}-{random.randint(1,12):02d}-{random.randint(1,28):02d} {self._generate_random_time()}"
            sign_time = f"{random.randint(2025, 2026)}-{random.randint(1,12):02d}-{random.randint(1,28):02d} {self._generate_random_time()}"
            delivery_status = random.choice(self.delivery_statuses)
            reconciler = self._get_random_name()
            distance = f"{random.randint(50, 2000)}km"
            origin_branch = f"{random.choice(['浦东', '朝阳', '天河', '南山', '余杭', '鼓楼'])}网点"
            destination_branch = f"{random.choice(['浦东', '朝阳', '天河', '南山', '余杭', '鼓楼'])}网点"
            abnormal_type = random.choice(self.abnormal_types)
            risk_level = random.choice(self.risk_levels)
            
            risk_records.append([
                waybill_number, start_place, end_place, collector_name, 
                collector_id, customer_name, supplier_name, cargo_type, 
                product_type, weight, volume, shipping_amount, 
                settlement_amount, delivery_time, collection_time, 
                delivery_time, sign_time, delivery_status, reconciler, 
                distance, origin_branch, destination_branch, 
                abnormal_type, risk_level
            ])
        
        with open(risk_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                "运单号", "发货地", "收货地", "揽收人", "揽收人ID", 
                "客户名称", "供应商名称", "货物类型", "产品类型", 
                "重量", "体积", "运费金额", "结算金额", "发货时间", 
                "揽收时间", "派件时间", "签收时间", "运单状态", 
                "对账人", "公里数", "发货网点", "收货网点", 
                "异常类型", "风险等级"
            ])
            writer.writerows(risk_records)
            
        print(f"Generated {len(risk_records)} risk records in {os.path.basename(risk_file)}")
            

            
    def validate_data_consistency(self):
        """验证数据一致性"""
        print("\n=== Data Consistency Validation ===")
        
        # 检查必要文件是否存在
        required_files = [
            "data/users.csv",
            "data/risk_data_001.csv"
        ]
        
        for file_path in required_files:
            full_path = os.path.join(self.config["base_dir"], file_path)
            if os.path.exists(full_path):
                print(f"✅ File exists: {file_path}")
            else:
                print(f"❌ File missing: {file_path}")
                
        # 验证用户数据格式
        try:
            with open(os.path.join(self.config["base_dir"], "data", "users.csv"), 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                next(reader)
                users = list(reader)
                
            print(f"✅ User data has {len(users)} records")
            
            # 验证用户角色分布
            roles = [user[2] for user in users]
            print(f"✅ Roles: {len([r for r in roles if r == '业务负责人'])}业务负责人, {len([r for r in roles if r == '普通分析人员'])}普通分析人员, {len([r for r in roles if r == '一线操作人员'])}一线操作人员")
            
        except Exception as e:
            print(f"❌ User data validation failed: {str(e)}")
            
        # 验证风险数据格式
        try:
            with open(os.path.join(self.config["base_dir"], "data", "risk_data_001.csv"), 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                next(reader)
                risk_records = list(reader)
                
            print(f"✅ Risk data has {len(risk_records)} records")
            
            # 验证快递公司一致性
            suppliers = [record[6] for record in risk_records]
            if all(supplier == "顺丰速运" for supplier in suppliers):
                print("✅ All records have '顺丰速运' as supplier")
            else:
                print(f"❌ Supplier inconsistent: Found {len(set(suppliers))} different suppliers")
                
            # 验证产品类型分布
            product_types = [record[8] for record in risk_records]
            print(f"✅ Product types: {len([p for p in product_types if p == '零担'])}零担, {len([p for p in product_types if p == '整车'])}整车, {len([p for p in product_types if p == '合同物流'])}合同物流")
            
            # 验证风险等级分布
            risk_levels = [record[23] for record in risk_records]
            print(f"✅ Risk levels: {len([rl for rl in risk_levels if rl == '低'])}低, {len([rl for rl in risk_levels if rl == '中'])}中, {len([rl for rl in risk_levels if rl == '高'])}高")
            
        except Exception as e:
            print(f"❌ Risk data validation failed: {str(e)}")
            
        print("\n=== Validation Complete ===")
        
    def run(self):
        """执行完整数据生成流程"""
        print("=== Starting Data Generation ===")
        
        self.generate_users()
        self.generate_risk_data()
        self.validate_data_consistency()
        
        print("\n=== Data Generation Complete ===")


if __name__ == "__main__":
    generator = DataGenerator()
    generator.run()
