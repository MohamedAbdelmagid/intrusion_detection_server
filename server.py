from flask import Flask, request, jsonify, abort
from flask_sqlalchemy import SQLAlchemy


app = Flask(__name__)

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///new_db.sqlite3'

db = SQLAlchemy(app)

class Device(db.Model):
    __tablename__ = 'devices'

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(20))
    ip_address = db.Column(db.String(39))
    port = db.Column(db.String(5))
    status = db.Column(db.String(7), default='unknown', nullable=False)

    def __repr__(self):
        return '<Device {}, class as {}>'.format(self.ip_address, self.status)
    
    def to_dict(self):
        device = {
            'id': self.id,
            'type': self.type,
            'ip_address': self.ip_address,
            'port': self.port,
            'status': self.status,
        }
        return device


@app.route('/<address>/<event>', methods=['GET'])
def authenticate_ip(address, event):
    current_device_IP = request.remote_addr
    print(current_device_IP)

    # Authenticate the current device
    currentDevice = Device.query.filter_by(ip_address=current_device_IP).first()
    if currentDevice:
        if currentDevice.status == 'blocked':
            abort(401)

    # Find device with this ip in the database
    device = Device.query.filter_by(ip_address=address).first()
    if device:
        if device.status != 'trusted' and event == 'abnormal':
            device.status = 'blocked'
            db.session.commit()

        return jsonify({ 'device': device.to_dict() })
    else:
        # Add new device to database
        newDevice = Device(ip_address=address)
        db.session.add(newDevice)
        db.session.commit()

        return jsonify({ 'device': newDevice.to_dict() })

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
        return jsonify({
            'msg': 'Already exist in the database',
            'address': address
        }), 303

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
    app.run(host='0.0.0.0', port=80)  # important to mention debug=True
    # app.run(debug=True)
