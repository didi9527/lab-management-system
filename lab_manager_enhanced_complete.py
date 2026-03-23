# lab_manager_enhanced_complete.py
import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
import os
import re
import hashlib
import shutil
from pathlib import Path
import tempfile
import time
import sys

# ==================== 云端适配配置 ====================
# 设置页面配置（必须在最前面）
st.set_page_config(
    page_title="实验室数据管理系统 - 密级管理版V2",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 云端环境适配
if 'streamlit_cloud' in sys.argv or os.environ.get('STREAMLIT_CLOUD') == 'true':
    # 云端环境配置
    DATA_DIR = '/mount/data'  # Streamlit Cloud 的持久化存储路径
    os.makedirs(DATA_DIR, exist_ok=True)
    DB_PATH = os.path.join(DATA_DIR, 'lab_data_enhanced.db')
else:
    # 本地环境配置
    DB_PATH = 'lab_data_enhanced.db'

# 自定义CSS样式
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1E88E5;
        font-weight: bold;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.8rem;
        color: #43A047;
        font-weight: bold;
        margin-top: 1.5rem;
        margin-bottom: 1rem;
    }
    .info-box {
        background-color: #E3F2FD;
        padding: 1rem;
        border-radius: 10px;
        border-left: 5px solid #2196F3;
        margin-bottom: 1rem;
    }
    .success-box {
        background-color: #E8F5E9;
        padding: 1rem;
        border-radius: 10px;
        border-left: 5px solid #4CAF50;
        margin-bottom: 1rem;
    }
    .warning-box {
        background-color: #FFF3E0;
        padding: 1rem;
        border-radius: 10px;
        border-left: 5px solid #FF9800;
        margin-bottom: 1rem;
    }
    .file-preview {
        background-color: #F5F5F5;
        padding: 1rem;
        border-radius: 5px;
        font-family: monospace;
        margin: 0.5rem 0;
    }
    .folder-preview {
        background-color: #E8F4FD;
        padding: 0.8rem;
        border-radius: 5px;
        font-family: monospace;
        color: #0B5E7E;
        margin: 0.5rem 0;
    }
    .security-badge-A {
        background-color: #4CAF50;
        color: white;
        padding: 0.2rem 0.5rem;
        border-radius: 4px;
        font-weight: bold;
        display: inline-block;
    }
    .security-badge-AA {
        background-color: #FF9800;
        color: white;
        padding: 0.2rem 0.5rem;
        border-radius: 4px;
        font-weight: bold;
        display: inline-block;
    }
    .security-badge-S {
        background-color: #F44336;
        color: white;
        padding: 0.2rem 0.5rem;
        border-radius: 4px;
        font-weight: bold;
        display: inline-block;
    }
    .stProgress > div > div > div > div {
        background-color: #4CAF50;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
    }
    .material-section {
        background-color: #FFF8E1;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #FFB300;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# 标题
st.markdown('<div class="main-header">🔬 实验室数据管理系统（密级管理版V2）</div>', unsafe_allow_html=True)
st.markdown("---")

# ==================== 辅助函数定义 ====================
def get_test_type_code(test_type):
    """获取测试类型代码 - 完整表达"""
    code_map = {
        "焓差测试": "焓差测试",
        "盐雾测试": "盐雾测试",
        "压力交变": "压力交变",
        "材料测试": "材料测试",
        "扫描电镜": "扫描电镜",
        "温度交变": "温度交变",
        "其他测试": "其他测试"
    }
    return code_map.get(test_type, "其他测试")

def get_equipment_code(equipment):
    """获取设备类型代码 - 不缩写，完整表达"""
    code_map = {
        "30kw": "30kw",
        "50kw": "50kw",
        "75kw": "75kw",
        "15kw": "15kw",
        "28kw": "28kw",
        "10kw": "10kw",
        "120kw": "120kw",
        "金相": "金相",
        "压力交变": "压力交变",
        "盐雾": "盐雾",
        "其他": "其他"
    }
    return code_map.get(equipment, equipment)

def get_equipment_display_name(equipment):
    """获取设备显示名称"""
    return equipment

def calculate_file_hash(file_path):
    """计算文件的MD5哈希值"""
    hash_md5 = hashlib.md5()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception as e:
        return f"error_{e}"

def generate_filename(params):
    """根据参数生成标准文件名"""
    # 清理输入
    project_clean = re.sub(r'[\\/*?:"<>|]', '_', params['test_project_name'].strip())
    core_clean = re.sub(r'[\\/*?:"<>|]', '_', params['core_drawing_number'].strip()) if params.get('core_drawing_number') and params['core_drawing_number'].strip() else "NODWG"
    applicant_clean = re.sub(r'[\\/*?:"<>|]', '_', params.get('applicant_name', '').strip()) if params.get('applicant_name') and params['applicant_name'].strip() else "未知"
    
    # 获取日期和代码
    date_str = params['experiment_date'].strftime("%Y%m%d")
    test_type_code = get_test_type_code(params['test_type'])
    equipment_code = get_equipment_code(params['equipment'])
    
    # 获取密级
    security_level = params.get('security_level', 'A').strip()
    
    # 构建文件名
    filename_parts = [
        project_clean,
        date_str,
        params['test_object'],
        core_clean,
        test_type_code,
        equipment_code,
        applicant_clean,
        security_level
    ]
    
    # 组合文件名
    filename = "_".join(filename_parts) + params['file_extension']
    return filename

def generate_folder_structure(params):
    """根据参数生成层级化文件夹路径"""
    # 清理输入
    project_clean = re.sub(r'[\\/*?:"<>|]', '_', params['test_project_name'].strip())
    core_clean = re.sub(r'[\\/*?:"<>|]', '_', params['core_drawing_number'].strip()) if params.get('core_drawing_number') and params['core_drawing_number'].strip() else "NODWG"
    applicant_clean = re.sub(r'[\\/*?:"<>|]', '_', params.get('applicant_name', '').strip()) if params.get('applicant_name') and params['applicant_name'].strip() else "未知"
    
    # 获取日期（年、月）
    year = params['experiment_date'].strftime("%Y")
    month = params['experiment_date'].strftime("%m")
    
    # 获取测试类型和对象
    test_type_clean = re.sub(r'[\\/*?:"<>|]', '_', params['test_type'].strip())
    test_object_clean = re.sub(r'[\\/*?:"<>|]', '_', params['test_object'].strip())
    
    # 获取密级
    security_level = params.get('security_level', 'A').strip()
    
    # 构建层级化文件夹路径
    folder_parts = [
        f"uploaded_files（密级{security_level}）",
        project_clean,
        year,
        month,
        core_clean,
        f"{test_type_clean}_{test_object_clean}_{applicant_clean}"
    ]
    
    folder_path = os.path.join(*folder_parts)
    return folder_path

def save_uploaded_file(uploaded_file, params, new_filename):
    """保存上传的文件到层级化文件夹结构"""
    try:
        # 生成文件夹路径
        folder_path = generate_folder_structure(params)
        
        # 确保目标目录存在
        os.makedirs(folder_path, exist_ok=True)
        
        # 构建完整路径
        target_path = os.path.join(folder_path, new_filename)
        
        # 保存文件
        with open(target_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        # 获取文件信息
        file_size = os.path.getsize(target_path)
        file_hash = calculate_file_hash(target_path)
        
        # 生成相对路径和服务器路径
        relative_path = os.path.relpath(target_path, os.path.dirname(target_path))
        server_path = f"\\\\server\\data\\{target_path.replace(os.sep, '/')}"
        
        return {
            "success": True,
            "file_path": target_path,
            "folder_path": folder_path,
            "relative_path": relative_path,
            "file_size": file_size,
            "file_hash": file_hash,
            "server_path": server_path
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

def validate_filename_inputs(project, date, obj, test_type, equipment, security_level, core, applicant):
    """验证文件名输入参数"""
    if not all([project, obj, test_type, equipment, security_level, core, applicant]):
        return False, "请填写所有必填项（带*号）"
    
    # 检查日期有效性
    if date > datetime.now().date():
        return False, "实验日期不能超过当前日期"
    
    return True, "验证通过"

# ==================== 数据库连接和迁移 ====================
@st.cache_resource
def get_connection():
    """获取数据库连接并确保所有字段存在"""
    # 确保数据库目录存在
    db_dir = os.path.dirname(DB_PATH)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    cursor = conn.cursor()
    
    # 检查表是否存在
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='experiments'")
    if not cursor.fetchone():
        # 表不存在，创建新表
        create_new_table(cursor, conn)
        return conn
    
    # 获取现有表结构
    cursor.execute("PRAGMA table_info(experiments)")
    existing_columns = [col[1] for col in cursor.fetchall()]
    
    # 需要添加的字段列表
    columns_to_add = {
        'applicant_name': 'TEXT',
        'flat_tube_mold': 'TEXT',
        'header_mold': 'TEXT',
        'fin_tool': 'TEXT',
        'refrigerant_type': 'TEXT'
    }
    
    # 添加缺失的字段
    added_fields = []
    for col_name, col_type in columns_to_add.items():
        if col_name not in existing_columns:
            try:
                cursor.execute(f"ALTER TABLE experiments ADD COLUMN {col_name} {col_type}")
                added_fields.append(col_name)
            except Exception as e:
                pass
    
    if added_fields:
        conn.commit()
    
    return conn

def create_new_table(cursor, conn):
    """创建新的数据库表"""
    cursor.execute('''
        CREATE TABLE experiments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data_id TEXT UNIQUE NOT NULL,
            test_project_name TEXT NOT NULL,
            experiment_date DATE NOT NULL,
            test_object TEXT NOT NULL,
            core_drawing_number TEXT,
            test_type TEXT NOT NULL,
            equipment TEXT,
            applicant_name TEXT,
            version_code TEXT,
            file_extension TEXT,
            flat_tube_mold TEXT,
            header_mold TEXT,
            fin_tool TEXT,
            refrigerant_type TEXT,
            original_filename TEXT,
            renamed_filename TEXT,
            file_path TEXT,
            server_path TEXT,
            file_size INTEGER,
            upload_time TIMESTAMP,
            file_hash TEXT,
            notes TEXT,
            created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 创建索引
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_applicant_name ON experiments (applicant_name)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_project_name ON experiments (test_project_name)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_date ON experiments (experiment_date)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_version_code ON experiments (version_code)')
    
    conn.commit()

# 建立数据库连接
conn = get_connection()

# ==================== 侧边栏导航 ====================
st.sidebar.markdown('<div class="main-header">导航菜单</div>', unsafe_allow_html=True)

menu = st.sidebar.radio(
    "选择功能",
    ["🏠 系统首页", "📁 文件管理", "🔍 数据查询", "📋 数据浏览", "📂 文件夹浏览", "⚙️ 系统设置"]
)

# 系统信息
st.sidebar.markdown("---")
st.sidebar.markdown("### 📊 系统信息")
st.sidebar.info(f"**版本**: 7.0\n\n**功能**: 密级管理版V2\n\n**数据库**: SQLite\n\n**环境**: {'云端' if os.environ.get('STREAMLIT_CLOUD') else '本地'}")

# ==================== 全局变量定义 ====================
# 设备类型选项
equipment_options = [
    "30kw", "50kw", "75kw", "15kw", "28kw", "10kw", "120kw",
    "金相", "压力交变", "盐雾", "其他"
]

# 测试类型选项
test_type_options = [
    "焓差测试", "盐雾测试", "压力交变", "材料测试", "扫描电镜", "温度交变", "其他测试"
]

# 密级选项
security_options = ["A", "AA", "S"]

security_descriptions = {
    "A": "保密数据",
    "AA": "高级保密数据", 
    "S": "绝密数据"
}

security_colors = {
    'A': 'security-badge-A',
    'AA': 'security-badge-AA',
    'S': 'security-badge-S'
}

# 实验对象选项
test_object_options = ["整机", "冷凝器", "蒸发器", "热泵", "水箱", "热虹吸", "其他"]

# ==================== 1. 系统首页 ====================
if menu == "🏠 系统首页":
    st.markdown('<div class="sub-header">欢迎使用实验室数据管理系统（密级管理版V2）</div>', unsafe_allow_html=True)
    
    st.markdown("""
    <div class="info-box">
    <h3>🎯 系统简介</h3>
    <p>本系统专为实验室数据管理设计，支持实验数据的文件上传、管理和查询分析，采用层级化文件夹结构存储文件，并支持文件密级管理。</p>
    <p><strong>核心功能</strong>：文件上传、自动重命名、层级化存储、密级管理、数据追踪、申请人追溯</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 系统统计
    st.markdown('<div class="sub-header">📈 系统统计</div>', unsafe_allow_html=True)
    
    try:
        col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
        
        with col_stat1:
            df_total = pd.read_sql_query("SELECT COUNT(*) as count FROM experiments", conn)
            st.metric("📊 总记录数", df_total['count'][0])
        
        with col_stat2:
            df_files = pd.read_sql_query("SELECT COUNT(*) as count FROM experiments WHERE renamed_filename IS NOT NULL", conn)
            st.metric("📁 有文件记录", df_files['count'][0])
        
        with col_stat3:
            df_projects = pd.read_sql_query("SELECT COUNT(DISTINCT test_project_name) as count FROM experiments", conn)
            st.metric("🏢 项目数量", df_projects['count'][0])
        
        with col_stat4:
            if os.path.exists(DB_PATH):
                db_size = os.path.getsize(DB_PATH) / 1024
                st.metric("💾 数据库大小", f"{db_size:.1f} KB")
    except Exception as e:
        st.warning("暂无数据，请先上传文件")
    
    # 使用指南
    with st.expander("📖 使用指南", expanded=False):
        st.markdown("""
        ### 🚀 快速开始
        
        1. **文件上传**：进入"文件管理"页面，上传实验文件
        2. **数据查询**：根据需要查询历史数据
        3. **文件夹浏览**：按层级化结构查看文件
        4. **密级管理**：每个文件都有对应的密级
        
        ### 📋 文件命名规则
        
        文件名格式：`项目名称_日期_对象_芯体图号_测试类型_设备_申请人_密级.扩展名`
        
        **示例**：`JCI蒸发器_20240115_蒸发器_DRG-EVAP-001_焓差测试_30kw_张三_A.xlsx`
        
        ### 📂 文件夹结构规则
        
        文件夹结构：`uploaded_files（密级X）/项目名称/年份/月份/芯体图号/测试类型_实验对象_申请人/`
        
        **示例**：`uploaded_files（密级A）/JCI蒸发器/2024/01/DRG-EVAP-001/焓差测试_蒸发器_张三/`
        
        ### 🔒 密级说明
        
        - **A级（绿色）**：保密数据
        - **AA级（橙色）**：高级保密数据
        - **S级（红色）**：绝密数据
        
        ### ⚠️ 注意事项
        
        - 带*号为必填项（包括芯体图号、密级和申请人姓名）
        - 文件上传后会自动重命名并存储到带密级的根目录
        - 建议定期备份数据库和上传文件
        """)

# ==================== 2. 文件管理页面 ====================
elif menu == "📁 文件管理":
    st.markdown('<div class="sub-header">📁 文件管理工具（密级管理V2）</div>', unsafe_allow_html=True)
    
    # 检查是否有从查询页面传递过来的选择
    if 'selected_data_id' in st.session_state:
        st.info(f"📌 从查询页面跳转：准备为数据ID `{st.session_state.selected_data_id}` 上传文件")
    
    # 标签页
    tab1, tab2, tab3 = st.tabs(["📤 单文件上传", "📦 批量文件处理", "📋 文件记录管理"])
    
    # ============= 选项卡1：单文件上传 =============
    with tab1:
        st.markdown("### 📤 单文件上传与管理")
        
        # 步骤1：选择或创建记录
        st.markdown("#### 步骤1：选择或创建实验记录")
        
        col_select1, col_select2 = st.columns(2)
        
        with col_select1:
            try:
                df_records = pd.read_sql_query(
                    """SELECT data_id, test_project_name, experiment_date, test_object, 
                              core_drawing_number, version_code as security_level, applicant_name 
                       FROM experiments ORDER BY experiment_date DESC""",
                    conn
                )
                
                if not df_records.empty:
                    record_options = [f"{row['data_id']} | {row['test_project_name']} | {row['applicant_name'] or '未知'} | 密级{row['security_level']}" 
                                     for _, row in df_records.iterrows()]
                    selected_option = st.selectbox(
                        "选择现有记录", 
                        record_options,
                        help="可以选择已有的实验记录进行文件上传"
                    )
                    
                    if selected_option:
                        selected_data_id = selected_option.split(" | ")[0]
                        selected_record = df_records[df_records['data_id'] == selected_data_id].iloc[0]
                        
                        with st.expander("📋 查看选中记录详情", expanded=False):
                            st.write(f"**数据ID**：{selected_record['data_id']}")
                            st.write(f"**测试项目**：{selected_record['test_project_name']}")
                            st.write(f"**实验日期**：{selected_record['experiment_date']}")
                            st.write(f"**实验对象**：{selected_record['test_object']}")
                            st.write(f"**芯体图号**：{selected_record['core_drawing_number'] or '未填写'}")
                            st.write(f"**申请人**：{selected_record['applicant_name'] or '未填写'}")
                            security_class = security_colors.get(selected_record['security_level'], 'security-badge-A')
                            st.markdown(f"**密级**：<span class='{security_class}'>密级{selected_record['security_level']}</span>", unsafe_allow_html=True)
                    
                    create_new = st.checkbox("创建新记录", value=False)
                else:
                    create_new = True
                    st.info("暂无现有记录，请创建新记录")
            except Exception as e:
                create_new = True
                st.warning("无法加载现有记录，请创建新记录")
        
        with col_select2:
            if create_new:
                st.markdown("**创建新记录**")
                
                with st.form("quick_record_form"):
                    quick_project = st.text_input("测试项目名称*", key="quick_project")
                    quick_date = st.date_input("实验日期*", value=datetime.now(), key="quick_date")
                    quick_object = st.selectbox("实验对象*", test_object_options, key="quick_object")
                    quick_type = st.selectbox("测试类型*", test_type_options, key="quick_type")
                    quick_equipment = st.selectbox("设备*", equipment_options, key="quick_equipment")
                    quick_security = st.selectbox("密级*", security_options, index=0, key="quick_security")
                    quick_core = st.text_input("芯体图号*", placeholder="如：DRG-EVAP-001", key="quick_core")
                    quick_applicant = st.text_input("申请人姓名*", placeholder="如：张三", key="quick_applicant")
                    
                    if st.form_submit_button("⚡ 快速创建记录"):
                        if all([quick_project, quick_object, quick_type, quick_equipment, quick_security, quick_core, quick_applicant]):
                            params = {
                                'test_project_name': quick_project,
                                'experiment_date': quick_date,
                                'test_object': quick_object,
                                'core_drawing_number': quick_core or "",
                                'test_type': quick_type,
                                'equipment': quick_equipment,
                                'security_level': quick_security,
                                'applicant_name': quick_applicant,
                                'file_extension': ".xlsx"
                            }
                            
                            filename = generate_filename(params)
                            data_id = filename.replace(".xlsx", "")
                            
                            try:
                                cursor = conn.cursor()
                                cursor.execute('''
                                    INSERT INTO experiments 
                                    (data_id, test_project_name, experiment_date, test_object,
                                     test_type, equipment, version_code, file_extension,
                                     core_drawing_number, applicant_name)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                ''', (
                                    data_id, quick_project, quick_date.strftime('%Y-%m-%d'),
                                    quick_object, quick_type, quick_equipment, quick_security, ".xlsx",
                                    quick_core or "", quick_applicant
                                ))
                                conn.commit()
                                st.success(f"✅ 记录创建成功！数据ID：{data_id}")
                                if 'selected_data_id' in st.session_state:
                                    del st.session_state.selected_data_id
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ 创建失败：{str(e)}")
                        else:
                            st.error("❌ 请填写所有必填项")
        
        # 步骤2：文件上传和配置
        st.markdown("#### 步骤2：上传文件")
        
        uploaded_file = st.file_uploader(
            "选择要上传的文件",
            type=['xlsx', 'csv', 'pdf', 'jpg', 'jpeg', 'png', 'docx', 'tif', 'dat', 'txt'],
            help="支持常见的实验数据文件格式"
        )
        
        if uploaded_file:
            file_size_kb = len(uploaded_file.getvalue()) / 1024
            st.markdown(f"""
            <div class="info-box">
            <h4>📄 已选择文件</h4>
            <p><strong>文件名</strong>: {uploaded_file.name}</p>
            <p><strong>文件大小</strong>: {file_size_kb:.1f} KB</p>
            </div>
            """, unsafe_allow_html=True)
            
            # 步骤3：配置信息
            st.markdown("#### 步骤3：配置文件信息")
            
            col_config1, col_config2 = st.columns(2)
            
            with col_config1:
                config_project = st.text_input("测试项目名称*", key="config_project", placeholder="如：JCI蒸发器")
                config_date = st.date_input("实验日期*", value=datetime.now(), key="config_date")
                config_object = st.selectbox("实验对象*", test_object_options, key="config_object")
                config_core = st.text_input("芯体图号*", key="config_core", placeholder="如：DRG-EVAP-001")
            
            with col_config2:
                config_type = st.selectbox("测试类型*", test_type_options, key="config_type")
                config_equipment = st.selectbox("设备*", equipment_options, key="config_equipment")
                config_security = st.selectbox("密级*", security_options, key="config_security")
                config_applicant = st.text_input("申请人姓名*", key="config_applicant", placeholder="如：张三")
                config_test_purpose = st.text_input("测试目的", key="config_test_purpose", placeholder="如：验证设计参数")
                original_ext = os.path.splitext(uploaded_file.name)[1].lower()
                config_ext = original_ext if original_ext else ".xlsx"
                config_ext = st.selectbox("文件类型*", [".xlsx", ".csv", ".pdf", ".jpg", ".png", ".docx", ".tif", ".dat"], 
                                         index=[".xlsx", ".csv", ".pdf", ".jpg", ".png", ".docx", ".tif", ".dat"].index(config_ext) if config_ext in [".xlsx", ".csv", ".pdf", ".jpg", ".png", ".docx", ".tif", ".dat"] else 0)
            
            # 三大主材模具号
            st.markdown('<div class="material-section">', unsafe_allow_html=True)
            st.markdown("### 🔧 三大主材模具号")
            
            col_material1, col_material2, col_material3 = st.columns(3)
            with col_material1:
                fin_mold = st.text_input("翅片模具号", placeholder="如：B150", key="fin_mold")
            with col_material2:
                header_mold = st.text_input("集流管模具号", placeholder="如：H100", key="header_mold")
            with col_material3:
                tube_mold = st.text_input("扁管模具号", placeholder="如：A43S", key="tube_mold")
            st.markdown('</div>', unsafe_allow_html=True)
            
            # 实时预览
            if config_project and config_object and config_type and config_equipment and config_security and config_core and config_applicant:
                preview_params = {
                    'test_project_name': config_project,
                    'experiment_date': config_date,
                    'test_object': config_object,
                    'core_drawing_number': config_core or "",
                    'test_type': config_type,
                    'equipment': config_equipment,
                    'security_level': config_security,
                    'applicant_name': config_applicant,
                    'file_extension': config_ext
                }
                
                preview_filename = generate_filename(preview_params)
                preview_folder = generate_folder_structure(preview_params)
                
                st.markdown('<div class="success-box">', unsafe_allow_html=True)
                st.markdown(f"### 📄 文件名预览")
                st.markdown(f'<div class="file-preview">{preview_filename}</div>', unsafe_allow_html=True)
                st.markdown(f"### 📂 存储路径预览")
                st.markdown(f'<div class="folder-preview">{preview_folder}</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
            
            # 上传按钮
            if st.button("🚀 上传并重命名", type="primary"):
                is_valid, message = validate_filename_inputs(
                    config_project, config_date, config_object, config_type, 
                    config_equipment, config_security, config_core, config_applicant
                )
                
                if not is_valid:
                    st.error(message)
                else:
                    try:
                        final_params = {
                            'test_project_name': config_project,
                            'experiment_date': config_date,
                            'test_object': config_object,
                            'core_drawing_number': config_core or "",
                            'test_type': config_type,
                            'equipment': config_equipment,
                            'security_level': config_security,
                            'applicant_name': config_applicant,
                            'file_extension': config_ext
                        }
                        
                        final_filename = generate_filename(final_params)
                        final_data_id = final_filename.replace(config_ext, "")
                        
                        result = save_uploaded_file(uploaded_file, final_params, final_filename)
                        
                        if not result["success"]:
                            st.error(f"❌ 文件保存失败：{result.get('error', '未知错误')}")
                        else:
                            materials_info = f"测试目的：{config_test_purpose or ''}"
                            if any([fin_mold, header_mold, tube_mold]):
                                materials_info += "\n\n三大主材模具号："
                                if fin_mold:
                                    materials_info += f"\n- 翅片模具：{fin_mold}"
                                if header_mold:
                                    materials_info += f"\n- 集流管模具：{header_mold}"
                                if tube_mold:
                                    materials_info += f"\n- 扁管模具：{tube_mold}"
                            
                            cursor = conn.cursor()
                            cursor.execute("SELECT COUNT(*) FROM experiments WHERE data_id = ?", (final_data_id,))
                            exists = cursor.fetchone()[0] > 0
                            
                            if exists:
                                cursor.execute('''
                                    UPDATE experiments SET
                                        original_filename = ?, renamed_filename = ?, file_path = ?,
                                        server_path = ?, file_size = ?, upload_time = ?,
                                        file_hash = ?, test_project_name = ?, experiment_date = ?,
                                        test_object = ?, core_drawing_number = ?, test_type = ?,
                                        equipment = ?, version_code = ?, file_extension = ?,
                                        notes = ?, flat_tube_mold = ?, header_mold = ?, fin_tool = ?,
                                        applicant_name = ?
                                    WHERE data_id = ?
                                ''', (
                                    uploaded_file.name, final_filename, result["file_path"],
                                    result["server_path"], result["file_size"], datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                    result["file_hash"], config_project, config_date.strftime('%Y-%m-%d'),
                                    config_object, config_core or "", config_type, config_equipment,
                                    config_security, config_ext, materials_info, tube_mold or "",
                                    header_mold or "", fin_mold or "", config_applicant, final_data_id
                                ))
                            else:
                                cursor.execute('''
                                    INSERT INTO experiments 
                                    (data_id, test_project_name, experiment_date, test_object, test_type,
                                     equipment, version_code, file_extension, core_drawing_number,
                                     applicant_name, original_filename, renamed_filename, file_path,
                                     server_path, file_size, upload_time, file_hash, notes,
                                     flat_tube_mold, header_mold, fin_tool)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                ''', (
                                    final_data_id, config_project, config_date.strftime('%Y-%m-%d'),
                                    config_object, config_type, config_equipment, config_security,
                                    config_ext, config_core or "", config_applicant, uploaded_file.name,
                                    final_filename, result["file_path"], result["server_path"],
                                    result["file_size"], datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                    result["file_hash"], materials_info, tube_mold or "",
                                    header_mold or "", fin_mold or ""
                                ))
                            
                            conn.commit()
                            st.success("✅ 文件上传成功！")
                            st.balloons()
                            
                    except Exception as e:
                        st.error(f"❌ 上传失败：{str(e)}")

    # ============= 选项卡2和3保持基本结构 =============
    with tab2:
        st.info("批量文件处理功能开发中...")
    
    with tab3:
        st.info("文件记录管理功能开发中...")

# ==================== 其他页面保持基本结构 ====================
elif menu == "🔍 数据查询":
    st.markdown('<div class="sub-header">🔍 实验数据查询</div>', unsafe_allow_html=True)
    st.info("数据查询功能开发中...")

elif menu == "📋 数据浏览":
    st.markdown('<div class="sub-header">📋 所有实验数据</div>', unsafe_allow_html=True)
    st.info("数据浏览功能开发中...")

elif menu == "📂 文件夹浏览":
    st.markdown('<div class="sub-header">📂 文件夹结构浏览</div>', unsafe_allow_html=True)
    st.info("文件夹浏览功能开发中...")

elif menu == "⚙️ 系统设置":
    st.markdown('<div class="sub-header">⚙️ 系统设置</div>', unsafe_allow_html=True)
    st.info("系统设置功能开发中...")

# ==================== 页脚信息 ====================
st.markdown("---")
col_footer1, col_footer2, col_footer3 = st.columns(3)

with col_footer1:
    st.write("**版本**: 7.0 (密级管理版V2 - 含申请人)")

with col_footer2:
    st.write("**技术支持**: 实验室数据管理团队")

with col_footer3:
    st.write(f"**环境**: {'云端' if os.environ.get('STREAMLIT_CLOUD') else '本地'}")
