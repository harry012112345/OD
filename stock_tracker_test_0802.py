import pandas as pd 
import requests 
from bs4 import BeautifulSoup
import sqlite3
import twstock
from twstock import Stock
import time
import os


url = "https://isin.twse.com.tw/isin/C_public.jsp?strMode=2" 
res = requests.get(url)
soup = BeautifulSoup(res.text, "lxml") 
tr = soup.findAll('tr')

tds = []
for raw in tr:
    data = [td.get_text() for td in raw.findAll("td")]
    if len(data) == 7:
        tds.append(data)

df = pd.DataFrame(tds[1:],columns=tds[0])
df.rename(columns={'有價證券代號及名稱 ': '有價證券代號及名稱'}, inplace=True)
df[['有價證券代號', '名稱']] = df['有價證券代號及名稱'].str.split('　', expand=True)
df.drop(columns=['有價證券代號及名稱'], inplace=True)
cols = ['有價證券代號', '名稱'] + [col for col in df.columns if col not in ['有價證券代號', '名稱']]
df = df[cols]
df['上市日'] = pd.to_datetime(df['上市日'], format='%Y/%m/%d', errors='coerce')



# 連接到 SQLite 資料庫（如果不存在則會自動創建）
conn = sqlite3.connect('taiwanese_stock_overview.db')

# 將 DataFrame 儲存到 SQLite 中
df.to_sql('taiwanese_stock_overview', conn, if_exists='replace', index=False)

# 確認資料是否成功存入
cursor = conn.cursor()
cursor.execute("SELECT * FROM taiwanese_stock_overview")
rows = cursor.fetchall()
for row in rows:
    print(row)

# 關閉資料庫連接
conn.close()


# 連接到 SQLite 資料庫
conn = sqlite3.connect('taiwanese_stock_overview.db')
# 建立游標物件
cursor = conn.cursor()
# 使用 PRAGMA 查詢表格的欄位資訊
cursor.execute("PRAGMA table_info(taiwanese_stock_overview)")
# 獲取所有欄位資訊
columns_info = cursor.fetchall()
# 初始化一個空的列表來存儲欄位名稱
column_names = []
# 遍歷每個欄位的資訊元組
for info in columns_info:
    # info[1] 是欄位名稱，將其加入列表
    column_names.append(info[1])
# 關閉資料庫連接
conn.close()
# 顯示欄位名稱
print(column_names)


# 連接到 SQLite 資料庫
conn = sqlite3.connect('taiwanese_stock_overview.db')

# 建立游標物件
cursor = conn.cursor()

# 執行 SQL 查詢來獲取 "名稱" 欄位
cursor.execute("SELECT 名稱 FROM taiwanese_stock_overview")
# 獲取所有查詢結果
rows_name = cursor.fetchall()

# 初始化一個空的列表來存儲名稱
stock_names = []
# 遍歷查詢結果，將每一行的名稱加入列表
for row in rows_name:
    stock_names.append(row[0])

# 執行 SQL 查詢來獲取 "有價證券代號" 欄位
cursor.execute("SELECT 有價證券代號 FROM taiwanese_stock_overview")
rows_code = cursor.fetchall()    

# 初始化一個空的列表來存儲有價證券代號
stock_codes = []
# 遍歷查詢結果，將每一行的有價證券代號加入列表
for row in rows_code:
    stock_codes.append(row[0])

# 關閉資料庫連接
conn.close()

# 顯示結果
# print("Stock Names:", stock_names)
# print("Stock Codes:", stock_codes)

# 假設 stock_names 和 stock_codes 都是包含字符串的列表
stock_names = stock_names[0:1000]
stock_names = [name.strip() for name in stock_names]
stock_codes = stock_codes[0:1000]
stock_codes = [code.strip() for code in stock_codes]



# 取得所有可用的股票代號
available_codes = twstock.codes.keys()
need_to_remove_index = []
# 遍歷 stock_codes 中的每一個代號
for index, code in enumerate(stock_codes):
    # 檢查代號是否存在於 available_codes 中
    if code not in available_codes:
        print(f"代號 {code} 在索引 {index} 不存在於 available_codes 中")
        need_to_remove_index.append(index)
need_to_remove_index.reverse()


for item in need_to_remove_index:
    del stock_names[item]
    del stock_codes[item]
    
    
available_codes = twstock.codes.keys()
need_to_remove_index = []
# 遍歷 stock_codes 中的每一個代號
for index, code in enumerate(stock_codes):
    # 檢查代號是否存在於 available_codes 中
    if code not in available_codes:
        print(f"代號 {code} 在索引 {index} 不存在於 available_codes 中")
        need_to_remove_index.append(index)
if need_to_remove_index == []:
    print('吻合！')

    
    

target_year = 2020
target_month = 7
all_time_start = time.time()
for names, codes in zip(stock_names, stock_codes):
    success = False
    while not success:
        try:
            start_time = time.time()  # 計算開始時間
            print(names+codes)
            stock = Stock(codes)
            
            # 計算下載數據時間
            data_fetch_start = time.time()
            data = stock.fetch_from(target_year, target_month)
            data_fetch_end = time.time()
            data_dict = {
                'date': [],
                'capacity': [],
                'turnover': [],
                'open': [],
                'high': [],
                'low': [],
                'close': [],
                'change': [],
                'transa': [],
                '5_ma': [],
                '5_bias': [],
                '5_capacity': [],
                '10_ma': [],
                '10_bias': [],
                '10_capacity': [],
                '20_ma': [],
                '20_bias': [],
                '20_capacity': [],
                '30_ma': [],
                '30_bias': [],
                '30_capacity': [],
                '90_ma': [],
                '90_bias': [],
                '90_capacity': [],
                '180_ma': [],
                '180_bias': [],
                '180_capacity': [],
                '365_ma': [],
                '365_bias': [],
                '365_capacity': []
            }

            for i in range(len(data)):
                data_dict['date'].append(data[i].date.strftime('%Y-%m-%d'))
                data_dict['capacity'].append(data[i].capacity)
                data_dict['turnover'].append(data[i].turnover)
                data_dict['open'].append(data[i].open)
                data_dict['high'].append(data[i].high)
                data_dict['low'].append(data[i].low)
                data_dict['close'].append(data[i].close)
                data_dict['change'].append(data[i].change)
                data_dict['transa'].append(data[i].transaction)

            if all(value is None for value in data_dict['close']):
                data_dict['close'] = [1] * len(data_dict['close'])
            elif all(value == 0 for value in data_dict['close']):
                data_dict['close'] = [1] * len(data_dict['close'])
            else:
                # 從右往左找到第一個非 None 的值
                last_non_none_value = None
                for index in range(len(data_dict['close']) - 1, -1, -1):
                    if data_dict['close'][index] is not None:
                        last_non_none_value = data_dict['close'][index]
                    elif last_non_none_value is not None:
                        data_dict['close'][index] = last_non_none_value

                # 從左往右填充剩餘的 None 值為 0
                for index in range(len(data_dict['close'])):
                    if data_dict['close'][index] is None:
                        data_dict['close'][index] = 1

            # 計算移動平均值和偏差時間
            ma_calc_start = time.time()
            for i in range(len(data)):
                if i >= (5 - 1):
                    data_dict['5_ma'].append(sum(data_dict['close'][i-4:i+1])/5)
                    data_dict['5_bias'].append(round((data_dict['close'][i] - data_dict['5_ma'][i])*1000 / data_dict['5_ma'][i], 2))
                    data_dict['5_capacity'].append(stock.moving_average(stock.capacity, 5)[i-4])
                else:
                    data_dict['5_ma'].append(0)
                    data_dict['5_bias'].append(0)
                    data_dict['5_capacity'].append(0)

                if i >= (10 - 1):
                    data_dict['10_ma'].append(sum(data_dict['close'][i-9:i+1])/10)
                    data_dict['10_bias'].append((data_dict['close'][i] - data_dict['10_ma'][i])/data_dict['10_ma'][i])
                    data_dict['10_capacity'].append(stock.moving_average(stock.capacity, 10)[i-9])
                else:
                    data_dict['10_ma'].append(0)
                    data_dict['10_bias'].append(0)
                    data_dict['10_capacity'].append(0)

                if i >= (20 - 1):
                    data_dict['20_ma'].append(sum(data_dict['close'][i-19:i+1])/20)
                    data_dict['20_bias'].append((data_dict['close'][i] - data_dict['20_ma'][i])/data_dict['20_ma'][i])
                    data_dict['20_capacity'].append(stock.moving_average(stock.capacity, 20)[i-19])
                else:
                    data_dict['20_ma'].append(0)
                    data_dict['20_bias'].append(0)
                    data_dict['20_capacity'].append(0)

                if i >= (30 - 1):
                    data_dict['30_ma'].append(sum(data_dict['close'][i-29:i+1])/30)
                    data_dict['30_bias'].append((data_dict['close'][i] - data_dict['30_ma'][i])/data_dict['30_ma'][i])
                    data_dict['30_capacity'].append(stock.moving_average(stock.capacity, 30)[i-29])
                else:
                    data_dict['30_ma'].append(0)
                    data_dict['30_bias'].append(0)
                    data_dict['30_capacity'].append(0)

                if i >= (90 - 1):
                    data_dict['90_ma'].append(sum(data_dict['close'][i-89:i+1])/90)
                    data_dict['90_bias'].append((data_dict['close'][i] - data_dict['90_ma'][i])/data_dict['90_ma'][i])
                    data_dict['90_capacity'].append(stock.moving_average(stock.capacity, 90)[i-89])
                else:
                    data_dict['90_ma'].append(0)
                    data_dict['90_bias'].append(0)
                    data_dict['90_capacity'].append(0)

                if i >= (180 - 1):
                    data_dict['180_ma'].append(sum(data_dict['close'][i-179:i+1])/180)
                    data_dict['180_bias'].append((data_dict['close'][i] - data_dict['180_ma'][i])/data_dict['180_ma'][i])
                    data_dict['180_capacity'].append(stock.moving_average(stock.capacity, 180)[i-179])
                else:
                    data_dict['180_ma'].append(0)
                    data_dict['180_bias'].append(0)
                    data_dict['180_capacity'].append(0)

                if i >= (365 - 1):
                    data_dict['365_ma'].append(sum(data_dict['close'][i-364:i+1])/365)
                    data_dict['365_bias'].append((data_dict['close'][i] - data_dict['365_ma'][i])/data_dict['365_ma'][i])
                    data_dict['365_capacity'].append(stock.moving_average(stock.capacity, 365)[i-364])
                else:
                    data_dict['365_ma'].append(0)
                    data_dict['365_bias'].append(0)
                    data_dict['365_capacity'].append(0)
            for k in range(len(data_dict['close'])):
                data_dict['5_ma'][k] = round(data_dict['5_ma'][k],2)
                data_dict['10_ma'][k] = round(data_dict['10_ma'][k],2)
                data_dict['20_ma'][k] = round(data_dict['20_ma'][k],2)
                data_dict['30_ma'][k] = round(data_dict['30_ma'][k],2)
                data_dict['90_ma'][k] = round(data_dict['90_ma'][k],2)
                data_dict['180_ma'][k] = round(data_dict['180_ma'][k],2)
                data_dict['365_ma'][k] = round(data_dict['365_ma'][k],2)

                data_dict['5_bias'][k] = round(data_dict['5_bias'][k]*1000,2)
                data_dict['10_bias'][k] = round(data_dict['10_bias'][k]*1000,2)
                data_dict['20_bias'][k] = round(data_dict['20_bias'][k]*1000,2)
                data_dict['30_bias'][k] = round(data_dict['30_bias'][k]*1000,2)
                data_dict['90_bias'][k] = round(data_dict['90_bias'][k]*1000,2)
                data_dict['180_bias'][k] = round(data_dict['180_bias'][k]*1000,2)
                data_dict['365_bias'][k] = round(data_dict['365_bias'][k]*1000,2)

            ma_calc_end = time.time()

            # 确保存储数据库的文件夹存在
            database_folder = 'taiwanese_stock_database'
            if not os.path.exists(database_folder):
                os.makedirs(database_folder)

            # 計算存儲數據到數據庫的時間
            db_store_start = time.time()

            # 使用完整路径创建数据库文件
            db_filename = os.path.join(database_folder, f"{codes}.db")  # 每個股票使用一個單獨的文件
            conn = sqlite3.connect(db_filename)
            cursor = conn.cursor()
            cursor.execute(f'''
                CREATE TABLE IF NOT EXISTS stock_data (
                    date TEXT PRIMARY KEY,
                    capacity INTEGER,
                    turnover INTEGER,
                    open REAL,
                    high REAL,
                    low REAL,
                    close REAL,
                    change REAL,
                    transa INTEGER,
                    ma5 REAL,
                    bias5 REAL,
                    capacity_ma5 REAL,
                    ma10 REAL,
                    bias10 REAL,
                    capacity_ma10 REAL,
                    ma20 REAL,
                    bias20 REAL,
                    capacity_ma20 REAL,
                    ma30 REAL,
                    bias30 REAL,
                    capacity_ma30 REAL,
                    ma90 REAL,
                    bias90 REAL,
                    capacity_ma90 REAL,
                    ma180 REAL,
                    bias180 REAL,
                    capacity_ma180 REAL,
                    ma365 REAL,
                    bias365 REAL,
                    capacity_ma365 REAL
                )
            ''')

            for j in range(len(data_dict['date'])):
                cursor.execute(f'''
                    INSERT OR IGNORE INTO stock_data (date, capacity, turnover, open, high, low, close, change, transa, ma5, bias5, capacity_ma5, ma10, bias10, capacity_ma10, ma20, bias20, capacity_ma20, ma30, bias30, capacity_ma30, ma90, bias90, capacity_ma90, ma180, bias180, capacity_ma180, ma365, bias365, capacity_ma365)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    data_dict['date'][j],
                    data_dict['capacity'][j],
                    data_dict['turnover'][j],
                    data_dict['open'][j],
                    data_dict['high'][j],
                    data_dict['low'][j],
                    data_dict['close'][j],
                    data_dict['change'][j],
                    data_dict['transa'][j],
                    data_dict['5_ma'][j],
                    data_dict['5_bias'][j],
                    data_dict['5_capacity'][j],
                    data_dict['10_ma'][j],
                    data_dict['10_bias'][j],
                    data_dict['10_capacity'][j],
                    data_dict['20_ma'][j],
                    data_dict['20_bias'][j],
                    data_dict['20_capacity'][j],
                    data_dict['30_ma'][j],
                    data_dict['30_bias'][j],
                    data_dict['30_capacity'][j],
                    data_dict['90_ma'][j],
                    data_dict['90_bias'][j],
                    data_dict['90_capacity'][j],
                    data_dict['180_ma'][j],
                    data_dict['180_bias'][j],
                    data_dict['180_capacity'][j],
                    data_dict['365_ma'][j],
                    data_dict['365_bias'][j],
                    data_dict['365_capacity'][j]
                ))

            conn.commit()
            conn.close()
            db_store_end = time.time()

            end_time = time.time()
            total_time = end_time - start_time
            fetch_time = data_fetch_end - data_fetch_start
            ma_calc_time = ma_calc_end - ma_calc_start
            db_store_time = db_store_end - db_store_start

            print(f"{names+codes}資料已成功儲存到 stock_data.db 資料庫。")
            print(f"總時間: {total_time:.2f} 秒")
            print(f"下載數據時間: {fetch_time:.2f} 秒")
            print(f"計算移動平均值和偏差時間: {ma_calc_time:.2f} 秒")
            print(f"存儲數據到數據庫時間: {db_store_time:.2f} 秒")

            success = True
        except Exception as e:
            print(f"錯誤: {e}，重新嘗試中...")

all_time_end = time.time()
print('------------------------------')
print(f'all_time:{all_time_end - all_time_start}秒')