#!/bin/bash
# EC2 launch template user-data: bootstraps an instance to run the producer
# (paced replay into Kinesis) and the Flask dashboard as systemd services.
set -e

yum install -y python3 python3-pip git || apt-get update && apt-get install -y python3 python3-pip git

cd /opt
git clone "${REPO_URL:-https://github.com/REPLACE_ME/bus-reliability-platform.git}" app
cd app
pip3 install -r requirements.txt

cat > /etc/systemd/system/bus-producer.service << 'EOF'
[Unit]
Description=Bus Reliability Producer
After=network.target

[Service]
WorkingDirectory=/opt/app
Environment=STREAM_BACKEND=kinesis
ExecStart=/usr/bin/python3 -m producer.producer
Restart=always

[Install]
WantedBy=multi-user.target
EOF

cat > /etc/systemd/system/bus-flask.service << 'EOF'
[Unit]
Description=Bus Reliability Dashboard
After=network.target

[Service]
WorkingDirectory=/opt/app
Environment=PORT=80
ExecStart=/usr/bin/python3 -m flask_api.app
Restart=always

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now bus-producer bus-flask
