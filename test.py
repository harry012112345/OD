from flask import Flask, render_template, jsonify, redirect, url_for
import requests

app = Flask(__name__)

# 服务器 IP 列表
server_ips = ['http://server1_ip', 'http://server2_ip', 'http://server3_ip', 'http://server4_ip']

def check_connections():
    for ip in server_ips:
        try:
            response = requests.post(ip)
            if response.status_code != 200:
                return False
        except requests.exceptions.RequestException:
            return False
    return True

@app.route('/')
def index():
    if check_connections():
        return render_template('next_page.html')  # 所有连接成功后显示的页面
    else:
        return redirect(url_for('connection_failed'))

@app.route('/connection_failed')
def connection_failed():
    return render_template('connection_failed.html')  # 连接失败的页面

if __name__ == '__main__':
    app.run(debug=True)