# app.py - Streamlit Cloud 完整修复版
import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
import os
import re
import hashlib
import time

# ==================== 云端适配配置 ====================
DB_PATH = '/tmp/lab_data.db'
UPLOAD_DIR = '/tmp/uploads'

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(os.path.join(UPLOAD_DIR, '密级A'), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_DIR, '密级AA'), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_DIR, '密级S'), exist_ok=True)

# ==================== 辅助函数 ====================
def get_test_type_code(test_type):
    """获取测试类型代码"""
    code_map = {
        "性能测试": "性能测试",
        "效率测试": "效率测试",
        "耐久测试": "耐久测试",
        "安全测试": "安全测试",
        "可靠性测试": "可靠性测试",
        "焓差测试": "焓差测试",
        "盐雾测试": "盐雾测试",
        "压力交变": "压力交变",
        "其他测试": "其他测试"
    }
    return code_map.get(test_type, "其他测试")

def get_equipment_code(equipment):
    """获取设备类型代码"""
    code_map = {
        "30kw": "30kw",
        "金相": "金相",
        "压力交变": "压力交变",
        "焓差": "焓差",
        "盐雾": "盐雾",
        "其他": "其他"
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
    except Exception as e:
        return f"error_{e}"

def generate_filename(params):
    """根据参数生成标准文件名"""
    project_clean = re.sub(r'[\\/*?:"<>|]', '_', params['test_project_name'].strip())
    core_clean = re.sub(r'[\\/*?:"<>|]', '_', params['core_drawing_number'].strip()) if params.get('core_drawing_number') and params['core_drawing_number'].strip() else "NODWG"
    applicant_clean = re.sub(r'[\\/*?:"<>|]', '_', params['applicant_name'].strip()) if params.get('applicant_name') and params['applicant_name'].strip() else "未知申请人"
    
    date_str = params['experiment_date'].strftime("%Y%m%d")
    test_type_code = get_test_type_code(params['test_type'])
    equipment_code = get_equipment_code(params['equipment'])
    security_level = params.get('security_level', 'A').strip()
    
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
    
    filename = "_".join(filename_parts) + params['file_extension']
    return filename

def save_uploaded_file(uploaded_file, params, new_filename):
    """保存上传的文件"""
    try:
        security_level = params.get('security_level', 'A')
        upload_subdir = os.path.join(UPLOAD_DIR, f'密级{security_level}')
        os.makedirs(upload_subdir, exist_ok=True)
        
        target_path = os.path.join(upload_subdir, new_filename)
        
        with open(target_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        file_size = os.path.getsize(target_path)
        file_hash = calculate_file_hash(target_path)
        
        return {
            "success": True,
            "file_path": target_path,
            "file_size": file_size,
            "file_hash": file_hash,
            "server_path": f"/tmp/uploads/密级{security_level}/{new_filename}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

def validate_inputs(project, obj, test_type, equipment, applicant, security, core):
    """验证输入参数"""
    if not all([project, obj, test_type, equipment, applicant, security, core]):
        return False, "请填写所有必填项（带*号）"
    return True, "验证通过"

def init_database():
    """初始化数据库"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS experiments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data_id TEXT UNIQUE NOT NULL,
            test_project_name TEXT NOT NULL,
            experiment_date DATE NOT NULL,
            test_object TEXT NOT NULL,
            core_drawing_number TEXT,
            test_type TEXT NOT NULL,
            equipment TEXT,
            applicant_name TEXT,
            security_level TEXT,
            file_extension TEXT,
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
    
    c.execute('CREATE INDEX IF NOT EXISTS idx_applicant ON experiments (applicant_name)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_security ON experiments (security_level)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_project ON experiments (test_project_name)')
    
    conn.commit()
    conn.close()

init_database()

# ==================== 页面配置 ====================
st.set_page_config(
    page_title="实验室数据管理系统",
    page_icon="🔬",
    layout="wide"
)

st.title("🔬 实验室数据管理系统")
st.markdown("---")

# ==================== 数据库连接 ====================
@st.cache_resource
def get_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

conn = get_connection()

# ==================== 侧边栏 ====================
st.sidebar.title("导航菜单")
menu = st.sidebar.radio(
    "选择功能",
    ["🏠 系统首页", "📝 数据录入", "📁 文件上传", "🔍 数据查询", "📋 数据浏览"]
)

st.sidebar.markdown("---")
st.sidebar.info("**版本**: 9.0\n\n**部署**: Streamlit Cloud")

# ==================== 全局变量 ====================
equipment_options = ["30kw", "金相", "压力交变", "焓差", "盐雾", "其他"]
test_type_options = ["性能测试", "效率测试", "耐久测试", "安全测试", "可靠性测试", 
                     "焓差测试", "盐雾测试", "压力交变", "其他测试"]
security_options = ["A", "AA", "S"]

security_colors = {
    'A': 'security-badge-A',
    'AA': 'security-badge-AA',
    'S': 'security-badge-S'
}

# ==================== 自定义CSS ====================
st.markdown("""
<style>
.security-badge-A {
    background-color: #4CAF50;
    color: white;
    padding: 2px 8px;
    border-radius: 4px;
    font-weight: bold;
    display: inline-block;
}
.security-badge-AA {
    background-color: #FF9800;
    color: white;
    padding: 2px 8px;
    border-radius: 4px;
    font-weight: bold;
    display: inline-block;
}
.security-badge-S {
    background-color: #F44336;
    color: white;
    padding: 2px 8px;
    border-radius: 4px;
    font-weight: bold;
    display: inline-block;
}
.info-box {
    background-color: #E3F2FD;
    padding: 15px;
    border-radius: 10px;
    border-left: 5px solid #2196F3;
    margin-bottom: 15px;
}
.success-box {
    background-color: #E8F5E9;
    padding: 15px;
    border-radius: 10px;
    border-left: 5px solid #4CAF50;
    margin-bottom: 15px;
}
.file-preview {
    background-color: #F5F5F5;
    padding: 10px;
    border-radius: 5px;
    font-family: monospace;
    margin: 10px 0;
}
</style>
""", unsafe_allow_html=True)

# ==================== 1. 系统首页 ====================
if menu == "🏠 系统首页":
    st.markdown("### 欢迎使用实验室数据管理系统")
    
    st.markdown("""
    <div class="info-box">
    <h3>🎯 系统简介</h3>
    <p>本系统专为实验室数据管理设计，支持实验数据的文件上传、管理和查询分析。</p>
    <p><strong>核心功能</strong>：文件上传、自动重命名、密级管理、申请人追踪</p>
    <p><strong>部署方式</strong>：Streamlit Cloud 云端部署</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 系统统计
    st.markdown("### 📈 系统统计")
    
    df_total = pd.read_sql_query("SELECT COUNT(*) as count FROM experiments", conn)
    df_files = pd.read_sql_query("SELECT COUNT(*) as count FROM experiments WHERE renamed_filename IS NOT NULL", conn)
    df_projects = pd.read_sql_query("SELECT COUNT(DISTINCT test_project_name) as count FROM experiments", conn)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📊 总记录数", df_total['count'][0])
    with col2:
        st.metric("📁 有文件记录", df_files['count'][0])
    with col3:
        st.metric("🏢 项目数量", df_projects['count'][0])
    with col4:
        st.metric("🌐 运行环境", "云端部署")
    
    # 最近活动
    st.markdown("### 🕒 最近活动")
    
    df_recent = pd.read_sql_query("""
        SELECT data_id, test_project_name, upload_time, renamed_filename, security_level
        FROM experiments WHERE upload_time IS NOT NULL 
        ORDER BY upload_time DESC LIMIT 5
    """, conn)
    
    if not df_recent.empty:
        for _, row in df_recent.iterrows():
            security_class = security_colors.get(row['security_level'], 'security-badge-A')
            st.markdown(f"📄 **{row['test_project_name']}** - {row['data_id']} "
                       f"<span class='{security_class}'>密级{row['security_level']}</span>", 
                       unsafe_allow_html=True)
    else:
        st.info("暂无最近活动")

# ==================== 2. 数据录入 ====================
elif menu == "📝 数据录入":
    st.markdown("### 📝 实验数据录入")
    
    with st.form("data_entry_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            test_project_name = st.text_input("测试项目名称*", placeholder="如：JCI蒸发器")
            experiment_date = st.date_input("实验日期*", value=datetime.now())
            test_object = st.selectbox("实验对象*", ["整机", "冷凝器", "蒸发器", "热泵", "水箱", "热虹吸", "其他"])
            core_drawing_number = st.text_input("芯体图号*", placeholder="如：DRG-EVAP-001")
        
        with col2:
            test_type = st.selectbox("测试类型*", test_type_options)
            equipment = st.selectbox("设备*", equipment_options)
            applicant_name = st.text_input("申请人姓名*", placeholder="如：张三")
            security_level = st.selectbox("密级*", security_options)
        
        refrigerant_type = st.selectbox("制冷剂类型", ["", "R134a", "R410a", "R32", "R22", "R407C", "R290"])
        notes = st.text_area("备注", height=100)
        
        submitted = st.form_submit_button("💾 保存数据", type="primary")
        
        if submitted:
            is_valid, msg = validate_inputs(test_project_name, test_object, test_type, 
                                           equipment, applicant_name, security_level, core_drawing_number)
            if not is_valid:
                st.error(msg)
            else:
                params = {
                    'test_project_name': test_project_name,
                    'experiment_date': experiment_date,
                    'test_object': test_object,
                    'core_drawing_number': core_drawing_number,
                    'test_type': test_type,
                    'equipment': equipment,
                    'applicant_name': applicant_name,
                    'security_level': security_level,
                    'file_extension': ".xlsx"
                }
                
                filename = generate_filename(params)
                data_id = filename.replace(".xlsx", "")
                
                try:
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT INTO experiments 
                        (data_id, test_project_name, experiment_date, test_object, core_drawing_number,
                         test_type, equipment, applicant_name, security_level, file_extension,
                         refrigerant_type, notes)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        data_id, test_project_name, experiment_date.strftime('%Y-%m-%d'),
                        test_object, core_drawing_number, test_type, equipment,
                        applicant_name, security_level, ".xlsx", refrigerant_type, notes
                    ))
                    conn.commit()
                    
                    st.success("✅ 数据保存成功！")
                    st.info(f"📁 数据ID: {data_id}")
                    st.info(f"📄 文件名预览: {filename}")
                    st.balloons()
                    
                except Exception as e:
                    st.error(f"保存失败: {str(e)}")

# ==================== 3. 文件上传 ====================
elif menu == "📁 文件上传":
    st.markdown("### 📤 文件上传")
    
    df_records = pd.read_sql_query("""
        SELECT data_id, test_project_name, applicant_name, security_level 
        FROM experiments ORDER BY experiment_date DESC
    """, conn)
    
    if not df_records.empty:
        record_options = [f"{row['data_id']} | {row['test_project_name']} | {row['applicant_name']}" 
                         for _, row in df_records.iterrows()]
        selected = st.selectbox("选择实验记录", record_options)
        
        if selected:
            data_id = selected.split(" | ")[0]
            record = df_records[df_records['data_id'] == data_id].iloc[0]
            
            st.markdown(f"""
            <div class="info-box">
            <b>📋 记录详情</b><br>
            <b>项目</b>: {record['test_project_name']}<br>
            <b>申请人</b>: {record['applicant_name']}<br>
            <b>密级</b>: <span class="{security_colors.get(record['security_level'], 'security-badge-A')}">密级{record['security_level']}</span>
            </div>
            """, unsafe_allow_html=True)
            
            uploaded_file = st.file_uploader("选择文件", type=['xlsx', 'csv', 'pdf', 'jpg', 'png', 'docx', 'tif', 'dat'])
            
            if uploaded_file:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM experiments WHERE data_id = ?", (data_id,))
                full_record = cursor.fetchone()
                col_names = [desc[0] for desc in cursor.description]
                record_dict = dict(zip(col_names, full_record))
                
                file_ext = os.path.splitext(uploaded_file.name)[1]
                
                params = {
                    'test_project_name': record_dict['test_project_name'],
                    'experiment_date': datetime.strptime(record_dict['experiment_date'], '%Y-%m-%d'),
                    'test_object': record_dict['test_object'],
                    'core_drawing_number': record_dict['core_drawing_number'] or "",
                    'test_type': record_dict['test_type'],
                    'equipment': record_dict['equipment'],
                    'applicant_name': record_dict['applicant_name'],
                    'security_level': record_dict['security_level'],
                    'file_extension': file_ext
                }
                
                final_filename = generate_filename(params)
                
                st.markdown(f"""
                <div class="success-box">
                <b>📄 文件名预览</b><br>
                <code>{final_filename}</code>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button("🚀 上传文件", type="primary"):
                    result = save_uploaded_file(uploaded_file, params, final_filename)
                    
                    if result["success"]:
                        cursor.execute('''
                            UPDATE experiments SET
                                original_filename = ?,
                                renamed_filename = ?,
                                file_path = ?,
                                server_path = ?,
                                file_size = ?,
                                upload_time = ?,
                                file_hash = ?
                            WHERE data_id = ?
                        ''', (uploaded_file.name, final_filename, result["file_path"], 
                              result["server_path"], result["file_size"], 
                              datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 
                              result["file_hash"], data_id))
                        conn.commit()
                        
                        st.success("✅ 文件上传成功！")
                        st.balloons()
                    else:
                        st.error(f"上传失败: {result.get('error', '未知错误')}")
    else:
        st.info("📭 暂无数据记录，请先在「数据录入」页面创建记录")

# ==================== 4. 数据查询 ====================
elif menu == "🔍 数据查询":
    st.markdown("### 🔍 数据查询")
    
    with st.expander("🔎 查询条件", expanded=True):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            query_project = st.text_input("项目名称", placeholder="输入关键字")
            query_object = st.multiselect("实验对象", ["整机", "冷凝器", "蒸发器", "热泵", "水箱", "热虹吸", "其他"])
        
        with col2:
            query_applicant = st.text_input("申请人", placeholder="输入姓名")
            query_security = st.multiselect("密级", security_options)
        
        with col3:
            query_has_file = st.checkbox("仅显示有文件的记录")
            date_range = st.date_input("日期范围", [datetime(2024, 1, 1), datetime.now()])
    
    if st.button("🔍 开始查询", type="primary"):
        sql = "SELECT * FROM experiments WHERE 1=1"
        params = []
        
        if query_project:
            sql += " AND test_project_name LIKE ?"
            params.append(f"%{query_project}%")
        
        if query_object:
            placeholders = ','.join(['?'] * len(query_object))
            sql += f" AND test_object IN ({placeholders})"
            params.extend(query_object)
        
        if query_applicant:
            sql += " AND applicant_name LIKE ?"
            params.append(f"%{query_applicant}%")
        
        if query_security:
            placeholders = ','.join(['?'] * len(query_security))
            sql += f" AND security_level IN ({placeholders})"
            params.extend(query_security)
        
        if query_has_file:
            sql += " AND renamed_filename IS NOT NULL"
        
        if len(date_range) == 2:
            sql += " AND experiment_date BETWEEN ? AND ?"
            params.extend([date_range[0].strftime('%Y-%m-%d'), date_range[1].strftime('%Y-%m-%d')])
        
        sql += " ORDER BY experiment_date DESC"
        
        df_results = pd.read_sql_query(sql, conn, params=params) if params else pd.read_sql_query(sql, conn)
        
        st.write(f"📊 共找到 **{len(df_results)}** 条记录")
        
        if not df_results.empty:
            display_cols = ['data_id', 'test_project_name', 'experiment_date', 'test_object', 
                           'test_type', 'applicant_name', 'security_level', 'renamed_filename']
            st.dataframe(df_results[display_cols], use_container_width=True, hide_index=True)

# ==================== 5. 数据浏览 ====================
elif menu == "📋 数据浏览":
    st.markdown("### 📋 所有数据")
    
    df_all = pd.read_sql_query("SELECT * FROM experiments ORDER BY experiment_date DESC", conn)
    st.write(f"📊 共 **{len(df_all)}** 条记录")
    
    if not df_all.empty:
        display_cols = ['data_id', 'test_project_name', 'experiment_date', 'test_object', 
                       'test_type', 'applicant_name', 'security_level', 'renamed_filename', 'upload_time']
        st.dataframe(df_all[display_cols], use_container_width=True, hide_index=True)
        
        st.markdown("### 📈 统计信息")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("总记录数", len(df_all))
        with col2:
            has_files = df_all['renamed_filename'].notna().sum()
            st.metric("有文件记录", has_files)
        with col3:
            applicants = df_all['applicant_name'].nunique()
            st.metric("申请人数量", applicants)
        with col4:
            projects = df_all['test_project_name'].nunique()
            st.metric("项目数量", projects)
        
        st.markdown("#### 🔒 密级分布")
        security_dist = df_all['security_level'].value_counts()
        for sec, count in security_dist.items():
            security_class = security_colors.get(sec, 'security-badge-A')
            st.markdown(f"<span class='{security_class}'>密级{sec}</span>：{count} 条", unsafe_allow_html=True)
