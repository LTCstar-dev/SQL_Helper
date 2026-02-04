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

    # 控件布局
    # 第一行：图表类型
    ttk.Label(chart_window, text="图表类型：").grid(row=0, column=0, padx=10, pady=5, sticky='e')
    ttk.Combobox(
        chart_window,
        textvariable=chart_type_var,
        values=["柱状图", "折线图", "饼图"]
    ).grid(row=0, column=1, padx=10, pady=5, sticky='w')

    # 第二行：X轴选择
    ttk.Label(chart_window, text="X 轴：").grid(row=1, column=0, padx=10, pady=5, sticky='e')
    ttk.Combobox(
        chart_window,
        textvariable=x_axis_var,
        values=df.columns.tolist()
    ).grid(row=1, column=1, padx=10, pady=5, sticky='w')

    # 第三行：Y轴选择
    ttk.Label(chart_window, text="Y 轴：").grid(row=2, column=0, padx=10, pady=5, sticky='e')
    ttk.Combobox(
        chart_window,
        textvariable=y_axis_var,
        values=df.columns.tolist()
    ).grid(row=2, column=1, padx=10, pady=5, sticky='w')

    # 第四行：排序设置
    ttk.Checkbutton(
        chart_window,
        text="启用排序",
        variable=sort_enabled_var
    ).grid(row=3, column=0, padx=10, pady=5, sticky='e')
    ttk.Combobox(
        chart_window,
        textvariable=sort_order_var,
        values=["升序", "降序"],
        state="readonly"
    ).grid(row=3, column=1, padx=10, pady=5, sticky='w')

    # 第五行：样式设置
    ttk.Label(chart_window, text="线条样式：").grid(row=4, column=0, padx=10, pady=5, sticky='e')
    ttk.Combobox(
        chart_window,
        textvariable=line_style_var,
        values=["实线", "虚线", "点线"],
        state="readonly"
    ).grid(row=4, column=1, padx=10, pady=5, sticky='w')

    ttk.Label(chart_window, text="颜色主题：").grid(row=5, column=0, padx=10, pady=5, sticky='e')
    ttk.Combobox(
        chart_window,
        textvariable=color_theme_var,
        values=["默认", "深色", "彩色"],
        state="readonly"
    ).grid(row=5, column=1, padx=10, pady=5, sticky='w')

    # 第六行：显示选项
    ttk.Checkbutton(
        chart_window,
        text="显示图例",
        variable=show_legend_var
    ).grid(row=6, column=0, padx=10, pady=5)
    ttk.Checkbutton(
        chart_window,
        text="显示网格",
        variable=show_grid_var
    ).grid(row=6, column=1, padx=10, pady=5)
    ttk.Checkbutton(
        chart_window,
        text="显示数据标签",
        variable=show_labels_var
    ).grid(row=7, column=0, columnspan=2, padx=10, pady=5)

    # 初始渲染
    update_chart()


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

# 在GUI布局部分添加一个“刷新”按钮
refresh_button = tk.Button(right_frame, text="刷新数据库", command=load_databases)
refresh_button.pack(pady=5)

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
