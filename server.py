from flask import Flask, request, jsonify, abort
from flask_sqlalchemy import SQLAlchemy

import requests


app = Flask(__name__)

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///new_db.sqlite3'

db = SQLAlchemy(app)

class Device(db.Model):
    __tablename__ = 'devices'

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(20))
    ip_address = db.Column(db.String(39))
    port = db.Column(db.String(5), default='80')
    status = db.Column(db.String(7), default='unknown', nullable=False)

    def __repr__(self):
        return '<Device {}, status : {}>'.format(self.ip_address, self.status)
    
    def to_dict(self):
        device = {
            'id': self.id,
            'type': self.type,
            'ip_address': self.ip_address,
            'port': self.port,
            'status': self.status,
        }
        return device

# Delete old database
db.drop_all()

# Create the database
db.create_all()

# Add the trusted devices
newDevice1 = Device(ip_address='192.168.1.3', port='3000', status='trusted')
newDevice2 = Device(ip_address='192.168.1.4', port='3000', status='trusted')
db.session.add(newDevice1)
db.session.add(newDevice2)
db.session.commit()

# A function for sending request for all trusted devices to add a device 
def tell_all_trusted_devices(device, current_device_IP):
    trusted_devices = Device.query.filter_by(status='trusted')
    for trusted_device in trusted_devices:
        if trusted_device.ip_address != current_device_IP:
            res = requests.post(
                'http://' + trusted_device.ip_address + ':' + trusted_device.port + '/add/' + device.ip_address + '/' + device.status
            )


@app.route('/', methods=['GET'])
def test():
    current_device_IP = request.remote_addr
    return jsonify({ 'msg': "success", 'Your IP': current_device_IP })

@app.route('/<event>/<address>', methods=['GET'])
def authenticate_ip(event, address):
    current_device_IP = request.remote_addr

    # Authenticate the current device
    currentDevice = Device.query.filter_by(ip_address=current_device_IP).first()
    if currentDevice:
        if currentDevice.status == 'blocked':
            abort(401)

    # Find device with this ip in the database
    device = Device.query.filter_by(ip_address=address).first()
    if device:
        if (device.status != 'trusted' and event == 'abnormal') or  device.status == 'blocked':
            device.status = 'blocked'
            db.session.commit()
    else:
        # Add new device to database
        if event == 'abnormal':
            device = Device(ip_address=address, status='blocked')
        else:
            device = Device(ip_address=address)

        db.session.add(device)
        db.session.commit()

    tell_all_trusted_devices(device, current_device_IP)
    return jsonify({ 'device': device.to_dict() })

@app.route('/test/<event>', methods=['GET'])
def direct_authenticate_ip(event):
    current_device_IP = request.remote_addr

    # Authenticate the current device
    currentDevice = Device.query.filter_by(ip_address=current_device_IP).first()
    if currentDevice:
        if currentDevice.status == 'blocked':
            abort(401)

        elif currentDevice.status != 'trusted' and event == 'abnormal':
            currentDevice.status = 'blocked'
            db.session.commit()

            tell_all_trusted_devices(currentDevice, current_device_IP)
            abort(401)
        else:
            return jsonify({ 'message': "Hi, you're welcome :)" })
    else:
        # Add new device to database
        if (event == 'abnormal'):
            currentDevice = Device(ip_address=current_device_IP, status='blocked')
        else:
            currentDevice = Device(ip_address=current_device_IP)

        db.session.add(currentDevice)
        db.session.commit()

        tell_all_trusted_devices(currentDevice, current_device_IP)

        if (currentDevice.status == 'blocked'):
            abort(401)
        else:
            return jsonify({ 'message': "Hi, you're welcome :)" })


# Helpers endpoints
@app.route('/all', methods=['GET'])
def get_all_devices():
    # Get all devices in the database
    devices = Device.query.all()
    data = {
        'devices': [device.to_dict() for device in devices]
    }

    return jsonify(data)

@app.route('/add/<address>/<status>', methods=['GET', 'POST'])
def add_new_device(address, status):
    # Find device with this ip in the database
    device = Device.query.filter_by(ip_address=address).first()
    if device:
        device.status = status
        return jsonify({
            'msg': 'Already exist in the database, but status is changed!',
            'device': device.to_dict()
        }), 204

    # Add new device to database
    newDevice = Device(ip_address=address, status=status)
    db.session.add(newDevice)
    db.session.commit()

    return jsonify({ 'added': newDevice.to_dict() }), 201

@app.route('/add/me', methods=['GET', 'POST'])
def add_me():
    current_device_IP = request.remote_addr
    # Find device with this ip in the database
    device = Device.query.filter_by(ip_address=current_device_IP).first()
    if device:
        return jsonify({ 
            'msg': 'You are already exist in the database',
            'device': device.to_dict()
        }), 303

    # Add new device to database
    newDevice = Device(ip_address=current_device_IP)
    db.session.add(newDevice)
    db.session.commit()

    return jsonify({ 'added': newDevice.to_dict() }), 201

@app.route('/delete/<address>', methods=['GET', 'POST'])
def delete_device(address):
    # Find device with this ip in the database
    device = Device.query.filter_by(ip_address=address).first()
    if device:
        # Delete the device from database
        db.session.delete(device)
        db.session.commit()

        return jsonify({ 'deleted': device.to_dict() }), 201

    return jsonify({ 'msg': 'Not exist in the database', 'address': address }), 303


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)  # important to mention debug=True
    # app.run(debug=True)
