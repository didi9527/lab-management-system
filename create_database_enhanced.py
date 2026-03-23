# create_database_enhanced.py
import sqlite3
from datetime import datetime

def create_database():
    """创建增强版数据库"""
    conn = sqlite3.connect('lab_data_enhanced.db')
    c = conn.cursor()
    
    print("正在创建增强版数据库...")
    
    # 创建实验数据表
    c.execute('''
        CREATE TABLE IF NOT EXISTS experiments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data_id TEXT UNIQUE NOT NULL,          -- 数据ID（按新命名规则）
            
            -- 核心信息
            test_project_name TEXT NOT NULL,       -- 测试项目名称
            experiment_date DATE NOT NULL,         -- 实验日期
            test_object TEXT NOT NULL,             -- 实验对象
            core_drawing_number TEXT,              -- 芯体图号
            test_type TEXT NOT NULL,               -- 测试类型
            equipment TEXT,                        -- 设备类型
            
            -- 申请人信息和密级
            applicant_name TEXT,                    -- 申请人姓名
            version_code TEXT,                      -- 密级 (A/AA/S)
            file_extension TEXT,                    -- 文件扩展名
            
            -- 模具信息
            flat_tube_mold TEXT,                    -- 扁管模具号
            header_mold TEXT,                       -- 集流管模具号
            fin_tool TEXT,                          -- 翅片模具号
            
            -- 制冷剂类型
            refrigerant_type TEXT,                  -- 制冷剂类型
            
            -- 文件上传信息
            original_filename TEXT,                 -- 原始文件名
            renamed_filename TEXT,                  -- 重命名后的文件名
            file_path TEXT,                         -- 本地文件路径
            server_path TEXT,                       -- 服务器文件路径
            file_size INTEGER,                      -- 文件大小（字节）
            upload_time TIMESTAMP,                  -- 上传时间
            file_hash TEXT,                         -- 文件哈希值
            
            -- 其他信息
            notes TEXT,                             -- 备注（测试目的）
            created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 创建文件管理相关索引
    c.execute('CREATE INDEX IF NOT EXISTS idx_original_filename ON experiments (original_filename)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_renamed_filename ON experiments (renamed_filename)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_upload_time ON experiments (upload_time)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_applicant_name ON experiments (applicant_name)')
    
    # 创建主索引
    c.execute('CREATE INDEX IF NOT EXISTS idx_project_name ON experiments (test_project_name)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_test_object ON experiments (test_object)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_date ON experiments (experiment_date)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_version_code ON experiments (version_code)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_test_type ON experiments (test_type)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_equipment ON experiments (equipment)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_core_drawing_number ON experiments (core_drawing_number)')
    
    # 创建模具号索引
    c.execute('CREATE INDEX IF NOT EXISTS idx_flat_tube_mold ON experiments (flat_tube_mold)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_header_mold ON experiments (header_mold)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_fin_tool ON experiments (fin_tool)')
    
    # 添加示例数据（使用更新后的测试类型和设备类型）
    sample_data = [
        # 示例1：焓差测试，30kw设备，A级密级
        ('JCI蒸发器_20240115_蒸发器_DRG-EVAP-001_焓差测试_30kw_张三_A', 
         'JCI蒸发器', '2024-01-15', '蒸发器', 'DRG-EVAP-001', 
         '焓差测试', '30kw', '张三', 'A', '.xlsx',
         'FMT-001', 'HMT-002', 'FTL-003', 'R134a',
         '原始数据.xlsx', 'JCI蒸发器_20240115_蒸发器_DRG-EVAP-001_焓差测试_30kw_张三_A.xlsx',
         'C:\\实验数据\\原始文件\\data.xlsx', '\\\\server\\data\\JCI蒸发器_20240115_蒸发器_DRG-EVAP-001_焓差测试_30kw_张三_A.xlsx',
         1024000, '2024-01-15 14:30:00', 'abc123def456', '测试目的：验证JCI蒸发器换热性能\n\n三大主材模具号：\n- 翅片模具：FMT-001\n- 集流管模具：HMT-002\n- 扁管模具：FTL-003'),
        
        # 示例2：盐雾测试，盐雾设备，AA级密级
        ('格力冷凝器_20240116_冷凝器_DRG-COND-002_盐雾测试_盐雾_李四_AA', 
         '格力冷凝器', '2024-01-16', '冷凝器', 'DRG-COND-002', 
         '盐雾测试', '盐雾', '李四', 'AA', '.xlsx',
         'FMT-002', 'HMT-003', 'FTL-004', 'R410a',
         '格力测试数据.xlsx', '格力冷凝器_20240116_冷凝器_DRG-COND-002_盐雾测试_盐雾_李四_AA.xlsx',
         'C:\\实验数据\\原始文件\\格力数据.xlsx', '\\\\server\\data\\格力冷凝器_20240116_冷凝器_DRG-COND-002_盐雾测试_盐雾_李四_AA.xlsx',
         2048000, '2024-01-16 10:20:00', 'def456ghi789', '测试目的：冷凝器耐腐蚀性能测试\n\n三大主材模具号：\n- 翅片模具：FMT-002\n- 集流管模具：HMT-003\n- 扁管模具：FTL-004'),
        
        # 示例3：压力交变测试，压力交变设备，S级密级
        ('美的热泵_20240117_热泵_DRG-HEAT-003_压力交变_压力交变_王五_S', 
         '美的热泵', '2024-01-17', '热泵', 'DRG-HEAT-003', 
         '压力交变', '压力交变', '王五', 'S', '.xlsx',
         'FMT-005', 'HMT-006', 'FTL-007', 'R32',
         '热泵压力测试.xlsx', '美的热泵_20240117_热泵_DRG-HEAT-003_压力交变_压力交变_王五_S.xlsx',
         'C:\\实验数据\\原始文件\\热泵压力测试.xlsx', '\\\\server\\data\\美的热泵_20240117_热泵_DRG-HEAT-003_压力交变_压力交变_王五_S.xlsx',
         3072000, '2024-01-17 16:45:00', 'ghi789jkl012', '测试目的：热泵压力交变耐久性测试\n\n三大主材模具号：\n- 翅片模具：FMT-005\n- 集流管模具：HMT-006\n- 扁管模具：FTL-007'),
        
        # 示例4：材料测试，50kw设备，A级密级
        ('海尔水箱_20240118_水箱_DRG-TANK-004_材料测试_50kw_赵六_A', 
         '海尔水箱', '2024-01-18', '水箱', 'DRG-TANK-004', 
         '材料测试', '50kw', '赵六', 'A', '.xlsx',
         'FMT-008', 'HMT-009', 'FTL-010', 'R134a',
         '材料性能测试.xlsx', '海尔水箱_20240118_水箱_DRG-TANK-004_材料测试_50kw_赵六_A.xlsx',
         'C:\\实验数据\\原始文件\\材料测试.xlsx', '\\\\server\\data\\海尔水箱_20240118_水箱_DRG-TANK-004_材料测试_50kw_赵六_A.xlsx',
         1536000, '2024-01-18 09:15:00', 'jkl012mno345', '测试目的：水箱材料性能分析\n\n三大主材模具号：\n- 翅片模具：FMT-008\n- 集流管模具：HMT-009\n- 扁管模具：FTL-010'),
        
        # 示例5：扫描电镜测试，金相设备，AA级密级
        ('比亚迪热虹吸_20240119_热虹吸_DRG-THS-005_扫描电镜_金相_孙七_AA', 
         '比亚迪热虹吸', '2024-01-19', '热虹吸', 'DRG-THS-005', 
         '扫描电镜', '金相', '孙七', 'AA', '.jpg',
         'FMT-011', 'HMT-012', 'FTL-013', 'R410a',
         'SEM图像.jpg', '比亚迪热虹吸_20240119_热虹吸_DRG-THS-005_扫描电镜_金相_孙七_AA.jpg',
         'C:\\实验数据\\原始文件\\SEM图像.jpg', '\\\\server\\data\\比亚迪热虹吸_20240119_热虹吸_DRG-THS-005_扫描电镜_金相_孙七_AA.jpg',
         5120000, '2024-01-19 11:30:00', 'mno345pqr678', '测试目的：热虹吸微观结构分析\n\n三大主材模具号：\n- 翅片模具：FMT-011\n- 集流管模具：HMT-012\n- 扁管模具：FTL-013'),
        
        # 示例6：温度交变测试，120kw设备，S级密级
        ('松下整机_20240120_整机_DRG-UNIT-006_温度交变_120kw_周八_S', 
         '松下整机', '2024-01-20', '整机', 'DRG-UNIT-006', 
         '温度交变', '120kw', '周八', 'S', '.csv',
         'FMT-014', 'HMT-015', 'FTL-016', 'R32',
         '温度循环数据.csv', '松下整机_20240120_整机_DRG-UNIT-006_温度交变_120kw_周八_S.csv',
         'C:\\实验数据\\原始文件\\温度循环数据.csv', '\\\\server\\data\\松下整机_20240120_整机_DRG-UNIT-006_温度交变_120kw_周八_S.csv',
         896000, '2024-01-20 13:20:00', 'pqr678stu901', '测试目的：整机温度交变循环测试\n\n三大主材模具号：\n- 翅片模具：FMT-014\n- 集流管模具：HMT-015\n- 扁管模具：FTL-016'),
        
        # 示例7：焓差测试，75kw设备，A级密级
        ('大金蒸发器_20240121_蒸发器_DRG-EVAP-007_焓差测试_75kw_吴九_A', 
         '大金蒸发器', '2024-01-21', '蒸发器', 'DRG-EVAP-007', 
         '焓差测试', '75kw', '吴九', 'A', '.xlsx',
         'FMT-017', 'HMT-018', 'FTL-019', 'R134a',
         '大金测试数据.xlsx', '大金蒸发器_20240121_蒸发器_DRG-EVAP-007_焓差测试_75kw_吴九_A.xlsx',
         'C:\\实验数据\\原始文件\\大金测试.xlsx', '\\\\server\\data\\大金蒸发器_20240121_蒸发器_DRG-EVAP-007_焓差测试_75kw_吴九_A.xlsx',
         2560000, '2024-01-21 15:00:00', 'stu901vwx234', '测试目的：大金蒸发器性能验证\n\n三大主材模具号：\n- 翅片模具：FMT-017\n- 集流管模具：HMT-018\n- 扁管模具：FTL-019'),
    ]
    
    inserted_count = 0
    for data in sample_data:
        try:
            c.execute('''
                INSERT OR IGNORE INTO experiments 
                (data_id, test_project_name, experiment_date, test_object, core_drawing_number,
                 test_type, equipment, applicant_name, version_code, file_extension,
                 flat_tube_mold, header_mold, fin_tool, refrigerant_type,
                 original_filename, renamed_filename, file_path, server_path,
                 file_size, upload_time, file_hash, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', data)
            if c.rowcount > 0:
                inserted_count += 1
        except Exception as e:
            print(f"插入示例数据失败: {e}")
    
    conn.commit()
    
    # 验证表是否创建成功
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='experiments'")
    if c.fetchone():
        print("✅ 表 'experiments' 创建成功")
    else:
        print("❌ 表 'experiments' 创建失败")
    
    # 显示表结构
    print("\n📊 表结构：")
    c.execute("PRAGMA table_info(experiments)")
    for col in c.fetchall():
        print(f"  - {col[1]} ({col[2]})")
    
    # 统计信息
    c.execute("SELECT COUNT(*) FROM experiments")
    total_count = c.fetchone()[0]
    print(f"\n📈 数据库统计：")
    print(f"  - 总记录数：{total_count}")
    
    if total_count > 0:
        c.execute("SELECT COUNT(DISTINCT test_project_name) FROM experiments")
        project_count = c.fetchone()[0]
        print(f"  - 项目数量：{project_count}")
        
        c.execute("SELECT COUNT(DISTINCT applicant_name) FROM experiments WHERE applicant_name IS NOT NULL")
        applicant_count = c.fetchone()[0]
        print(f"  - 申请人数量：{applicant_count}")
        
        c.execute("SELECT version_code, COUNT(*) FROM experiments GROUP BY version_code")
        security_stats = c.fetchall()
        print(f"  - 密级分布：")
        for level, count in security_stats:
            print(f"    密级{level}: {count}条")
    
    conn.close()
    print(f"\n✅ 增强版数据库创建成功！文件：lab_data_enhanced.db")
    print(f"✅ 已添加 {inserted_count} 条示例数据")

if __name__ == "__main__":
    create_database()
