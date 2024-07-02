from flask import Flask, request, render_template, jsonify, send_file, redirect, url_for,flash,session
from flask_restful import Api, Resource
import json
import requests
import csv
import io
import os
import datetime

app = Flask(__name__)
api = Api(app)

# 用于存储上传的数据
received_data = []

app.secret_key = 'your_secret_key'
users = {'admin': 'admin'}

class ClientServer(Resource):
    def __init__(self):
        self.setup_routes()

    def setup_routes(self):
        self.app.add_url_rule('/', view_func=self.index)
        self.app.add_url_rule('/submit', view_func=self.submit, methods=['POST'])

    def index(self):
        return render_template('index.html')

#communication set_server

    def submit(self):
        data = {
        'servo_1': request.form.get('servo_1'),
        'servo_2': request.form.get('servo_2'),
        'servo_3': request.form.get('servo_3'),
        'servo_4': request.form.get('servo_4'),
        'servo_5': request.form.get('servo_5'),
        'servo_6': request.form.get('servo_6')
        }




class ReceiveData(Resource):
    def post(self):
#        data = request.json
#        ip_address = data.get('ip_address')
#        self.process_data(data, ip_address)
#
#    def process_data(self, data, ip):
#        # 根据 IP 地址执行不同的处理逻辑
#        if ip == '192.168.15.102':
#            self.handle_ip_1(data)
#        elif ip == '192.168.15.100':
#            self.handle_ip_2(data)
#
#    def handle_ip_2(self, data):
#        print(data)
#
#
#    def handle_ip_1(self, data):
        data = request.json
        servo_1_value = data['servo_1']
        servo_2_value = data['servo_2']
        servo_3_value = data['servo_3']
        servo_4_value = data['servo_4']
        servo_5_value = data['servo_5']
        servo_6_value = data['servo_6']

        test = requests.post(f'http://192.168.15.102/set_servo?servo_1={servo_1_value}&servo_2={servo_2_value}&servo_3={servo_3_value}&servo_4={servo_4_value}&servo_5={servo_5_value}&servo_6={servo_6_value}')
  #      print(data)
     #   print(f"""servo_1={servo_1}&servo_2={servo_2}&servo_3={servo_3}&servo_4={servo_4}&servo_5={servo_5}&servo_6={servo_6}""")
            # 提取各个键的值
        #    data = json.loads(response.get_data(as_text=True))
        #    servo_1_value = data['servo_1']
        #    servo_2_value = data['servo_2']
        #    servo_3_value = data['servo_3']
        #    servo_4_value = data['servo_4']
        #    servo_5_value = data['servo_5']
        #    servo_6_value = data['servo_6']
        #    print(f'servo_1={servo_1_value}&servo_2={servo_2_value}&servo_3={servo_3_value}&servo_4={servo_4_value}&servo_5={servo_5_value}&servo_6={servo_6_value}')
        #    print(response.get_data(as_text=True))  # 打印实际的 JSON 数据内容
        #    test = requests.get(f'http://192.168.15.100/set_servo?servo_1={servo_1_value}&servo_2={servo_2_value}&servo_3={servo_3_value}&servo_4={servo_4_value}&servo_5={servo_5_value}&servo_6={servo_6_value}')
          #   http://192.168.15.100/set_servo?servo_1=5&servo_2=5&servo_3=5&servo_4=5&servo_5=5&servo_6=5
        if test.status_code == 200:
             # 解析 JSON 数据
            data = test.json()
            received_data.append(data)
            #   receivedtime=time.time()
            now = datetime.datetime.now()
            formatted_time = now.strftime('%Y-%m-%d %H:%M:%S')
            data['receivedtime'] = formatted_time
            print(data)
            test = requests.post(f'http://192.168.15.100/set_MC026_binding')
            if test.status_code == 200:
                print(received_data)
                data = test.json()
                received_data.append(data)
                return jsonify(received_data)
            else:
                print("Failed to retrieve data:", test.status_code)
                # 存储为CSV文件
#               file_path = 'uploads/received_data.csv'
#               os.makedirs(os.path.dirname(file_path), exist_ok=True)
#               with open(file_path, 'w', newline='') as csvfile:
#                fieldnames = ['servo_1', 'servo_2', 'servo_3', 'servo_4', 'servo_5', 'servo_6','temperature','humidity','ip_address','detect','set_servo','receivedtime']
#                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
#                writer.writeheader()
#                writer.writerow({
#                'servo_1': data['servo_dict']['servo_1'],
#                'servo_2': data['servo_dict']['servo_2'],
#                'servo_3': data['servo_dict']['servo_3'],
#                'servo_4': data['servo_dict']['servo_4'],
#                'servo_5': data['servo_dict']['servo_5'],
#                'servo_6': data['servo_dict']['servo_6'],
#                'temperature': data['temperature'],
#                'humidity': data['humidity'],
#                'ip_address': data['ip_address'],
#                'detect': data['detect'],
#                'set_servo': data['set_servo'],
#                'receivedtime' : data['receivedtime']
#                })
 #           response = jsonify(data)
 #              print("Received data:", data)
            return jsonify(data)  # 返回接收到的数据
    #       {'receivedtime': formatted_time} 
        else:
               print("Failed to retrieve data:", test.status_code)
    


@app.route('/')
def index():
    return redirect(url_for('login'))
#    return render_template('index.html', received_data=received_data)

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
        ip_address = data.get('ip_address')
        print(data)
#        print(f"Received IP address: {ip_address}")
        response_data = {'message': "IP address received successfully", 'ip_received': ip_address}
        return jsonify(response_data)
    else:
        return jsonify({'error': 'Invalid JSON format'}), 400
    
    


api.add_resource(ClientServer, '/api/generate')
api.add_resource(ReceiveData, '/api/receive')


if __name__ == '__main__':
    app.run(host='0.0.0.0')
