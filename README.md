# Hardware installation

## Install required software

On the Raspberry Pi's terminal

1. Update dependencies
```
sudo apt-get update
```
2. Install Python
```
sudo apt-get install python3
```
3. Install Node.js
```
sudo curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.35.2/install.sh | bash
sudo nvm install 17
```
4. Pull code from GitHub
```
mkdir duckduck
cd duckduck
git clone https://github.com/Black3800/duckduck-clockface.git
git clone https://github.com/Black3800/duckduck-event-listener.git
git clone https://github.com/Black3800/duckduck-illumination-service.git
```
5. Install dependencies in each service
```
cd ./duckduck-clockface.git
npm install
cd ../duckduck-event-listener.git
python -m venv ./.venv
./.venv/bin/pip install -r requirements.txt
cd ../duckduck-illumination-service.git
python -m venv ./.venv
./.venv/bin/pip install -r requirements.txt
cd ..
```
6. Config the bulb ip
```
echo "export BULB_IP=192.168.1.93" > ./duckduck-illumination-service/bulb.conf
```
7. Add configuration file
```
nano ./duckduck-event-listener/.device_config
```
Enter the following configuration. Adjust as appropriate.
```
{
    "device_code": "SSAC99",
    "device_secret": "duckduck99",
    "mqtt_username": "duckduck",
    "mqtt_password": "12345678",
    "mqtt_host": "55.55.55.55",
    "mqtt_port": 1883,
    "illumination_service": "http://localhost:8000",
    "server": "https://duckduck.example.com/api/v1"
}
```
8. Add DuckDuck shortcut to desktop
```
cp ./duckduck-illumination-service/DuckDuck ~/Desktop/DuckDuck
chmod +x ~/Desktop/DuckDuck
```