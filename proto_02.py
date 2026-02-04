import tkinter as tk
from tkinter import ttk, messagebox
import mysql.connector
from mysql.connector import Error
import pandas as pd

# 创建主窗口
root = tk.Tk()
root.title("MySQL数据库工具")
root.geometry("800x600")

# 默认数据库连接配置
db_config = {
    'host': 'localhost',
    'port': 3307,
    'user': 'root',
    'password': 'root'
}

# 全局变量
conn = None
current_db = None
current_table = None
show_structure = False  # 标志变量，False 表示显示表内容，True 表示显示表结构

# 创建连接
def connect_db():
    global conn
    try:
        conn = mysql.connector.connect(**db_config)
        if conn.is_connected():
            messagebox.showinfo("成功", "数据库连接成功！")
            load_databases()
        else:
            messagebox.showerror("错误", "数据库连接失败！")
    except Error as e:
        messagebox.showerror("错误", f"数据库连接失败: {e}")

# 关闭连接
def close_db():
    global conn
    if conn and conn.is_connected():
        conn.close()
        conn = None

# 加载所有数据库
def load_databases():
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

# 加载数据库中的表
def load_tables(db_node, db_name):
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

# 显示表内容或结构
def show_table_data_or_structure(event):
    global current_db, current_table
    selected_item = tree.selection()[0]
    item_type = tree.item(selected_item, "values")[0]
    if item_type == "Table":
        current_db = tree.item(tree.parent(selected_item), "text")
        current_table = tree.item(selected_item, "text")
        refresh_table_display()

# 刷新表显示
def refresh_table_display():
    if current_db and current_table:
        if show_structure:
            show_table_structure()
        else:
            show_table_data()

# 显示表内容
def show_table_data():
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

# 显示表结构
def show_table_structure():
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

# 切换显示表结构或内容
def toggle_display():
    global show_structure
    show_structure = not show_structure
    refresh_table_display()
    toggle_button.config(text="显示表结构" if not show_structure else "显示表内容")

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
            result = cursor.fetchall()
            if result:
                df = pd.DataFrame(result, columns=cursor.column_names)
                result_text.delete(1.0, tk.END)
                result_text.insert(tk.END, df.to_string())
            else:
                result_text.delete(1.0, tk.END)
                result_text.insert(tk.END, "查询成功，但没有返回结果。")
        except Error as e:
            messagebox.showerror("错误", f"查询执行失败: {e}")

# 打开设置窗口
def open_settings():
    settings_window = tk.Toplevel(root)
    settings_window.title("设置")
    settings_window.geometry("300x200")

    # 主机名
    host_label = tk.Label(settings_window, text="主机名:")
    host_label.grid(row=0, column=0, padx=10, pady=10)
    host_entry = tk.Entry(settings_window)
    host_entry.grid(row=0, column=1, padx=10, pady=10)
    host_entry.insert(0, db_config['host'])

    # 端口号
    port_label = tk.Label(settings_window, text="端口号:")
    port_label.grid(row=1, column=0, padx=10, pady=10)
    port_entry = tk.Entry(settings_window)
    port_entry.grid(row=1, column=1, padx=10, pady=10)
    port_entry.insert(0, db_config['port'])

    # 用户名
    user_label = tk.Label(settings_window, text="用户名:")
    user_label.grid(row=2, column=0, padx=10, pady=10)
    user_entry = tk.Entry(settings_window)
    user_entry.grid(row=2, column=1, padx=10, pady=10)
    user_entry.insert(0, db_config['user'])

    # 密码
    password_label = tk.Label(settings_window, text="密码:")
    password_label.grid(row=3, column=0, padx=10, pady=10)
    password_entry = tk.Entry(settings_window, show="*")
    password_entry.grid(row=3, column=1, padx=10, pady=10)
    password_entry.insert(0, db_config['password'])

    # 保存设置
    def save_settings():
        global db_config
        db_config['host'] = host_entry.get()
        db_config['port'] = int(port_entry.get())
        db_config['user'] = user_entry.get()
        db_config['password'] = password_entry.get()

        # 关闭当前连接
        close_db()

        # 重新连接数据库并刷新列表
        connect_db()

        messagebox.showinfo("成功", "设置已保存并刷新数据库列表！")
        settings_window.destroy()

    save_button = tk.Button(settings_window, text="保存", command=save_settings)
    save_button.grid(row=4, column=0, columnspan=2, pady=10)

# GUI布局
menu_bar = tk.Menu(root)
root.config(menu=menu_bar)

settings_menu = tk.Menu(menu_bar, tearoff=0)
settings_menu.add_command(label="设置", command=open_settings)
menu_bar.add_cascade(label="选项", menu=settings_menu)

left_frame = tk.Frame(root)
left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)

right_frame = tk.Frame(root)
right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)

# 左侧树形结构
tree = ttk.Treeview(left_frame)
tree.pack(fill=tk.BOTH, expand=True)
tree["columns"] = ("type",)
tree.column("#0", width=200)
tree.column("type", width=50)
tree.heading("#0", text="数据库/表")
tree.heading("type", text="类型")
tree.bind("<Double-1>", show_table_data_or_structure)

# 右侧查询输入
query_label = tk.Label(right_frame, text="输入SQL查询:")
query_label.pack(pady=5)

query_entry = tk.Text(right_frame, height=5, width=70)
query_entry.pack(pady=5)

execute_button = tk.Button(right_frame, text="执行查询", command=execute_query)
execute_button.pack(pady=5)

# 切换显示按钮
toggle_button = tk.Button(right_frame, text="显示表结构", command=toggle_display)
toggle_button.pack(pady=5)

result_label = tk.Label(right_frame, text="查询结果:")
result_label.pack(pady=5)

result_text = tk.Text(right_frame, height=20, width=70)
result_text.pack(pady=5)

# 初始连接数据库
connect_db()

# 运行主循环
root.mainloop()