from flask import Flask, request, render_template, jsonify, send_file, redirect, url_for,flash,session
from flask_restful import Api, Resource
from flask_socketio import SocketIO, emit
import json
import requests
import csv
import io
import os
import datetime

app = Flask(__name__)
socketio = SocketIO(app)

# 用于存储上传的数据
received_data = []

global_dut_ip=[]
global_arm_ip=[]
global_step_ip=[]
global_unet_ip=[]

app.secret_key = 'your_secret_key'
users = {'admin': 'admin'}

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
            return redirect(url_for('welcome'))
        else:
            flash('Invalid username or password!')
    return render_template('login.html')

now = datetime.datetime.now()
formatted_time = now.strftime('%Y-%m-%d %H:%M:%S')
local_ip='192.168.15.108'

@app.route('/welcome')
def welcome():
    if 'username' not in session:
        return redirect(url_for('login'))
    username=session['username']
    return render_template('welcome.html',formatted_time=formatted_time,username=username,local_ip=local_ip)

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))
    username=session['username']
    return render_template('index.html', received_data=received_data,formatted_time=formatted_time,username=username,local_ip=local_ip)



@app.route('/receive_ip', methods=["POST"])
def receive_ip():
    if request.is_json:
        data = request.get_json()
        if data["name"] == 'arm_server':
            ip_address = data.get('ip_address')
            global global_arm_ip
            global_arm_ip=ip_address
        elif data["name"] == 'dut_server':
            ip_address = data.get('ip_address')
            global global_dut_ip
            global_dut_ip=ip_address
        elif data["name"] == 'step_server':
            ip_address = data.get('ip_address')
            global global_step_ip
            global_step_ip=ip_address
        elif data["name"] == 'unet_server':
            ip_address = data.get('ip_address')
            global global_unet_ip
            global_unet_ip=ip_address
        response_data = {'message': "IP address received successfully", 'ip_received': ip_address}
        return jsonify(response_data)
    else:
        return jsonify({'error': 'Invalid JSON format'}), 400

@app.route('/detection', methods=['POST'])
def detection():
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
