"""
实验室数据管理系统 - Streamlit Cloud 部署版本
支持密级管理、文件上传、数据查询等功能
"""

import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
import os
import re
import hashlib
import shutil
import tempfile
import time
import platform
from pathlib import Path

# ==================== 页面配置 ====================
st.set_page_config(
    page_title="实验室数据管理系统",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== 辅助函数定义 ====================

def sanitize_filename(filename):
    """清理文件名中的非法字符"""
    return re.sub(r'[\\/*?:"<>|]', '_', filename.strip())

def get_test_type_code(test_type):
    """获取测试类型代码"""
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
    """获取设备类型代码"""
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

def calculate_file_hash(file_path):
    """计算文件的MD5哈希值"""
    hash_md5 = hashlib.md5()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception as e:
        return f"error_{e}"

def generate_filename(params):
    """根据参数生成标准文件名"""
    project_clean = sanitize_filename(params['test_project_name'])
    core_clean = sanitize_filename(params.get('core_drawing_number', '').strip()) if params.get('core_drawing_number') and params['core_drawing_number'].strip() else "NODWG"
    applicant_clean = sanitize_filename(params.get('applicant_name', '').strip()) if params.get('applicant_name') and params['applicant_name'].strip() else "未知"
    test_object_clean = sanitize_filename(params['test_object'])
    
    date_str = params['experiment_date'].strftime("%Y%m%d")
    test_type_code = get_test_type_code(params['test_type'])
    equipment_code = get_equipment_code(params['equipment'])
    security_level = params.get('security_level', 'A').strip()
    
    filename = "_".join([
        project_clean, date_str, test_object_clean, core_clean,
        test_type_code, equipment_code, applicant_clean, security_level
    ]) + params['file_extension']
    
    return filename

def generate_folder_structure(params):
    """生成文件夹路径"""
    project_clean = sanitize_filename(params['test_project_name'])
    core_clean = sanitize_filename(params.get('core_drawing_number', '').strip()) if params.get('core_drawing_number') and params['core_drawing_number'].strip() else "NODWG"
    applicant_clean = sanitize_filename(params.get('applicant_name', '').strip()) if params.get('applicant_name') and params['applicant_name'].strip() else "未知"
    
    year = params['experiment_date'].strftime("%Y")
    month = params['experiment_date'].strftime("%m")
    test_type_clean = sanitize_filename(params['test_type'])
    test_object_clean = sanitize_filename(params['test_object'])
    security_level = params.get('security_level', 'A').strip()
    
    folder_parts = [
        f"uploaded_files（密级{security_level}）",
        project_clean, year, month, core_clean,
        f"{test_type_clean}_{test_object_clean}_{applicant_clean}"
    ]
    
    return os.path.join(*folder_parts)

def save_uploaded_file(uploaded_file, params, new_filename, base_path="."):
    """保存上传的文件"""
    try:
        folder_path = os.path.join(base_path, generate_folder_structure(params))
        os.makedirs(folder_path, exist_ok=True)
        target_path = os.path.join(folder_path, new_filename)
        
        # 分块写入
        CHUNK_SIZE = 1024 * 1024
        with open(target_path, "wb") as f:
            if hasattr(uploaded_file, 'getvalue'):
                f.write(uploaded_file.getbuffer())
            else:
                while True:
                    chunk = uploaded_file.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    f.write(chunk)
        
        file_size = os.path.getsize(target_path)
        file_hash = calculate_file_hash(target_path)
        relative_path = os.path.relpath(target_path, base_path).replace(os.sep, '/')
        server_path = f"/app/data/{relative_path}"
        
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
        return {"success": False, "error": str(e)}

def validate_filename_inputs(project, date, obj, test_type, equipment, security_level, core, applicant):
    """验证输入参数"""
    if not all([project, obj, test_type, equipment, security_level, core, applicant]):
        return False, "请填写所有必填项（带*号）"
    if date > datetime.now().date():
        return False, "实验日期不能超过当前日期"
    return True, "验证通过"

def init_database():
    """初始化数据库"""
    conn = sqlite3.connect('lab_data.db', check_same_thread=False)
    cursor = conn.cursor()
    
    # 创建表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS experiments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data_id TEXT UNIQUE,
            test_project_name TEXT,
            experiment_date TEXT,
            test_object TEXT,
            test_type TEXT,
            equipment TEXT,
            version_code TEXT,
            file_extension TEXT,
            core_drawing_number TEXT,
            applicant_name TEXT,
            original_filename TEXT,
            renamed_filename TEXT,
            file_path TEXT,
            server_path TEXT,
            file_size INTEGER,
            upload_time TEXT,
            file_hash TEXT,
            notes TEXT,
            flat_tube_mold TEXT,
            header_mold TEXT,
            fin_tool TEXT,
            refrigerant_type TEXT,
            created_time TEXT
        )
    ''')
    
    # 检查并添加缺失字段
    cursor.execute("PRAGMA table_info(experiments)")
    columns = [col[1] for col in cursor.fetchall()]
    
    fields_to_add = {
        'refrigerant_type': 'TEXT',
        'created_time': 'TEXT'
    }
    
    for field, field_type in fields_to_add.items():
        if field not in columns:
            try:
                cursor.execute(f"ALTER TABLE experiments ADD COLUMN {field} {field_type}")
            except:
                pass
    
    conn.commit()
    return conn

def parse_notes_field(notes):
    """解析notes字段"""
    result = {'test_purpose': '', 'fin_mold': '', 'header_mold': '', 'tube_mold': ''}
    if not notes:
        return result
    
    lines = notes.split('\n')
    for line in lines:
        line = line.strip()
        if line.startswith('测试目的：'):
            result['test_purpose'] = line.replace('测试目的：', '')
        elif line.startswith('- 翅片模具：'):
            result['fin_mold'] = line.replace('- 翅片模具：', '')
        elif line.startswith('- 集流管模具：'):
            result['header_mold'] = line.replace('- 集流管模具：', '')
        elif line.startswith('- 扁管模具：'):
            result['tube_mold'] = line.replace('- 扁管模具：', '')
    
    return result

# ==================== 自定义CSS ====================
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
.security-badge-A { background-color: #4CAF50; color: white; padding: 0.2rem 0.5rem; border-radius: 4px; display: inline-block; }
.security-badge-AA { background-color: #FF9800; color: white; padding: 0.2rem 0.5rem; border-radius: 4px; display: inline-block; }
.security-badge-S { background-color: #F44336; color: white; padding: 0.2rem 0.5rem; border-radius: 4px; display: inline-block; }
.material-section {
    background-color: #FFF8E1;
    padding: 1rem;
    border-radius: 8px;
    border-left: 4px solid #FFB300;
    margin: 1rem 0;
}
</style>
""", unsafe_allow_html=True)

# ==================== 初始化 ====================
conn = init_database()

# 全局变量
equipment_options = ["30kw", "50kw", "75kw", "15kw", "28kw", "10kw", "120kw", "金相", "压力交变", "盐雾", "其他"]
test_type_options = ["焓差测试", "盐雾测试", "压力交变", "材料测试", "扫描电镜", "温度交变", "其他测试"]
security_options = ["A", "AA", "S"]
security_descriptions = {"A": "保密数据", "AA": "高级保密数据", "S": "绝密数据"}
security_colors = {'A': 'security-badge-A', 'AA': 'security-badge-AA', 'S': 'security-badge-S'}

# ==================== 侧边栏导航 ====================
st.sidebar.markdown('<div class="main-header">导航菜单</div>', unsafe_allow_html=True)

menu = st.sidebar.radio(
    "选择功能",
    ["🏠 系统首页", "📁 文件管理", "🔍 数据查询", "📋 数据浏览", "⚙️ 系统设置"]
)

st.sidebar.markdown("---")
st.sidebar.markdown("### 📊 系统信息")
st.sidebar.info(f"**版本**: 7.1\n\n**部署**: Streamlit Cloud\n\n**数据库**: SQLite")

# ==================== 系统首页 ====================
if menu == "🏠 系统首页":
    st.markdown('<div class="main-header">🔬 实验室数据管理系统</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">欢迎使用</div>', unsafe_allow_html=True)
    
    # 统计信息
    col_stat1, col_stat2, col_stat3 = st.columns(3)
    
    with col_stat1:
        df_total = pd.read_sql_query("SELECT COUNT(*) as count FROM experiments", conn)
        st.metric("📊 总记录数", df_total['count'][0])
    
    with col_stat2:
        df_files = pd.read_sql_query("SELECT COUNT(*) as count FROM experiments WHERE renamed_filename IS NOT NULL AND renamed_filename != ''", conn)
        st.metric("📁 有文件记录", df_files['count'][0])
    
    with col_stat3:
        df_projects = pd.read_sql_query("SELECT COUNT(DISTINCT test_project_name) as count FROM experiments", conn)
        st.metric("🏢 项目数量", df_projects['count'][0])
    
    # 功能简介
    st.markdown("""
    <div class="info-box">
    <h3>🎯 系统功能</h3>
    <ul>
    <li><strong>文件上传</strong> - 支持单文件上传和批量处理</li>
    <li><strong>自动命名</strong> - 根据实验信息自动生成标准文件名</li>
    <li><strong>层级存储</strong> - 按项目/日期/芯体图号组织文件</li>
    <li><strong>密级管理</strong> - 支持A/AA/S三级密级管理</li>
    <li><strong>模具追踪</strong> - 记录三大主材模具号信息</li>
    </ul>
    </div>
    """, unsafe_allow_html=True)

# ==================== 文件管理 ====================
elif menu == "📁 文件管理":
    st.markdown('<div class="sub-header">📁 文件管理</div>', unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["📤 单文件上传", "📋 文件记录管理"])
    
    with tab1:
        st.markdown("### 📤 上传实验文件")
        
        # 创建新记录表单
        with st.form("upload_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                project_name = st.text_input("项目名称 *", placeholder="如：JCI蒸发器")
                experiment_date = st.date_input("实验日期 *", value=datetime.now())
                test_object = st.selectbox("实验对象 *", ["整机", "冷凝器", "蒸发器", "热泵", "水箱", "热虹吸", "其他"])
                core_number = st.text_input("芯体图号 *", placeholder="如：DRG-EVAP-001")
            
            with col2:
                test_type = st.selectbox("测试类型 *", test_type_options)
                equipment = st.selectbox("设备 *", equipment_options)
                security_level = st.selectbox("密级 *", security_options, format_func=lambda x: f"{x} - {security_descriptions[x]}")
                applicant = st.text_input("申请人姓名 *", placeholder="如：张三")
            
            # 测试目的
            test_purpose = st.text_input("测试目的", placeholder="如：验证设计参数、性能评估等")
            
            # 模具号
            st.markdown('<div class="material-section">', unsafe_allow_html=True)
            st.markdown("**🔧 三大主材模具号**")
            col_mold1, col_mold2, col_mold3 = st.columns(3)
            with col_mold1:
                fin_mold = st.text_input("翅片模具号", placeholder="如：B150")
            with col_mold2:
                header_mold = st.text_input("集流管模具号", placeholder="如：H100")
            with col_mold3:
                tube_mold = st.text_input("扁管模具号", placeholder="如：A43S")
            st.markdown('</div>', unsafe_allow_html=True)
            
            # 文件上传
            uploaded_file = st.file_uploader(
                "选择文件",
                type=['xlsx', 'csv', 'pdf', 'jpg', 'png', 'docx', 'dat', 'txt'],
                help="支持常见实验数据文件格式"
            )
            
            submit = st.form_submit_button("🚀 上传文件", type="primary", use_container_width=True)
            
            if submit and uploaded_file:
                is_valid, msg = validate_filename_inputs(
                    project_name, experiment_date, test_object, test_type,
                    equipment, security_level, core_number, applicant
                )
                
                if not is_valid:
                    st.error(msg)
                else:
                    try:
                        # 生成文件名
                        params = {
                            'test_project_name': project_name,
                            'experiment_date': experiment_date,
                            'test_object': test_object,
                            'core_drawing_number': core_number,
                            'test_type': test_type,
                            'equipment': equipment,
                            'security_level': security_level,
                            'applicant_name': applicant,
                            'file_extension': os.path.splitext(uploaded_file.name)[1].lower()
                        }
                        
                        new_filename = generate_filename(params)
                        data_id = new_filename.replace(params['file_extension'], "")
                        
                        # 保存文件
                        result = save_uploaded_file(uploaded_file, params, new_filename)
                        
                        if not result["success"]:
                            st.error(f"文件保存失败：{result.get('error', '未知错误')}")
                        else:
                            # 组合notes字段
                            notes = f"测试目的：{test_purpose or ''}"
                            if any([fin_mold, header_mold, tube_mold]):
                                notes += "\n\n三大主材模具号："
                                if fin_mold:
                                    notes += f"\n- 翅片模具：{fin_mold}"
                                if header_mold:
                                    notes += f"\n- 集流管模具：{header_mold}"
                                if tube_mold:
                                    notes += f"\n- 扁管模具：{tube_mold}"
                            
                            # 保存到数据库
                            cursor = conn.cursor()
                            cursor.execute('''
                                INSERT OR REPLACE INTO experiments 
                                (data_id, test_project_name, experiment_date, test_object,
                                 test_type, equipment, version_code, file_extension,
                                 core_drawing_number, applicant_name,
                                 original_filename, renamed_filename, file_path,
                                 server_path, file_size, upload_time, file_hash, notes,
                                 fin_tool, header_mold, flat_tube_mold, created_time)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ''', (
                                data_id, project_name, experiment_date.strftime('%Y-%m-%d'),
                                test_object, test_type, equipment, security_level, params['file_extension'],
                                core_number, applicant,
                                uploaded_file.name, new_filename, result['file_path'],
                                result['server_path'], result['file_size'],
                                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                result['file_hash'], notes,
                                fin_mold or "", header_mold or "", tube_mold or "",
                                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            ))
                            conn.commit()
                            
                            st.success("✅ 文件上传成功！")
                            st.balloons()
                            
                            # 显示预览
                            with st.expander("📋 查看上传详情", expanded=True):
                                st.markdown(f"**文件名**: `{new_filename}`")
                                st.markdown(f"**存储路径**: `{result['folder_path']}`")
                                st.markdown(f"**数据ID**: `{data_id}`")
                                security_class = security_colors.get(security_level, 'security-badge-A')
                                st.markdown(f"**密级**: <span class='{security_class}'>密级{security_level}</span>", unsafe_allow_html=True)
                    
                    except Exception as e:
                        st.error(f"上传失败：{str(e)}")
            
            elif submit and not uploaded_file:
                st.warning("请选择要上传的文件")
    
    with tab2:
        st.markdown("### 📋 文件记录")
        
        # 搜索筛选
        col_search1, col_search2 = st.columns(2)
        with col_search1:
            search_project = st.text_input("搜索项目", placeholder="输入项目名称")
            search_core = st.text_input("搜索芯体图号", placeholder="输入芯体图号")
        with col_search2:
            search_applicant = st.text_input("搜索申请人", placeholder="输入申请人姓名")
            security_filter = st.multiselect("密级筛选", security_options)
        
        # 构建查询
        sql = "SELECT rowid, data_id, test_project_name, experiment_date, test_object, test_type, equipment, version_code, core_drawing_number, applicant_name, renamed_filename, file_size, upload_time FROM experiments WHERE 1=1"
        params = []
        
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
        
        sql += " ORDER BY experiment_date DESC"
        
        df_records = pd.read_sql_query(sql, conn, params=params)
        
        if not df_records.empty:
            st.dataframe(
                df_records,
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
                    "file_size": st.column_config.NumberColumn("文件大小", format="%.1f KB"),
                    "upload_time": "上传时间"
                }
            )
        else:
            st.info("暂无文件记录")

# ==================== 数据查询 ====================
elif menu == "🔍 数据查询":
    st.markdown('<div class="sub-header">🔍 数据查询</div>', unsafe_allow_html=True)
    
    with st.expander("🔎 查询条件", expanded=True):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            query_project = st.text_input("项目名称")
            query_applicant = st.text_input("申请人")
        with col2:
            query_test_type = st.selectbox("测试类型", [""] + test_type_options)
            query_security = st.multiselect("密级", security_options)
        with col3:
            query_core = st.text_input("芯体图号")
            query_fin = st.text_input("翅片模具号")
    
    if st.button("🔍 查询", type="primary", use_container_width=True):
        sql = "SELECT * FROM experiments WHERE 1=1"
        params = []
        
        if query_project:
            sql += " AND test_project_name LIKE ?"
            params.append(f"%{query_project}%")
        if query_applicant:
            sql += " AND applicant_name LIKE ?"
            params.append(f"%{query_applicant}%")
        if query_test_type:
            sql += " AND test_type = ?"
            params.append(query_test_type)
        if query_security:
            placeholders = ','.join(['?'] * len(query_security))
            sql += f" AND version_code IN ({placeholders})"
            params.extend(query_security)
        if query_core:
            sql += " AND core_drawing_number LIKE ?"
            params.append(f"%{query_core}%")
        if query_fin:
            sql += " AND fin_tool LIKE ?"
            params.append(f"%{query_fin}%")
        
        sql += " ORDER BY experiment_date DESC"
        
        df_results = pd.read_sql_query(sql, conn, params=params)
        
        st.markdown(f"### 查询结果（共 {len(df_results)} 条）")
        
        if not df_results.empty:
            st.dataframe(df_results, use_container_width=True, hide_index=True)
            
            # 导出
            csv = df_results.to_csv(index=False)
            st.download_button(
                label="📥 导出结果",
                data=csv,
                file_name=f"查询结果_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        else:
            st.info("未找到匹配的记录")

# ==================== 数据浏览 ====================
elif menu == "📋 数据浏览":
    st.markdown('<div class="sub-header">📋 所有实验数据</div>', unsafe_allow_html=True)
    
    # 获取所有数据
    df_all = pd.read_sql_query("SELECT data_id, test_project_name, experiment_date, test_object, test_type, equipment, version_code, core_drawing_number, applicant_name, renamed_filename FROM experiments ORDER BY experiment_date DESC", conn)
    
    if not df_all.empty:
        st.dataframe(df_all, use_container_width=True, hide_index=True)
        
        # 统计信息
        st.markdown("### 📊 统计信息")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("总记录数", len(df_all))
        with col2:
            st.metric("项目数", df_all['test_project_name'].nunique())
        with col3:
            st.metric("申请人数量", df_all['applicant_name'].nunique())
        with col4:
            st.metric("有文件记录", df_all['renamed_filename'].notna().sum())
        
        # 导出
        csv = df_all.to_csv(index=False)
        st.download_button(
            label="📥 导出全部数据",
            data=csv,
            file_name=f"全部数据_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    else:
        st.info("暂无数据")

# ==================== 系统设置 ====================
elif menu == "⚙️ 系统设置":
    st.markdown('<div class="sub-header">⚙️ 系统设置</div>', unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["📖 使用帮助", "💾 数据管理"])
    
    with tab1:
        st.markdown("""
        ### 🚀 使用指南
        
        #### 1. 文件上传
        1. 进入"文件管理"页面
        2. 填写实验信息（带*号为必填）
        3. 选择要上传的文件
        4. 点击"上传文件"
        
        #### 2. 文件命名规则
