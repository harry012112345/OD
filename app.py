from flask import Flask, request, render_template, jsonify, send_file, redirect, url_for,flash,session
from flask_restful import Api, Resource
from flask_cors import CORS  # 导入CORS
from flask_socketio import SocketIO, emit
import pandas as pd
import json
import requests
import csv
import io
import os
import datetime
import time
import asyncio
import aiohttp
from threading import Thread

app = Flask(__name__,static_folder='templates',template_folder='templates')
# socketio = SocketIO(app)

CORS(app)  # 启用CORS
socketio = SocketIO(app, cors_allowed_origins="*")  # 允许所有来源连接


current_path = os.getcwd()
additional_path = "test_excel"
output = "output"
UPLOAD_FOLDER = os.path.join(current_path, additional_path)
DOWNLOAD_FOLDER = os.path.join(current_path, output)

# 用於儲存上傳的數據
received_data = []

global_dut_ip=[]
global_arm_ip=[]
global_sb_ip=[]
global_unet_ip=[]

global_dut_delay=0

temperature_max=0
temperature_min=0
humidity_max=0
humidity_min=0
detect_axis=''
execute_excel=[]

log_arm_data=[]
log_dut_data=[]
log_sb_data=[]
log_unet_data=[]

server_dead_flag=True
detect_flag=False
return_flag=False
detect_confirm_flag=False
stop_processing = False
end_processing=False
app.secret_key = 'your_secret_key'
users = {'admin': 'admin'}
now = datetime.datetime.now()
formatted_time = now.strftime('%Y-%m-%d %H:%M:%S')
local_ip='192.168.15.108'
server_ips = [f'http://{global_dut_ip}/get_info', f'http://{global_arm_ip}/get_info', f'http://{global_sb_ip}/get_info', f'http://{global_unet_ip}/get_info']




def save_excel_to_folder(excel_data, file_name):
    """
    参数:
    - file_path (str): 主文件夹路径。
    - excel_data (pd.DataFrame): 要保存的数据。
    - file_name (str): Excel 文件名，默认是 'data.xlsx'。
    """

    if not os.path.exists(DOWNLOAD_FOLDER):
        os.makedirs(DOWNLOAD_FOLDER)

    # 保存 Excel 文件到目标文件夹
    excel_full_path = os.path.join(DOWNLOAD_FOLDER, file_name)
    excel_data.to_excel(excel_full_path, index=False)
    print(f"Excel 文件已保存到 {excel_full_path}")





async def check_connection(name, ip):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(ip) as response:
                if response.status != 200:
                    return {name: 'Not connected'}
                return {name: 'Connected'}
    except Exception as e:
        print(f"Request failed for {ip} with exception: {e}")
        return {name: 'Not connected'}

async def check_all_connections(server_ips):
    tasks = [check_connection(name, ip) for name, ip in server_ips.items()]
    results = await asyncio.gather(*tasks)
    return dict((k, v) for d in results for k, v in d.items())  # Flatten the list of dicts

async def send_request(url):
    async with aiohttp.ClientSession() as session:
        async with session.post(url) as response:
            if response.status == 200:
                try:
                    return await response.json()
                except aiohttp.ContentTypeError:
                    return {'error': 'Invalid content type', 'content': await response.text()}
            else:
                return {'error': f'HTTP {response.status}', 'content': await response.text()}

def check_init_data(input_data):
    # 初始化結果字典
    result = {}

    # 處理servo
    for i in range(1, 7):
        check_key = f'check_servo_{i}'
        servo_key = f'servo_{i}'
        if input_data.get(check_key) == 'true':
            result[servo_key] = input_data[servo_key]

    # 處理arm_servo
    for i in range(1, 7):
        check_key = f'check_arm_servo_{i}'
        arm_servo_key = f'arm_servo_{i}'
        if input_data.get(check_key) == 'true':
            result[arm_servo_key] = input_data[arm_servo_key]

    excel_file = os.path.join(UPLOAD_FOLDER, 'IEC13680.xlsx')
    # 讀取 Excel 數據到 DataFrame
    df = pd.read_excel(excel_file)

# 更新 DataFrame 中的多行
    for index, row in df.iterrows():
        row_value = row.iloc[0]  # 讀取 row[0] 的值
        if row_value in ['dut_server', 'arm_server']:
            new_values = {}
            for key, value in result.items():
                if row_value == 'dut_server' and key.startswith('servo'):
                    new_values[key.replace('servo', 'parameter')] = value
                elif row_value == 'arm_server' and key.startswith('arm_servo'):
                    new_values[key.replace('arm_servo', 'parameter')] = value
            if new_values:
                df.loc[index, new_values.keys()] = new_values.values()
    df.to_excel(excel_file, index=False)



def load_ips_from_file():
    ip_addresses = {}
    if os.path.exists('ip_addresses.txt'):
        with open('ip_addresses.txt', 'r') as file:
            lines = file.readlines()
            for line in lines:
                if ': ' in line:
                    name, ip = line.strip().split(': ')
                    ip_addresses[name] = ip
    return ip_addresses

def save_ips_to_file(ip_addresses):
    with open('ip_addresses.txt', 'w') as file:
        for name, ip in ip_addresses.items():
            file.write(f"{name}: {ip}\n")



ip_addresses = load_ips_from_file()
global_arm_ip = ip_addresses.get('arm_server', 'Not found')
global_dut_ip = ip_addresses.get('dut_server', 'Not found')
global_sb_ip = ip_addresses.get('sb_server', 'Not found')
global_unet_ip = ip_addresses.get('unet_server', 'Not found')


@app.route('/')
def index():
    global global_dut_ip, global_arm_ip, global_sb_ip, global_unet_ip
    ip_addresses = load_ips_from_file()
    global_arm_ip = ip_addresses.get('arm_server', 'Not found')
    global_dut_ip = ip_addresses.get('dut_server', 'Not found')
    global_sb_ip = ip_addresses.get('sb_server', 'Not found')
    global_unet_ip = ip_addresses.get('unet_server', 'Not found')
    return render_template(('login.html'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in users and users[username] == password:
            session['username'] = username
            return render_template('index.html')
        else:
            flash('Invalid username or password!')
    return render_template('login.html')

@app.route('/check_connections', methods=['GET'])
async def check_connections():
    global global_dut_ip, global_arm_ip, global_sb_ip, global_unet_ip
    ip_addresses = load_ips_from_file()
    global_arm_ip = ip_addresses.get('arm_server', 'Not found')
    global_dut_ip = ip_addresses.get('dut_server', 'Not found')
    global_sb_ip = ip_addresses.get('sb_server', 'Not found')
    global_unet_ip = ip_addresses.get('unet_server', 'Not found')
    server_ips = {
        'arm_server': f'http://{global_arm_ip}/get_info',
        'dut_server': f'http://{global_dut_ip}/get_info',
        'sb_server': f'http://{global_sb_ip}/get_info',
        'unet_server': f'http://{global_unet_ip}/get_info'
    }
    results = await check_all_connections(server_ips)
    test=requests.get(f'http://{global_sb_ip}/self_check_and_turn_on_system')
    return jsonify(results)

@app.route('/welcome')
def welcome():
    if 'username' not in session:
        return redirect(url_for('login'))
    username=session['username']
    global global_dut_ip,global_arm_ip,global_sb_ip,global_unet_ip
    ip_addresses = load_ips_from_file()
    global_arm_ip = ip_addresses.get('arm_server', 'Not found')
    global_dut_ip = ip_addresses.get('dut_server', 'Not found')
    global_sb_ip = ip_addresses.get('sb_server', 'Not found')
    global_unet_ip = ip_addresses.get('unet_server', 'Not found')
    return render_template('welcome.html',formatted_time=formatted_time,username=username,local_ip=local_ip)

@app.route('/test',methods=['GET', 'POST'])
def test():
    if 'username' not in session:
        return redirect(url_for('login'))
    username=session['username']
    return render_template('test.html',formatted_time=formatted_time,username=username,local_ip=local_ip)

@app.route('/dashboard',methods=['GET', 'POST'])
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))
    ip_addresses = load_ips_from_file()
    global global_dut_ip,global_arm_ip,global_sb_ip,global_unet_ip
    global_arm_ip = ip_addresses.get('arm_server', 'Not found')
    global_dut_ip = ip_addresses.get('dut_server', 'Not found')
    global_sb_ip = ip_addresses.get('sb_server', 'Not found')
    global_unet_ip = ip_addresses.get('unet_server', 'Not found')
    username=session['username']
    return render_template('index.html', received_data=received_data,formatted_time=formatted_time,username=username,local_ip=local_ip)


#@app.route('/dashboard_ip')
#def dashboard_ip():
#    username=session['username']
#    return render_template('dashboard_ip.html',formatted_time=formatted_time,username=username,local_ip=local_ip)


@app.route('/test_ip')
def test_ip():
    username=session['username']
    ip_addresses = load_ips_from_file()
    global global_dut_ip,global_arm_ip,global_sb_ip,global_unet_ip
    global_arm_ip = ip_addresses.get('arm_server', 'Not found')
    global_dut_ip = ip_addresses.get('dut_server', 'Not found')
    global_sb_ip = ip_addresses.get('sb_server', 'Not found')
    global_unet_ip = ip_addresses.get('unet_server', 'Not found')
    files = [f for f in os.listdir(UPLOAD_FOLDER) if f.endswith(('.xlsx', '.xls'))]
    return render_template('test_ip.html',formatted_time=formatted_time,username=username,local_ip=local_ip,files=files)

#@app.route('/dashboard_data', methods=["POST"])
#async def dashboard_data():
#    data = request.json
#    dut_servo_1 = data['servo_1']
#    dut_servo_2 = data['servo_2']
#    dut_servo_3 = data['servo_3']
#    dut_servo_4 = data['servo_4']
#    dut_servo_5 = data['servo_5']
#    dut_servo_6 = data['servo_6']
#    arm_servo_1 = data['arm_servo_1']
#    arm_servo_2 = data['arm_servo_2']
#    arm_servo_3 = data['arm_servo_3']
#    arm_servo_4 = data['arm_servo_4']
#    arm_servo_5 = data['arm_servo_5']
#    arm_servo_6 = data['arm_servo_6']
#    sb_value = data['real_position']
#    
#    now = datetime.datetime.now()
#    formatted_time = now.strftime('%Y-%m-%d %H:%M:%S')
#
#    test_1_url = f'http://{global_dut_ip}/set_servo?servo_1={dut_servo_1}&servo_2={dut_servo_2}&servo_3={dut_servo_3}&servo_4={dut_servo_4}&servo_5={dut_servo_5}&servo_6={dut_servo_6}'
#    test_2_url = f'http://{global_arm_ip}/set_servo?servo_1={arm_servo_1}&servo_2={arm_servo_2}&servo_3={arm_servo_3}&servo_4={arm_servo_4}&servo_5={arm_servo_5}&servo_6={arm_servo_6}'
#    test_3_url = f'http://{global_sb_ip}/set_distance?position={sb_value}'
#
#    # 同時發送所有請求
#    responses = await asyncio.gather(
#        send_request(test_1_url),
#        send_request(test_2_url),
#        send_request(test_3_url)
#    )
#
#
#    # 處理 test_1 的回傳資料
#    test_1_data = responses[0]
#    if test_1_data:
#        test_1_data['receivedtime'] = formatted_time
#        global log_dut_data
#        log_dut_data = {
#            'time': test_1_data['receivedtime'],
#            'device': 'dut機器手臂',
#            'command': f'{dut_servo_1},{dut_servo_2},{dut_servo_3},{dut_servo_4},{dut_servo_5},{dut_servo_6}',
#            'status': f"{test_1_data.get('servo_dict', {}).get('servo_1', '')},{test_1_data.get('servo_dict', {}).get('servo_2', '')},{test_1_data.get('servo_dict', {}).get('servo_3', '')},{test_1_data.get('servo_dict', {}).get('servo_4', '')},{test_1_data.get('servo_dict', {}).get('servo_5', '')},{test_1_data.get('servo_dict', {}).get('servo_6', '')},{test_1_data.get('temperature', '')},{test_1_data.get('humidity', '')},{test_1_data.get('detect', '')},{test_1_data.get('ip_address', '')}",
#            'operator': 'Frank'
#        }
#
#    # 處理 test_2 的回傳資料
#    test_2_data = responses[1]
#
#    if test_2_data:
#        test_2_data['receivedtime'] = formatted_time
#        global log_arm_data
#        log_arm_data = {
#            'time': test_2_data['receivedtime'],
#            'device': 'arm機器手臂',
#            'command': f'{arm_servo_1},{arm_servo_2},{arm_servo_3},{arm_servo_4},{arm_servo_5},{arm_servo_6}',
#            'status': f"{test_2_data.get('servo_dict', {}).get('servo_1', '')},{test_2_data.get('servo_dict', {}).get('servo_2', '')},{test_2_data.get('servo_dict', {}).get('servo_3', '')},{test_2_data.get('servo_dict', {}).get('servo_4', '')},{test_2_data.get('servo_dict', {}).get('servo_5', '')},{test_2_data.get('servo_dict', {}).get('servo_6', '')},{test_2_data.get('temperature', '')},{test_2_data.get('humidity', '')},{test_2_data.get('detect', '')},{test_2_data.get('ip_address', '')}",
#            'operator': 'Frank'
#        }
#    
#    # 處理 test_3 的回傳資料
#    test_3_data = responses[2]
#    if test_3_data:
#        test_3_data['step_time'] = formatted_time
#        test_3_data['step_ip'] = global_step_ip
#        global log_step_data
#        log_step_data = {
#            'time': test_3_data['step_time'],
#            'device': 'step馬達',
#            'command': f'往前{step_value}(cm)',
#            'status': f"{test_3_data.get('real_position', '')},{test_3_data.get('step_ip', '')}",
#            'operator': 'Frank'
#        }
#
#    return jsonify(status='success')

@app.route('/test_data', methods=["POST"])
async def test_data():
    data = request.json
    print(data)
    global execute_excel
    execute_excel =  'IEC13680.xlsx'
    dut_servo_1 = data['servo_1']
    dut_servo_2 = data['servo_2']
    dut_servo_3 = data['servo_3']
    dut_servo_4 = data['servo_4']
    dut_servo_5 = data['servo_5']
    dut_servo_6 = data['servo_6']
    arm_servo_1 = data['arm_servo_1']
    arm_servo_2 = data['arm_servo_2']
    arm_servo_3 = data['arm_servo_3']
    arm_servo_4 = data['arm_servo_4']
    arm_servo_5 = data['arm_servo_5']
    arm_servo_6 = data['arm_servo_6']
    dut_delay = data['dut_delay_time']
    sb_target_distance=data['target_distance']
    unet_status = data['check_unet']
    global temperature_max,temperature_min,humidity_max,humidity_min
    temperature_max = float(data['temperature-max'])
    temperature_min = float(data['temperature-min'])
    humidity_max = float(data['humidity-max'])
    humidity_min = float(data['humidity-min'])
    global global_dut_delay
    global_dut_delay=int(dut_delay)

    new_data = [
        ['dut_server', dut_servo_1, dut_servo_2, dut_servo_3, dut_servo_4, dut_servo_5, dut_servo_6, dut_delay, 'no', None],
        ['arm_server', arm_servo_1, arm_servo_2, arm_servo_3, arm_servo_4, arm_servo_5, arm_servo_6, 1, 'no', None],
        ['sb_server', sb_target_distance, None, None, None, None, None, 1, 'no', None],
        ['unet_server', unet_status, None, None, None, None, None, 1, 'no', None]
    ]
    new_df = pd.DataFrame(new_data, columns=[
        'server_name', 'parameter_1', 'parameter_2', 'parameter_3', 'parameter_4',
        'parameter_5', 'parameter_6', 'delay_time', 'active_detection','axis'
    ])
    excel_file = os.path.join(UPLOAD_FOLDER, 'IEC13680.xlsx')
    # 讀取 Excel 數據到 DataFrame
    df = pd.read_excel(excel_file)
    df.iloc[:4] = new_df
    df.to_excel(excel_file, index=False)

    # check_init_data(data)
    test_1_url = f'http://{global_dut_ip}/set_servo?servo_1={dut_servo_1}&servo_2={dut_servo_2}&servo_3={dut_servo_3}&servo_4={dut_servo_4}&servo_5={dut_servo_5}&servo_6={dut_servo_6}'
    test_2_url = f'http://{global_arm_ip}/set_servo?servo_1={arm_servo_1}&servo_2={arm_servo_2}&servo_3={arm_servo_3}&servo_4={arm_servo_4}&servo_5={arm_servo_5}&servo_6={arm_servo_6}'
    test_3_url = f'http://{global_sb_ip}/move?target_distance={sb_target_distance}'
    test_4_url = f'http://{global_unet_ip}/AN203_{unet_status}'

    # 同時執行所有請求
    responses = await asyncio.gather(
        send_request(test_1_url),
        send_request(test_2_url),
        send_request(test_3_url),
        send_request(test_4_url)
    )
  
#    now = datetime.datetime.now()
#    formatted_time = now.strftime('%Y-%m-%d %H:%M:%S')
#    # 處理 test_1 的回傳資料
#    test_1_data = responses[0]
#    if test_1_data:
#        test_1_data['receivedtime'] = formatted_time
#        test_1_data['server_type'] = 'dut_server'
#        global log_dut_data
#        log_dut_data = {
#            'time': test_1_data['receivedtime'],
#            'device': 'dut機器手臂',   
#            'command': f'{dut_servo_1},{dut_servo_2},{dut_servo_3},{dut_servo_4},{dut_servo_5},{dut_servo_6}',
#            'status': f"{test_1_data.get('servo_dict', {}).get('servo_1', '')},{test_1_data.get('servo_dict', {}).get('servo_2', '')},{test_1_data.get('servo_dict', {}).get('servo_3', '')},{test_1_data.get('servo_dict', {}).get('servo_4', '')},{test_1_data.get('servo_dict', {}).get('servo_5', '')},{test_1_data.get('servo_dict', {}).get('servo_6', '')},{test_1_data.get('temperature', '')},{test_1_data.get('humidity', '')},{test_1_data.get('detect', '')},{test_1_data.get('ip_address', '')}",
#            'operator': 'Frank'
#        }
#        test_1_data['logs'] = log_dut_data
#        print(test_1_data)
#    #    socketio.emit('update_result',test_1_data)
#    # 處理 test_2 的回傳資料
    test_2_data = responses[1]
    content = json.loads(test_2_data['content'])
    temperature = float(content['temperature'])
    humidity = float(content['humidity'])
    if humidity>humidity_max or humidity<humidity_min or temperature>temperature_max or temperature<temperature_min:
        while True:
              arm_response = requests.get(f'http://{global_arm_ip}/get_info')
              data = arm_response.json()
              print(data)
              if temperature_min>data['temperature']:
                 test = requests.post(f'http://{global_unet_ip}/AN203_ON')
              elif data['temperature']>temperature_max:
                 test = requests.post(f'http://{global_unet_ip}/AN203_OFF')
              if humidity_min<data['humidity']<humidity_max and temperature_min<data['temperature']<temperature_max:
                  break
#        test_2_data['receivedtime'] = formatted_time
#        test_2_data['server_type'] = 'arm_server'
#        global log_arm_data
#        log_arm_data = {
#            'time': test_2_data['receivedtime'],
#            'device': 'arm機器手臂',
#            'command': f'{arm_servo_1},{arm_servo_2},{arm_servo_3},{arm_servo_4},{arm_servo_5},{arm_servo_6}',
#            'status': f"{test_2_data.get('servo_dict', {}).get('servo_1', '')},{test_2_data.get('servo_dict', {}).get('servo_2', '')},{test_2_data.get('servo_dict', {}).get('servo_3', '')},{test_2_data.get('servo_dict', {}).get('servo_4', '')},{test_2_data.get('servo_dict', {}).get('servo_5', '')},{test_2_data.get('servo_dict', {}).get('servo_6', '')},{test_2_data.get('temperature', '')},{test_2_data.get('humidity', '')},{test_2_data.get('detect', '')},{test_2_data.get('ip_address', '')}",
#            'operator': 'Frank'
#        }
#        test_2_data['logs'] = log_arm_data
#        print(test_2_data)
#        socketio.emit('update_result',test_2_data)
#
#     處理 test_3 的回傳資料
#    test_3_data = responses[2]
#    if test_3_data:
#        test_3_data['step_time'] = formatted_time
#        test_3_data['step_ip'] = global_step_ip
#        test_3_data['server_type'] = 'step_server'
#        global log_step_data
#        log_step_data = {
#            'time': test_3_data['step_time'],
#            'device': 'step馬達',
#            'command': f'往前{step_value}(cm)',
#            'status': f"{test_3_data.get('real_position', '')},{test_3_data.get('step_ip', '')}",
#            'operator': 'Frank'
#        }
#        test_3_data['logs'] = log_arm_data
#        print(test_3_data)
#        socketio.emit('update_result',test_3_data)
#    
#    test_4_data = responses[3]
#    if test_4_data:
#        data = {
#           'set_MC026_binding' : 'successfully',
#            }
#        now = datetime.datetime.now()
#        formatted_time = now.strftime('%Y-%m-%d %H:%M:%S')
#        data['AN203_ON_OFF_test']=f'AN203_{unet_status}'
#        data['server_type'] = 'unet_server'
#        data['unet_time'] = formatted_time 
#        data['unet_ip'] = global_unet_ip
#        global log_unet_data
#        log_unet_data={
#            'time': f'{data['unet_time']}',
#            'device': 'unet_AN203',
#            'command': f'{data['AN203_ON_OFF_test']}',
#            'status': f'{data['AN203_ON_OFF_test']},{data['unet_ip']}',
#            'operator': 'Frank'
#            }
#        data['logs'] = log_unet_data
#        print(test_4_data)
    #    socketio.emit('update_result',data)
    return jsonify(status='success')
    
#def detection_thread(detect_time):
#    start_time = time.time()
#    global detect_flag
#    while time.time() - start_time < detect_time:
#        app.test_request_context('/detection', method='POST')
#    detect_flag=False

@socketio.on('start_processing')
def handle_start_processing():
    now = datetime.datetime.now()
    global stop_processing
    stop_processing = False
    global end_processing
    end_processing = False
    df_download = pd.DataFrame({
    "time": [""],
    "device": [""],
    "commands": [""],
    "status": [""],
    "detect_axis": [""]
    })

    formatted_time = now.strftime('%Y-%m-%d %H:%M:%S')
    data={
          'time': formatted_time,
        'device': '開始處理'
        }
    emit('start_button',data)
    excel_file = os.path.join(UPLOAD_FOLDER,'IEC13680.xlsx')
    df = pd.read_excel(excel_file)
    global return_flag
    global detect_confirm_flag
    global detect_flag
    global server_dead_flag
    global detect_axis
    global global_dut_delay
    for index, row in df.iterrows():
        # print(server_dead_flag)
        # if server_dead_flag==True:
        #    break
        # server_dead_flag=True
        while stop_processing ==True:
            continue
        if end_processing==True:
            break
        return_flag=False
        detect_confirm_flag=False
        server_type = row['server_name']
        delay_time=row['delay_time']
        # active_detection = row['active_detection']
        # if active_detection == 'yes':
        #    detect_axis = row['axis']
        #    detect_flag = True
        # else:
        #    detect_flag = False
        try:
            if row[0] == "dut_server":
             delay_time=global_dut_delay
             param1 = str(row['parameter_1'])
             param2 = str(row['parameter_2'])
             param3 = str(row['parameter_3'])
             param4 = str(row['parameter_4'])
             param5 = str(row['parameter_5'])
             param6 = str(row['parameter_6'])
             global global_dut_ip
             ip_address=global_dut_ip
             detect_axis = row['axis']
             url=f'http://{ip_address}/set_servo?servo_1={param1}&servo_2={param2}&servo_3={param3}&servo_4={param4}&servo_5={param5}&servo_6={param6}'
             test = requests.post(url,timeout=15)
             if test.status_code == 200:
                 # 解析 JSON 數據
                data = test.json()
                now = datetime.datetime.now()
                formatted_time = now.strftime('%Y-%m-%d %H:%M:%S')
                data['receivedtime'] = formatted_time
                data['server_type'] = server_type
                global log_dut_data
                log_dut_data={
                'time': f"{data['receivedtime']}",
                'device': 'dut機器手臂',
                'command': f"{param1},{param2},{param3},{param4},{param5},{param6}",
                'status': f"{data['servo_dict']['servo_1']},{data['servo_dict']['servo_2']},{data['servo_dict']['servo_3']},{data['servo_dict']['servo_4']},{data['servo_dict']['servo_5']},{data['servo_dict']['servo_6']},{data['temperature']},{data['humidity']},{data['detect']},{data['ip_address']}",
                'detect_axis': ''
                }
                data['logs'] = log_dut_data
                download_data=[log_dut_data]   
                df_new = pd.DataFrame(download_data)
                df_download = pd.concat([df_download, df_new], ignore_index=True)
            elif row[0] == "arm_server":
             param1 = str(row['parameter_1'])
             param2 = str(row['parameter_2'])
             param3 = str(row['parameter_3'])
             param4 = str(row['parameter_4'])
             param5 = str(row['parameter_5'])
             param6 = str(row['parameter_6'])
             global global_arm_ip
             ip_address=global_arm_ip
             url=f'http://{ip_address}/set_servo?servo_1={param1}&servo_2={param2}&servo_3={param3}&servo_4={param4}&servo_5={param5}&servo_6={param6}'
             test = requests.post(url,timeout=15)
             if test.status_code == 200:
                 # 解析 JSON 數據
                data = test.json()
                now = datetime.datetime.now()
                formatted_time = now.strftime('%Y-%m-%d %H:%M:%S')
                data['receivedtime'] = formatted_time
                data['server_type'] = server_type
                global log_arm_data
                log_arm_data={
                'time': f"{data['receivedtime']}",
                'device': 'arm機器手臂',
                'command': f"{param1},{param2},{param3},{param4},{param5},{param6}",
                'status': f"{data['servo_dict']['servo_1']},{data['servo_dict']['servo_2']},{data['servo_dict']['servo_3']},{data['servo_dict']['servo_4']},{data['servo_dict']['servo_5']},{data['servo_dict']['servo_6']},{data['temperature']},{data['humidity']},{data['detect']},{data['ip_address']}",
                'detect_axis': ''
                }
                data['logs'] = log_arm_data
                download_data=[log_arm_data]   
                df_new = pd.DataFrame(download_data)
                df_download = pd.concat([df_download, df_new], ignore_index=True)
                if data['humidity']>humidity_max or data['humidity']<humidity_min or data['temperature']>temperature_max or data['temperature']<temperature_min:
                    while True:
                          arm_response = requests.get(f'http://{global_arm_ip}/get_info')
                          arm_data = arm_response.json()
                          print(arm_data)
                          if temperature_min>arm_data['temperature']:
                             test = requests.post(f'http://{global_unet_ip}/AN203_ON')
                          elif arm_data['temperature']>temperature_max:
                             test = requests.post(f'http://{global_unet_ip}/AN203_OFF')
                          if humidity_min<arm_data['humidity']<humidity_max and temperature_min<arm_data['temperature']<temperature_max:
                             break
            elif row[0] == "sb_server":
             param1 = int(row['parameter_1'])
             global global_sb_ip
             ip_address=global_sb_ip
             url=f'http://{ip_address}/move?target_distance={param1}'
             print(url)
             test = requests.post(url,timeout=15)
             if test.status_code == 200:
                 # 解析 JSON 數據
                data = test.json()
                now = datetime.datetime.now()
                formatted_time = now.strftime('%Y-%m-%d %H:%M:%S')

                data['server_type'] = server_type
                data['sb_time'] = formatted_time
                data['sb_ip'] = ip_address
                global log_sb_data
                log_sb_data = {
                    'time': data['sb_time'],
                    'device': 'sb馬達',
                    'command': f'target_distance={param1}',
                    'status': f"{data['location']['target_distance']}",
                    'detect_axis': ''
                }
                data['logs'] = log_sb_data   
                download_data=[log_sb_data]   
                df_new = pd.DataFrame(download_data)
                df_download = pd.concat([df_download, df_new], ignore_index=True)
            elif row[0] == "unet_server":
             param1 = str(row['parameter_1'])
             ip_address=global_unet_ip
             url=f'http://{ip_address}/AN203_{param1}'
             test = requests.post(url,timeout=15)
             if test.status_code == 200:
                 # 解析 JSON 數據
                data = {
               'set_MC026_binding' : 'successfully',
                }
                now = datetime.datetime.now()
                formatted_time = now.strftime('%Y-%m-%d %H:%M:%S')
                data['AN203_ON_OFF_test']=f'AN203_{param1}'
                data['server_type'] = server_type
                data['unet_time'] = formatted_time 
                data['unet_ip'] = ip_address
                global log_unet_data
                log_unet_data={
                'time': f"{data['unet_time']}",
                'device': 'unet_AN203',
                'command': f"{data['AN203_ON_OFF_test']}",
                'status': f"{data['AN203_ON_OFF_test']},{data['unet_ip']}",
                'detect_axis': ''
                }
                data['logs'] = log_unet_data
                df_new = pd.DataFrame([log_unet_data])
                df_download = pd.concat([df_download, df_new], ignore_index=True)
            elif row[0] == "iec63180_movement_set":
                ip_address=global_arm_ip
                url=f'http://{ip_address}/iec63180_movement_set'
                detect_flag=True
                test = requests.get(url,timeout=15)
                detect_flag=False
                if test.status_code == 200:
                   data = test.json()
                   now = datetime.datetime.now()
                   formatted_time = now.strftime('%Y-%m-%d %H:%M:%S')
                   data['receivedtime'] = formatted_time
                   data['server_type'] = server_type
                   log_arm_data={
                   'time': f"{data['receivedtime']}",
                   'device': 'arm機器手臂',
                   'command': f"{param1},{param2},{param3},{param4},{param5},{param6}",
                   'status': f"{data['servo_dict']['servo_1']},{data['servo_dict']['servo_2']},{data['servo_dict']['servo_3']},{data['servo_dict']['servo_4']},{data['servo_dict']['servo_5']},{data['servo_dict']['servo_6']},{data['temperature']},{data['humidity']},{data['ip_address']}",
                   'detect_axis': ''
                   }
                   data['logs'] = log_arm_data
                   if data['humidity']>humidity_max or data['humidity']<humidity_min or data['temperature']>temperature_max or data['temperature']<temperature_min:
                       while True:
                          arm_response = requests.get(f'http://{global_arm_ip}/get_info')
                          arm_data = arm_response.json()
                          print(arm_data)
                          if temperature_min>arm_data['temperature']:
                             test = requests.post(f'http://{global_unet_ip}/AN203_ON')
                          elif arm_data['temperature']>temperature_max:
                             test = requests.post(f'http://{global_unet_ip}/AN203_OFF')
                          if humidity_min<arm_data['humidity']<humidity_max and temperature_min<arm_data['temperature']<temperature_max:
                             break
                   
            
            # 模擬一些處理時間
            # 將結果發送給客戶端
            emit('update_result',data)
            return_flag=True
            if return_flag == True and detect_confirm_flag == True and isinstance(log_arm_data, dict) and isinstance(log_dut_data, dict):
                now = datetime.datetime.now()
                formatted_time = now.strftime('%Y-%m-%d %H:%M:%S')
                update_data = {
                    'time': formatted_time,
                  'device': log_sb_data['status'],
                  'status': log_arm_data['status'],
                 'command': log_dut_data['command'],
                'detect_axis': detect_axis
              }
                emit('update_detect',update_data)
            if delay_time>=1:
                time.sleep(delay_time)
            # if active_detection == 'yes':
            #     detect_flag=True
        except requests.RequestException as e:
            connection_break_flag=True
            print(f"请求失败: {e}")
            # 處理 POST 請求失敗
            now = datetime.datetime.now()
            formatted_time = now.strftime('%Y-%m-%d %H:%M:%S')
            data={
                  'time': formatted_time,
                'device': 'connection fail'
                }
            emit('connection_fail',data)
            # 對四個服務器發送 get_info 請求
            servers = {
                'dut': global_dut_ip,
                'arm': global_arm_ip,
                'sb': global_sb_ip,
                'unet': global_unet_ip
            }
            for server_name, ip in servers.items():
                try:
                    info_response = requests.get(f'http://{ip}/get_info')
                    info_response.raise_for_status()
                    if info_response.status_code == 200:
                        print(f"{server_name} 服务器正常")
                except requests.RequestException:
                    # 服務器沒有回覆，彈出提示視窗
                    emit('show_popup', {'server': server_name, 'status': '需要重启'})
                    # 繼續嘗試直到收到回覆
                    while True:
                        try:
                            info_response = requests.get(f'http://{ip}/get_info')
                            info_response.raise_for_status()
                            break
                        except requests.RequestException:
                            continue
            now = datetime.datetime.now()
            formatted_time = now.strftime('%Y-%m-%d %H:%M:%S')
            data={
                  'time': formatted_time,
                'device': 'connection restore'
                }
            emit('reconnection',data)
            # if active_detection == 'yes':
            #    detect_flag = True
            # else:
            #    detect_flag = False
            print(row[0])
            if row[0] == "iec63180_movement_set":
               test = requests.get(url,timeout=15)
            else:
               test = requests.post(url,timeout=15)
            data = test.json()
            now = datetime.datetime.now()
            formatted_time = now.strftime('%Y-%m-%d %H:%M:%S')
            data['receivedtime'] = formatted_time
            data['server_type'] = server_type
            if row[0]=='dut_server':
               log_dut_data={
               'time': f"{data['receivedtime']}",
               'device': 'dut機器手臂',
               'command': f"{param1},{param2},{param3},{param4},{param5},{param6}",
               'status': f"{data['servo_dict']['servo_1']},{data['servo_dict']['servo_2']},{data['servo_dict']['servo_3']},{data['servo_dict']['servo_4']},{data['servo_dict']['servo_5']},{data['servo_dict']['servo_6']},{data['temperature']},{data['humidity']},{data['detect']},{global_dut_ip}",
               'detect_axis': ''  
               }
               data['logs'] = log_dut_data 
               download_data=[log_dut_data]   
               df_new = pd.DataFrame(download_data)
               df_download = pd.concat([df_download, df_new], ignore_index=True)
            elif row[0]=='arm_server':
                log_arm_data={
                'time': f"{data['receivedtime']}",
                'device': 'arm機器手臂',
                'command': f'{param1},{param2},{param3},{param4},{param5},{param6}',
                'status': f"{data['servo_dict']['servo_1']},{data['servo_dict']['servo_2']},{data['servo_dict']['servo_3']},{data['servo_dict']['servo_4']},{data['servo_dict']['servo_5']},{data['servo_dict']['servo_6']},{data['temperature']},{data['humidity']},{data['detect']},{global_arm_ip}",
                'detect_axis': ''
                }
                data['logs'] = log_arm_data
                download_data=[log_arm_data]   
                df_new = pd.DataFrame(download_data)
                df_download = pd.concat([df_download, df_new], ignore_index=True)
                if data['humidity']>humidity_max or data['humidity']<humidity_min or data['temperature']>temperature_max or data['temperature']<temperature_min:
                    while True:
                          arm_response = requests.get(f'http://{global_arm_ip}/get_info')
                          arm_data = arm_response.json()
                          if temperature_min>arm_data['temperature']:
                             test = requests.post(f'http://{global_unet_ip}/AN203_ON')
                          elif arm_data['temperature']>temperature_max:
                             test = requests.post(f'http://{global_unet_ip}/AN203_OFF')
                          if humidity_min<arm_data['humidity']<humidity_max and temperature_min<arm_data['temperature']<temperature_max:
                             break
            elif row[0]=='sb_server':
                log_sb_data = {
                    'time': data['receivedtime'],
                    'device': 'sb馬達',
                    'command': f'target_distance={param1}',
                    'status': f"{data['location']['target_distance']},{global_sb_ip}",
                    'detect_axis': ''
                }
                data['logs'] = log_sb_data
                download_data=[log_sb_data]   
                df_new = pd.DataFrame(download_data)
                df_download = pd.concat([df_download, df_new], ignore_index=True)
            elif row[0]=='unet_server':
                data['AN203_ON_OFF_test']=f'AN203_{param1}'
                log_unet_data={
                'time': f"{data['receivedtime']}",
                'device': 'unet_AN203',
                'command': f"{data['AN203_ON_OFF_test']}",
                'status': f"{data['AN203_ON_OFF_test']},{global_unet_ip}",
                'detect_axis': ''
                }
                data['logs'] = log_unet_data
                df_new = pd.DataFrame(data['logs'])
                df_download = pd.concat([df_download, df_new], ignore_index=True)
            elif row[0] == "iec63180_movement_set":
                ip_address=global_arm_ip
                url=f'http://{ip_address}/iec63180_movement_set'
                detect_flag=True
                test = requests.get(url,timeout=15)
                detect_flag=False
                if test.status_code == 200:
                   data = test.json()
                   now = datetime.datetime.now()
                   formatted_time = now.strftime('%Y-%m-%d %H:%M:%S')
                   data['receivedtime'] = formatted_time
                   data['server_type'] = server_type
                   log_arm_data={
                   'time': f"{data['receivedtime']}",
                   'device': 'arm機器手臂',
                   'command': f"{param1},{param2},{param3},{param4},{param5},{param6}",
                   'status': f"{data['servo_dict']['servo_1']},{data['servo_dict']['servo_2']},{data['servo_dict']['servo_3']},{data['servo_dict']['servo_4']},{data['servo_dict']['servo_5']},{data['servo_dict']['servo_6']},{data['temperature']},{data['humidity']},{data['ip_address']}",
                   'detect_axis': ''
                   }
                   data['logs'] = log_arm_data
                   if data['humidity']>humidity_max or data['humidity']<humidity_min or data['temperature']>temperature_max or data['temperature']<temperature_min:
                       while True:
                          arm_response = requests.get(f'http://{global_arm_ip}/get_info')
                          arm_data = arm_response.json()
                          print(arm_data)
                          if temperature_min>arm_data['temperature']:
                             test = requests.post(f'http://{global_unet_ip}/AN203_ON')
                          elif arm_data['temperature']>temperature_max:
                             test = requests.post(f'http://{global_unet_ip}/AN203_OFF')
                          if humidity_min<arm_data['humidity']<humidity_max and temperature_min<arm_data['temperature']<temperature_max:
                             break
                # 將結果發送給客戶端
            emit('update_result',data)
            return_flag=True
            if return_flag == True and detect_confirm_flag == True and isinstance(log_arm_data, dict) and isinstance(log_dut_data, dict):
                now = datetime.datetime.now()
                formatted_time = now.strftime('%Y-%m-%d %H:%M:%S')
                update_data = {
                    'time': formatted_time,
                  'device': log_sb_data['status'],
                  'status': log_arm_data['status'],
                 'command': log_dut_data['command'],
                'detect_axis': detect_axis
              }
                emit('update_detect',update_data)
            if delay_time>=1:
              time.sleep(delay_time)
            # if active_detection[0] == 'yes':
            #     detect_flag=True
            return_flag = False
            
    if end_processing == False:
       now = datetime.datetime.now()
       formatted_time = now.strftime('%Y-%m-%d %H:%M:%S')
       data={
             'time': formatted_time,
           'device': '法規結束'
           }
       emit('reconnection',data)
       emit('end_button',data)
       download_time=now.strftime('%Y-%m-%d_%H_%M_%S')
       download_excel=(f"IEC13680_{download_time}.xlsx")
       save_excel_to_folder(df,download_excel)


@socketio.on('page_still_active')
def page_still_active():
    global server_dead_flag
    server_dead_flag=False


@socketio.on('pause_processing')
def handle_pause_processing():
    global stop_processing
    stop_processing = True
    global end_processing
    end_processing = False
    now = datetime.datetime.now()
    formatted_time = now.strftime('%Y-%m-%d %H:%M:%S')
    data={
          'time': formatted_time,
        'device': '暫停執行'
        }
    emit('connection_fail',data)
    emit('pause_processing', {'status': 'paused'})


@socketio.on('continue_processing')
def handle_continue_processing():
    global stop_processing
    stop_processing = False
    global end_processing
    end_processing = False
    now = datetime.datetime.now()
    formatted_time = now.strftime('%Y-%m-%d %H:%M:%S')
    data={
          'time': formatted_time,
        'device': '繼續執行'
        }
    emit('reconnection',data)
    emit('continue_processing', {'status': 'continued'})

@socketio.on('stop_processing')
def handle_stop_processing():
    global stop_processing
    stop_processing = False
    global end_processing
    end_processing = True
    now = datetime.datetime.now()
    formatted_time = now.strftime('%Y-%m-%d %H:%M:%S')
    data={
          'time': formatted_time,
        'device': '法規結束'
        }
    emit('start_button',data)
    print("強制結束")
    emit('stop_processing', {'status': 'stopped'})



@app.route('/receive_ip', methods=["POST"])
def receive_ip():
    if request.is_json:
        data = request.get_json()
        ip_addresses = load_ips_from_file()
        print(data)
        name = data.get('name')
        ip_address = data.get('ip_address')
        
        if name and ip_address:
            if name == 'arm_server':
                global global_arm_ip
                global_arm_ip = ip_address
                ip_addresses['arm_server'] = global_arm_ip

            elif name == 'dut_server':
                global global_dut_ip
                global_dut_ip = ip_address
                ip_addresses['dut_server'] = global_dut_ip

            elif name == 'sb_server':
                global global_sb_ip
                global_sb_ip = ip_address
                ip_addresses['sb_server'] = global_sb_ip

            elif name == 'unet_server':
                global global_unet_ip
                global_unet_ip = ip_address
                ip_addresses['unet_server'] = global_unet_ip

            save_ips_to_file(ip_addresses)

        response_data = {'message': "IP address received successfully", 'ip_received': ip_address}
        return jsonify(response_data)
    else:
        return jsonify({'error': 'Invalid JSON format'}), 400
 



@app.route('/server_keep_alive', methods=["POST"])
def server_keep_alive():
    data = request.get_json()
    name = data.get('name')
    now = datetime.datetime.now()
    formatted_time = now.strftime('%Y-%m-%d %H:%M:%S')
    data['server_type']=name
    data['receivedtime']=formatted_time
    socketio.emit('server_keep_alive',data)
    response_data = {'message': "server_keep_alive received successfully"}
    return jsonify(response_data)



@app.route("/execute_api", methods=["GET"])
def execute_api():
    global global_sb_ip
    ip_address=global_sb_ip
    api_id = request.args.get('api_id')
    print(api_id)
    test = requests.get(f'http://{ip_address}/{api_id}')
    data = test.json()
    print(data)
    return jsonify(data)




@app.route('/self_check', methods=["GET"])
def self_check():
    global global_sb_ip
    ip_address=global_sb_ip
    print(global_sb_ip)
    test = requests.get(f'http://{ip_address}/self_check_and_turn_on_system')
    data = test.json()
    print(data)
    if test.status_code == 200:
       data = test.json()
       print(data)
    return jsonify(data)





@app.route('/detection', methods=['POST'])
def detection():
    data = request.get_json()
    global detect_confirm_flag
    global detect_flag
    if detect_flag ==True and data['detected'] == True:
        detect_confirm_flag =True
        if return_flag == True and isinstance(log_arm_data, dict) and isinstance(log_dut_data, dict):
            now = datetime.datetime.now()
            formatted_time = now.strftime('%Y-%m-%d %H:%M:%S')
            update_data = {
                    'time': formatted_time,
                  'device': log_sb_data['status'],
                  'status': log_arm_data['status'],
                 'command': log_dut_data['command'],
                'detect_axis': detect_axis
              }
            print(update_data)
            socketio.emit('update_detect',update_data)
    return {'message': 'detection received'}, 200




@app.route('/api/dut', methods=['POST'])
def dut():
    data = request.json
    now = datetime.datetime.now()
    formatted_time = now.strftime('%Y-%m-%d %H:%M:%S')
    global global_dut_ip
    ip_address=global_dut_ip
    servo_1_value = data['servo_1']
    servo_2_value = data['servo_2']
    servo_3_value = data['servo_3']
    servo_4_value = data['servo_4']
    servo_5_value = data['servo_5']
    servo_6_value = data['servo_6']
    test = requests.post(f'http://{ip_address}/set_servo?servo_1={servo_1_value}&servo_2={servo_2_value}&servo_3={servo_3_value}&servo_4={servo_4_value}&servo_5={servo_5_value}&servo_6={servo_6_value}')
    if test.status_code == 200:
             # 解析 JSON 數據
            data = test.json()
            now = datetime.datetime.now()
            formatted_time = now.strftime('%Y-%m-%d %H:%M:%S')
            data['receivedtime'] = formatted_time
            print(data)
    else:
        print("Failed to retrieve data:", test.status_code)
    log_dut_data={
        'time': f"{data['receivedtime']}",
        'device': 'dut機器手臂',
        'command': f'{servo_1_value},{servo_2_value},{servo_3_value},{servo_4_value},{servo_5_value},{servo_6_value}',
        'status': f"{data['servo_dict']['servo_1']},{data['servo_dict']['servo_2']},{data['servo_dict']['servo_3']},{data['servo_dict']['servo_4']},{data['servo_dict']['servo_5']},{data['servo_dict']['servo_6']},{data['temperature']},{data['humidity']},{data['detect']},{data['ip_address']}",
        'detect_axis': ''
        }
    
    data['logs'] = log_dut_data
    return jsonify(data)


@app.route('/api/arm', methods=['POST'])
def arm():
    data = request.json
    now = datetime.datetime.now()
    formatted_time = now.strftime('%Y-%m-%d %H:%M:%S')
    global global_arm_ip
    ip_address=global_arm_ip
    servo_1_value = data['servo_1']
    servo_2_value = data['servo_2']
    servo_3_value = data['servo_3']
    servo_4_value = data['servo_4']
    servo_5_value = data['servo_5'] 
    servo_6_value = data['servo_6']
    test = requests.post(f'http://{ip_address}/set_servo?servo_1={servo_1_value}&servo_2={servo_2_value}&servo_3={servo_3_value}&servo_4={servo_4_value}&servo_5={servo_5_value}&servo_6={servo_6_value}')
    if test.status_code == 200:
             # 解析 JSON 數據
            data = test.json()
            now = datetime.datetime.now()
            formatted_time = now.strftime('%Y-%m-%d %H:%M:%S')
            data['receivedtime'] = formatted_time
    else:
        print("Failed to retrieve data:", test.status_code)
    log_arm_data={
        'time': f"{data['receivedtime']}",
        'device': 'arm機器手臂',
        'command': f'{servo_1_value},{servo_2_value},{servo_3_value},{servo_4_value},{servo_5_value},{servo_6_value}',
        'status': f"{data['servo_dict']['servo_1']},{data['servo_dict']['servo_2']},{data['servo_dict']['servo_3']},{data['servo_dict']['servo_4']},{data['servo_dict']['servo_5']},{data['servo_dict']['servo_6']},{data['temperature']},{data['humidity']},{data['detect']},{data['ip_address']}",
        'detect_axis': ''
        }
    data['logs'] = log_arm_data
    return jsonify(data)


@app.route('/api/sb', methods=['POST'])
def sb():
    now = datetime.datetime.now()
    formatted_time = now.strftime('%Y-%m-%d %H:%M:%S')
    data = request.get_json()
    global global_sb_ip
    ip_address=global_sb_ip
    target_distance=data.get('target_distance')
    test = requests.post(f'http://{ip_address}/move?target_distance={target_distance}')
    if test.status_code == 200:
            data = test.json()
    else:
        print("Failed to retrieve data:", test.status_code)
    if not isinstance(data, dict):
        message=data
        data={
            'location':{
            'track': "",
            'target_distance':"",
            'direction':"",
            },
            'sb_time':"",
            'sb_ip':"",
            'logs':{
                'time': f"{formatted_time}",
                'device': 'sb馬達',
                'command': f'{target_distance}',
                'status': f"{message},{ip_address}",
                'detect_axis': ''
                }
        }
    else:
        data['sb_time'] = formatted_time
        data['sb_ip'] = ip_address
        log_sb_data = {
            'time': data['sb_time'],
            'device': 'sb馬達',
            'command': f'{target_distance}',
            'status': f"{data['location']['target_distance']},{data['location']['direction']},{data['sb_ip']}",
            'detect_axis': ''
        }
        data['logs'] = log_sb_data
    print(data)
    return jsonify(data)




@app.route('/api/button', methods=['POST'])
def button_pressed():
    data = request.get_json()
    button_id = data.get('button_id')
    global global_unet_ip
    ip_address=global_unet_ip
    now = datetime.datetime.now()
    formatted_time = now.strftime('%Y-%m-%d %H:%M:%S')
    received_data = {
        'set_MC026_binding' : 'successfully',
    }
    # 根據button_id處理不同的按鈕請求
#    if button_id == 'bing-btn':
#        test = requests.post(f'http://{ip_address}/set_MC026_binding')
#        if test.status_code == 200:
#            data = test.json()
#            print(data)
#            return jsonify(data)
#        else:
#            print("Failed to retrieve data:", test.status_code)
#    elif button_id == 'test-btn':
#        test = requests.post(f'http://{ip_address}/AN203_ON_OFF_test')
#        if test.status_code == 200:
#            data = test.json()
#            print(data)
#            return jsonify(data)
#        else:
#            print("Failed to retrieve data:", test.status_code)
    if button_id == 'on-btn':
        test = requests.get(f'http://{ip_address}/AN203_ON')
        print(test)
        if test.status_code == 200:
            data = test.json()
            print(data)
            received_data['AN203_ON_OFF_test']='AN203_ON'
        else:
            print("Failed to retrieve data:", test.status_code)
    elif button_id == 'off-btn':
        test = requests.get(f'http://{ip_address}/AN203_OFF')
        print(test)
        if test.status_code == 200:
            data = test.json()
            print(data)
            received_data['AN203_ON_OFF_test']='AN203_OFF'
        else:
            print("Failed to retrieve data:", test.status_code)
    
    received_data['unet_time'] = formatted_time 
    received_data['unet_ip'] = ip_address
    log_unet_data={
        'time': f"{received_data['unet_time']}",
        'device': 'unet_AN203',
        'command': f"{received_data['AN203_ON_OFF_test']}",
        'status': f"{received_data['AN203_ON_OFF_test']},{received_data['unet_ip']}",
        'detect_axis': ''
        }
    received_data['logs'] = log_unet_data
    return jsonify(received_data)



if __name__ == '__main__':
    app.run(host='0.0.0.0',port=13333)
