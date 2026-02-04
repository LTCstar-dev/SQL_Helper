import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import mysql.connector
from mysql.connector import Error
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# 创建主窗口
root = tk.Tk()
root.title("SQL Helper!")
root.geometry("1000x600")

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


# 插入数据
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


# 图表生成功能
def generate_chart():
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
        df = pd.DataFrame(result, columns=cursor.column_names)
    except Error as e:
        messagebox.showerror("错误", f"获取表数据失败: {e}")
        return

    # 弹出图表生成窗口
    chart_window = tk.Toplevel(root)
    chart_window.title("生成图表")
    chart_window.geometry("1000x900")

    # 选择图表类型
    tk.Label(chart_window, text="选择图表类型：").grid(row=0, column=0, padx=10, pady=10)
    chart_type_var = tk.StringVar(value="柱状图")  # 默认柱状图
    chart_type_menu = ttk.Combobox(chart_window, textvariable=chart_type_var, values=["柱状图", "折线图", "饼图"])
    chart_type_menu.grid(row=0, column=1, padx=10, pady=10)

    # 选择 X 轴
    tk.Label(chart_window, text="选择 X 轴：").grid(row=1, column=0, padx=10, pady=10)
    x_axis_var = tk.StringVar()
    x_axis_menu = ttk.Combobox(chart_window, textvariable=x_axis_var, values=df.columns.tolist())
    x_axis_menu.grid(row=1, column=1, padx=10, pady=10)

    # 选择 Y 轴
    tk.Label(chart_window, text="选择 Y 轴：").grid(row=2, column=0, padx=10, pady=10)
    y_axis_var = tk.StringVar()
    y_axis_menu = ttk.Combobox(chart_window, textvariable=y_axis_var, values=df.columns.tolist())
    y_axis_menu.grid(row=2, column=1, padx=10, pady=10)

    # 是否排序复选框
    sort_enabled_var = tk.BooleanVar(value=False)
    sort_check = tk.Checkbutton(chart_window, text="是否启用排序", variable=sort_enabled_var)
    sort_check.grid(row=3, column=0, columnspan=2, pady=5)

    # 排序方式选择
    tk.Label(chart_window, text="选择排序方式：").grid(row=4, column=0, padx=10, pady=10)
    sort_order_var = tk.StringVar(value="升序")  # 默认升序
    sort_order_menu = ttk.Combobox(chart_window, textvariable=sort_order_var, values=["升序", "降序"])
    sort_order_menu.grid(row=4, column=1, padx=10, pady=10)

    # 生成图表函数
    def plot_chart():
        chart_type = chart_type_var.get()
        x_axis = x_axis_var.get()
        y_axis = y_axis_var.get()
        sort_enabled = sort_enabled_var.get()
        sort_order = sort_order_var.get()

        if not x_axis or not y_axis:
            messagebox.showwarning("警告", "请选择 X 轴和 Y 轴！")
            return

        try:
            # 复制 DataFrame，避免修改原数据
            df_copy = df.copy()

            # 确保 X 和 Y 轴是数值类型
            df_copy[x_axis] = pd.to_numeric(df_copy[x_axis], errors='coerce')
            df_copy[y_axis] = pd.to_numeric(df_copy[y_axis], errors='coerce')

            # 处理 NaN 值
            if df_copy[x_axis].isnull().any() or df_copy[y_axis].isnull().any():
                messagebox.showerror("错误", "所选列包含无效数据，请检查数据格式")
                return

            # 如果启用排序，则按照用户选择进行排序
            if sort_enabled:
                df_copy = df_copy.sort_values(by=x_axis, ascending=(sort_order == "升序"))

            # 创建 Matplotlib 图表
            fig, ax = plt.subplots()

            if chart_type == "柱状图":
                df_copy.plot(kind="bar", x=x_axis, y=y_axis, ax=ax)
            elif chart_type == "折线图":
                # **确保按 DataFrame 原始顺序绘制，不让 Matplotlib 自动排序**
                ax.plot(df_copy[y_axis].values, marker="o", linestyle="-")
                ax.set_xticks(range(len(df_copy)))  # 设置 X 轴为索引顺序
                ax.set_xticklabels(df_copy[x_axis].astype(str).values, rotation=45)  # 用原始 X 轴值作为标签
                ax.set_xlabel(x_axis)
                ax.set_ylabel(y_axis)
            elif chart_type == "饼图":
                df_copy.plot(kind="pie", y=y_axis, labels=df_copy[x_axis], ax=ax, autopct="%1.1f%%")

            plt.title(f"{chart_type}")
            plt.tight_layout()

            # 在 Tkinter 窗口中显示图表
            chart_canvas = FigureCanvasTkAgg(fig, master=chart_window)
            chart_canvas.draw()
            chart_canvas.get_tk_widget().grid(row=6, column=0, columnspan=2, padx=10, pady=10)

        except Exception as e:
            messagebox.showerror("错误", f"生成图表失败: {e}")

    # 绘制图表按钮
    plot_button = tk.Button(chart_window, text="绘制图表", command=plot_chart)
    plot_button.grid(row=5, column=0, columnspan=2, pady=10)

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

# 操作按钮
button_frame = tk.Frame(right_frame)
button_frame.pack(pady=5)

insert_button = tk.Button(button_frame, text="插入", command=insert_data)
insert_button.grid(row=0, column=0, padx=5)

update_button = tk.Button(button_frame, text="更新", command=update_data)
update_button.grid(row=0, column=1, padx=5)

delete_button = tk.Button(button_frame, text="删除", command=delete_data)
delete_button.grid(row=0, column=2, padx=5)

# 图表生成按钮
chart_button = tk.Button(right_frame, text="生成图表", command=generate_chart)
chart_button.pack(pady=5)

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
