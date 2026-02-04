import tkinter as tk
from tkinter import ttk, messagebox
import mysql.connector
from mysql.connector import Error
import pandas as pd

# 创建主窗口
root = tk.Tk()
root.title("MySQL数据库工具")
root.geometry("800x600")

# 数据库连接配置
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'root',
    'port': 3307
}

# 全局变量
conn = None
current_db = None

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

# 加载所有数据库
def load_databases():
    if conn:
        try:
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

# 显示表结构
def show_table_structure(event):
    selected_item = tree.selection()[0]
    item_type = tree.item(selected_item, "values")[0]
    if item_type == "Table":
        db_name = tree.item(tree.parent(selected_item), "text")
        table_name = tree.item(selected_item, "text")
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute(f"USE {db_name}")
                cursor.execute(f"DESCRIBE {table_name}")
                result = cursor.fetchall()
                df = pd.DataFrame(result, columns=["Field", "Type", "Null", "Key", "Default", "Extra"])
                result_text.delete(1.0, tk.END)
                result_text.insert(tk.END, df.to_string())
            except Error as e:
                messagebox.showerror("错误", f"获取表结构失败: {e}")

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

# GUI布局
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
tree.bind("<Double-1>", show_table_structure)

# 右侧查询输入
query_label = tk.Label(right_frame, text="输入SQL查询:")
query_label.pack(pady=5)

query_entry = tk.Text(right_frame, height=5, width=70)
query_entry.pack(pady=5)

execute_button = tk.Button(right_frame, text="执行查询", command=execute_query)
execute_button.pack(pady=5)

result_label = tk.Label(right_frame, text="查询结果:")
result_label.pack(pady=5)

result_text = tk.Text(right_frame, height=20, width=70)
result_text.pack(pady=5)

# 连接数据库
connect_db()

# 运行主循环
root.mainloop()