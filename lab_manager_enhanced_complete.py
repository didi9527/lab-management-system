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
import io

# 尝试导入可选依赖
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import openpyxl
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False

# ==================== 云端适配配置 ====================
st.set_page_config(
    page_title="实验室数据管理系统 - 密级管理版V2",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 云端环境适配
if 'streamlit_cloud' in sys.argv or os.environ.get('STREAMLIT_CLOUD') == 'true':
    DATA_DIR = '/mount/data'
    os.makedirs(DATA_DIR, exist_ok=True)
    DB_PATH = os.path.join(DATA_DIR, 'lab_data_enhanced.db')
else:
    DB_PATH = 'lab_data_enhanced.db'

# 自定义CSS样式
st.markdown("""
<style>
    .main-header { font-size: 2.5rem; color: #1E88E5; font-weight: bold; margin-bottom: 1rem; }
    .sub-header { font-size: 1.8rem; color: #43A047; font-weight: bold; margin-top: 1.5rem; margin-bottom: 1rem; }
    .info-box { background-color: #E3F2FD; padding: 1rem; border-radius: 10px; border-left: 5px solid #2196F3; margin-bottom: 1rem; }
    .success-box { background-color: #E8F5E9; padding: 1rem; border-radius: 10px; border-left: 5px solid #4CAF50; margin-bottom: 1rem; }
    .warning-box { background-color: #FFF3E0; padding: 1rem; border-radius: 10px; border-left: 5px solid #FF9800; margin-bottom: 1rem; }
    .file-preview { background-color: #F5F5F5; padding: 1rem; border-radius: 5px; font-family: monospace; margin: 0.5rem 0; }
    .folder-preview { background-color: #E8F4FD; padding: 0.8rem; border-radius: 5px; font-family: monospace; color: #0B5E7E; margin: 0.5rem 0; }
    .security-badge-A { background-color: #4CAF50; color: white; padding: 0.2rem 0.5rem; border-radius: 4px; font-weight: bold; display: inline-block; }
    .security-badge-AA { background-color: #FF9800; color: white; padding: 0.2rem 0.5rem; border-radius: 4px; font-weight: bold; display: inline-block; }
    .security-badge-S { background-color: #F44336; color: white; padding: 0.2rem 0.5rem; border-radius: 4px; font-weight: bold; display: inline-block; }
    .material-section { background-color: #FFF8E1; padding: 1rem; border-radius: 8px; border-left: 4px solid #FFB300; margin: 1rem 0; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header">🔬 实验室数据管理系统（密级管理版V2）</div>', unsafe_allow_html=True)
st.markdown("---")

# ==================== 辅助函数定义 ====================
def get_test_type_code(test_type):
    """获取测试类型代码"""
    code_map = {
        "焓差测试": "焓差测试", "盐雾测试": "盐雾测试", "压力交变": "压力交变",
        "材料测试": "材料测试", "扫描电镜": "扫描电镜", "温度交变": "温度交变", "其他测试": "其他测试"
    }
    return code_map.get(test_type, "其他测试")

def get_equipment_code(equipment):
    """获取设备类型代码"""
    code_map = {
        "30kw": "30kw", "50kw": "50kw", "75kw": "75kw", "15kw": "15kw",
        "28kw": "28kw", "10kw": "10kw", "120kw": "120kw", "金相": "金相",
        "压力交变": "压力交变", "盐雾": "盐雾", "其他": "其他"
    }
    return code_map.get(equipment, equipment)

def calculate_file_hash(file_path):
    """计算文件的MD5哈希值"""
    hash_md5 = hashlib.md5()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception:
        return f"error"

def generate_filename(params):
    """根据参数生成标准文件名"""
    project_clean = re.sub(r'[\\/*?:"<>|]', '_', params['test_project_name'].strip())
    core_clean = re.sub(r'[\\/*?:"<>|]', '_', params['core_drawing_number'].strip()) if params.get('core_drawing_number') and params['core_drawing_number'].strip() else "NODWG"
    applicant_clean = re.sub(r'[\\/*?:"<>|]', '_', params.get('applicant_name', '').strip()) if params.get('applicant_name') and params['applicant_name'].strip() else "未知"
    
    date_str = params['experiment_date'].strftime("%Y%m%d")
    test_type_code = get_test_type_code(params['test_type'])
    equipment_code = get_equipment_code(params['equipment'])
    security_level = params.get('security_level', 'A').strip()
    
    filename_parts = [project_clean, date_str, params['test_object'], core_clean, test_type_code, equipment_code, applicant_clean, security_level]
    filename = "_".join(filename_parts) + params['file_extension']
    return filename

def generate_folder_structure(params):
    """根据参数生成层级化文件夹路径"""
    project_clean = re.sub(r'[\\/*?:"<>|]', '_', params['test_project_name'].strip())
    core_clean = re.sub(r'[\\/*?:"<>|]', '_', params['core_drawing_number'].strip()) if params.get('core_drawing_number') and params['core_drawing_number'].strip() else "NODWG"
    applicant_clean = re.sub(r'[\\/*?:"<>|]', '_', params.get('applicant_name', '').strip()) if params.get('applicant_name') and params['applicant_name'].strip() else "未知"
    
    year = params['experiment_date'].strftime("%Y")
    month = params['experiment_date'].strftime("%m")
    test_type_clean = re.sub(r'[\\/*?:"<>|]', '_', params['test_type'].strip())
    test_object_clean = re.sub(r'[\\/*?:"<>|]', '_', params['test_object'].strip())
    security_level = params.get('security_level', 'A').strip()
    
    base_dir = os.getcwd()
    folder_parts = [
        f"uploaded_files（密级{security_level}）", project_clean, year, month,
        core_clean, f"{test_type_clean}_{test_object_clean}_{applicant_clean}"
    ]
    folder_path = os.path.join(base_dir, *folder_parts)
    return folder_path

def save_uploaded_file(uploaded_file, params, new_filename):
    """保存上传的文件到层级化文件夹结构"""
    try:
        folder_path = generate_folder_structure(params)
        os.makedirs(folder_path, exist_ok=True)
        target_path = os.path.join(folder_path, new_filename)
        
        with open(target_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        file_size = os.path.getsize(target_path)
        file_hash = calculate_file_hash(target_path)
        relative_path = os.path.relpath(target_path, os.getcwd())
        server_path = target_path
        
        return {"success": True, "file_path": target_path, "folder_path": folder_path,
                "relative_path": relative_path, "file_size": file_size, "file_hash": file_hash, "server_path": server_path}
    except Exception as e:
        return {"success": False, "error": str(e)}

def validate_filename_inputs(project, date, obj, test_type, equipment, security_level, core, applicant):
    """验证文件名输入参数"""
    if not all([project, obj, test_type, equipment, security_level, core, applicant]):
        return False, "请填写所有必填项（带*号）"
    if date > datetime.now().date():
        return False, "实验日期不能超过当前日期"
    return True, "验证通过"

def show_file_preview(file_path, filename, file_ext):
    """显示文件预览"""
    st.markdown(f"### 📄 文件预览: {filename}")
    
    try:
        # Excel文件
        if file_ext in ['.xlsx', '.xls']:
            if OPENPYXL_AVAILABLE:
                df_excel = pd.read_excel(file_path, engine='openpyxl')
                st.dataframe(df_excel, use_container_width=True)
                if hasattr(pd.ExcelFile(file_path), 'sheet_names'):
                    with st.expander("📑 工作表信息"):
                        excel_file = pd.ExcelFile(file_path)
                        for sheet in excel_file.sheet_names:
                            st.write(f"- {sheet}")
            else:
                st.warning("需要安装 openpyxl 库来预览Excel文件")
        
        # CSV文件
        elif file_ext == '.csv':
            try:
                df_csv = pd.read_csv(file_path, encoding='utf-8')
            except:
                try:
                    df_csv = pd.read_csv(file_path, encoding='gbk')
                except:
                    df_csv = pd.read_csv(file_path, encoding='latin-1')
            st.dataframe(df_csv, use_container_width=True)
        
        # 图片文件
        elif file_ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp']:
            if PIL_AVAILABLE:
                image = Image.open(file_path)
                st.image(image, caption=filename, use_container_width=True)
            else:
                st.warning("需要安装 Pillow 库来预览图片")
        
        # 文本文件
        elif file_ext in ['.txt', '.dat', '.log']:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except:
                try:
                    with open(file_path, 'r', encoding='gbk') as f:
                        content = f.read()
                except:
                    with open(file_path, 'r', encoding='latin-1') as f:
                        content = f.read()
            st.text_area("文件内容", content, height=400)
        
        # PDF文件
        elif file_ext == '.pdf':
            st.info("PDF文件无法直接预览，请点击下方按钮下载查看")
        
        else:
            st.info(f"暂不支持预览 {file_ext} 格式的文件")
        
        # 下载按钮
        with open(file_path, 'rb') as f:
            st.download_button(
                label="⬇️ 下载文件",
                data=f,
                file_name=filename
            )
    
    except Exception as e:
        st.error(f"文件预览失败：{str(e)}")
        # 提供下载选项
        with open(file_path, 'rb') as f:
            st.download_button(
                label="⬇️ 下载文件",
                data=f,
                file_name=filename
            )

def verify_all_files():
    """验证所有文件是否存在"""
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, renamed_filename, file_path, server_path FROM experiments WHERE renamed_filename IS NOT NULL")
        records = cursor.fetchall()
        
        missing_files = []
        found_count = 0
        fixed_count = 0
        
        for record in records:
            file_id, filename, file_path, server_path = record
            file_exists = False
            
            if file_path and os.path.exists(file_path):
                file_exists = True
                found_count += 1
            elif server_path and os.path.exists(server_path):
                file_exists = True
                found_count += 1
                # 更新正确的路径
                cursor.execute("UPDATE experiments SET file_path = ? WHERE id = ?", (server_path, file_id))
                fixed_count += 1
            else:
                # 搜索文件
                for root, dirs, files in os.walk('.'):
                    if filename in files:
                        found_path = os.path.join(root, filename)
                        file_exists = True
                        found_count += 1
                        cursor.execute("UPDATE experiments SET file_path = ? WHERE id = ?", (found_path, file_id))
                        fixed_count += 1
                        break
            
            if not file_exists:
                missing_files.append(filename)
        
        conn.commit()
        
        if missing_files:
            st.warning(f"⚠️ 发现 {len(missing_files)} 个缺失文件")
            with st.expander("查看缺失文件列表"):
                for f in missing_files:
                    st.write(f"- {f}")
        else:
            st.success(f"✅ 所有文件都存在（共 {found_count} 个文件）")
        
        if fixed_count > 0:
            st.info(f"🔧 已修复 {fixed_count} 个文件路径")
    
    except Exception as e:
        st.error(f"验证失败：{str(e)}")

# ==================== 数据库连接和迁移 ====================
@st.cache_resource
def get_connection():
    """获取数据库连接并确保所有字段存在"""
    db_dir = os.path.dirname(DB_PATH)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='experiments'")
    if not cursor.fetchone():
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
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_applicant_name ON experiments (applicant_name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_project_name ON experiments (test_project_name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_date ON experiments (experiment_date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_version_code ON experiments (version_code)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_test_type ON experiments (test_type)')
        conn.commit()
        return conn
    
    cursor.execute("PRAGMA table_info(experiments)")
    existing_columns = [col[1] for col in cursor.fetchall()]
    
    columns_to_add = {
        'applicant_name': 'TEXT', 'flat_tube_mold': 'TEXT',
        'header_mold': 'TEXT', 'fin_tool': 'TEXT', 'refrigerant_type': 'TEXT'
    }
    
    for col_name, col_type in columns_to_add.items():
        if col_name not in existing_columns:
            try:
                cursor.execute(f"ALTER TABLE experiments ADD COLUMN {col_name} {col_type}")
            except Exception:
                pass
    
    conn.commit()
    return conn

conn = get_connection()

# ==================== 侧边栏导航 ====================
st.sidebar.markdown('<div class="main-header">导航菜单</div>', unsafe_allow_html=True)
menu = st.sidebar.radio("选择功能", ["🏠 系统首页", "📁 文件管理", "🔍 数据查询", "📋 数据浏览", "📂 文件夹浏览", "⚙️ 系统设置"])

st.sidebar.markdown("---")
st.sidebar.markdown("### 📊 系统信息")
st.sidebar.info(f"**版本**: 7.0\n\n**功能**: 密级管理版V2\n\n**数据库**: SQLite\n\n**环境**: {'云端' if os.environ.get('STREAMLIT_CLOUD') else '本地'}")

# ==================== 全局变量定义 ====================
equipment_options = ["30kw", "50kw", "75kw", "15kw", "28kw", "10kw", "120kw", "金相", "压力交变", "盐雾", "其他"]
test_type_options = ["焓差测试", "盐雾测试", "压力交变", "材料测试", "扫描电镜", "温度交变", "其他测试"]
security_options = ["A", "AA", "S"]
security_descriptions = {"A": "保密数据", "AA": "高级保密数据", "S": "绝密数据"}
security_colors = {'A': 'security-badge-A', 'AA': 'security-badge-AA', 'S': 'security-badge-S'}
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
    
    st.markdown('<div class="sub-header">📈 系统统计</div>', unsafe_allow_html=True)
    
    try:
        col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
        df_total = pd.read_sql_query("SELECT COUNT(*) as count FROM experiments", conn)
        with col_stat1:
            st.metric("📊 总记录数", df_total['count'][0])
        
        df_files = pd.read_sql_query("SELECT COUNT(*) as count FROM experiments WHERE renamed_filename IS NOT NULL", conn)
        with col_stat2:
            st.metric("📁 有文件记录", df_files['count'][0])
        
        df_projects = pd.read_sql_query("SELECT COUNT(DISTINCT test_project_name) as count FROM experiments", conn)
        with col_stat3:
            st.metric("🏢 项目数量", df_projects['count'][0])
        
        with col_stat4:
            if os.path.exists(DB_PATH):
                db_size = os.path.getsize(DB_PATH) / 1024
                st.metric("💾 数据库大小", f"{db_size:.1f} KB")
    except Exception:
        st.info("暂无数据，请先上传文件")
    
    with st.expander("📖 使用指南", expanded=False):
        st.markdown("""
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
    
    tab1, tab2, tab3 = st.tabs(["📤 单文件上传", "📦 批量文件处理", "📋 文件记录管理"])
    
    # 单文件上传
    with tab1:
        st.markdown("### 📤 单文件上传与管理")
        
        col_select1, col_select2 = st.columns(2)
        
        with col_select1:
            try:
                df_records = pd.read_sql_query(
                    "SELECT data_id, test_project_name, experiment_date, test_object, core_drawing_number, version_code as security_level, applicant_name FROM experiments ORDER BY experiment_date DESC",
                    conn
                )
                if not df_records.empty:
                    record_options = [f"{row['data_id']} | {row['test_project_name']} | {row['applicant_name'] or '未知'} | 密级{row['security_level']}" for _, row in df_records.iterrows()]
                    selected_option = st.selectbox("选择现有记录", record_options)
                    if selected_option:
                        selected_data_id = selected_option.split(" | ")[0]
                        selected_record = df_records[df_records['data_id'] == selected_data_id].iloc[0]
                        with st.expander("📋 查看选中记录详情", expanded=False):
                            st.write(f"**数据ID**：{selected_record['data_id']}")
                            st.write(f"**测试项目**：{selected_record['test_project_name']}")
                            st.write(f"**申请人**：{selected_record['applicant_name'] or '未填写'}")
                    create_new = st.checkbox("创建新记录", value=False)
                else:
                    create_new = True
                    st.info("暂无现有记录，请创建新记录")
            except Exception:
                create_new = True
        
        with col_select2:
            if create_new:
                with st.form("quick_record_form"):
                    quick_project = st.text_input("测试项目名称*", key="quick_project")
                    quick_date = st.date_input("实验日期*", value=datetime.now(), key="quick_date")
                    quick_object = st.selectbox("实验对象*", test_object_options, key="quick_object")
                    quick_type = st.selectbox("测试类型*", test_type_options, key="quick_type")
                    quick_equipment = st.selectbox("设备*", equipment_options, key="quick_equipment")
                    quick_security = st.selectbox("密级*", security_options, key="quick_security")
                    quick_core = st.text_input("芯体图号*", placeholder="如：DRG-EVAP-001", key="quick_core")
                    quick_applicant = st.text_input("申请人姓名*", placeholder="如：张三", key="quick_applicant")
                    
                    if st.form_submit_button("⚡ 快速创建记录"):
                        if all([quick_project, quick_object, quick_type, quick_equipment, quick_security, quick_core, quick_applicant]):
                            params = {'test_project_name': quick_project, 'experiment_date': quick_date, 'test_object': quick_object,
                                     'core_drawing_number': quick_core, 'test_type': quick_type, 'equipment': quick_equipment,
                                     'security_level': quick_security, 'applicant_name': quick_applicant, 'file_extension': ".xlsx"}
                            filename = generate_filename(params)
                            data_id = filename.replace(".xlsx", "")
                            try:
                                cursor = conn.cursor()
                                cursor.execute('''INSERT INTO experiments (data_id, test_project_name, experiment_date, test_object,
                                                test_type, equipment, version_code, file_extension, core_drawing_number, applicant_name)
                                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                                               (data_id, quick_project, quick_date.strftime('%Y-%m-%d'), quick_object,
                                                quick_type, quick_equipment, quick_security, ".xlsx", quick_core, quick_applicant))
                                conn.commit()
                                st.success(f"✅ 记录创建成功！数据ID：{data_id}")
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ 创建失败：{str(e)}")
                        else:
                            st.error("❌ 请填写所有必填项")
        
        uploaded_file = st.file_uploader("选择要上传的文件", type=['xlsx', 'csv', 'pdf', 'jpg', 'jpeg', 'png', 'docx', 'tif', 'dat', 'txt'])
        
        if uploaded_file:
            col_config1, col_config2 = st.columns(2)
            with col_config1:
                config_project = st.text_input("测试项目名称*", key="config_project")
                config_date = st.date_input("实验日期*", value=datetime.now(), key="config_date")
                config_object = st.selectbox("实验对象*", test_object_options, key="config_object")
                config_core = st.text_input("芯体图号*", key="config_core", placeholder="如：DRG-EVAP-001")
            with col_config2:
                config_type = st.selectbox("测试类型*", test_type_options, key="config_type")
                config_equipment = st.selectbox("设备*", equipment_options, key="config_equipment")
                config_security = st.selectbox("密级*", security_options, key="config_security")
                config_applicant = st.text_input("申请人姓名*", key="config_applicant", placeholder="如：张三")
                config_test_purpose = st.text_input("测试目的", key="config_test_purpose")
                config_ext = st.selectbox("文件类型*", [".xlsx", ".csv", ".pdf", ".jpg", ".png", ".docx", ".tif", ".dat"])
            
            st.markdown('<div class="material-section">', unsafe_allow_html=True)
            col_m1, col_m2, col_m3 = st.columns(3)
            with col_m1:
                fin_mold = st.text_input("翅片模具号", placeholder="如：B150")
            with col_m2:
                header_mold = st.text_input("集流管模具号", placeholder="如：H100")
            with col_m3:
                tube_mold = st.text_input("扁管模具号", placeholder="如：A43S")
            st.markdown('</div>', unsafe_allow_html=True)
            
            if config_project and config_object and config_type and config_equipment and config_security and config_core and config_applicant:
                preview_params = {'test_project_name': config_project, 'experiment_date': config_date, 'test_object': config_object,
                                 'core_drawing_number': config_core, 'test_type': config_type, 'equipment': config_equipment,
                                 'security_level': config_security, 'applicant_name': config_applicant, 'file_extension': config_ext}
                preview_filename = generate_filename(preview_params)
                preview_folder = generate_folder_structure(preview_params)
                st.markdown('<div class="success-box">', unsafe_allow_html=True)
                st.markdown(f"### 📄 文件名预览\n`{preview_filename}`")
                st.markdown(f"### 📂 存储路径预览\n`{preview_folder}`")
                st.markdown('</div>', unsafe_allow_html=True)
            
            if st.button("🚀 上传并重命名", type="primary"):
                is_valid, msg = validate_filename_inputs(config_project, config_date, config_object, config_type,
                                                         config_equipment, config_security, config_core, config_applicant)
                if not is_valid:
                    st.error(msg)
                else:
                    final_params = {'test_project_name': config_project, 'experiment_date': config_date, 'test_object': config_object,
                                   'core_drawing_number': config_core, 'test_type': config_type, 'equipment': config_equipment,
                                   'security_level': config_security, 'applicant_name': config_applicant, 'file_extension': config_ext}
                    final_filename = generate_filename(final_params)
                    final_data_id = final_filename.replace(config_ext, "")
                    result = save_uploaded_file(uploaded_file, final_params, final_filename)
                    
                    if not result["success"]:
                        st.error(f"❌ 文件保存失败：{result.get('error')}")
                    else:
                        materials_info = f"测试目的：{config_test_purpose or ''}"
                        if any([fin_mold, header_mold, tube_mold]):
                            materials_info += "\n\n三大主材模具号："
                            if fin_mold: materials_info += f"\n- 翅片模具：{fin_mold}"
                            if header_mold: materials_info += f"\n- 集流管模具：{header_mold}"
                            if tube_mold: materials_info += f"\n- 扁管模具：{tube_mold}"
                        
                        cursor = conn.cursor()
                        cursor.execute("SELECT COUNT(*) FROM experiments WHERE data_id = ?", (final_data_id,))
                        exists = cursor.fetchone()[0] > 0
                        
                        if exists:
                            cursor.execute('''UPDATE experiments SET original_filename=?, renamed_filename=?, file_path=?,
                                            server_path=?, file_size=?, upload_time=?, file_hash=?, test_project_name=?,
                                            experiment_date=?, test_object=?, core_drawing_number=?, test_type=?,
                                            equipment=?, version_code=?, file_extension=?, notes=?, flat_tube_mold=?,
                                            header_mold=?, fin_tool=?, applicant_name=? WHERE data_id=?''',
                                           (uploaded_file.name, final_filename, result["file_path"], result["server_path"],
                                            result["file_size"], datetime.now().strftime('%Y-%m-%d %H:%M:%S'), result["file_hash"],
                                            config_project, config_date.strftime('%Y-%m-%d'), config_object, config_core,
                                            config_type, config_equipment, config_security, config_ext, materials_info,
                                            tube_mold, header_mold, fin_mold, config_applicant, final_data_id))
                        else:
                            cursor.execute('''INSERT INTO experiments (data_id, test_project_name, experiment_date, test_object,
                                            test_type, equipment, version_code, file_extension, core_drawing_number,
                                            applicant_name, original_filename, renamed_filename, file_path, server_path,
                                            file_size, upload_time, file_hash, notes, flat_tube_mold, header_mold, fin_tool)
                                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                                           (final_data_id, config_project, config_date.strftime('%Y-%m-%d'), config_object,
                                            config_type, config_equipment, config_security, config_ext, config_core,
                                            config_applicant, uploaded_file.name, final_filename, result["file_path"],
                                            result["server_path"], result["file_size"], datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                            result["file_hash"], materials_info, tube_mold, header_mold, fin_mold))
                        
                        conn.commit()
                        st.success("✅ 文件上传成功！")
                        st.balloons()
    
    # 批量文件处理
    with tab2:
        st.markdown("### 📦 批量文件处理")
        st.info("批量上传功能：选择多个文件，使用相同的配置信息批量上传")
        
        uploaded_files = st.file_uploader("选择多个文件", type=['xlsx', 'csv', 'pdf', 'jpg', 'jpeg', 'png', 'docx', 'tif', 'dat'],
                                          accept_multiple_files=True)
        
        if uploaded_files:
            st.success(f"✅ 已选择 {len(uploaded_files)} 个文件")
            
            col_b1, col_b2 = st.columns(2)
            with col_b1:
                batch_project = st.text_input("批量项目名称*", placeholder="如：JCI蒸发器批量测试")
                batch_date = st.date_input("批量实验日期*", value=datetime.now())
                batch_object = st.selectbox("批量实验对象*", test_object_options)
                batch_core = st.text_input("批量芯体图号*", placeholder="如：DRG-EVAP-001")
            with col_b2:
                batch_type = st.selectbox("批量测试类型*", test_type_options)
                batch_equipment = st.selectbox("批量设备*", equipment_options)
                batch_security = st.selectbox("批量密级*", security_options)
                batch_applicant = st.text_input("批量申请人姓名*", placeholder="如：张三")
                start_number = st.number_input("起始编号*", min_value=1, value=1)
            
            if st.button("🚀 执行批量上传", type="primary"):
                if all([batch_project, batch_core, batch_applicant]):
                    success_count = 0
                    progress_bar = st.progress(0)
                    
                    for idx, file in enumerate(uploaded_files):
                        progress = int((idx + 1) / len(uploaded_files) * 100)
                        progress_bar.progress(progress)
                        
                        file_ext = os.path.splitext(file.name)[1].lower() or ".dat"
                        params = {'test_project_name': batch_project, 'experiment_date': batch_date, 'test_object': batch_object,
                                 'core_drawing_number': f"{batch_core}-{idx+start_number:03d}", 'test_type': batch_type,
                                 'equipment': batch_equipment, 'security_level': batch_security, 'applicant_name': batch_applicant,
                                 'file_extension': file_ext}
                        new_name = generate_filename(params)
                        data_id = new_name.replace(file_ext, "")
                        
                        result = save_uploaded_file(file, params, new_name)
                        if result["success"]:
                            cursor = conn.cursor()
                            cursor.execute('''INSERT OR REPLACE INTO experiments (data_id, test_project_name, experiment_date,
                                            test_object, core_drawing_number, test_type, equipment, version_code,
                                            file_extension, applicant_name, original_filename, renamed_filename,
                                            file_path, server_path, file_size, upload_time, file_hash)
                                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                                           (data_id, batch_project, batch_date.strftime('%Y-%m-%d'), batch_object,
                                            f"{batch_core}-{idx+start_number:03d}", batch_type, batch_equipment,
                                            batch_security, file_ext, batch_applicant, file.name, new_name,
                                            result["file_path"], result["server_path"], result["file_size"],
                                            datetime.now().strftime('%Y-%m-%d %H:%M:%S'), result["file_hash"]))
                            success_count += 1
                    
                    conn.commit()
                    st.success(f"✅ 批量上传完成！成功 {success_count}/{len(uploaded_files)} 个文件")
                else:
                    st.error("请填写所有必填项")
    
    # 文件记录管理
    with tab3:
        st.markdown("### 📋 文件记录管理")
        
        col_verify1, col_verify2 = st.columns(2)
        with col_verify1:
            if st.button("🔍 验证所有文件路径"):
                verify_all_files()
        
        try:
            df_files = pd.read_sql_query("SELECT * FROM experiments WHERE renamed_filename IS NOT NULL ORDER BY upload_time DESC", conn)
            st.markdown(f"### 📊 文件记录列表（共 **{len(df_files)}** 条）")
            
            if not df_files.empty:
                for _, row in df_files.iterrows():
                    with st.expander(f"📄 {row['renamed_filename']}", expanded=False):
                        col1, col2, col3 = st.columns(3)
                        
                        # 检查文件是否存在
                        file_exists = False
                        file_path = None
                        
                        if row['file_path'] and os.path.exists(row['file_path']):
                            file_exists = True
                            file_path = row['file_path']
                        elif row['server_path'] and os.path.exists(row['server_path']):
                            file_exists = True
                            file_path = row['server_path']
                        
                        with col1:
                            st.write(f"**项目**: {row['test_project_name']}")
                            st.write(f"**申请人**: {row['applicant_name'] or '未填写'}")
                            st.write(f"**芯体图号**: {row['core_drawing_number'] or '未填写'}")
                            st.write(f"**文件状态**: {'✅ 存在' if file_exists else '❌ 缺失'}")
                        
                        with col2:
                            st.write(f"**上传时间**: {row['upload_time']}")
                            if row['file_size']:
                                st.write(f"**文件大小**: {row['file_size']/1024:.1f} KB")
                            st.write(f"**文件类型**: {row['file_extension']}")
                        
                        with col3:
                            if file_exists:
                                if st.button(f"👁️ 查看文件", key=f"view_{row['id']}"):
                                    show_file_preview(file_path, row['renamed_filename'], row['file_extension'])
                            
                            if st.button(f"🗑️ 删除记录", key=f"del_{row['id']}"):
                                try:
                                    cursor = conn.cursor()
                                    cursor.execute("DELETE FROM experiments WHERE id = ?", (row['id'],))
                                    conn.commit()
                                    st.success("✅ 记录已删除")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"删除失败：{str(e)}")
            else:
                st.info("暂无文件记录")
        except Exception as e:
            st.warning(f"加载记录失败：{str(e)}")

# ==================== 3. 数据查询页面 ====================
elif menu == "🔍 数据查询":
    st.markdown('<div class="sub-header">🔍 实验数据查询</div>', unsafe_allow_html=True)
    
    with st.expander("🔎 查询条件设置", expanded=True):
        col_f1, col_f2, col_f3 = st.columns(3)
        
        with col_f1:
            query_project = st.text_input("项目名称", placeholder="输入项目名称关键字")
            query_test_object = st.multiselect("实验对象", test_object_options)
            date_range = st.date_input("实验日期范围", [datetime(2024, 1, 1), datetime.now()])
            query_applicant = st.text_input("申请人姓名", placeholder="输入申请人姓名")
        
        with col_f2:
            query_test_type = st.selectbox("测试类型", [""] + test_type_options)
            query_equipment = st.multiselect("设备类型", equipment_options)
            query_security = st.multiselect("密级", security_options)
        
        with col_f3:
            query_filename = st.text_input("文件名关键字", placeholder="输入文件名关键字")
            query_core = st.text_input("芯体图号关键字", placeholder="输入芯体图号关键字")
            st.markdown("**🔧 模具号搜索**")
            query_fin = st.text_input("翅片模具号", placeholder="如：B150")
            query_header = st.text_input("集流管模具号", placeholder="如：H100")
            query_tube = st.text_input("扁管模具号", placeholder="如：A43S")
    
    col_s1, col_s2 = st.columns([2, 1])
    with col_s1:
        search_clicked = st.button("🔍 开始查询", type="primary")
    with col_s2:
        if st.button("🔄 重置条件"):
            st.rerun()
    
    if search_clicked:
        sql = "SELECT * FROM experiments WHERE 1=1"
        params = []
        
        if query_project:
            sql += " AND test_project_name LIKE ?"
            params.append(f"%{query_project}%")
        if query_test_object:
            sql += f" AND test_object IN ({','.join(['?']*len(query_test_object))})"
            params.extend(query_test_object)
        if query_applicant:
            sql += " AND applicant_name LIKE ?"
            params.append(f"%{query_applicant}%")
        if query_test_type:
            sql += " AND test_type = ?"
            params.append(query_test_type)
        if query_equipment:
            sql += f" AND equipment IN ({','.join(['?']*len(query_equipment))})"
            params.extend(query_equipment)
        if query_security:
            sql += f" AND version_code IN ({','.join(['?']*len(query_security))})"
            params.extend(query_security)
        if len(date_range) == 2:
            sql += " AND experiment_date BETWEEN ? AND ?"
            params.extend([date_range[0].strftime('%Y-%m-%d'), date_range[1].strftime('%Y-%m-%d')])
        if query_filename:
            sql += " AND (renamed_filename LIKE ? OR original_filename LIKE ?)"
            params.extend([f"%{query_filename}%", f"%{query_filename}%"])
        if query_core:
            sql += " AND core_drawing_number LIKE ?"
            params.append(f"%{query_core}%")
        
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
        
        try:
            df_results = pd.read_sql_query(sql, conn, params=params)
            st.markdown(f'<div class="sub-header">📊 查询结果（共 {len(df_results)} 条）</div>', unsafe_allow_html=True)
            
            if not df_results.empty:
                # 显示结果表格
                display_fields = st.multiselect("选择显示字段",
                    ['data_id', 'test_project_name', 'experiment_date', 'test_object', 'test_type',
                     'equipment', 'version_code', 'core_drawing_number', 'applicant_name', 'renamed_filename'],
                    default=['data_id', 'test_project_name', 'experiment_date', 'test_object', 'test_type',
                            'core_drawing_number', 'applicant_name', 'version_code', 'renamed_filename'])
                
                if display_fields:
                    st.dataframe(df_results[display_fields], use_container_width=True, hide_index=True)
                
                # 文件查看区域
                st.markdown('<div class="sub-header">📄 文件预览</div>', unsafe_allow_html=True)
                
                # 选择要查看的文件
                file_options = []
                for _, row in df_results.iterrows():
                    if row['renamed_filename'] and pd.notnull(row['renamed_filename']):
                        file_options.append({
                            'display': f"{row['renamed_filename']} - {row['test_project_name']} - {row['applicant_name']}",
                            'id': row['id'],
                            'filename': row['renamed_filename'],
                            'file_path': row['file_path'],
                            'server_path': row['server_path'],
                            'file_extension': row['file_extension']
                        })
                
                if file_options:
                    selected_file = st.selectbox(
                        "选择要查看的文件",
                        options=file_options,
                        format_func=lambda x: x['display']
                    )
                    
                    if selected_file:
                        # 查找文件实际路径
                        file_path = None
                        if selected_file['file_path'] and os.path.exists(selected_file['file_path']):
                            file_path = selected_file['file_path']
                        elif selected_file['server_path'] and os.path.exists(selected_file['server_path']):
                            file_path = selected_file['server_path']
                        else:
                            # 搜索文件
                            for root, dirs, files in os.walk('.'):
                                if selected_file['filename'] in files:
                                    file_path = os.path.join(root, selected_file['filename'])
                                    break
                        
                        if file_path and os.path.exists(file_path):
                            show_file_preview(file_path, selected_file['filename'], selected_file['file_extension'])
                        else:
                            st.error(f"❌ 文件不存在: {selected_file['filename']}")
                            st.info("请检查文件是否已被移动或删除")
                
                # 导出功能
                st.markdown("### 📥 数据导出")
                csv_data = df_results.to_csv(index=False)
                st.download_button(
                    "💾 导出查询结果", 
                    csv_data, 
                    f"查询结果_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv", 
                    "text/csv"
                )
            else:
                st.info("🔍 未找到匹配的数据记录")
        except Exception as e:
            st.error(f"查询失败：{str(e)}")

# ==================== 4. 数据浏览页面 ====================
elif menu == "📋 数据浏览":
    st.markdown('<div class="sub-header">📋 所有实验数据</div>', unsafe_allow_html=True)
    
    filter_option = st.selectbox("筛选方式", ["全部数据", "按项目名称筛选", "按实验对象筛选", "按设备类型筛选", "按芯体图号筛选", "按测试类型筛选", "按密级筛选", "按申请人筛选"])
    
    sql = "SELECT data_id, test_project_name, experiment_date, test_object, test_type, equipment, version_code, core_drawing_number, applicant_name, renamed_filename, file_path, server_path, file_extension FROM experiments"
    
    if filter_option == "按项目名称筛选":
        projects = pd.read_sql_query("SELECT DISTINCT test_project_name FROM experiments ORDER BY test_project_name", conn)
        if not projects.empty:
            selected_project = st.selectbox("选择项目名称", projects['test_project_name'].tolist())
            sql += f" WHERE test_project_name = '{selected_project}'"
    elif filter_option == "按实验对象筛选":
        selected_object = st.selectbox("选择实验对象", test_object_options)
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
    
    try:
        df_all = pd.read_sql_query(sql, conn)
        st.markdown(f"### 📊 数据概览（共 **{len(df_all)}** 条记录）")
        
        if not df_all.empty:
            st.dataframe(df_all, use_container_width=True, hide_index=True)
            
            # 文件预览区域
            st.markdown('<div class="sub-header">📄 文件预览</div>', unsafe_allow_html=True)
            
            file_options = []
            for _, row in df_all.iterrows():
                if row['renamed_filename'] and pd.notnull(row['renamed_filename']):
                    file_options.append({
                        'display': f"{row['renamed_filename']} - {row['test_project_name']} - {row['applicant_name']}",
                        'filename': row['renamed_filename'],
                        'file_path': row['file_path'],
                        'server_path': row['server_path'],
                        'file_extension': row['file_extension']
                    })
            
            if file_options:
                selected_file = st.selectbox(
                    "选择要查看的文件",
                    options=file_options,
                    format_func=lambda x: x['display']
                )
                
                if selected_file:
                    file_path = None
                    if selected_file['file_path'] and os.path.exists(selected_file['file_path']):
                        file_path = selected_file['file_path']
                    elif selected_file['server_path'] and os.path.exists(selected_file['server_path']):
                        file_path = selected_file['server_path']
                    
                    if file_path:
                        show_file_preview(file_path, selected_file['filename'], selected_file['file_extension'])
                    else:
                        st.warning(f"文件不存在: {selected_file['filename']}")
            
            # 导出功能
            csv_data = df_all.to_csv(index=False)
            st.download_button("💾 导出数据", csv_data, f"实验室数据_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv")
        else:
            st.info("📭 暂无数据记录")
    except Exception as e:
        st.error(f"加载数据失败：{str(e)}")

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
    
    upload_dirs = [d for d in os.listdir('.') if d.startswith('uploaded_files（密级') and os.path.isdir(d)]
    
    if upload_dirs:
        selected_root = st.selectbox("选择密级根目录", upload_dirs)
        if selected_root:
            projects = [d for d in os.listdir(selected_root) if os.path.isdir(os.path.join(selected_root, d))]
            if projects:
                selected_project = st.selectbox("选择项目", projects)
                if selected_project:
                    project_path = os.path.join(selected_root, selected_project)
                    years = [d for d in os.listdir(project_path) if os.path.isdir(os.path.join(project_path, d))]
                    if years:
                        selected_year = st.selectbox("选择年份", sorted(years, reverse=True))
                        if selected_year:
                            year_path = os.path.join(project_path, selected_year)
                            months = [d for d in os.listdir(year_path) if os.path.isdir(os.path.join(year_path, d))]
                            if months:
                                selected_month = st.selectbox("选择月份", sorted(months, reverse=True))
                                if selected_month:
                                    month_path = os.path.join(year_path, selected_month)
                                    cores = [d for d in os.listdir(month_path) if os.path.isdir(os.path.join(month_path, d))]
                                    if cores:
                                        selected_core = st.selectbox("选择芯体图号", cores)
                                        if selected_core:
                                            core_path = os.path.join(month_path, selected_core)
                                            test_folders = [d for d in os.listdir(core_path) if os.path.isdir(os.path.join(core_path, d))]
                                            if test_folders:
                                                selected_folder = st.selectbox("选择测试文件夹", test_folders)
                                                if selected_folder:
                                                    folder_path = os.path.join(core_path, selected_folder)
                                                    files = [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))]
                                                    if files:
                                                        st.markdown(f"### 📄 文件列表（共 {len(files)} 个）")
                                                        for file in files:
                                                            with st.expander(f"📄 {file}", expanded=False):
                                                                file_full_path = os.path.join(folder_path, file)
                                                                file_ext = os.path.splitext(file)[1].lower()
                                                                if st.button(f"👁️ 查看文件", key=f"view_{file}"):
                                                                    show_file_preview(file_full_path, file, file_ext)
                                                    else:
                                                        st.info("该文件夹中没有文件")
    else:
        st.info("暂无上传的文件，请先上传文件")

# ==================== 6. 系统设置页面 ====================
elif menu == "⚙️ 系统设置":
    st.markdown('<div class="sub-header">⚙️ 系统设置</div>', unsafe_allow_html=True)
    
    tab_set1, tab_set2, tab_set3 = st.tabs(["🔧 系统配置", "💾 数据管理", "📖 使用帮助"])
    
    with tab_set1:
        st.markdown("### 🔧 系统配置")
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            st.markdown("#### 文件设置")
            max_file_size = st.number_input("最大文件大小(MB)", min_value=1, max_value=500, value=200)
            allowed_extensions = st.multiselect("允许的文件类型", [".xlsx", ".csv", ".pdf", ".jpg", ".png", ".docx", ".tif", ".dat", ".txt"],
                                               default=[".xlsx", ".csv", ".pdf", ".jpg", ".png"])
        with col_s2:
            st.markdown("#### 数据库信息")
            if os.path.exists(DB_PATH):
                db_size = os.path.getsize(DB_PATH) / 1024
                st.write(f"**数据库文件**: {os.path.basename(DB_PATH)}")
                st.write(f"**文件大小**: {db_size:.1f} KB")
                try:
                    df_stats = pd.read_sql_query("SELECT COUNT(*) as total FROM experiments", conn)
                    st.write(f"**记录总数**: {df_stats['total'][0]} 条")
                except:
                    st.write("**记录总数**: 0 条")
    
    with tab_set2:
        st.markdown("### 💾 数据管理")
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            if st.button("💾 备份数据库"):
                try:
                    backup_file = f"lab_data_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
                    shutil.copy2(DB_PATH, backup_file)
                    st.success(f"✅ 数据库已备份到: {backup_file}")
                except Exception as e:
                    st.error(f"❌ 备份失败: {str(e)}")
            
            if st.button("🔍 验证所有文件"):
                verify_all_files()
        
        with col_d2:
            days_to_keep = st.number_input("保留最近多少天的数据", min_value=1, max_value=365, value=90)
            if st.button("🧹 清理旧数据"):
                try:
                    cutoff_date = (datetime.now() - timedelta(days=days_to_keep)).strftime('%Y-%m-%d')
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM experiments WHERE experiment_date < ? AND renamed_filename IS NULL", (cutoff_date,))
                    deleted_count = cursor.rowcount
                    conn.commit()
                    st.success(f"✅ 已清理 {deleted_count} 条旧记录")
                except Exception as e:
                    st.error(f"❌ 清理失败: {str(e)}")
    
    with tab_set3:
        st.markdown("### 📖 使用帮助")
        st.markdown("""
        #### 文件命名规则
        文件名格式：`项目名称_日期_对象_芯体图号_测试类型_设备_申请人_密级.扩展名`
        
        #### 文件夹结构规则
        文件夹结构：`uploaded_files（密级X）/项目名称/年份/月份/芯体图号/测试类型_实验对象_申请人/`
        
        #### 密级说明
        - **A级（绿色）**：保密数据
        - **AA级（橙色）**：高级保密数据
        - **S级（红色）**：绝密数据
        
        #### 测试类型说明
        - **焓差测试**：换热性能测试
        - **盐雾测试**：耐腐蚀性能测试
        - **压力交变**：压力循环耐久测试
        - **材料测试**：材料性能分析
        - **扫描电镜**：微观结构分析
        - **温度交变**：温度循环测试
        
        #### 设备类型说明
        - **10kW-120kW**：不同功率规格的测试设备
        - **金相**：金相分析设备
        - **压力交变**：压力交变测试设备
        - **盐雾**：盐雾试验设备
        
        #### 支持的文件预览格式
        - Excel文件 (.xlsx, .xls) - 表格预览
        - CSV文件 - 表格预览
        - 图片文件 (.jpg, .png, .gif, .bmp) - 图片预览
        - 文本文件 (.txt, .dat, .log) - 文本预览
        - PDF文件 - 下载查看
        """)

# ==================== 页脚 ====================
st.markdown("---")
col_f1, col_f2, col_f3 = st.columns(3)
with col_f1:
    st.write("**版本**: 7.0 (密级管理版V2 - 含申请人)")
with col_f2:
    st.write("**技术支持**: 实验室数据管理团队")
with col_f3:
    st.write(f"**环境**: {'云端' if os.environ.get('STREAMLIT_CLOUD') else '本地'}")
