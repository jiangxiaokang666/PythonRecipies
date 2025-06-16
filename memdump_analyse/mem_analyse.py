import re
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog , messagebox , ttk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import pandas as pd
import seaborn as sns
from typing import List, Dict, Optional


class MemoryMapper:
    def __init__(self):
        self.blocks = []
        self.summary = {}
        self.total_memory = 0
        self.total_free = 0
        self.total_used = 0

    def parse_memory_output(self, text:str)->None:
        lines = text.strip().split('\n')
        current_parent = None

        for line in lines:
            if not line or 'BeginMemOutput' in line:
                continue
            
            if 'EndMemOutput' in line:
                break
            
            main_match = re.match(r'^([0-9a-fA-F]+)\s+(\w+)\s+(\d+)',line)
            child_match = re.match(r'\s+([0-9a-fA-F]+)\s+(\w+)\s+(\d+)',line)

            if main_match:
                start = int(main_match.group(1),16)
                mem_type = main_match.group(2)
                size = int(main_match.group(3))
                end = start + size

                parent_block = {
                    'type':mem_type,
                    'start':start,
                    'end':end,
                    'size':size,
                    'children':[]
                }

                self.blocks.append(parent_block)
                current_parent = parent_block

                if mem_type == 'Free':
                    self.total_free += size
                else:
                    self.total_used += size
                
                self.summary[mem_type] = self.summary.get(mem_type,0) + size

            elif child_match and current_parent:
                start = int(child_match.group(1),16)
                mem_type = child_match.group(2)
                size = int(child_match.group(3))
                end = start + size

                child_block = {
                    'type':mem_type,
                    'start':start,
                    'end':end,
                    'size':size
                }
                current_parent['children'].append(child_block)

        self.total_memory = self.total_used + self.total_free

    def query_type(self, type_name: str)->List[Dict]:
        return [block for block in self.blocks if block['type'] == type_name]

class MemoryMapperGUI:
    def __init__(self,root):
        self.root = root
        self.root.title('内存映射分析工具')
        self.mapper = MemoryMapper()
        import matplotlib.pyplot as plt
        plt.rcParams['font.sans-serif'] = ['SimHei']
        plt.rcParams['axes.unicode_minus'] = False

        self.create_widgets()
    
    def create_widgets(self):

        self.bie_frame = tk.Frame(root)

        self.load_button = tk.Button(self.bie_frame,text='点击加载内存映射文件',command=self.load_file)
        self.load_button.pack(pady=10)

        self.figure = plt.Figure(figsize=(8,5), dpi=100)
        self.ax = self.figure.add_subplot(111)
        self.ax.set_xticks([])  # 移除x轴的刻度
        self.ax.set_yticks([])  # 移除y轴的刻度
        self.ax.set_xticklabels([])  # 移除x轴的标签
        self.ax.set_yticklabels([])  # 移除y轴的标签
        self.ax.set_xlabel('')  # 清空x轴标签文本
        self.ax.set_ylabel('')  # 清空y轴标签文本
        self.ax.spines['top'].set_visible(False)    # 隐藏顶部边框线
        self.ax.spines['right'].set_visible(False)  # 隐藏右侧边框线
        self.ax.spines['bottom'].set_visible(False) # 隐藏底部边框线
        self.ax.spines['left'].set_visible(False)   # 隐藏左侧边框线

        self.canvas = FigureCanvasTkAgg(self.figure, master=self.bie_frame)
        self.canvas.get_tk_widget().pack(side='left',fill='both',expand=True)
        self.bie_frame.pack(side='left',fill='both',expand=True)

        self.tree_frame = tk.Frame(root)
        self.tree = ttk.Treeview(self.tree_frame,columns=('Start','Size'),
                                  show='tree headings')

        self.tree.heading('#0',text='名称')
        self.tree.heading('Start',text='起始地址')
        self.tree.heading('Size', text='大小')

        self.tree.column('#0',width=150,anchor='w')
        self.tree.column('Start', width=200, anchor='w')
        self.tree.column('Size', width=100, anchor='e')


        self.scrollbar = ttk.Scrollbar(self.tree_frame,orient='vertical',command=self.tree.yview)
        self.tree.configure(yscrollcommand=self.scrollbar.set)

        self.tree.pack(side='left',fill='both',expand=True)
        self.tree_frame.pack(side='right', fill='y')

    def load_file(self):
        filename = filedialog.askopenfilename(filetypes=[("Text files","*.txt")])
        if not filename:
            return
        
        try:
            with open(filename,"r",encoding="GBK") as f:
                content = f.read()
            self.mapper.parse_memory_output(content)
            self.update_chart()
            self.update_tree_view()
        except Exception as e:
            messagebox.showerror("错误",f"加载文件失败：{e}")

    def update_chart(self):
        df = pd.DataFrame(self.mapper.summary.items(), columns=["Type","Size"])
        df = df[df['Size']>0]
        df = df.sort_values(by="Size",ascending=False)

        self.ax.clear()

        patches, texts, _ = self.ax.pie(
            x = df['Size'],
            labels=df['Type'],
            startangle=90, 
            radius=1.0,
            wedgeprops=dict(width=0.4),
            autopct='%1.1f%%',
            textprops={'fontsize':8},
            pctdistance=0.85,
        )
        plt.setp(texts, fontsize=8)
        self.ax.axis('equal')
        self.ax.set_title('内存类型分布',fontsize=14)

        self.canvas.draw()

    def update_tree_view(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        grouped = {}
        for block in self.mapper.blocks:
            mem_type = block['type']
            if mem_type not in grouped:
                grouped[mem_type] = {
                    'total_size':0,
                    'blocks':[]
                }
            grouped[mem_type]['total_size']+= block['size']
            grouped[mem_type]['blocks'].append(block)

        # 插入数据
        for idx, (mem_type, data) in enumerate(grouped.items()):
            total_size_str = get_memory_str(data['total_size'])

            # 第一级：内存类型
            type_item = self.tree.insert(
                '', 'end',
                iid=f"type_{idx}",
                text=f"{mem_type} ({total_size_str})",
                values=('', ''),
                open=False,
                tags=('parent',)
            )

            # 第二级：主块地址段
            for block_idx, block in enumerate(data['blocks']):
                start = hex(block['start'])
                size = get_memory_str(block['size'])

                main_item = self.tree.insert(
                    type_item, 'end',
                    iid=f"main_{idx}_{block_idx}",
                    text=start,
                    values=(start, size),
                    open=False,
                    tags=('parent',)
                )

                # 第三级：子块信息，横向显示 Start 和 Size
                for child_idx, child in enumerate(block['children']):
                    child_start = hex(child['start'])
                    child_size = get_memory_str(child['size'])

                    self.tree.insert(
                        main_item, 'end',
                        iid=f"child_{idx}_{block_idx}_{child_idx}",
                        text="子段",
                        values=(child_start, child_size)
                    )

def get_memory_str(size_bytes:int)->str :
    if size_bytes == 0:
        return "0B"

    units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
    i = 0
    while size_bytes >= 1024 and i < len(units) - 1:
        size_bytes /= 1024
        i += 1

    return f"{size_bytes:.2f}{units[i]}"


# def test_load_file(filename:str):
#     try:
#         with open(filename,'r',encoding='GBK') as f:
#             content = f.read()
#             mapper = MemoryMapper()
#             mapper.parse_memory_output(content)
#             print('%s %s %s '%(get_memory_str(mapper.total_memory), get_memory_str(mapper.total_used), get_memory_str(mapper.total_free)))
#     except Exception as e:
#         print('exception path = %s msg = %s' % (filename,e))    

if __name__ == '__main__':
    # test_load_file(r'./MemDump.txt')
    root = tk.Tk()
    app = MemoryMapperGUI(root)
    root.mainloop()