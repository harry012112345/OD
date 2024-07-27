from flask import Flask, render_template, jsonify, redirect, url_for
import requests
from flask import Flask, request, render_template, jsonify, send_file, redirect, url_for,flash,session
import os
import aiohttp
import asyncio
app = Flask(__name__)

global_dut_ip=[]
global_arm_ip=[]
global_step_ip=[]
global_unet_ip=[]

# 服务器 IP 列表

def save_ips_to_file(ip_addresses):
    with open('ip_addresses.txt', 'w') as file:
        for name, ip in ip_addresses.items():
            file.write(f"{name}: {ip}\n")

async def check_connection(ip):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(ip) as response:
                if response.status != 200:
                    return False
                return True
    except Exception as e:
        print(f"Request failed for {ip} with exception: {e}")
        return False

async def check_connections():
    server_ips = [
        f'http://{global_arm_ip}/get_info',
        f'http://{global_dut_ip}/get_info',
        f'http://{global_step_ip}/get_info',
        f'http://{global_unet_ip}/get_info'
    ]
    tasks = [check_connection(ip) for ip in server_ips]
    results = await asyncio.gather(*tasks)
    return all(results)

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

@app.route('/')
async def index():
    global global_dut_ip,global_arm_ip,global_step_ip,global_unet_ip
    ip_addresses = load_ips_from_file()
    global_arm_ip = ip_addresses.get('arm_server', 'Not found')
    global_dut_ip = ip_addresses.get('dut_server', 'Not found')
    global_step_ip = ip_addresses.get('step_server', 'Not found')
    global_unet_ip = ip_addresses.get('unet_server', 'Not found')
    if await check_connections():
        return render_template('next_page.html')  # 所有连接成功后显示的页面
    else:
        return redirect(url_for('connection_failed'))

@app.route('/connection_failed')
def connection_failed():
    return render_template('connection_failed.html')  # 连接失败的页面

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

if __name__ == '__main__':
    app.run(host='0.0.0.0')