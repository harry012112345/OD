from flask import Flask, request, render_template, jsonify, send_file, redirect, url_for,flash,session
from flask_restful import Api, Resource
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
import queue

app = Flask(__name__)
socketio = SocketIO(app)

UPLOAD_FOLDER = 'C:\\Users\\Harry\\Desktop\\OD\\test_excel'

# 队列用于存储中断的请求
request_queue = queue.Queue()

# 用于存储上传的数据
received_data = []

global_dut_ip=[]
global_arm_ip=[]
global_step_ip=[]
global_unet_ip=[]

temperature_max=0
temperature_min=0
humidity_max=0
humidity_min=0

execute_excel=[]

log_arm_data=[]
log_dut_data=[]
log_step_data=[]
log_unet_data=[]

detect_flag=True
return_flag=False
detect_confirm_flag=False
stop_processing = False

app.secret_key = 'your_secret_key'
users = {'admin': 'admin'}
now = datetime.datetime.now()
formatted_time = now.strftime('%Y-%m-%d %H:%M:%S')
local_ip='192.168.15.108'
server_ips = [f'http://{global_dut_ip}/get_info', f'http://{global_arm_ip}/get_info', f'http://{global_step_ip}/get_info', f'http://{global_step_ip}/get_info']

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
    # 初始化结果字典
    result = {}

    # 处理servo
    for i in range(1, 7):
        check_key = f'check_servo_{i}'
        servo_key = f'servo_{i}'
        if input_data.get(check_key) == 'true':
            result[servo_key] = input_data[servo_key]

    # 处理arm_servo
    for i in range(1, 7):
        check_key = f'check_arm_servo_{i}'
        arm_servo_key = f'arm_servo_{i}'
        if input_data.get(check_key) == 'true':
            result[arm_servo_key] = input_data[arm_servo_key]

    file =input_data['file']
    excel_file = os.path.join(UPLOAD_FOLDER, file)
    # 读取 Excel 数据到 DataFrame
    df = pd.read_excel(excel_file)

# 更新 DataFrame 中的多行
    for index, row in df.iterrows():
        row_value = row.iloc[0]  # 读取 row[0] 的值
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

def detection_thread(detect_time):
    global detect_flag
    time.sleep(detect_time)
    detect_flag = False

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



@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in users and users[username] == password:
            session['username'] = username
            return render_template('ip_confirm.html')
        else:
            flash('Invalid username or password!')
    return render_template('login.html')

@app.route('/check_connections', methods=['GET'])
async def check_connections():
    global global_dut_ip, global_arm_ip, global_step_ip, global_unet_ip
    ip_addresses = load_ips_from_file()
    global_arm_ip = ip_addresses.get('arm_server', 'Not found')
    global_dut_ip = ip_addresses.get('dut_server', 'Not found')
    global_step_ip = ip_addresses.get('step_server', 'Not found')
    global_unet_ip = ip_addresses.get('unet_server', 'Not found')
    
    server_ips = {
        'arm_server': f'http://{global_arm_ip}/get_info',
        'dut_server': f'http://{global_dut_ip}/get_info',
        'step_server': f'http://{global_step_ip}/get_info',
        'unet_server': f'http://{global_unet_ip}/get_info'
    }

    results = await check_all_connections(server_ips)
    return jsonify(results)

@app.route('/welcome')
def welcome():
    if 'username' not in session:
        return redirect(url_for('login'))
    username=session['username']
    global global_dut_ip,global_arm_ip,global_step_ip,global_unet_ip
    ip_addresses = load_ips_from_file()
    global_arm_ip = ip_addresses.get('arm_server', 'Not found')
    global_dut_ip = ip_addresses.get('dut_server', 'Not found')
    global_step_ip = ip_addresses.get('step_server', 'Not found')
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
    global global_dut_ip,global_arm_ip,global_step_ip,global_unet_ip
    global_arm_ip = ip_addresses.get('arm_server', 'Not found')
    global_dut_ip = ip_addresses.get('dut_server', 'Not found')
    global_step_ip = ip_addresses.get('step_server', 'Not found')
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
    global global_dut_ip,global_arm_ip,global_step_ip,global_unet_ip
    global_arm_ip = ip_addresses.get('arm_server', 'Not found')
    global_dut_ip = ip_addresses.get('dut_server', 'Not found')
    global_step_ip = ip_addresses.get('step_server', 'Not found')
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
#    step_value = data['real_position']
#    
#    now = datetime.datetime.now()
#    formatted_time = now.strftime('%Y-%m-%d %H:%M:%S')
#
#    test_1_url = f'http://{global_dut_ip}/set_servo?servo_1={dut_servo_1}&servo_2={dut_servo_2}&servo_3={dut_servo_3}&servo_4={dut_servo_4}&servo_5={dut_servo_5}&servo_6={dut_servo_6}'
#    test_2_url = f'http://{global_arm_ip}/set_servo?servo_1={arm_servo_1}&servo_2={arm_servo_2}&servo_3={arm_servo_3}&servo_4={arm_servo_4}&servo_5={arm_servo_5}&servo_6={arm_servo_6}'
#    test_3_url = f'http://{global_step_ip}/set_distance?position={step_value}'
#
#    # 并发执行所有请求
#    responses = await asyncio.gather(
#        send_request(test_1_url),
#        send_request(test_2_url),
#        send_request(test_3_url)
#    )
#
#
#    # 处理 test_1 的响应
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
#    # 处理 test_2 的响应
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
#    # 处理 test_3 的响应
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
    execute_excel = data['file']
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
    step_value = data['real_position']
    unet_status = data['check_unet']
    global temperature_max,temperature_min,humidity_max,humidity_min
    temperature_max = float(data['temperature-max'])
    temperature_min = float(data['temperature-min'])
    humidity_max = float(data['humidity-max'])
    humidity_min = float(data['humidity-min'])
    new_data = [
        ['dut_server', dut_servo_1, dut_servo_2, dut_servo_3, dut_servo_4, dut_servo_5, dut_servo_6, 1, 'no'],
        ['arm_server', arm_servo_1, arm_servo_2, arm_servo_3, arm_servo_4, arm_servo_5, arm_servo_6, 1, 'no'],
        ['step_server', step_value, None, None, None, None, None, 1, 'no'],
        ['unet_server', unet_status, None, None, None, None, None, 1, 'no']
    ]
    new_df = pd.DataFrame(new_data, columns=[
        'server_name', 'parameter_1', 'parameter_2', 'parameter_3', 'parameter_4',
        'parameter_5', 'parameter_6', 'delay_time', 'active_detection'
    ])
    excel_file = os.path.join(UPLOAD_FOLDER, execute_excel)
    # 读取 Excel 数据到 DataFrame
    df = pd.read_excel(excel_file)
    df.iloc[:4] = new_df
    df.to_excel(excel_file, index=False)

    check_init_data(data)
    test_1_url = f'http://{global_dut_ip}/set_servo?servo_1={dut_servo_1}&servo_2={dut_servo_2}&servo_3={dut_servo_3}&servo_4={dut_servo_4}&servo_5={dut_servo_5}&servo_6={dut_servo_6}'
    test_2_url = f'http://{global_arm_ip}/set_servo?servo_1={arm_servo_1}&servo_2={arm_servo_2}&servo_3={arm_servo_3}&servo_4={arm_servo_4}&servo_5={arm_servo_5}&servo_6={arm_servo_6}'
    test_3_url = f'http://{global_step_ip}/set_distance?position={step_value}'
    test_4_url = f'http://{global_unet_ip}/AN203_{unet_status}'
    # 并发执行所有请求
    responses = await asyncio.gather(
        send_request(test_1_url),
        send_request(test_2_url),
        send_request(test_3_url),
        send_request(test_4_url)
    )
  
#    now = datetime.datetime.now()
#    formatted_time = now.strftime('%Y-%m-%d %H:%M:%S')
#    # 处理 test_1 的响应
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
#    # 处理 test_2 的响应
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
#    #    socketio.emit('update_result',test_2_data)
#
#    # 处理 test_3 的响应
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
#    #    socketio.emit('update_result',test_3_data)
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
    formatted_time = now.strftime('%Y-%m-%d %H:%M:%S')
    data={
          'time': formatted_time,
        'device': '開始處理'
        }
    emit('start_button',data)
    excel_file = os.path.join(UPLOAD_FOLDER, execute_excel)
    df = pd.read_excel(excel_file)
    global return_flag
    global detect_confirm_flag
    global detect_flag
    for index, row in df.iterrows():
        if stop_processing ==True:
            break
        return_flag=False
        detect_confirm_flag=False
        delay_time=row['delay_time']
        server_type = row['server_name']
        active_detection = row['active_detection'].split(',')
        if active_detection[0] == 'yes':
           detect_flag = True
           detect_time = int(active_detection[1])
           detect_thread = Thread(target=detection_thread, args=(detect_time,))
           detect_thread.start()
        else:
           detect_flag = False
        try:
            if row[0] == "dut_server":
             param1 = str(row['parameter_1'])
             param2 = str(row['parameter_2'])
             param3 = str(row['parameter_3'])
             param4 = str(row['parameter_4'])
             param5 = str(row['parameter_5'])
             param6 = str(row['parameter_6'])
             global global_dut_ip
             ip_address=global_dut_ip
             url=f'http://{ip_address}/set_servo?servo_1={param1}&servo_2={param2}&servo_3={param3}&servo_4={param4}&servo_5={param5}&servo_6={param6}'
             test = requests.post(url)
             if test.status_code == 200:
                 # 解析 JSON 数据
                data = test.json()
                now = datetime.datetime.now()
                formatted_time = now.strftime('%Y-%m-%d %H:%M:%S')
                data['receivedtime'] = formatted_time
                data['server_type'] = server_type
                global log_dut_data
                log_dut_data={
                'time': f'{data['receivedtime']}',
                'device': 'dut機器手臂',
                'command': f'{param1},{param2},{param3},{param4},{param5},{param6}',
                'status': f'{data['servo_dict']['servo_1']},{data['servo_dict']['servo_2']},{data['servo_dict']['servo_3']},{data['servo_dict']['servo_4']},{data['servo_dict']['servo_5']},{data['servo_dict']['servo_6']},{data['temperature']},{data['humidity']},{data['detect']},{data['ip_address']}',
                'operator': 'Frank'
                }
                data['logs'] = log_dut_data   
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
             test = requests.post(url)
             if test.status_code == 200:
                 # 解析 JSON 数据
                data = test.json()
                now = datetime.datetime.now()
                formatted_time = now.strftime('%Y-%m-%d %H:%M:%S')
                data['receivedtime'] = formatted_time
                data['server_type'] = server_type
                global log_arm_data
                log_arm_data={
                'time': f'{data['receivedtime']}',
                'device': 'arm機器手臂',
                'command': f'{param1},{param2},{param3},{param4},{param5},{param6}',
                'status': f'{data['servo_dict']['servo_1']},{data['servo_dict']['servo_2']},{data['servo_dict']['servo_3']},{data['servo_dict']['servo_4']},{data['servo_dict']['servo_5']},{data['servo_dict']['servo_6']},{data['temperature']},{data['humidity']},{data['detect']},{data['ip_address']}',
                'operator': 'Frank'
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
            elif row[0] == "step_server":
             param1 = str(row['parameter_1'])
             global global_step_ip
             ip_address=global_step_ip
             url=f'http://{ip_address}/set_distance?position={param1}'
             test = requests.post(url)
             if test.status_code == 200:
                 # 解析 JSON 数据
                data = test.json()
                now = datetime.datetime.now()
                formatted_time = now.strftime('%Y-%m-%d %H:%M:%S')
                data['server_type'] = server_type
                data['step_time'] = formatted_time
                data['step_ip'] = ip_address
                global log_step_data
                log_step_data = {
                    'time': data['step_time'],
                    'device': 'step馬達',
                    'command': f'往前{param1}(cm)',
                    'status': f'{data['real_position']},{data['step_ip']}',
                    'operator': 'Frank'
                }
                data['logs'] = log_step_data   
            elif row[0] == "unet_server":
             param1 = str(row['parameter_1'])
             ip_address=global_unet_ip
             url=f'http://{ip_address}/AN203_{param1}'
             test = requests.post(url)
             if test.status_code == 200:
                 # 解析 JSON 数据
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
                'time': f'{data['unet_time']}',
                'device': 'unet_AN203',
                'command': f'{data['AN203_ON_OFF_test']}',
                'status': f'{data['AN203_ON_OFF_test']},{data['unet_ip']}',
                'operator': 'Frank'
                }
                data['logs'] = log_unet_data
            # 模拟一些处理时间
            # 将结果发送给客户端
            emit('update_result',data)
            return_flag=True
            if return_flag == True and detect_confirm_flag == True and isinstance(log_arm_data, dict) and isinstance(log_dut_data, dict):
                now = datetime.datetime.now()
                formatted_time = now.strftime('%Y-%m-%d %H:%M:%S')
                update_data = {
                    'time': formatted_time,
                  'device': log_step_data['status'].split(',')[0],
                  'status': log_arm_data['status'],
                 'command': log_dut_data['command'],
                'operator': 'Frank'
              }
                emit('update_detect',update_data)
            time.sleep(delay_time)
            if active_detection[0] == 'yes':
                detect_thread.join()
        except requests.RequestException as e:
            connection_break_flag=True
            print(f"请求失败: {e}")
            # 处理 POST 请求失败
            now = datetime.datetime.now()
            formatted_time = now.strftime('%Y-%m-%d %H:%M:%S')
            data={
                  'time': formatted_time,
                'device': 'connection fail'
                }
            emit('connection_fail',data)
            # 对四个服务器发送 get_info 请求
            servers = {
                'dut': global_dut_ip,
                'arm': global_arm_ip,
                'step': global_step_ip,
                'unet': global_unet_ip
            }
            for server_name, ip in servers.items():
                try:
                    info_response = requests.get(f'http://{ip}/get_info')
                    info_response.raise_for_status()
                    if info_response.status_code == 200:
                        print(f"{server_name} 服务器正常")
                except requests.RequestException:
                    # 服务器未响应，弹出提示窗口
                    emit('show_popup', {'server': server_name, 'status': '需要重启'})
                    # 继续尝试请求直到收到响应
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
            if active_detection[0] == 'yes':
               detect_flag = True
               detect_time = int(active_detection[1])
               detect_thread = Thread(target=detection_thread, args=(detect_time,))
               detect_thread.start()
            else:
               detect_flag = False
            test = requests.post(url)
            data = test.json()
            now = datetime.datetime.now()
            formatted_time = now.strftime('%Y-%m-%d %H:%M:%S')
            data['receivedtime'] = formatted_time
            data['server_type'] = server_type
            if data['name']=='dut_server':
               log_dut_data={
               'time': f'{data['receivedtime']}',
               'device': 'dut機器手臂',
               'command': f'{param1},{param2},{param3},{param4},{param5},{param6}',
               'status': f'{data['servo_dict']['servo_1']},{data['servo_dict']['servo_2']},{data['servo_dict']['servo_3']},{data['servo_dict']['servo_4']},{data['servo_dict']['servo_5']},{data['servo_dict']['servo_6']},{data['temperature']},{data['humidity']},{data['detect']},{global_dut_ip}',
               'operator': 'Frank'
               }
               data['logs'] = log_dut_data 
            elif data['name']=='arm_server':
                log_arm_data={
                'time': f'{data['receivedtime']}',
                'device': 'arm機器手臂',
                'command': f'{param1},{param2},{param3},{param4},{param5},{param6}',
                'status': f'{data['servo_dict']['servo_1']},{data['servo_dict']['servo_2']},{data['servo_dict']['servo_3']},{data['servo_dict']['servo_4']},{data['servo_dict']['servo_5']},{data['servo_dict']['servo_6']},{data['temperature']},{data['humidity']},{data['detect']},{global_arm_ip}',
                'operator': 'Frank'
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
            elif data['name']=='step_server':
                log_step_data = {
                    'time': data['receivedtime'],
                    'device': 'step馬達',
                    'command': f'往前{param1}(cm)',
                    'status': f'{data['real_position']},{global_step_ip}',
                    'operator': 'Frank'
                }
                data['logs'] = log_step_data
            elif data['name']=='unet_server':
                data['AN203_ON_OFF_test']=f'AN203_{param1}'
                log_unet_data={
                'time': f'{data['receivedtime']}',
                'device': 'unet_AN203',
                'command': f'{data['AN203_ON_OFF_test']}',
                'status': f'{data['AN203_ON_OFF_test']},{global_unet_ip}',
                'operator': 'Frank'
                }
                data['logs'] = log_unet_data
                # 模拟一些处理时间
                # 将结果发送给客户端
            emit('update_result',data)
            return_flag=True
            if return_flag == True and detect_confirm_flag == True and isinstance(log_arm_data, dict) and isinstance(log_dut_data, dict):
                now = datetime.datetime.now()
                formatted_time = now.strftime('%Y-%m-%d %H:%M:%S')
                update_data = {
                    'time': formatted_time,
                  'device': log_step_data['status'].split(',')[0],
                  'status': log_arm_data['status'],
                 'command': log_dut_data['command'],
                'operator': 'Frank'
              }
                emit('update_detect',update_data)
            time.sleep(delay_time)
            if active_detection[0] == 'yes':
                detect_thread.join()
            # 继续执行当前任务
            return_flag = False

@socketio.on('stop_processing')
def handle_stop_processing():
    global stop_processing
    stop_processing = True
    emit('processing_stopped', {'status': 'Process stopped'})


@app.route('/receive_ip', methods=["POST"])
def receive_ip():
    if request.is_json:
        data = request.get_json()
        ip_addresses = load_ips_from_file()

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

            elif name == 'step_server':
                global global_step_ip
                global_step_ip = ip_address
                ip_addresses['step_server'] = global_step_ip

            elif name == 'unet_server':
                global global_unet_ip
                global_unet_ip = ip_address
                ip_addresses['unet_server'] = global_unet_ip

            save_ips_to_file(ip_addresses)

        response_data = {'message': "IP address received successfully", 'ip_received': ip_address}
        return jsonify(response_data)
    else:
        return jsonify({'error': 'Invalid JSON format'}), 400
 
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
                  'device': log_step_data['status'].split(',')[0],
                  'status': log_arm_data['status'],
                 'command': log_dut_data['command'],
                'operator': 'Frank'
              }
            print(update_data)
            socketio.emit('update_detect',update_data)
    socketio.emit('led_trigger', {'status': 'triggered'})
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
             # 解析 JSON 数据
            data = test.json()
            now = datetime.datetime.now()
            formatted_time = now.strftime('%Y-%m-%d %H:%M:%S')
            data['receivedtime'] = formatted_time
            print(data)
    else:
        print("Failed to retrieve data:", test.status_code)
    log_dut_data={
        'time': f'{data['receivedtime']}',
        'device': 'dut機器手臂',
        'command': f'{servo_1_value},{servo_2_value},{servo_3_value},{servo_4_value},{servo_5_value},{servo_6_value}',
        'status': f'{data['servo_dict']['servo_1']},{data['servo_dict']['servo_2']},{data['servo_dict']['servo_3']},{data['servo_dict']['servo_4']},{data['servo_dict']['servo_5']},{data['servo_dict']['servo_6']},{data['temperature']},{data['humidity']},{data['detect']},{data['ip_address']}',
        'operator': 'Frank'
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
             # 解析 JSON 数据
            data = test.json()
            now = datetime.datetime.now()
            formatted_time = now.strftime('%Y-%m-%d %H:%M:%S')
            data['receivedtime'] = formatted_time
    else:
        print("Failed to retrieve data:", test.status_code)
    log_arm_data={
        'time': f'{data['receivedtime']}',
        'device': 'arm機器手臂',
        'command': f'{servo_1_value},{servo_2_value},{servo_3_value},{servo_4_value},{servo_5_value},{servo_6_value}',
        'status': f'{data['servo_dict']['servo_1']},{data['servo_dict']['servo_2']},{data['servo_dict']['servo_3']},{data['servo_dict']['servo_4']},{data['servo_dict']['servo_5']},{data['servo_dict']['servo_6']},{data['temperature']},{data['humidity']},{data['detect']},{data['ip_address']}',
        'operator': 'Frank'
        }
    data['logs'] = log_arm_data
    return jsonify(data)


@app.route('/api/step', methods=['POST'])
def step():
    now = datetime.datetime.now()
    formatted_time = now.strftime('%Y-%m-%d %H:%M:%S')
    data = request.get_json()
    global global_step_ip
    ip_address=global_step_ip
    in_real_position=data.get('real_position')
    test = requests.post(f'http://{ip_address}/set_distance?position={in_real_position}')
    if test.status_code == 200:
            data = test.json()
    else:
        print("Failed to retrieve data:", test.status_code)
    data['step_time'] = formatted_time
    data['step_ip'] = ip_address
    print(data)
    log_step_data = {
        'time': data['step_time'],
        'device': 'step馬達',
        'command': f'往前{in_real_position}(cm)',
        'status': f'{data['real_position']},{data['step_ip']}',
        'operator': 'Frank'
    }
    data['logs'] = log_step_data
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
        'time': f'{received_data['unet_time']}',
        'device': 'unet_AN203',
        'command': f'{received_data['AN203_ON_OFF_test']}',
        'status': f'{received_data['AN203_ON_OFF_test']},{received_data['unet_ip']}',
        'operator': 'Frank'
        }
    received_data['logs'] = log_unet_data
    return jsonify(received_data)



if __name__ == '__main__':
    app.run(host='0.0.0.0')
