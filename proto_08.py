import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import mysql.connector
from mysql.connector import Error
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import requests
import json

# 创建主窗口
root = tk.Tk()
root.title("SQL Helper with AI!")
root.geometry("1100x700")  # 增大窗口尺寸以适应新功能

# 默认数据库连接配置
db_config = {
    'host': 'localhost',
    'port': 3307,
    'user': 'root',
    'password': 'root',
    'ai_api_key': '',
    'ai_api_url': 'https://api.siliconflow.ai/v1/chat/completions'  # 示例API端点
}

# 全局变量
conn = None
current_db = None
current_table = None
show_structure = False  # 标志变量，False 表示显示表内容，True 表示显示表结构
ai_context = ""  # 保存当前表结构信息
current_ai_sql = ""  # 保存AI生成的SQL


# ---------------------------- AI 功能函数 ----------------------------

def call_ai_api(user_input, table_structure):
    """调用硅基流动AI API生成SQL"""
    if 'ai_api_key' not in db_config or not db_config['ai_api_key']:
        messagebox.showerror("错误", "请先在设置中配置AI API Key")
        return None

    try:
        headers = {
            "Authorization": f"Bearer {db_config['ai_api_key']}",
            "Content-Type": "application/json"
        }

        prompt = f"""
        你是一个专业的SQL助手。请根据以下表结构和用户需求生成合适的MySQL查询语句。

        表结构:
        {table_structure}

        用户需求: {user_input}

        请只返回JSON格式的响应，包含以下字段:
        - "sql": 生成的SQL语句
        - "explanation": 对SQL的简要解释
        """

        data = {
            "model": "silicon-flow-model",  # 替换为实际模型名称
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "response_format": {"type": "json_object"}
        }

        response = requests.post(
            db_config['ai_api_url'],
            headers=headers,
            data=json.dumps(data),
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            # 解析API响应，假设返回格式为 {"sql": "...", "explanation": "..."}
            return result
        else:
            messagebox.showerror("错误", f"AI API调用失败: {response.text}")
            return None

    except Exception as e:
        messagebox.showerror("错误", f"调用AI API时出错: {e}")
        return None


def generate_sql_with_ai():
    """使用AI生成SQL查询"""
    global current_db, current_table, ai_context, current_ai_sql

    if not current_db or not current_table:
        messagebox.showwarning("警告", "请先选择一个表！")
        return

    # 获取用户输入的自然语言描述
    user_input = ai_input.get("1.0", tk.END).strip()
    if not user_input:
        messagebox.showwarning("警告", "请输入你的需求描述！")
        return

    # 获取表结构作为上下文
    try:
        cursor = conn.cursor()
        cursor.execute(f"USE {current_db}")
        cursor.execute(f"DESCRIBE {current_table}")
        structure = cursor.fetchall()

        # 构建表结构描述
        ai_context = f"表 {current_table} 的结构:\n"
        for column in structure:
            ai_context += f"- {column[0]}: {column[1]}, {'允许NULL' if column[2] == 'YES' else '非NULL'}, {column[3] or ''}\n"

        # 显示等待提示
        ai_output.config(state='normal')
        ai_output.delete(1.0, tk.END)
        ai_output.insert(tk.END, "正在生成SQL，请稍候...")
        ai_output.config(state='disabled')
        root.update()  # 立即更新界面

        # 调用AI API
        response = call_ai_api(user_input, ai_context)

        # 解析AI响应
        if response and 'sql' in response:
            current_ai_sql = response['sql']
            explanation = response.get('explanation', '')

            ai_output.config(state='normal')
            ai_output.delete(1.0, tk.END)
            ai_output.insert(tk.END, f"生成的SQL:\n{current_ai_sql}\n\n解释:\n{explanation}")
            ai_output.config(state='disabled')

            # 启用执行按钮
            execute_ai_button.config(state='normal')
        else:
            messagebox.showerror("错误", "无法从AI获取有效的SQL语句")

    except Error as e:
        messagebox.showerror("错误", f"获取表结构失败: {e}")


def execute_ai_sql():
    """执行AI生成的SQL"""
    global current_ai_sql

    if not current_ai_sql:
        messagebox.showwarning("警告", "没有可执行的SQL语句！")
        return

    # 提取SQL语句（可能包含解释文本）
    sql_lines = [line for line in current_ai_sql.split('\n') if line.strip() and not line.strip().startswith('--')]
    sql_to_execute = ' '.join(sql_lines)

    # 确认执行
    confirm = messagebox.askyesno("确认", f"确定要执行以下SQL吗？\n\n{sql_to_execute}")
    if confirm:
        query_entry.delete(1.0, tk.END)
        query_entry.insert(tk.END, sql_to_execute)
        execute_query()  # 复用现有的执行函数


# ---------------------------- 数据库功能函数 ----------------------------

def connect_db():
    """连接数据库"""
    global conn
    try:
        conn = mysql.connector.connect(
            host=db_config['host'],
            port=db_config['port'],
            user=db_config['user'],
            password=db_config['password']
        )
        if conn.is_connected():
            messagebox.showinfo("成功", "数据库连接成功！")
            load_databases()
        else:
            messagebox.showerror("错误", "数据库连接失败！")
    except Error as e:
        messagebox.showerror("错误", f"数据库连接失败: {e}")


def close_db():
    """关闭数据库连接"""
    global conn
    if conn and conn.is_connected():
        conn.close()
        conn = None


def load_databases():
    """加载所有数据库"""
    if conn:
        try:
            # 清空当前树形结构
            for item in tree.get_children():
                tree.delete(item)

            cursor = conn.cursor()
            cursor.execute("SHOW DATABASES")
            databases = cursor.fetchall()
            for db in databases:
                db_name = db[0]
                db_node = tree.insert("", "end", text=db_name, values=("DB",))
                load_tables(db_node, db_name)
        except Error as e:
            messagebox.showerror("错误", f"加载数据库失败: {e}")


def load_tables(db_node, db_name):
    """加载数据库中的表"""
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute(f"USE {db_name}")
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            for table in tables:
                table_name = table[0]
                tree.insert(db_node, "end", text=table_name, values=("Table",))
        except Error as e:
            messagebox.showerror("错误", f"加载表失败: {e}")


def show_table_data_or_structure(event):
    """显示表内容或结构"""
    global current_db, current_table
    selected_item = tree.selection()[0]
    item_type = tree.item(selected_item, "values")[0]
    if item_type == "Table":
        current_db = tree.item(tree.parent(selected_item), "text")
        current_table = tree.item(selected_item, "text")
        refresh_table_display()

        # 更新AI区域的上下文提示
        ai_context_label.config(text=f"当前表: {current_db}.{current_table}")


def refresh_table_display():
    """刷新表显示"""
    if current_db and current_table:
        if show_structure:
            show_table_structure()
        else:
            show_table_data()


def show_table_data():
    """显示表内容"""
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute(f"USE {current_db}")
            cursor.execute(f"SELECT * FROM {current_table}")
            result = cursor.fetchall()
            if result:
                df = pd.DataFrame(result, columns=cursor.column_names)
                result_text.delete(1.0, tk.END)
                result_text.insert(tk.END, df.to_string())
            else:
                result_text.delete(1.0, tk.END)
                result_text.insert(tk.END, "表为空。")
        except Error as e:
            messagebox.showerror("错误", f"获取表内容失败: {e}")


def show_table_structure():
    """显示表结构"""
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute(f"USE {current_db}")
            cursor.execute(f"DESCRIBE {current_table}")
            result = cursor.fetchall()
            df = pd.DataFrame(result, columns=["Field", "Type", "Null", "Key", "Default", "Extra"])
            result_text.delete(1.0, tk.END)
            result_text.insert(tk.END, df.to_string())
        except Error as e:
            messagebox.showerror("错误", f"获取表结构失败: {e}")


def toggle_display():
    """切换显示表结构或内容"""
    global show_structure
    show_structure = not show_structure
    refresh_table_display()
    toggle_button.config(text="显示表结构" if not show_structure else "显示表内容")


# ... (保留原有的 insert_data, update_data, delete_data, execute_query, generate_chart 函数) ...
def insert_data():
    if not current_db or not current_table:
        messagebox.showwarning("警告", "请先选择一个表！")
        return

    # 获取表结构
    try:
        cursor = conn.cursor()
        cursor.execute(f"USE {current_db}")
        cursor.execute(f"DESCRIBE {current_table}")
        columns = cursor.fetchall()
    except Error as e:
        messagebox.showerror("错误", f"获取表结构失败: {e}")
        return

    # 弹出输入对话框
    insert_window = tk.Toplevel(root)
    insert_window.title("插入数据")
    insert_window.geometry("400x300")

    entries = {}
    for i, column in enumerate(columns):
        field_name = column[0]
        field_type = column[1]
        label = tk.Label(insert_window, text=f"{field_name} ({field_type}):")
        label.grid(row=i, column=0, padx=10, pady=5)
        entry = tk.Entry(insert_window)
        entry.grid(row=i, column=1, padx=10, pady=5)
        entries[field_name] = entry

    # 插入数据
    def perform_insert():
        try:
            cursor = conn.cursor()
            columns_str = ", ".join(entries.keys())
            values_str = ", ".join([f"'{entry.get()}'" for entry in entries.values()])
            query = f"INSERT INTO {current_table} ({columns_str}) VALUES ({values_str})"
            cursor.execute(query)
            conn.commit()
            messagebox.showinfo("成功", "数据插入成功！")
            insert_window.destroy()
            refresh_table_display()
        except Error as e:
            messagebox.showerror("错误", f"插入数据失败: {e}")

    insert_button = tk.Button(insert_window, text="插入", command=perform_insert)
    insert_button.grid(row=len(columns), column=0, columnspan=2, pady=10)


# 更新数据
def update_data():
    if not current_db or not current_table:
        messagebox.showwarning("警告", "请先选择一个表！")
        return

    # 获取表数据
    try:
        cursor = conn.cursor()
        cursor.execute(f"USE {current_db}")
        cursor.execute(f"SELECT * FROM {current_table}")
        result = cursor.fetchall()
        if not result:
            messagebox.showwarning("警告", "表中没有数据！")
            return
    except Error as e:
        messagebox.showerror("错误", f"获取表数据失败: {e}")
        return

    # 弹出选择行对话框
    selected_row = simpledialog.askinteger("选择行", "请输入要更新的行号（从 0 开始）：")
    if selected_row is None or selected_row < 0 or selected_row >= len(result):
        messagebox.showwarning("警告", "无效的行号！")
        return

    # 获取表结构
    try:
        cursor.execute(f"DESCRIBE {current_table}")
        columns = cursor.fetchall()
    except Error as e:
        messagebox.showerror("错误", f"获取表结构失败: {e}")
        return

    # 弹出更新对话框
    update_window = tk.Toplevel(root)
    update_window.title("更新数据")
    update_window.geometry("400x300")

    entries = {}
    for i, column in enumerate(columns):
        field_name = column[0]
        field_type = column[1]
        label = tk.Label(update_window, text=f"{field_name} ({field_type}):")
        label.grid(row=i, column=0, padx=10, pady=5)
        entry = tk.Entry(update_window)
        entry.grid(row=i, column=1, padx=10, pady=5)
        entry.insert(0, result[selected_row][i])  # 填充当前值
        entries[field_name] = entry

    # 更新数据
    def perform_update():
        try:
            cursor = conn.cursor()
            set_str = ", ".join([f"{field} = '{entry.get()}'" for field, entry in entries.items()])
            primary_key = columns[0][0]  # 假设第一列是主键
            primary_value = result[selected_row][0]
            query = f"UPDATE {current_table} SET {set_str} WHERE {primary_key} = '{primary_value}'"
            cursor.execute(query)
            conn.commit()
            messagebox.showinfo("成功", "数据更新成功！")
            update_window.destroy()
            refresh_table_display()
        except Error as e:
            messagebox.showerror("错误", f"更新数据失败: {e}")

    update_button = tk.Button(update_window, text="更新", command=perform_update)
    update_button.grid(row=len(columns), column=0, columnspan=2, pady=10)


# 删除数据
def delete_data():
    if not current_db or not current_table:
        messagebox.showwarning("警告", "请先选择一个表！")
        return

    # 获取表数据
    try:
        cursor = conn.cursor()
        cursor.execute(f"USE {current_db}")
        cursor.execute(f"SELECT * FROM {current_table}")
        result = cursor.fetchall()
        if not result:
            messagebox.showwarning("警告", "表中没有数据！")
            return
    except Error as e:
        messagebox.showerror("错误", f"获取表数据失败: {e}")
        return

    # 弹出选择行对话框
    selected_row = simpledialog.askinteger("选择行", "请输入要删除的行号（从 0 开始）：")
    if selected_row is None or selected_row < 0 or selected_row >= len(result):
        messagebox.showwarning("警告", "无效的行号！")
        return

    # 确认删除
    confirm = messagebox.askyesno("确认", "确定要删除该行数据吗？")
    if not confirm:
        return

    # 执行删除
    try:
        cursor = conn.cursor()
        primary_key = cursor.description[0][0]  # 假设第一列是主键
        primary_value = result[selected_row][0]
        query = f"DELETE FROM {current_table} WHERE {primary_key} = '{primary_value}'"
        cursor.execute(query)
        conn.commit()
        messagebox.showinfo("成功", "数据删除成功！")
        refresh_table_display()
    except Error as e:
        messagebox.showerror("错误", f"删除数据失败: {e}")


# 执行SQL查询
def execute_query():
    query = query_entry.get("1.0", tk.END).strip()
    if not query:
        messagebox.showwarning("警告", "请输入SQL查询语句！")
        return

    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute(query)

            # 检查是否有数据返回
            if cursor.description:
                result = cursor.fetchall()
                df = pd.DataFrame(result, columns=cursor.column_names)
                result_text.delete(1.0, tk.END)
                result_text.insert(tk.END, df.to_string())
            else:
                result_text.delete(1.0, tk.END)
                result_text.insert(tk.END, "SQL 执行成功，没有返回数据。")

            conn.commit()  # 确保变更生效
            load_databases()  # **执行完 SQL 语句后自动刷新数据库列表**
        except Error as e:
            messagebox.showerror("错误", f"查询执行失败: {e}")


# 图表生成功能
def generate_chart():
    if not current_db or not current_table:
        messagebox.showwarning("警告", "请先选择一个表！")
        return

    try:
        cursor = conn.cursor()
        cursor.execute(f"USE {current_db}")
        cursor.execute(f"SELECT * FROM {current_table}")
        result = cursor.fetchall()
        if not result:
            messagebox.showwarning("警告", "表中没有数据！")
            return
        df = pd.DataFrame(result, columns=cursor.column_names)
    except Error as e:
        messagebox.showerror("错误", f"获取表数据失败: {e}")
        return

    chart_window = tk.Toplevel(root)
    chart_window.title("生成图表")
    chart_window.geometry("700x900")

    # 图表容器和状态跟踪
    chart_container = tk.Frame(chart_window)
    chart_container.grid(row=10, column=0, columnspan=2, padx=10, pady=10)
    current_canvas = None

    # 选项变量定义
    chart_type_var = tk.StringVar(value="柱状图")
    x_axis_var = tk.StringVar()
    y_axis_var = tk.StringVar()
    sort_enabled_var = tk.BooleanVar(value=False)
    sort_order_var = tk.StringVar(value="升序")
    show_legend_var = tk.BooleanVar(value=True)
    show_grid_var = tk.BooleanVar(value=True)
    show_labels_var = tk.BooleanVar(value=False)
    line_style_var = tk.StringVar(value="实线")
    color_theme_var = tk.StringVar(value="默认")

    # 动态更新函数
    def update_chart(*args):
        nonlocal current_canvas

        # 清除旧图表
        if current_canvas:
            current_canvas.get_tk_widget().destroy()
            plt.close('all')

        # 验证必要选项
        if not x_axis_var.get() or not y_axis_var.get():
            return

        try:
            # 数据预处理
            df_copy = df.copy()
            x_col = x_axis_var.get()
            y_col = y_axis_var.get()

            # 转换数值类型
            df_copy[x_col] = pd.to_numeric(df_copy[x_col], errors='coerce')
            df_copy[y_col] = pd.to_numeric(df_copy[y_col], errors='coerce')
            df_copy = df_copy.dropna(subset=[x_col, y_col])

            # 排序处理（修复折线图排序问题）
            if sort_enabled_var.get():
                df_copy = df_copy.sort_values(
                    by=x_col,
                    ascending=(sort_order_var.get() == "升序")
                ).reset_index(drop=True)  # 重置索引

            # 创建图表
            fig, ax = plt.subplots(figsize=(8, 5))
            chart_type = chart_type_var.get()

            # 设置颜色主题（修复颜色问题）
            plt.style.use('default')  # 重置样式
            theme_settings = {
                "默认": {'bg': 'white', 'text': 'black'},
                "深色": {'bg': 'black', 'text': 'white'},
                "彩色": {'bg': '#f0f0f0', 'text': 'black'}
            }
            theme = theme_settings[color_theme_var.get()]

            fig.patch.set_facecolor(theme['bg'])
            ax.set_facecolor(theme['bg'])
            ax.xaxis.label.set_color(theme['text'])
            ax.yaxis.label.set_color(theme['text'])
            ax.title.set_color(theme['text'])
            ax.tick_params(axis='x', colors=theme['text'])
            ax.tick_params(axis='y', colors=theme['text'])

            # 绘制图表
            if chart_type == "柱状图":
                bars = ax.bar(df_copy[x_col].astype(str), df_copy[y_col], color='#1f77b4')
                if show_labels_var.get():
                    for bar in bars:
                        height = bar.get_height()
                        ax.text(bar.get_x() + bar.get_width() / 2., height,
                                f'{height:.1f}', ha='center', va='bottom',
                                color=theme['text'])
                ax.set_xlabel(x_col)
                ax.set_ylabel(y_col)

            elif chart_type == "折线图":
                linestyle = {"实线": "-", "虚线": "--", "点线": ":"}[line_style_var.get()]
                line, = ax.plot(df_copy[x_col], df_copy[y_col],  # 使用实际x值
                                marker='o',
                                linestyle=linestyle,
                                color='#2ca02c')
                ax.set_xticks(df_copy[x_col].unique())  # 显示唯一值
                ax.set_xticklabels(df_copy[x_col].astype(str), rotation=45)
                if show_labels_var.get():
                    for x, y in zip(df_copy[x_col], df_copy[y_col]):
                        ax.text(x, y, f'{y:.1f}',
                                ha='center', va='bottom',
                                color=theme['text'])
                ax.set_xlabel(x_col)
                ax.set_ylabel(y_col)

            elif chart_type == "饼图":
                wedges, texts = ax.pie(
                    df_copy[y_col],
                    labels=df_copy[x_col].astype(str),
                    autopct='%1.1f%%',
                    colors=plt.cm.tab20.colors
                )
                for text in texts:
                    text.set_color(theme['text'])

            # 通用设置
            if show_legend_var.get() and chart_type != "饼图":
                ax.legend([y_col], facecolor=theme['bg'], edgecolor=theme['text'])
            if show_grid_var.get():
                ax.grid(True, color=theme['text'], alpha=0.3)
            plt.title(f"{chart_type} - {y_col} vs {x_col}")
            plt.tight_layout()

            # 嵌入图表
            current_canvas = FigureCanvasTkAgg(fig, master=chart_container)
            current_canvas.draw()
            current_canvas.get_tk_widget().pack()
        except Exception as e:
            print(f"图表更新失败: {e}")

    # 绑定变量跟踪（保持之前的正确跟踪方式）
    track_vars = [
        chart_type_var, x_axis_var, y_axis_var,
        sort_enabled_var, sort_order_var,
        show_legend_var, show_grid_var, show_labels_var,
        line_style_var, color_theme_var
    ]

    for var in track_vars:
        var.trace_add("write", update_chart)  # 统一使用"write"

def open_settings():
    """打开设置窗口"""
    settings_window = tk.Toplevel(root)
    settings_window.title("设置")
    settings_window.geometry("400x350")  # 增大窗口高度

    # 数据库配置
    db_label = tk.Label(settings_window, text="数据库配置", font=('Arial', 10, 'bold'))
    db_label.grid(row=0, column=0, columnspan=2, pady=(10, 5))

    host_label = tk.Label(settings_window, text="主机名:")
    host_label.grid(row=1, column=0, padx=10, pady=5, sticky='e')
    host_entry = tk.Entry(settings_window)
    host_entry.grid(row=1, column=1, padx=10, pady=5)
    host_entry.insert(0, db_config['host'])

    port_label = tk.Label(settings_window, text="端口号:")
    port_label.grid(row=2, column=0, padx=10, pady=5, sticky='e')
    port_entry = tk.Entry(settings_window)
    port_entry.grid(row=2, column=1, padx=10, pady=5)
    port_entry.insert(0, db_config['port'])

    user_label = tk.Label(settings_window, text="用户名:")
    user_label.grid(row=3, column=0, padx=10, pady=5, sticky='e')
    user_entry = tk.Entry(settings_window)
    user_entry.grid(row=3, column=1, padx=10, pady=5)
    user_entry.insert(0, db_config['user'])

    password_label = tk.Label(settings_window, text="密码:")
    password_label.grid(row=4, column=0, padx=10, pady=5, sticky='e')
    password_entry = tk.Entry(settings_window, show="*")
    password_entry.grid(row=4, column=1, padx=10, pady=5)
    password_entry.insert(0, db_config['password'])

    # AI配置
    ai_label = tk.Label(settings_window, text="AI 配置", font=('Arial', 10, 'bold'))
    ai_label.grid(row=5, column=0, columnspan=2, pady=(10, 5))

    api_key_label = tk.Label(settings_window, text="API Key:")
    api_key_label.grid(row=6, column=0, padx=10, pady=5, sticky='e')
    api_key_entry = tk.Entry(settings_window)
    api_key_entry.grid(row=6, column=1, padx=10, pady=5)
    api_key_entry.insert(0, db_config.get('ai_api_key', ''))

    api_url_label = tk.Label(settings_window, text="API URL:")
    api_url_label.grid(row=7, column=0, padx=10, pady=5, sticky='e')
    api_url_entry = tk.Entry(settings_window)
    api_url_entry.grid(row=7, column=1, padx=10, pady=5)
    api_url_entry.insert(0, db_config.get('ai_api_url', ''))

    def save_settings():
        """保存设置"""
        global db_config
        db_config['host'] = host_entry.get()
        db_config['port'] = int(port_entry.get())
        db_config['user'] = user_entry.get()
        db_config['password'] = password_entry.get()
        db_config['ai_api_key'] = api_key_entry.get()
        db_config['ai_api_url'] = api_url_entry.get()

        # 关闭当前连接
        close_db()

        # 重新连接数据库并刷新列表
        connect_db()

        messagebox.showinfo("成功", "设置已保存并刷新数据库列表！")
        settings_window.destroy()

    save_button = tk.Button(settings_window, text="保存", command=save_settings)
    save_button.grid(row=8, column=0, columnspan=2, pady=10)


# ---------------------------- GUI布局 ----------------------------

# 菜单栏
menu_bar = tk.Menu(root)
root.config(menu=menu_bar)

settings_menu = tk.Menu(menu_bar, tearoff=0)
settings_menu.add_command(label="设置", command=open_settings)
menu_bar.add_cascade(label="选项", menu=settings_menu)

# 主布局
main_paned = tk.PanedWindow(root, orient=tk.HORIZONTAL)
main_paned.pack(fill=tk.BOTH, expand=True)

# 左侧面板 - 数据库树
left_frame = tk.Frame(main_paned, width=250)
main_paned.add(left_frame)

tree = ttk.Treeview(left_frame)
tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
tree["columns"] = ("type",)
tree.column("#0", width=200)
tree.column("type", width=50)
tree.heading("#0", text="数据库/表")
tree.heading("type", text="类型")
tree.bind("<Double-1>", show_table_data_or_structure)

# 右侧面板 - 主功能区
right_paned = tk.PanedWindow(main_paned, orient=tk.VERTICAL)
main_paned.add(right_paned)

# 上部 - 查询和结果
query_frame = tk.Frame(right_paned)
right_paned.add(query_frame)

query_label = tk.Label(query_frame, text="SQL查询:")
query_label.pack(pady=5)

query_entry = tk.Text(query_frame, height=5, width=80)
query_entry.pack(pady=5)

button_frame = tk.Frame(query_frame)
button_frame.pack(pady=5)

execute_button = tk.Button(button_frame, text="执行查询", command=execute_query)
execute_button.grid(row=0, column=0, padx=5)

insert_button = tk.Button(button_frame, text="插入", command=insert_data)
insert_button.grid(row=0, column=1, padx=5)

update_button = tk.Button(button_frame, text="更新", command=update_data)
update_button.grid(row=0, column=2, padx=5)

delete_button = tk.Button(button_frame, text="删除", command=delete_data)
delete_button.grid(row=0, column=3, padx=5)

toggle_button = tk.Button(button_frame, text="显示表结构", command=toggle_display)
toggle_button.grid(row=0, column=4, padx=5)

chart_button = tk.Button(button_frame, text="生成图表", command=generate_chart)
chart_button.grid(row=0, column=5, padx=5)

refresh_button = tk.Button(button_frame, text="刷新数据库", command=load_databases)
refresh_button.grid(row=0, column=6, padx=5)

result_label = tk.Label(query_frame, text="查询结果:")
result_label.pack(pady=5)

result_text = tk.Text(query_frame, height=15, width=80)
result_text.pack(pady=5)

# 下部 - AI功能区
ai_frame = tk.Frame(right_paned)
right_paned.add(ai_frame)

ai_title = tk.Label(ai_frame, text="AI SQL助手", font=('Arial', 12, 'bold'))
ai_title.pack(pady=5)

ai_context_label = tk.Label(ai_frame, text="当前表: 无")
ai_context_label.pack(pady=5)

ai_input_label = tk.Label(ai_frame, text="用自然语言描述你的需求:")
ai_input_label.pack(pady=5)

ai_input = tk.Text(ai_frame, height=5, width=80)
ai_input.pack(pady=5)

ai_button_frame = tk.Frame(ai_frame)
ai_button_frame.pack(pady=5)

generate_button = tk.Button(ai_button_frame, text="生成SQL", command=generate_sql_with_ai)
generate_button.grid(row=0, column=0, padx=5)

execute_ai_button = tk.Button(ai_button_frame, text="执行SQL", command=execute_ai_sql, state='disabled')
execute_ai_button.grid(row=0, column=1, padx=5)

ai_output_label = tk.Label(ai_frame, text="AI生成结果:")
ai_output_label.pack(pady=5)

ai_output = tk.Text(ai_frame, height=8, width=80, state='disabled')
ai_output.pack(pady=5)

# 初始连接数据库
connect_db()

# 运行主循环
root.mainloop()