# lab_manager_enhanced_complete.py
import os
import sys
import tempfile

# 云端部署适配
if 'STREAMLIT_CLOUD' in os.environ:
    # 使用临时目录存储文件
    UPLOAD_DIR = tempfile.mkdtemp()
    DB_PATH = os.path.join(tempfile.gettempdir(), 'lab_data.db')
else:
    UPLOAD_DIR = 'uploaded_files'
    DB_PATH = 'lab_data_enhanced.db'

# 创建上传目录
os.makedirs(UPLOAD_DIR, exist_ok=True)
for sec in ['A', 'AA', 'S']:
    os.makedirs(f"{UPLOAD_DIR}（密级{sec}）", exist_ok=True)
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
        applicant_clean,  # 申请人姓名
        security_level    # 密级
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
    
    # 构建层级化文件夹路径：uploaded_files（密级X）/项目名称/年份/月份/芯体图号/测试类型_实验对象_申请人/
    folder_parts = [
        f"uploaded_files（密级{security_level}）",  # 根目录带密级
        project_clean,
        year,
        month,
        core_clean,
        f"{test_type_clean}_{test_object_clean}_{applicant_clean}"  # 增加申请人
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

# ==================== 页面配置 ====================
st.set_page_config(
    page_title="实验室数据管理系统 - 密级管理版V2",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded"
)

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

# ==================== 数据库连接 ====================
@st.cache_resource
def get_connection():
    """获取数据库连接"""
    return sqlite3.connect('lab_data_enhanced.db', check_same_thread=False)

conn = get_connection()

# 添加applicant_name字段（如果不存在）
try:
    cursor = conn.cursor()
    cursor.execute("ALTER TABLE experiments ADD COLUMN applicant_name TEXT")
    conn.commit()
except sqlite3.OperationalError:
    pass  # 字段已存在

# ==================== 侧边栏导航 ====================
st.sidebar.markdown('<div class="main-header">导航菜单</div>', unsafe_allow_html=True)

menu = st.sidebar.radio(
    "选择功能",
    ["🏠 系统首页", "📁 文件管理", "🔍 数据查询", "📋 数据浏览", "📂 文件夹浏览", "⚙️ 系统设置"]
)

# 系统信息
st.sidebar.markdown("---")
st.sidebar.markdown("### 📊 系统信息")
st.sidebar.info("**版本**: 7.0\n\n**功能**: 密级管理版V2（含申请人）\n\n**数据库**: SQLite")

# ==================== 全局变量定义 ====================
# 设备类型选项 - 包含各种功率规格
equipment_options = [
    "30kw", 
    "50kw",      # 50kW设备
    "75kw",      # 75kW设备
    "15kw",      # 15kW设备
    "28kw",      # 28kW设备
    "10kw",      # 10kW设备
    "120kw",     # 120kW设备
    "金相", 
    "压力交变", 
    "盐雾", 
    "其他"
]

# 测试类型选项 - 新材料测试相关
test_type_options = [
    "焓差测试",      # 焓差性能测试
    "盐雾测试",      # 耐腐蚀测试
    "压力交变",      # 压力循环测试
    "材料测试",      # 材料性能测试
    "扫描电镜",      # SEM扫描电镜分析
    "温度交变",      # 温度循环测试
    "其他测试"
]

# 密级选项 - A级(保密), AA级(高级保密), S级(绝密)
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

# ==================== 1. 系统首页 ====================
if menu == "🏠 系统首页":
    st.markdown('<div class="sub-header">欢迎使用实验室数据管理系统（密级管理版V2）</div>', unsafe_allow_html=True)
    
    # 欢迎信息
    st.markdown("""
    <div class="info-box">
    <h3>🎯 系统简介</h3>
    <p>本系统专为实验室数据管理设计，支持实验数据的文件上传、管理和查询分析，采用层级化文件夹结构存储文件，并支持文件密级管理。</p>
    <p><strong>核心功能</strong>：文件上传、自动重命名、层级化存储、密级管理、数据追踪</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 功能特色
    st.markdown('<div class="sub-header">✨ 功能特色</div>', unsafe_allow_html=True)
    
    col_feature1, col_feature2, col_feature3 = st.columns(3)
    
    with col_feature1:
        st.markdown("""
        <div class="info-box">
        <h4>📁 智能文件管理</h4>
        <ul>
        <li>自动重命名文件</li>
        <li>层级化文件夹存储</li>
        <li>根目录带密级标识</li>
        <li>批量处理支持</li>
        <li>包含申请人信息</li>
        </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with col_feature2:
        st.markdown("""
        <div class="info-box">
        <h4>🔍 高级数据查询</h4>
        <ul>
        <li>多条件组合筛选</li>
        <li>三大主材模具号搜索</li>
        <li>按密级筛选（A/AA/S）</li>
        <li>按申请人搜索</li>
        <li>实时数据预览</li>
        </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with col_feature3:
        st.markdown("""
        <div class="info-box">
        <h4>📊 数据分析统计</h4>
        <ul>
        <li>项目统计报表</li>
        <li>文件类型分析</li>
        <li>密级分布统计</li>
        <li>申请人统计</li>
        <li>数据导出功能</li>
        </ul>
        </div>
        """, unsafe_allow_html=True)
    
    # 系统统计
    st.markdown('<div class="sub-header">📈 系统统计</div>', unsafe_allow_html=True)
    
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
        if os.path.exists('lab_data_enhanced.db'):
            db_size = os.path.getsize('lab_data_enhanced.db') / 1024
            st.metric("💾 数据库大小", f"{db_size:.1f} KB")
    
    # 密级统计
    st.markdown('<div class="sub-header">🔒 密级分布</div>', unsafe_allow_html=True)
    
    col_sec1, col_sec2, col_sec3 = st.columns(3)
    
    df_security = pd.read_sql_query("SELECT version_code as security_level, COUNT(*) as count FROM experiments GROUP BY version_code", conn)
    
    if not df_security.empty:
        for i, (_, row) in enumerate(df_security.iterrows()):
            cols = [col_sec1, col_sec2, col_sec3]
            with cols[i % 3]:
                security_class = security_colors.get(row['security_level'], 'security-badge-A')
                st.markdown(f'<span class="{security_class}">密级{row["security_level"]}</span>', unsafe_allow_html=True)
                st.metric("数量", f"{row['count']} 条")
    
    # 最近活动
    st.markdown('<div class="sub-header">🕒 最近活动</div>', unsafe_allow_html=True)
    
    df_recent = pd.read_sql_query(
        """SELECT data_id, test_project_name, upload_time, renamed_filename, version_code as security_level, applicant_name
        FROM experiments 
        WHERE upload_time IS NOT NULL 
        ORDER BY upload_time DESC LIMIT 5""", 
        conn
    )
    
    if not df_recent.empty:
        for _, row in df_recent.iterrows():
            col_act1, col_act2, col_act3 = st.columns([3, 2, 1])
            with col_act1:
                st.write(f"📄 **{row['test_project_name']}** - {row['data_id']}")
                if row['applicant_name']:
                    st.write(f"👤 申请人: {row['applicant_name']}")
            with col_act2:
                if row['upload_time']:
                    st.write(f"🕒 {row['upload_time'].split(' ')[0]}")
            with col_act3:
                security_class = security_colors.get(row['security_level'], 'security-badge-A')
                st.markdown(f'<span class="{security_class}">密级{row["security_level"]}</span>', unsafe_allow_html=True)
    else:
        st.info("暂无最近活动记录")
    
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
        
        **示例**：`uploaded_files（密级A）/JCI蒸发器/2024/01/DRG-EVAP-001/焓差测试_蒸发器_张三/JCI蒸发器_20240115_蒸发器_DRG-EVAP-001_焓差测试_30kw_张三_A.xlsx`
        
        ### 🔒 密级说明
        
        - **A级（绿色）**：保密数据
        - **AA级（橙色）**：高级保密数据
        - **S级（红色）**：绝密数据
        
        ### 🔧 测试类型说明
        
        - **焓差测试**：换热性能测试
        - **盐雾测试**：耐腐蚀性能测试
        - **压力交变**：压力循环耐久测试
        - **材料测试**：材料性能分析
        - **扫描电镜**：微观结构分析
        - **温度交变**：温度循环测试
        
        ### ⚙️ 设备类型说明
        
        - **10kW-120kW**：不同功率规格的测试设备
        - **金相**：金相分析设备
        - **压力交变**：压力交变测试设备
        - **盐雾**：盐雾试验设备
        
        ### ⚠️ 注意事项
        
        - 带*号为必填项（包括芯体图号、密级和申请人姓名）
        - 文件上传后会自动重命名并存储到带密级的根目录
        - 芯体图号、申请人和密级会影响文件名和文件夹路径生成
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
        
        # 步骤指示器
        col_step1, col_step2, col_step3, col_step4 = st.columns(4)
        with col_step1:
            st.markdown("**1️⃣ 选择记录**")
        with col_step2:
            st.markdown("**2️⃣ 上传文件**")
        with col_step3:
            st.markdown("**3️⃣ 配置信息**")
        with col_step4:
            st.markdown("**4️⃣ 完成上传**")
        
        # 步骤1：选择或创建记录
        st.markdown("#### 步骤1：选择或创建实验记录")
        
        col_select1, col_select2 = st.columns(2)
        
        with col_select1:
            # 选择现有记录
            df_records = pd.read_sql_query(
                "SELECT data_id, test_project_name, experiment_date, test_object, core_drawing_number, version_code as security_level, applicant_name FROM experiments ORDER BY experiment_date DESC",
                conn
            )
            
            if not df_records.empty:
                # 如果有从查询页面传递的ID，优先选择
                if 'selected_data_id' in st.session_state:
                    default_index = 0
                    for i, (_, row) in enumerate(df_records.iterrows()):
                        if row['data_id'] == st.session_state.selected_data_id:
                            default_index = i
                            break
                else:
                    default_index = 0
                
                record_options = [f"{row['data_id']} | {row['test_project_name']} | {row['applicant_name'] or '未知'} | 密级{row['security_level']}" 
                                 for _, row in df_records.iterrows()]
                selected_option = st.selectbox(
                    "选择现有记录", 
                    record_options,
                    index=default_index,
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
                
                create_new = st.checkbox("创建新记录", value=False, help="如果没有合适的记录，可以创建新记录")
            else:
                create_new = True
                st.info("暂无现有记录，请创建新记录")
        
        with col_select2:
            if create_new:
                st.markdown("**创建新记录**")
                
                # 快速创建表单
                with st.form("quick_record_form"):
                    quick_project = st.text_input("测试项目名称*", key="quick_project")
                    quick_date = st.date_input("实验日期*", value=datetime.now(), key="quick_date")
                    quick_object = st.selectbox("实验对象*", 
                        ["整机", "冷凝器", "蒸发器", "热泵", "水箱", "热虹吸", "其他"], key="quick_object")
                    quick_type = st.selectbox("测试类型*", test_type_options, key="quick_type")
                    quick_equipment = st.selectbox("设备*", equipment_options, key="quick_equipment")
                    quick_security = st.selectbox(
                        "密级*", 
                        security_options, 
                        index=0, 
                        key="quick_security",
                        help=f"A-{security_descriptions['A']}, AA-{security_descriptions['AA']}, S-{security_descriptions['S']}"
                    )
                    quick_core = st.text_input("芯体图号*", placeholder="如：DRG-EVAP-001", key="quick_core",
                                              help="芯体图号将影响文件名生成")
                    quick_applicant = st.text_input("申请人姓名*", placeholder="如：张三", key="quick_applicant",
                                                   help="填写申请实验的人员姓名")
                    
                    if st.form_submit_button("⚡ 快速创建记录"):
                        if all([quick_project, quick_object, quick_type, quick_equipment, quick_security, quick_core, quick_applicant]):
                            # 生成数据ID
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
                                # 清空传递的ID
                                if 'selected_data_id' in st.session_state:
                                    del st.session_state.selected_data_id
                                st.rerun()
                            
                            except sqlite3.IntegrityError:
                                st.error("❌ 数据ID已存在，请调整参数")
                            except Exception as e:
                                st.error(f"❌ 创建失败：{str(e)}")
                        else:
                            st.error("❌ 请填写所有必填项")
        
        # 步骤2：文件上传
        st.markdown("#### 步骤2：上传文件")
        
        uploaded_file = st.file_uploader(
            "选择要上传的文件",
            type=['xlsx', 'csv', 'pdf', 'jpg', 'jpeg', 'png', 'docx', 'tif', 'dat', 'txt'],
            help="支持常见的实验数据文件格式，最大文件大小：200MB"
        )
        
        if uploaded_file:
            # 显示文件信息
            file_size_kb = len(uploaded_file.getvalue()) / 1024
            st.markdown(f"""
            <div class="info-box">
            <h4>📄 已选择文件</h4>
            <p><strong>文件名</strong>: {uploaded_file.name}</p>
            <p><strong>文件大小</strong>: {file_size_kb:.1f} KB</p>
            <p><strong>文件类型</strong>: {os.path.splitext(uploaded_file.name)[1]}</p>
            </div>
            """, unsafe_allow_html=True)
            
            # 步骤3：配置文件信息
            st.markdown("#### 步骤3：配置文件信息")
            
            col_config1, col_config2 = st.columns(2)
            
            # 初始化配置变量
            if not create_new and selected_option:
                # 从数据库获取完整记录
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM experiments WHERE data_id = ?", (selected_data_id,))
                record = cursor.fetchone()
                
                if record:
                    # 使用记录信息预填表单
                    record_dict = dict(zip([desc[0] for desc in cursor.description], record))
                    
                    with col_config1:
                        config_project = st.text_input(
                            "测试项目名称*", 
                            value=record_dict['test_project_name'], 
                            key="config_project_1"
                        )
                        config_date = st.date_input(
                            "实验日期*", 
                            value=datetime.strptime(record_dict['experiment_date'], '%Y-%m-%d'), 
                            key="config_date_1"
                        )
                        config_object = st.selectbox(
                            "实验对象*", 
                            ["整机", "冷凝器", "蒸发器", "热泵", "水箱", "热虹吸", "其他"],
                            index=["整机", "冷凝器", "蒸发器", "热泵", "水箱", "热虹吸", "其他"].index(record_dict['test_object']), 
                            key="config_object_1"
                        )
                        config_core = st.text_input(
                            "芯体图号*", 
                            value=record_dict['core_drawing_number'] or "", 
                            key="config_core_1",
                            help="芯体图号将影响文件名生成"
                        )
                    
                    with col_config2:
                        config_type = st.selectbox(
                            "测试类型*", 
                            test_type_options,
                            index=test_type_options.index(record_dict['test_type']) if record_dict['test_type'] in test_type_options else 0, 
                            key="config_type_1"
                        )
                        config_equipment = st.selectbox(
                            "设备*", 
                            equipment_options,
                            index=equipment_options.index(record_dict['equipment']) if record_dict['equipment'] in equipment_options else 0, 
                            key="config_equipment_1"
                        )
                        
                        # 处理密级
                        security_value = record_dict['version_code']
                        security_index = 0
                        if security_value in security_options:
                            security_index = security_options.index(security_value)
                        else:
                            st.warning(f"⚠️ 数据库中的密级 '{security_value}' 不在当前选项列表中，已自动设置为默认密级 A")
                        
                        config_security = st.selectbox(
                            "密级*", 
                            security_options,
                            index=security_index, 
                            key="config_security_1",
                            help=f"A-{security_descriptions['A']}, AA-{security_descriptions['AA']}, S-{security_descriptions['S']}"
                        )
                        
                        config_applicant = st.text_input(
                            "申请人姓名*", 
                            value=record_dict.get('applicant_name', '') or '',
                            placeholder="如：张三",
                            key="config_applicant_1",
                            help="填写申请实验的人员姓名"
                        )
                        
                        config_test_purpose = st.text_input(
                            "测试目的",
                            value=record_dict.get('notes', '') or '',
                            placeholder="如：验证设计参数、性能评估等",
                            key="config_test_purpose_1",
                            help="填写本次测试的主要目的"
                        )
                        original_ext = os.path.splitext(uploaded_file.name)[1].lower()
                        config_ext = original_ext if original_ext else record_dict['file_extension']
                        config_ext = st.selectbox(
                            "文件类型*", 
                            [".xlsx", ".csv", ".pdf", ".jpg", ".png", ".docx", ".tif", ".dat"],
                            index=[".xlsx", ".csv", ".pdf", ".jpg", ".png", ".docx", ".tif", ".dat"].index(config_ext) if config_ext in [".xlsx", ".csv", ".pdf", ".jpg", ".png", ".docx", ".tif", ".dat"] else 0, 
                            key="config_ext_1"
                        )
                else:
                    # 记录不存在，使用默认值
                    st.warning("⚠️ 选中的记录不存在，请重新选择或创建新记录")
                    create_new = True
            
            if create_new:
                with col_config1:
                    config_project = st.text_input(
                        "测试项目名称*", 
                        key="config_project_2",
                        placeholder="如：JCI蒸发器"
                    )
                    config_date = st.date_input(
                        "实验日期*", 
                        value=datetime.now(), 
                        key="config_date_2"
                    )
                    config_object = st.selectbox(
                        "实验对象*", 
                        ["整机", "冷凝器", "蒸发器", "热泵", "水箱", "热虹吸", "其他"], 
                        key="config_object_2"
                    )
                    config_core = st.text_input(
                        "芯体图号*", 
                        key="config_core_2",
                        placeholder="如：DRG-EVAP-001",
                        help="芯体图号将影响文件名生成"
                    )
                
                with col_config2:
                    config_type = st.selectbox(
                        "测试类型*", 
                        test_type_options,
                        index=0, 
                        key="config_type_2"
                    )
                    config_equipment = st.selectbox(
                        "设备*", 
                        equipment_options,
                        index=0, 
                        key="config_equipment_2"
                    )
                    config_security = st.selectbox(
                        "密级*", 
                        security_options,
                        index=0, 
                        key="config_security_2",
                        help=f"A-{security_descriptions['A']}, AA-{security_descriptions['AA']}, S-{security_descriptions['S']}"
                    )
                    config_applicant = st.text_input(
                        "申请人姓名*", 
                        placeholder="如：张三",
                        key="config_applicant_2",
                        help="填写申请实验的人员姓名"
                    )
                    config_test_purpose = st.text_input(
                        "测试目的",
                        placeholder="如：验证设计参数、性能评估等",
                        key="config_test_purpose_2",
                        help="填写本次测试的主要目的"
                    )
                    original_ext = os.path.splitext(uploaded_file.name)[1].lower()
                    config_ext = original_ext if original_ext else ".xlsx"
                    config_ext = st.selectbox(
                        "文件类型*", 
                        [".xlsx", ".csv", ".pdf", ".jpg", ".png", ".docx", ".tif", ".dat"],
                        index=[".xlsx", ".csv", ".pdf", ".jpg", ".png", ".docx", ".tif", ".dat"].index(config_ext) if config_ext in [".xlsx", ".csv", ".pdf", ".jpg", ".png", ".docx", ".tif", ".dat"] else 0, 
                        key="config_ext_2"
                    )
            
            # 三大主材模具号
            st.markdown('<div class="material-section">', unsafe_allow_html=True)
            st.markdown("### 🔧 三大主材模具号")
            st.markdown("请输入各主材的模具编号")
            
            col_material1, col_material2, col_material3 = st.columns(3)
            
            with col_material1:
                st.markdown("#### 🌀 翅片模具")
                fin_mold = st.text_input(
                    "翅片模具号", 
                    placeholder="如：B150、B200、F-001",
                    key="fin_mold",
                    help="输入翅片模具编号"
                )
                st.caption("示例：B150, B200, F-001, FIN-001")
            
            with col_material2:
                st.markdown("#### 📦 集流管模具")
                header_mold = st.text_input(
                    "集流管模具号", 
                    placeholder="如：H100、H200、HEAD-001",
                    key="header_mold",
                    help="输入集流管模具编号"
                )
                st.caption("示例：H100, H200, HEAD-001, COL-001")
            
            with col_material3:
                st.markdown("#### 🧊 扁管模具")
                tube_mold = st.text_input(
                    "扁管模具号", 
                    placeholder="如：A43S、A50S、T100",
                    key="tube_mold",
                    help="输入扁管模具编号"
                )
                st.caption("示例：A43S, A50S, T100, TUBE-001")
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            # 实时文件名和文件夹预览
            if config_project and config_object and config_type and config_equipment and config_security and config_core and config_applicant:
                # 实时生成预览文件名
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
                preview_data_id = preview_filename.replace(config_ext, "")
                preview_folder = generate_folder_structure(preview_params)
                preview_relative_path = os.path.join(
                    os.path.basename(preview_folder),
                    preview_filename
                ).replace(os.sep, '/')
                
                # 显示文件名预览
                st.markdown('<div class="success-box">', unsafe_allow_html=True)
                st.markdown(f"### 📄 文件名预览")
                st.markdown(f'<div class="file-preview">{preview_filename}</div>', unsafe_allow_html=True)
                
                # 显示文件夹路径预览
                st.markdown(f"### 📂 存储路径预览")
                st.markdown(f'<div class="folder-preview">{preview_folder}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="folder-preview">完整路径: {preview_folder}/{preview_filename}</div>', unsafe_allow_html=True)
                
                st.write(f"**数据ID**: {preview_data_id}")
                st.write(f"**相对路径**: {preview_relative_path}")
                security_class = security_colors.get(config_security, 'security-badge-A')
                st.markdown(f"**密级**: <span class='{security_class}'>密级{config_security}</span>", unsafe_allow_html=True)
                st.write(f"**根目录**: uploaded_files（密级{config_security}）")
                st.write(f"**申请人**: {config_applicant}")
                
                # 显示芯体图号影响
                if config_core:
                    st.success(f"✅ 芯体图号 `{config_core}` 已包含在文件名和文件夹路径中")
                else:
                    st.error("❌ 请填写芯体图号")
                st.markdown('</div>', unsafe_allow_html=True)
            
            # 步骤4：上传和处理
            st.markdown("#### 步骤4：上传和处理")
            
            col_action1, col_action2, col_action3 = st.columns(3)
            
            with col_action1:
                if st.button("🚀 上传并重命名", type="primary", width='stretch'):
                    # 验证输入
                    is_valid, message = validate_filename_inputs(
                        config_project, config_date, config_object, 
                        config_type, config_equipment, config_security, config_core, config_applicant
                    )
                    
                    if not is_valid:
                        st.error(message)
                    else:
                        try:
                            # 生成最终文件名参数
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
                            
                            # 保存文件到层级化文件夹
                            result = save_uploaded_file(uploaded_file, final_params, final_filename)
                            
                            if not result["success"]:
                                st.error(f"❌ 文件保存失败：{result.get('error', '未知错误')}")
                            else:
                                file_path = result["file_path"]
                                folder_path = result["folder_path"]
                                relative_path = result["relative_path"]
                                file_size = result["file_size"]
                                file_hash = result["file_hash"]
                                server_path = result["server_path"]
                                upload_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                
                                # 进度条
                                progress_bar = st.progress(0)
                                status_text = st.empty()
                                
                                # 模拟上传过程
                                for i in range(100):
                                    time.sleep(0.01)
                                    progress_bar.progress(i + 1)
                                    if i < 30:
                                        status_text.text("正在验证文件...")
                                    elif i < 70:
                                        status_text.text("正在保存文件...")
                                    else:
                                        status_text.text("正在更新数据库...")
                                
                                # 组合模具号信息到notes字段
                                materials_info = f"测试目的：{config_test_purpose or ''}"
                                if any([fin_mold, header_mold, tube_mold]):
                                    materials_info += "\n\n三大主材模具号："
                                    if fin_mold:
                                        materials_info += f"\n- 翅片模具：{fin_mold}"
                                    if header_mold:
                                        materials_info += f"\n- 集流管模具：{header_mold}"
                                    if tube_mold:
                                        materials_info += f"\n- 扁管模具：{tube_mold}"
                                
                                # 更新数据库
                                cursor = conn.cursor()
                                
                                # 检查记录是否存在
                                cursor.execute("SELECT COUNT(*) FROM experiments WHERE data_id = ?", (final_data_id,))
                                exists = cursor.fetchone()[0] > 0
                                
                                if exists:
                                    # 更新现有记录
                                    cursor.execute('''
                                        UPDATE experiments SET
                                            original_filename = ?,
                                            renamed_filename = ?,
                                            file_path = ?,
                                            server_path = ?,
                                            file_size = ?,
                                            upload_time = ?,
                                            file_hash = ?,
                                            test_project_name = ?,
                                            experiment_date = ?,
                                            test_object = ?,
                                            core_drawing_number = ?,
                                            test_type = ?,
                                            equipment = ?,
                                            version_code = ?,
                                            file_extension = ?,
                                            notes = ?,
                                            flat_tube_mold = ?,
                                            header_mold = ?,
                                            fin_tool = ?,
                                            applicant_name = ?
                                        WHERE data_id = ?
                                    ''', (
                                        uploaded_file.name,
                                        final_filename,
                                        file_path,
                                        server_path,
                                        file_size,
                                        upload_time,
                                        file_hash,
                                        config_project,
                                        config_date.strftime('%Y-%m-%d'),
                                        config_object,
                                        config_core or "",
                                        config_type,
                                        config_equipment,
                                        config_security,
                                        config_ext,
                                        materials_info,
                                        tube_mold or "",
                                        header_mold or "",
                                        fin_mold or "",
                                        config_applicant,
                                        final_data_id
                                    ))
                                else:
                                    # 插入新记录
                                    cursor.execute('''
                                        INSERT INTO experiments 
                                        (data_id, test_project_name, experiment_date, test_object, 
                                         test_type, equipment, version_code, file_extension,
                                         core_drawing_number, applicant_name,
                                         original_filename, renamed_filename, file_path, server_path,
                                         file_size, upload_time, file_hash, notes,
                                         flat_tube_mold, header_mold, fin_tool)
                                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                    ''', (
                                        final_data_id,
                                        config_project,
                                        config_date.strftime('%Y-%m-%d'),
                                        config_object,
                                        config_type,
                                        config_equipment,
                                        config_security,
                                        config_ext,
                                        config_core or "",
                                        config_applicant,
                                        uploaded_file.name,
                                        final_filename,
                                        file_path,
                                        server_path,
                                        file_size,
                                        upload_time,
                                        file_hash,
                                        materials_info,
                                        tube_mold or "",
                                        header_mold or "",
                                        fin_mold or ""
                                    ))
                                
                                conn.commit()
                                
                                # 完成进度条
                                progress_bar.progress(100)
                                status_text.text("✅ 上传完成！")
                                
                                # 显示成功信息
                                st.success("✅ 文件上传成功！")
                                st.balloons()
                                
                                # 显示详细信息
                                with st.expander("📋 查看上传详情", expanded=True):
                                    col_detail1, col_detail2 = st.columns(2)
                                    
                                    with col_detail1:
                                        st.markdown("**📄 文件信息**")
                                        st.write(f"- **原始文件名**：{uploaded_file.name}")
                                        st.write(f"- **标准文件名**：{final_filename}")
                                        st.write(f"- **文件大小**：{file_size / 1024:.1f} KB")
                                        st.write(f"- **上传时间**：{upload_time}")
                                        st.write(f"- **芯体图号**：{config_core}")
                                        st.write(f"- **申请人**：{config_applicant}")
                                        security_class = security_colors.get(config_security, 'security-badge-A')
                                        st.markdown(f"- **密级**：<span class='{security_class}'>密级{config_security}</span>", unsafe_allow_html=True)
                                        st.write(f"- **测试目的**：{config_test_purpose or '未填写'}")
                                        st.write(f"- **文件哈希**：{file_hash[:16]}...")
                                    
                                    with col_detail2:
                                        st.markdown("**💾 存储信息**")
                                        st.write(f"- **本地路径**：`{file_path}`")
                                        st.write(f"- **服务器路径**：`{server_path}`")
                                        st.write(f"- **相对路径**：`{relative_path}`")
                                        st.write(f"- **数据ID**：{final_data_id}")
                                        st.write(f"- **根目录**：uploaded_files（密级{config_security}）")
                                    
                                    # 显示模具号信息
                                    if any([fin_mold, header_mold, tube_mold]):
                                        st.markdown("### 🔧 三大主材模具号")
                                        col_mat_display1, col_mat_display2, col_mat_display3 = st.columns(3)
                                        
                                        with col_mat_display1:
                                            st.markdown("**🔄 翅片模具**")
                                            st.write(fin_mold or "未填写")
                                        
                                        with col_mat_display2:
                                            st.markdown("**📦 集流管模具**")
                                            st.write(header_mold or "未填写")
                                        
                                        with col_mat_display3:
                                            st.markdown("**🧊 扁管模具**")
                                            st.write(tube_mold or "未填写")
                                
                                # 清空传递的ID
                                if 'selected_data_id' in st.session_state:
                                    del st.session_state.selected_data_id
                            
                        except Exception as e:
                            st.error(f"❌ 上传失败：{str(e)}")
            
            with col_action2:
                # 仅重命名选项
                if st.button("📝 仅预览文件名", type="secondary", width='stretch'):
                    if not all([config_project, config_object, config_type, config_equipment, config_security, config_core, config_applicant]):
                        st.error("请填写所有必填项（带*号）")
                    else:
                        # 生成新文件名
                        rename_params = {
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
                        
                        new_filename = generate_filename(rename_params)
                        st.markdown('<div class="info-box">', unsafe_allow_html=True)
                        st.markdown("### 📝 文件名建议")
                        st.markdown(f'<div class="file-preview">{new_filename}</div>', unsafe_allow_html=True)
                        security_class = security_colors.get(config_security, 'security-badge-A')
                        st.markdown(f"**密级**: <span class='{security_class}'>密级{config_security}</span>", unsafe_allow_html=True)
                        st.write(f"**申请人**: {config_applicant}")
                        st.write("此功能仅显示建议文件名，实际上传需要点击'上传并重命名'")
                        st.markdown('</div>', unsafe_allow_html=True)
            
            with col_action3:
                # 取消按钮
                if st.button("❌ 取消操作", width='stretch'):
                    st.info("已取消上传操作")
                    st.rerun()

    # ============= 选项卡2：批量文件处理 =============
    with tab2:
        st.markdown("### 📦 批量文件处理")
        
        st.markdown("""
        <div class="info-box">
        <h4>📚 批量处理说明</h4>
        <p>批量上传适用于多个相似文件的处理，所有文件将使用相同的项目信息，但会按顺序编号。</p>
        <p><strong>适用场景</strong>：同一项目的多次实验、系列测试数据、分批次上传</p>
        </div>
        """, unsafe_allow_html=True)
        
        uploaded_files = st.file_uploader(
            "选择多个文件",
            type=['xlsx', 'csv', 'pdf', 'jpg', 'jpeg', 'png', 'docx', 'tif', 'dat'],
            accept_multiple_files=True,
            help="按住Ctrl或Shift键可以选择多个文件"
        )
        
        if uploaded_files:
            st.success(f"✅ 已选择 {len(uploaded_files)} 个文件")
            
            # 显示文件列表
            with st.expander("📋 查看文件列表", expanded=True):
                file_list = []
                for i, file in enumerate(uploaded_files, 1):
                    file_size_kb = len(file.getvalue()) / 1024
                    file_ext = os.path.splitext(file.name)[1].lower()
                    file_list.append({
                        "序号": i,
                        "文件名": file.name,
                        "类型": file_ext,
                        "大小": f"{file_size_kb:.1f} KB"
                    })
                
                file_df = pd.DataFrame(file_list)
                st.dataframe(file_df, use_container_width=True, hide_index=True)
            
            # 批量配置
            st.markdown("### ⚙️ 批量配置")
            
            col_batch1, col_batch2 = st.columns(2)
            
            with col_batch1:
                batch_project = st.text_input(
                    "批量项目名称*", 
                    placeholder="如：JCI蒸发器批量测试",
                    help="所有文件将使用相同的项目名称"
                )
                batch_date = st.date_input(
                    "批量实验日期*", 
                    value=datetime.now(),
                    help="所有文件的实验日期"
                )
                batch_object = st.selectbox(
                    "批量实验对象*", 
                    ["整机", "冷凝器", "蒸发器", "热泵", "水箱", "热虹吸", "其他"],
                    help="所有文件的实验对象"
                )
                batch_core = st.text_input(
                    "批量芯体图号*", 
                    placeholder="如：DRG-EVAP-001",
                    help="所有文件的芯体图号前缀"
                )
            
            with col_batch2:
                batch_type = st.selectbox(
                    "批量测试类型*", 
                    test_type_options,
                    index=0,
                    help="所有文件的测试类型"
                )
                batch_equipment = st.selectbox(
                    "批量设备*", 
                    equipment_options,
                    index=0,
                    help="所有文件的设备类型"
                )
                batch_security = st.selectbox(
                    "批量密级*", 
                    security_options,
                    index=0,
                    help="所有文件的密级"
                )
                batch_applicant = st.text_input(
                    "批量申请人姓名*", 
                    placeholder="如：张三",
                    help="所有文件的申请人姓名"
                )
                batch_test_purpose = st.text_input(
                    "批量测试目的",
                    placeholder="如：批量性能验证",
                    help="所有文件的测试目的"
                )
                start_number = st.number_input(
                    "起始编号*", 
                    min_value=1, 
                    value=1,
                    help="文件编号的起始值"
                )
            
            # 批量三大主材模具号
            st.markdown('<div class="material-section">', unsafe_allow_html=True)
            st.markdown("### 🔧 批量三大主材模具号")
            st.markdown("请输入各主材的模具编号（将应用于所有批量文件）")
            
            col_batch_mat1, col_batch_mat2, col_batch_mat3 = st.columns(3)
            
            with col_batch_mat1:
                st.markdown("#### 🌀 批量翅片模具")
                batch_fin_mold = st.text_input(
                    "批量翅片模具号", 
                    placeholder="如：B150",
                    key="batch_fin_mold",
                    help="输入批量翅片模具编号"
                )
            
            with col_batch_mat2:
                st.markdown("#### 📦 批量集流管模具")
                batch_header_mold = st.text_input(
                    "批量集流管模具号", 
                    placeholder="如：H100",
                    key="batch_header_mold",
                    help="输入批量集流管模具编号"
                )
            
            with col_batch_mat3:
                st.markdown("#### 🧊 批量扁管模具")
                batch_tube_mold = st.text_input(
                    "批量扁管模具号", 
                    placeholder="如：A43S",
                    key="batch_tube_mold",
                    help="输入批量扁管模具编号"
                )
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            # 预览批量重命名
            if st.button("👀 预览批量重命名", width='stretch'):
                if not all([batch_project, batch_core, batch_applicant]):
                    st.error("请填写批量项目名称、芯体图号和申请人")
                else:
                    preview_data = []
                    for i, file in enumerate(uploaded_files, start=start_number):
                        original_name = file.name
                        file_ext = os.path.splitext(original_name)[1].lower()
                        if not file_ext:
                            file_ext = ".dat"
                        
                        # 生成文件名
                        params = {
                            'test_project_name': batch_project,
                            'experiment_date': batch_date,
                            'test_object': batch_object,
                            'core_drawing_number': f"{batch_core}-{i:03d}",
                            'test_type': batch_type,
                            'equipment': batch_equipment,
                            'security_level': batch_security,
                            'applicant_name': batch_applicant,
                            'file_extension': file_ext
                        }
                        
                        new_name = generate_filename(params)
                        
                        preview_data.append({
                            "序号": i,
                            "原文件名": original_name,
                            "新文件名": new_name,
                            "文件类型": file_ext,
                            "大小": f"{len(file.getvalue()) / 1024:.1f} KB",
                            "芯体图号": f"{batch_core}-{i:03d}",
                            "申请人": batch_applicant,
                            "密级": batch_security
                        })
                    
                    preview_df = pd.DataFrame(preview_data)
                    
                    st.markdown("### 📝 批量重命名预览")
                    st.dataframe(preview_df, use_container_width=True, hide_index=True)
                    
                    # 保存到session
                    st.session_state.batch_preview = preview_data
                    st.session_state.batch_params = {
                        'project': batch_project,
                        'date': batch_date,
                        'object': batch_object,
                        'core': batch_core,
                        'type': batch_type,
                        'equipment': batch_equipment,
                        'security': batch_security,
                        'applicant': batch_applicant,
                        'purpose': batch_test_purpose,
                        'fin_mold': batch_fin_mold,
                        'header_mold': batch_header_mold,
                        'tube_mold': batch_tube_mold,
                        'start_num': start_number
                    }
            
            # 执行批量处理
            if 'batch_preview' in st.session_state:
                if st.button("🚀 执行批量上传", type="primary", width='stretch'):
                    if not all([batch_project, batch_core, batch_applicant]):
                        st.error("请填写批量项目名称、芯体图号和申请人")
                    else:
                        success_count = 0
                        error_list = []
                        
                        # 进度条
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        for idx, item in enumerate(st.session_state.batch_preview):
                            try:
                                file = uploaded_files[idx]
                                new_name = item['新文件名']
                                data_id = new_name.replace(os.path.splitext(new_name)[1], "")
                                
                                # 更新进度
                                progress = int((idx + 1) / len(uploaded_files) * 100)
                                progress_bar.progress(progress)
                                status_text.text(f"正在处理文件 {idx + 1}/{len(uploaded_files)}: {new_name}")
                                
                                # 生成文件名参数
                                params = {
                                    'test_project_name': batch_project,
                                    'experiment_date': batch_date,
                                    'test_object': batch_object,
                                    'core_drawing_number': f"{batch_core}-{idx+start_number:03d}",
                                    'test_type': batch_type,
                                    'equipment': batch_equipment,
                                    'security_level': batch_security,
                                    'applicant_name': batch_applicant,
                                    'file_extension': os.path.splitext(new_name)[1]
                                }
                                
                                # 保存文件到层级化文件夹
                                result = save_uploaded_file(file, params, new_name)
                                
                                if not result["success"]:
                                    error_list.append(f"文件 {item['原文件名']}: {result.get('error', '保存失败')}")
                                    continue
                                
                                # 文件信息
                                file_size = result["file_size"]
                                file_hash = result["file_hash"]
                                file_path = result["file_path"]
                                server_path = result["server_path"]
                                upload_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                
                                # 组合模具号信息
                                batch_materials_info = f"测试目的：{batch_test_purpose or ''}"
                                if any([batch_fin_mold, batch_header_mold, batch_tube_mold]):
                                    batch_materials_info += "\n\n三大主材模具号："
                                    if batch_fin_mold:
                                        batch_materials_info += f"\n- 翅片模具：{batch_fin_mold}"
                                    if batch_header_mold:
                                        batch_materials_info += f"\n- 集流管模具：{batch_header_mold}"
                                    if batch_tube_mold:
                                        batch_materials_info += f"\n- 扁管模具：{batch_tube_mold}"
                                
                                # 插入数据库
                                cursor = conn.cursor()
                                cursor.execute('''
                                    INSERT OR REPLACE INTO experiments 
                                    (data_id, test_project_name, experiment_date, test_object, 
                                     core_drawing_number, test_type, equipment, version_code, file_extension,
                                     applicant_name,
                                     original_filename, renamed_filename, file_path, server_path,
                                     file_size, upload_time, file_hash, notes,
                                     flat_tube_mold, header_mold, fin_tool)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                ''', (
                                    data_id,
                                    batch_project,
                                    batch_date.strftime('%Y-%m-%d'),
                                    batch_object,
                                    f"{batch_core}-{idx+start_number:03d}",
                                    batch_type,
                                    batch_equipment,
                                    batch_security,
                                    os.path.splitext(new_name)[1],
                                    batch_applicant,
                                    item['原文件名'],
                                    new_name,
                                    file_path,
                                    server_path,
                                    file_size,
                                    upload_time,
                                    file_hash,
                                    batch_materials_info,
                                    batch_tube_mold or "",
                                    batch_header_mold or "",
                                    batch_fin_mold or ""
                                ))
                                
                                success_count += 1
                                
                            except Exception as e:
                                error_list.append(f"文件 {item['原文件名']}: {str(e)}")
                        
                        conn.commit()
                        
                        # 完成进度
                        progress_bar.progress(100)
                        status_text.text("✅ 批量处理完成！")
                        
                        if success_count > 0:
                            st.success(f"✅ 批量上传完成！成功 {success_count}/{len(uploaded_files)} 个文件")
                        
                        if error_list:
                            st.error("⚠️ 部分文件上传失败")
                            with st.expander("查看错误详情"):
                                for error in error_list:
                                    st.error(error)
                        
                        # 清空预览
                        if 'batch_preview' in st.session_state:
                            del st.session_state.batch_preview
    
    # ============= 选项卡3：文件记录管理 =============
    with tab3:
        st.markdown("### 📋 文件记录管理")
        
        # 搜索和筛选
        col_search1, col_search2 = st.columns(2)
        
        with col_search1:
            search_filename = st.text_input(
                "搜索文件名", 
                placeholder="输入文件名关键字",
                help="支持模糊查询"
            )
            search_project = st.text_input(
                "搜索项目", 
                placeholder="输入项目名称关键字",
                help="支持模糊查询"
            )
            search_core = st.text_input(
                "搜索芯体图号", 
                placeholder="输入芯体图号关键字",
                help="支持模糊查询"
            )
            search_applicant = st.text_input(
                "搜索申请人", 
                placeholder="输入申请人姓名",
                help="支持模糊查询"
            )
        
        with col_search2:
            # 密级筛选
            security_filter = st.multiselect(
                "密级筛选",
                security_options,
                help="按密级筛选记录"
            )
            
            has_files_only = st.checkbox("仅显示有文件的记录", value=True)
            sort_by = st.selectbox(
                "排序方式", 
                ["上传时间 最新", "上传时间 最早", "文件大小 降序", "文件大小 升序", "项目名称", "芯体图号", "密级", "申请人"],
                help="选择排序方式"
            )
            
            # 模具号搜索
            search_material = st.text_input(
                "搜索模具号", 
                placeholder="输入翅片/集流管/扁管模具号关键词",
                help="搜索三大主材模具号信息"
            )
        
        # 构建查询
        sql = "SELECT * FROM experiments WHERE 1=1"
        params = []
        
        if has_files_only:
            sql += " AND renamed_filename IS NOT NULL"
        
        if search_filename:
            sql += " AND (renamed_filename LIKE ? OR original_filename LIKE ?)"
            params.extend([f"%{search_filename}%", f"%{search_filename}%"])
        
        if search_project:
            sql += " AND test_project_name LIKE ?"
            params.append(f"%{search_project}%")
        
        if search_core:
            sql += " AND core_drawing_number LIKE ?"
            params.append(f"%{search_core}%")
        
        if search_applicant:
            sql += " AND applicant_name LIKE ?"
            params.append(f"%{search_applicant}%")
        
        if security_filter:
            placeholders = ','.join(['?'] * len(security_filter))
            sql += f" AND version_code IN ({placeholders})"
            params.extend(security_filter)
        
        if search_material:
            sql += " AND (fin_tool LIKE ? OR header_mold LIKE ? OR flat_tube_mold LIKE ?)"
            params.extend([f"%{search_material}%", f"%{search_material}%", f"%{search_material}%"])
        
        # 排序
        if sort_by == "上传时间 最新":
            sql += " ORDER BY upload_time DESC"
        elif sort_by == "上传时间 最早":
            sql += " ORDER BY upload_time ASC"
        elif sort_by == "文件大小 降序":
            sql += " ORDER BY file_size DESC"
        elif sort_by == "文件大小 升序":
            sql += " ORDER BY file_size ASC"
        elif sort_by == "项目名称":
            sql += " ORDER BY test_project_name"
        elif sort_by == "芯体图号":
            sql += " ORDER BY core_drawing_number"
        elif sort_by == "密级":
            sql += " ORDER BY version_code"
        elif sort_by == "申请人":
            sql += " ORDER BY applicant_name"
        
        # 执行查询
        df_files = pd.read_sql_query(sql, conn, params=params) if params else pd.read_sql_query(sql, conn)
        
        st.markdown(f"### 📊 文件记录列表（共 **{len(df_files)}** 条）")
        
        if not df_files.empty:
            # 文件统计
            col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
            
            with col_stat1:
                total_size = df_files['file_size'].sum() / (1024*1024)
                st.metric("总文件大小", f"{total_size:.1f} MB")
            
            with col_stat2:
                avg_size = df_files['file_size'].mean() / 1024
                st.metric("平均文件大小", f"{avg_size:.1f} KB")
            
            with col_stat3:
                file_types = df_files['file_extension'].value_counts()
                st.metric("文件类型数", len(file_types))
            
            with col_stat4:
                projects_count = df_files['test_project_name'].nunique()
                st.metric("涉及项目数", projects_count)
            
            # 文件列表
            for _, row in df_files.iterrows():
                with st.expander(f"📄 {row['renamed_filename'] or '未命名文件'}", expanded=False):
                    col_file1, col_file2 = st.columns(2)
                    
                    with col_file1:
                        st.markdown("**📋 基本信息**")
                        st.write(f"- **数据ID**: {row['data_id']}")
                        st.write(f"- **测试项目**: {row['test_project_name']}")
                        st.write(f"- **实验日期**: {row['experiment_date']}")
                        st.write(f"- **实验对象**: {row['test_object']}")
                        st.write(f"- **芯体图号**: {row['core_drawing_number'] or '未填写'}")
                        st.write(f"- **申请人**: {row['applicant_name'] or '未填写'}")
                        security_class = security_colors.get(row['version_code'], 'security-badge-A')
                        st.markdown(f"- **密级**: <span class='{security_class}'>密级{row['version_code']}</span>", unsafe_allow_html=True)
                        st.write(f"- **原始文件名**: {row['original_filename']}")
                        st.write(f"- **标准文件名**: {row['renamed_filename']}")
                    
                    with col_file2:
                        st.markdown("**💾 文件信息**")
                        if row['file_size']:
                            st.write(f"- **文件大小**: {row['file_size'] / 1024:.1f} KB")
                        if row['upload_time']:
                            st.write(f"- **上传时间**: {row['upload_time']}")
                        if row['server_path']:
                            st.write(f"- **服务器路径**: `{row['server_path']}`")
                        if row['file_hash']:
                            st.write(f"- **文件哈希**: `{row['file_hash'][:16]}...`")
                        st.write(f"- **文件类型**: {row['file_extension']}")
                    
                    # 显示测试目的和模具号信息
                    if row['notes']:
                        st.markdown("**📝 测试目的和模具号信息**")
                        notes_lines = row['notes'].split('\n')
                        for line in notes_lines:
                            if line.strip():
                                st.write(line)
                    
                    # 显示模具号
                    if row['fin_tool'] or row['header_mold'] or row['flat_tube_mold']:
                        st.markdown("**🔧 三大主材模具号**")
                        col_mat1, col_mat2, col_mat3 = st.columns(3)
                        
                        with col_mat1:
                            st.write(f"**翅片**: {row['fin_tool'] or '未填写'}")
                        with col_mat2:
                            st.write(f"**集流管**: {row['header_mold'] or '未填写'}")
                        with col_mat3:
                            st.write(f"**扁管**: {row['flat_tube_mold'] or '未填写'}")
                    
                    # 操作按钮
                    col_action1, col_action2, col_action3 = st.columns(3)
                    
                    with col_action1:
                        if st.button("📋 复制路径", key=f"copy_path_{row['id']}"):
                            if row['server_path']:
                                st.info(f"已复制：{row['server_path']}")
                    
                    with col_action2:
                        if st.button("🔄 重新上传", key=f"reupload_{row['id']}"):
                            st.info("请在单文件上传页面重新上传")
                    
                    with col_action3:
                        if st.button("🗑️ 删除记录", key=f"delete_{row['id']}"):
                            st.warning("⚠️ 此操作将删除文件记录，请谨慎操作！")
                            confirm = st.checkbox(f"确认删除 {row['renamed_filename']}?", key=f"confirm_{row['id']}")
                            if confirm:
                                try:
                                    cursor = conn.cursor()
                                    cursor.execute("DELETE FROM experiments WHERE id = ?", (row['id'],))
                                    conn.commit()
                                    st.success("✅ 记录已删除")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"删除失败：{str(e)}")
            
            # 导出功能
            st.markdown("### 📥 数据导出")
            csv_data = df_files.to_csv(index=False)
            st.download_button(
                label="💾 导出文件记录",
                data=csv_data,
                file_name=f"文件记录_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                width='stretch'
            )
        
        else:
            st.info("📭 暂无文件记录")

# ==================== 3. 数据查询页面 ====================
elif menu == "🔍 数据查询":
    st.markdown('<div class="sub-header">🔍 实验数据查询</div>', unsafe_allow_html=True)
    
    # 查询条件区域
    with st.expander("🔎 查询条件设置", expanded=True):
        col_filter1, col_filter2, col_filter3 = st.columns(3)
        
        with col_filter1:
            query_project = st.text_input(
                "项目名称", 
                placeholder="输入项目名称关键字",
                help="支持模糊查询"
            )
            
            query_test_object = st.multiselect(
                "实验对象", 
                ["整机", "冷凝器", "蒸发器", "热泵", "水箱", "热虹吸", "其他"],
                help="可选择多个实验对象"
            )
            
            date_range = st.date_input(
                "实验日期范围",
                [datetime(2024, 1, 1), datetime.now()],
                help="选择日期查询范围"
            )
            
            query_applicant = st.text_input(
                "申请人姓名", 
                placeholder="输入申请人姓名",
                help="支持模糊查询"
            )
        
        with col_filter2:
            query_test_type = st.selectbox(
                "测试类型", 
                [""] + test_type_options,
                help="选择测试类型"
            )
            
            query_equipment = st.multiselect(
                "设备类型", 
                equipment_options,
                help="可选择多个设备类型"
            )
            
            query_security = st.multiselect(
                "密级", 
                security_options,
                help="按密级筛选"
            )
        
        with col_filter3:
            query_filename = st.text_input(
                "文件名关键字", 
                placeholder="输入文件名包含的关键字",
                help="支持模糊查询"
            )
            
            query_core = st.text_input(
                "芯体图号关键字", 
                placeholder="输入芯体图号包含的关键字",
                help="支持模糊查询"
            )
            
            # 模具号搜索
            st.markdown("**🔧 三大主材模具号搜索**")
            query_fin = st.text_input(
                "翅片模具号", 
                placeholder="输入翅片模具号关键词",
                help="如：B150、F-001"
            )
            query_header = st.text_input(
                "集流管模具号", 
                placeholder="输入集流管模具号关键词",
                help="如：H100、HEAD-001"
            )
            query_tube = st.text_input(
                "扁管模具号", 
                placeholder="输入扁管模具号关键词",
                help="如：A43S、T100"
            )
    
    # 查询按钮
    col_search1, col_search2, col_search3 = st.columns([2, 1, 1])
    with col_search1:
        search_clicked = st.button("🔍 开始查询", type="primary", width='stretch')
    with col_search2:
        reset_clicked = st.button("🔄 重置条件", width='stretch')
    
    if reset_clicked:
        st.rerun()
    
    if search_clicked:
        # 构建查询SQL
        sql = "SELECT * FROM experiments WHERE 1=1"
        params = []
        
        if query_project:
            sql += " AND test_project_name LIKE ?"
            params.append(f"%{query_project}%")
        
        if query_test_object:
            placeholders = ','.join(['?'] * len(query_test_object))
            sql += f" AND test_object IN ({placeholders})"
            params.extend(query_test_object)
        
        if query_equipment:
            placeholders = ','.join(['?'] * len(query_equipment))
            sql += f" AND equipment IN ({placeholders})"
            params.extend(query_equipment)
        
        if query_security:
            placeholders = ','.join(['?'] * len(query_security))
            sql += f" AND version_code IN ({placeholders})"
            params.extend(query_security)
        
        if query_test_type:
            sql += " AND test_type = ?"
            params.append(query_test_type)
        
        if query_applicant:
            sql += " AND applicant_name LIKE ?"
            params.append(f"%{query_applicant}%")
        
        if len(date_range) == 2:
            sql += " AND experiment_date BETWEEN ? AND ?"
            params.extend([
                date_range[0].strftime('%Y-%m-%d'),
                date_range[1].strftime('%Y-%m-%d')
            ])
        
        if query_filename:
            sql += " AND (renamed_filename LIKE ? OR original_filename LIKE ?)"
            params.extend([f"%{query_filename}%", f"%{query_filename}%"])
        
        if query_core:
            sql += " AND core_drawing_number LIKE ?"
            params.append(f"%{query_core}%")
        
        # 模具号搜索条件
        mold_conditions = []
        if query_fin:
            mold_conditions.append("fin_tool LIKE ?")
            params.append(f"%{query_fin}%")
        if query_header:
            mold_conditions.append("header_mold LIKE ?")
            params.append(f"%{query_header}%")
        if query_tube:
            mold_conditions.append("flat_tube_mold LIKE ?")
            params.append(f"%{query_tube}%")
        
        if mold_conditions:
            sql += " AND (" + " OR ".join(mold_conditions) + ")"
        
        sql += " ORDER BY experiment_date DESC"
        
        # 执行查询
        with st.spinner("正在查询数据..."):
            df_results = pd.read_sql_query(sql, conn, params=params)
        
        # 显示结果
        st.markdown(f'<div class="sub-header">📊 查询结果（共 {len(df_results)} 条）</div>', unsafe_allow_html=True)
        
        if not df_results.empty:
            # 选择显示字段
            display_fields = st.multiselect(
                "选择显示字段",
                ['data_id', 'test_project_name', 'experiment_date', 'test_object', 
                 'test_type', 'equipment', 'version_code', 'core_drawing_number',
                 'applicant_name', 'renamed_filename', 'file_size', 'upload_time', 
                 'fin_tool', 'header_mold', 'flat_tube_mold'],
                default=['data_id', 'test_project_name', 'experiment_date', 
                        'test_object', 'test_type', 'core_drawing_number', 
                        'applicant_name', 'version_code', 'renamed_filename']
            )
            
            if display_fields:
                # 格式化显示
                display_df = df_results[display_fields].copy()
                
                # 格式化文件大小
                if 'file_size' in display_df.columns:
                    display_df['file_size'] = display_df['file_size'].apply(
                        lambda x: f"{x/1024:.1f} KB" if pd.notnull(x) and x > 0 else ""
                    )
                
                # 显示表格
                st.dataframe(
                    display_df,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "data_id": "数据ID",
                        "test_project_name": "项目名称",
                        "experiment_date": "实验日期",
                        "test_object": "实验对象",
                        "test_type": "测试类型",
                        "equipment": "设备",
                        "version_code": "密级",
                        "core_drawing_number": "芯体图号",
                        "applicant_name": "申请人",
                        "renamed_filename": "文件名",
                        "file_size": "文件大小",
                        "upload_time": "上传时间",
                        "fin_tool": "翅片模具",
                        "header_mold": "集流管模具",
                        "flat_tube_mold": "扁管模具"
                    }
                )
            
            # 详细查看
            st.markdown("### 📖 详细查看")
            selected_id = st.selectbox(
                "选择记录查看详情",
                df_results['data_id'].tolist(),
                key="detail_select"
            )
            
            if selected_id:
                record = df_results[df_results['data_id'] == selected_id].iloc[0]
                
                # 创建详情标签页
                tab_detail1, tab_detail2, tab_detail3 = st.tabs(["📋 基本信息", "📁 文件信息", "🔧 模具信息"])
                
                with tab_detail1:
                    col_info1, col_info2 = st.columns(2)
                    
                    with col_info1:
                        st.write("**核心信息**")
                        st.write(f"- **数据ID**：{record['data_id']}")
                        st.write(f"- **测试项目**：{record['test_project_name']}")
                        st.write(f"- **实验日期**：{record['experiment_date']}")
                        st.write(f"- **实验对象**：{record['test_object']}")
                        st.write(f"- **测试类型**：{record['test_type']}")
                        st.write(f"- **设备**：{record['equipment']}")
                        st.write(f"- **芯体图号**：{record['core_drawing_number'] or '未填写'}")
                        st.write(f"- **申请人**：{record['applicant_name'] or '未填写'}")
                    
                    with col_info2:
                        st.write("**其他信息**")
                        security_class = security_colors.get(record['version_code'], 'security-badge-A')
                        st.markdown(f"- **密级**：<span class='{security_class}'>密级{record['version_code']}</span>", unsafe_allow_html=True)
                        st.write(f"- **文件类型**：{record['file_extension']}")
                        st.write(f"- **制冷剂类型**：{record['refrigerant_type'] or '未填写'}")
                        st.write(f"- **创建时间**：{record['created_time']}")
                
                with tab_detail2:
                    if pd.notnull(record['renamed_filename']) and record['renamed_filename']:
                        col_file1, col_file2 = st.columns(2)
                        
                        with col_file1:
                            st.write("**文件详情**")
                            st.write(f"- **原始文件名**：{record['original_filename']}")
                            st.write(f"- **标准文件名**：{record['renamed_filename']}")
                            if record['file_size']:
                                st.write(f"- **文件大小**：{record['file_size'] / 1024:.1f} KB")
                            if record['upload_time']:
                                st.write(f"- **上传时间**：{record['upload_time']}")
                            if record['file_hash']:
                                st.write(f"- **文件哈希**：{record['file_hash'][:16]}...")
                        
                        with col_file2:
                            st.write("**文件路径**")
                            if record['file_path']:
                                st.write(f"- **本地路径**：`{record['file_path']}`")
                            if record['server_path']:
                                st.write(f"- **服务器路径**：`{record['server_path']}`")
                            st.write(f"- **根目录**：uploaded_files（密级{record['version_code']}）")
                        
                        # 文件操作
                        st.write("### 📂 文件操作")
                        col_op1, col_op2, col_op3 = st.columns(3)
                        
                        with col_op1:
                            if st.button("📋 复制路径", key=f"copy_{selected_id}"):
                                if record['server_path']:
                                    st.info(f"已复制服务器路径：{record['server_path']}")
                        
                        with col_op2:
                            # 模拟下载
                            if st.button("⬇️ 下载文件", key=f"download_{selected_id}"):
                                st.info("在实际部署中，这里会触发文件下载")
                        
                        with col_op3:
                            if st.button("🔄 重新上传", key=f"reupload_{selected_id}"):
                                st.info("请在文件管理页面重新上传文件")
                    else:
                        st.info("⚠️ 该记录没有关联文件")
                        if st.button("📤 立即上传文件", key=f"upload_{selected_id}"):
                            st.session_state.selected_data_id = selected_id
                            st.session_state.menu = "📁 文件管理"
                            st.rerun()
                
                with tab_detail3:
                    if record['fin_tool'] or record['header_mold'] or record['flat_tube_mold'] or record['notes']:
                        if record['notes']:
                            st.markdown("**📝 测试目的**")
                            # 解析notes字段，提取测试目的
                            notes_lines = record['notes'].split('\n')
                            for line in notes_lines:
                                if line.startswith("测试目的："):
                                    st.write(line)
                        
                        if record['fin_tool'] or record['header_mold'] or record['flat_tube_mold']:
                            st.markdown("**🔧 三大主材模具号**")
                            col_mat1, col_mat2, col_mat3 = st.columns(3)
                            
                            with col_mat1:
                                st.markdown("**🔄 翅片模具**")
                                st.write(record['fin_tool'] or "未填写")
                            
                            with col_mat2:
                                st.markdown("**📦 集流管模具**")
                                st.write(record['header_mold'] or "未填写")
                            
                            with col_mat3:
                                st.markdown("**🧊 扁管模具**")
                                st.write(record['flat_tube_mold'] or "未填写")
                    else:
                        st.info("未填写模具号信息")
            
            # 导出功能
            st.markdown("### 📥 数据导出")
            col_export1, col_export2 = st.columns(2)
            
            with col_export1:
                csv_data = df_results.to_csv(index=False)
                st.download_button(
                    label="💾 导出为CSV",
                    data=csv_data,
                    file_name=f"查询结果_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    width='stretch'
                )
            
            with col_export2:
                # 导出选中的记录
                if selected_id:
                    selected_data = df_results[df_results['data_id'] == selected_id]
                    selected_csv = selected_data.to_csv(index=False)
                    st.download_button(
                        label="📄 导出当前记录",
                        data=selected_csv,
                        file_name=f"记录_{selected_id}_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv",
                        width='stretch'
                    )
        
        else:
            st.info("🔍 未找到匹配的数据记录")

# ==================== 4. 数据浏览页面 ====================
elif menu == "📋 数据浏览":
    st.markdown('<div class="sub-header">📋 所有实验数据</div>', unsafe_allow_html=True)
    
    # 快速筛选
    filter_option = st.selectbox(
        "筛选方式", 
        ["全部数据", "按项目名称筛选", "按实验对象筛选", "按设备类型筛选", "按芯体图号筛选", "按测试类型筛选", "按密级筛选", "按申请人筛选"],
        help="选择数据筛选方式"
    )
    
    # 构建查询
    sql = "SELECT data_id, test_project_name, experiment_date, test_object, test_type, equipment, version_code, core_drawing_number, applicant_name, renamed_filename, fin_tool, header_mold, flat_tube_mold FROM experiments"
    
    if filter_option == "按项目名称筛选":
        projects = pd.read_sql_query("SELECT DISTINCT test_project_name FROM experiments ORDER BY test_project_name", conn)
        if not projects.empty:
            selected_project = st.selectbox("选择项目名称", projects['test_project_name'].tolist())
            sql += f" WHERE test_project_name = '{selected_project}'"
    
    elif filter_option == "按实验对象筛选":
        selected_object = st.selectbox("选择实验对象", 
            ["整机", "冷凝器", "蒸发器", "热泵", "水箱", "热虹吸", "其他"])
        sql += f" WHERE test_object = '{selected_object}'"
    
    elif filter_option == "按设备类型筛选":
        selected_equip = st.selectbox("选择设备类型", equipment_options)
        sql += f" WHERE equipment = '{selected_equip}'"
    
    elif filter_option == "按芯体图号筛选":
        cores = pd.read_sql_query("SELECT DISTINCT core_drawing_number FROM experiments WHERE core_drawing_number IS NOT NULL AND core_drawing_number != '' ORDER BY core_drawing_number", conn)
        if not cores.empty:
            selected_core = st.selectbox("选择芯体图号", cores['core_drawing_number'].tolist())
            sql += f" WHERE core_drawing_number = '{selected_core}'"
    
    elif filter_option == "按测试类型筛选":
        selected_test_type = st.selectbox("选择测试类型", test_type_options)
        sql += f" WHERE test_type = '{selected_test_type}'"
    
    elif filter_option == "按密级筛选":
        selected_security = st.selectbox("选择密级", security_options)
        sql += f" WHERE version_code = '{selected_security}'"
    
    elif filter_option == "按申请人筛选":
        applicants = pd.read_sql_query("SELECT DISTINCT applicant_name FROM experiments WHERE applicant_name IS NOT NULL AND applicant_name != '' ORDER BY applicant_name", conn)
        if not applicants.empty:
            selected_applicant = st.selectbox("选择申请人", applicants['applicant_name'].tolist())
            sql += f" WHERE applicant_name = '{selected_applicant}'"
    
    sql += " ORDER BY experiment_date DESC"
    
    # 执行查询
    df_all = pd.read_sql_query(sql, conn)
    
    # 显示数据
    st.markdown(f"### 📊 数据概览（共 **{len(df_all)}** 条记录）")
    
    if not df_all.empty:
        # 数据显示
        st.dataframe(
            df_all,
            use_container_width=True,
            hide_index=True,
            column_config={
                "data_id": "数据ID",
                "test_project_name": "项目名称",
                "experiment_date": "实验日期",
                "test_object": "实验对象",
                "test_type": "测试类型",
                "equipment": "设备",
                "version_code": "密级",
                "core_drawing_number": "芯体图号",
                "applicant_name": "申请人",
                "renamed_filename": "文件名",
                "fin_tool": "翅片模具",
                "header_mold": "集流管模具",
                "flat_tube_mold": "扁管模具"
            }
        )
        
        # 统计信息
        st.markdown("### 📈 统计信息")
        
        col_stat1, col_stat2, col_stat3, col_stat4, col_stat5 = st.columns(5)
        
        with col_stat1:
            has_files = df_all['renamed_filename'].notna().sum()
            st.metric("📁 有文件记录", f"{has_files} 条")
        
        with col_stat2:
            no_files = len(df_all) - has_files
            st.metric("📭 无文件记录", f"{no_files} 条")
        
        with col_stat3:
            file_ratio = has_files / len(df_all) * 100 if len(df_all) > 0 else 0
            st.metric("📊 文件完整率", f"{file_ratio:.1f}%")
        
        with col_stat4:
            unique_projects = df_all['test_project_name'].nunique()
            st.metric("🏢 项目数量", unique_projects)
        
        with col_stat5:
            unique_applicants = df_all['applicant_name'].nunique()
            st.metric("👥 申请人数量", unique_applicants)
        
        # 导出功能
        st.markdown("### 📥 数据导出")
        
        col_export1, col_export2 = st.columns(2)
        
        with col_export1:
            csv_data = df_all.to_csv(index=False)
            st.download_button(
                label="💾 导出全部数据",
                data=csv_data,
                file_name=f"实验室数据_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                width='stretch'
            )
        
        with col_export2:
            # 导出当前筛选的数据
            st.download_button(
                label="📄 导出筛选数据",
                data=csv_data,
                file_name=f"筛选数据_{filter_option}_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                width='stretch'
            )
    else:
        st.info("📭 暂无数据记录")

# ==================== 5. 文件夹浏览页面 ====================
elif menu == "📂 文件夹浏览":
    st.markdown('<div class="sub-header">📂 文件夹结构浏览</div>', unsafe_allow_html=True)
    
    st.markdown("""
    <div class="info-box">
    <h4>📁 文件存储结构</h4>
    <p>文件按以下层级结构存储：</p>
    <code>uploaded_files（密级X）/项目名称/年份/月份/芯体图号/测试类型_实验对象_申请人/文件名</code>
    </div>
    """, unsafe_allow_html=True)
    
    # 获取上传目录 - 查找所有带密级的根目录
    upload_dirs = [d for d in os.listdir('.') if d.startswith('uploaded_files（密级') and os.path.isdir(d)]
    
    if upload_dirs:
        # 让用户选择密级根目录
        selected_root = st.selectbox("选择密级根目录", upload_dirs)
        
        if selected_root:
            # 获取所有项目
            projects = [d for d in os.listdir(selected_root) if os.path.isdir(os.path.join(selected_root, d))]
            
            if projects:
                selected_project = st.selectbox("选择项目", projects)
                
                if selected_project:
                    project_path = os.path.join(selected_root, selected_project)
                    
                    # 获取年份
                    years = [d for d in os.listdir(project_path) if os.path.isdir(os.path.join(project_path, d))]
                    
                    if years:
                        selected_year = st.selectbox("选择年份", sorted(years, reverse=True))
                        
                        if selected_year:
                            year_path = os.path.join(project_path, selected_year)
                            
                            # 获取月份
                            months = [d for d in os.listdir(year_path) if os.path.isdir(os.path.join(year_path, d))]
                            
                            if months:
                                selected_month = st.selectbox("选择月份", sorted(months, reverse=True))
                                
                                if selected_month:
                                    month_path = os.path.join(year_path, selected_month)
                                    
                                    # 获取芯体图号
                                    cores = [d for d in os.listdir(month_path) if os.path.isdir(os.path.join(month_path, d))]
                                    
                                    if cores:
                                        selected_core = st.selectbox("选择芯体图号", cores)
                                        
                                        if selected_core:
                                            core_path = os.path.join(month_path, selected_core)
                                            
                                            # 获取测试类型_实验对象_申请人文件夹
                                            test_folders = [d for d in os.listdir(core_path) if os.path.isdir(os.path.join(core_path, d))]
                                            
                                            if test_folders:
                                                selected_test_folder = st.selectbox("选择测试类型文件夹", test_folders)
                                                
                                                if selected_test_folder:
                                                    test_folder_path = os.path.join(core_path, selected_test_folder)
                                                    
                                                    # 获取文件列表
                                                    files = [f for f in os.listdir(test_folder_path) if os.path.isfile(os.path.join(test_folder_path, f))]
                                                    
                                                    if files:
                                                        st.markdown(f"### 📄 文件列表（共 {len(files)} 个）")
                                                        
                                                        file_data = []
                                                        for file in files:
                                                            file_path = os.path.join(test_folder_path, file)
                                                            file_size = os.path.getsize(file_path) / 1024
                                                            file_mod_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                                                            
                                                            # 从文件名提取密级
                                                            file_parts = file.split('_')
                                                            security = file_parts[-1].split('.')[0] if file_parts else 'Unknown'
                                                            security_class = security_colors.get(security, 'security-badge-A')
                                                            
                                                            # 提取申请人（文件名倒数第二个部分）
                                                            applicant = file_parts[-2] if len(file_parts) >= 2 else 'Unknown'
                                                            
                                                            file_data.append({
                                                                "文件名": file,
                                                                "大小(KB)": f"{file_size:.1f}",
                                                                "修改时间": file_mod_time.strftime('%Y-%m-%d %H:%M:%S'),
                                                                "申请人": applicant,
                                                                "密级": f"<span class='{security_class}'>密级{security}</span>"
                                                            })
                                                        
                                                        file_df = pd.DataFrame(file_data)
                                                        st.write(file_df.to_html(escape=False), unsafe_allow_html=True)
                                                        
                                                        # 完整路径
                                                        st.markdown("### 📂 完整路径")
                                                        st.code(test_folder_path)
                                                    else:
                                                        st.info("该文件夹中没有文件")
                                            else:
                                                st.info("该芯体图号下没有测试类型文件夹")
                                    else:
                                        st.info("该月份下没有芯体图号文件夹")
                            else:
                                st.info("该年份下没有月份文件夹")
                    else:
                        st.info("该项目下没有年份文件夹")
            else:
                st.info("该根目录下没有项目文件夹")
    else:
        st.info("暂无上传的文件，请先上传文件")

# ==================== 6. 系统设置页面 ====================
elif menu == "⚙️ 系统设置":
    st.markdown('<div class="sub-header">⚙️ 系统设置</div>', unsafe_allow_html=True)
    
    tab_setting1, tab_setting2, tab_setting3 = st.tabs(["🔧 系统配置", "💾 数据管理", "📖 使用帮助"])
    
    with tab_setting1:
        st.markdown("### 🔧 系统配置")
        
        col_set1, col_set2 = st.columns(2)
        
        with col_set1:
            st.markdown("#### 文件设置")
            max_file_size = st.number_input(
                "最大文件大小(MB)", 
                min_value=1, 
                max_value=500, 
                value=200,
                help="限制上传文件的最大大小"
            )
            
            allowed_extensions = st.multiselect(
                "允许的文件类型",
                [".xlsx", ".csv", ".pdf", ".jpg", ".png", ".docx", ".tif", ".dat", ".txt"],
                default=[".xlsx", ".csv", ".pdf", ".jpg", ".png"],
                help="选择允许上传的文件类型"
            )
            
            auto_rename = st.checkbox(
                "自动重命名文件", 
                value=True,
                help="上传时自动按规则重命名文件"
            )
        
        with col_set2:
            st.markdown("#### 数据库设置")
            
            # 数据库信息
            if os.path.exists('lab_data_enhanced.db'):
                db_size = os.path.getsize('lab_data_enhanced.db') / 1024
                st.write(f"**数据库文件**: lab_data_enhanced.db")
                st.write(f"**文件大小**: {db_size:.1f} KB")
                
                # 统计信息
                df_stats = pd.read_sql_query("SELECT COUNT(*) as total FROM experiments", conn)
                st.write(f"**记录总数**: {df_stats['total'][0]} 条")
                
                df_with_files = pd.read_sql_query("SELECT COUNT(*) as count FROM experiments WHERE renamed_filename IS NOT NULL", conn)
                st.write(f"**有文件记录**: {df_with_files['count'][0]} 条")
            else:
                st.warning("数据库文件不存在")
            
            # 数据库操作
            st.markdown("#### 数据库操作")
            
            if st.button("🔄 重新创建数据库", width='stretch'):
                try:
                    import create_database_enhanced
                    create_database_enhanced.create_database()
                    st.success("✅ 数据库重新创建成功")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ 创建失败：{str(e)}")
            
            if st.button("📊 更新统计信息", width='stretch'):
                st.info("统计信息已更新")
                st.rerun()
        
        # 保存设置
        if st.button("💾 保存设置", type="primary", width='stretch'):
            st.success("✅ 设置已保存")
    
    with tab_setting2:
        st.markdown("### 💾 数据管理")
        
        col_data1, col_data2 = st.columns(2)
        
        with col_data1:
            st.markdown("#### 数据备份")
            
            if st.button("💾 备份数据库", width='stretch'):
                try:
                    backup_file = f"lab_data_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
                    shutil.copy2('lab_data_enhanced.db', backup_file)
                    st.success(f"✅ 数据库已备份到: {backup_file}")
                except Exception as e:
                    st.error(f"❌ 备份失败: {str(e)}")
            
            if st.button("📄 导出全部数据", width='stretch'):
                try:
                    df_all = pd.read_sql_query("SELECT * FROM experiments", conn)
                    csv_data = df_all.to_csv(index=False)
                    
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = f"实验室数据_完整导出_{timestamp}.csv"
                    
                    st.download_button(
                        label="⬇️ 下载导出的数据",
                        data=csv_data,
                        file_name=filename,
                        mime="text/csv",
                        width='stretch'
                    )
                except Exception as e:
                    st.error(f"❌ 导出失败: {str(e)}")
        
        with col_data2:
            st.markdown("#### 数据清理")
            
            st.warning("⚠️ 数据清理操作不可恢复，请谨慎操作！")
            
            days_to_keep = st.number_input(
                "保留最近多少天的数据", 
                min_value=1, 
                max_value=365, 
                value=90,
                help="自动清理指定天数前的无文件记录"
            )
            
            if st.button("🧹 清理旧数据", width='stretch'):
                try:
                    cutoff_date = (datetime.now() - timedelta(days=days_to_keep)).strftime('%Y-%m-%d')
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM experiments WHERE experiment_date < ? AND renamed_filename IS NULL", (cutoff_date,))
                    deleted_count = cursor.rowcount
                    conn.commit()
                    st.success(f"✅ 已清理 {deleted_count} 条旧记录")
                except Exception as e:
                    st.error(f"❌ 清理失败: {str(e)}")
    
    with tab_setting3:
        st.markdown("### 📖 使用帮助")
        
        st.markdown("""
        <div class="info-box">
        <h4>🚀 快速开始指南</h4>
        
        #### 1. 文件上传
        1. 进入"文件管理"页面
        2. 选择"单文件上传"或"批量文件处理"
        3. 配置文件信息（包括三大主材模具号、申请人和密级）
        4. 系统会自动重命名文件并存储到带密级的根目录
        
        #### 2. 数据查询
        1. 进入"数据查询"页面
        2. 设置查询条件（支持密级、申请人和模具号搜索）
        3. 查看查询结果
        4. 可以查看详细信息和操作文件
        
        #### 3. 文件夹浏览
        1. 进入"文件夹浏览"页面
        2. 按层级结构浏览文件
        3. 查看文件详细信息
        
        #### 4. 文件命名规则
        文件名格式：`项目名称_日期_对象_芯体图号_测试类型_设备_申请人_密级.扩展名`
        
        **示例**: `JCI蒸发器_20240115_蒸发器_DRG-EVAP-001_焓差测试_30kw_张三_A.xlsx`
        
        #### 5. 文件夹结构规则
        文件夹结构：`uploaded_files（密级X）/项目名称/年份/月份/芯体图号/测试类型_实验对象_申请人/`
        
        **示例**: `uploaded_files（密级A）/JCI蒸发器/2024/01/DRG-EVAP-001/焓差测试_蒸发器_张三/JCI蒸发器_20240115_蒸发器_DRG-EVAP-001_焓差测试_30kw_张三_A.xlsx`
        
        #### 6. 三大主材模具号
        - **翅片模具**: 如 B150, B200, F-001
        - **集流管模具**: 如 H100, H200, HEAD-001
        - **扁管模具**: 如 A43S, A50S, T100
        
        #### 7. 测试类型说明
        - **焓差测试**：换热性能测试
        - **盐雾测试**：耐腐蚀性能测试
        - **压力交变**：压力循环耐久测试
        - **材料测试**：材料性能分析
        - **扫描电镜**：微观结构分析
        - **温度交变**：温度循环测试
        
        #### 8. 设备类型说明
        - **10kW-120kW**：不同功率规格的测试设备
        - **金相**：金相分析设备
        - **压力交变**：压力交变测试设备
        - **盐雾**：盐雾试验设备
        
        #### 9. 密级说明
        - **A级（绿色）**：保密数据
        - **AA级（橙色）**：高级保密数据
        - **S级（红色）**：绝密数据
        
        #### 10. 注意事项
        - 带*号为必填项（包括芯体图号、密级和申请人姓名）
        - 文件上传后会自动重命名并存储到带密级的根目录
        - 芯体图号、申请人和密级会影响文件名和文件夹路径生成
        - 建议定期备份重要数据
        
        #### 11. 常见问题
        **Q: 如何搜索特定密级的数据？**
        A: 在数据查询页面的"密级"筛选框中可以选择需要的密级。
        
        **Q: 如何搜索特定申请人的数据？**
        A: 在数据查询页面的"申请人姓名"输入框中可以输入申请人姓名进行搜索。
        
        **Q: 如何搜索特定模具号的数据？**
        A: 在数据查询页面的"三大主材模具号搜索"部分，可以输入翅片、集流管、扁管的模具号关键词进行搜索。
        
        **Q: 文件存储在哪里？**
        A: 文件存储在带密级的根目录中：`uploaded_files（密级X）/项目名称/年份/月份/芯体图号/测试类型_实验对象_申请人/`
        
        **Q: 如何查看文件夹结构？**
        A: 使用"文件夹浏览"页面，可以按层级结构浏览所有上传的文件。
        </div>
        """, unsafe_allow_html=True)

# ==================== 页脚信息 ====================
st.markdown("---")
col_footer1, col_footer2, col_footer3 = st.columns(3)

with col_footer1:
    st.write("**版本**: 7.0 (密级管理版V2 - 含申请人)")

with col_footer2:
    st.write("**技术支持**: 实验室数据管理团队")

with col_footer3:
    st.write("**数据库**: SQLite")

# 创建必要目录
# 注意：不再创建默认的uploaded_files目录，而是根据密级动态创建

# 检查数据库
if not os.path.exists('lab_data_enhanced.db'):
    st.warning("⚠️ 数据库文件不存在，请先运行 create_database_enhanced.py")
    if st.button("🔄 创建数据库", width='stretch'):
        try:
            import subprocess
            subprocess.run(["python", "create_database_enhanced.py"], check=True)
            st.success("✅ 数据库创建成功，请刷新页面")
            st.rerun()
        except Exception as e:
            st.error(f"❌ 创建失败：{str(e)}")
