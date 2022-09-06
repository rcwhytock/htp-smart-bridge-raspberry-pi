#!/bin/bash
set -e
sudo systemctl disable systemd-timesyncd.service
sudo raspi-config nonint do_wifi_country NL
sudo raspi-config nonint do_spi 1
sudo raspi-config nonint do_i2c 1
sudo raspi-config nonint do_boot_wait 1

sudo bash -c 'cat >/boot/config.txt <<EOL
# For more options and information see
# http://rpf.io/configtxt

# Disable audio
dtparam=audio=off

# Disable BT
dtparam=disable-bt

# Needed to enable USB ports on the Compute Module
dtoverlay=dwc2,dr_mode=host

# For communication with RockBlock and PMP
enable_uart=1
dtoverlay=uart0
dtoverlay=uart3
EOL'

sudo apt update
sudo apt install python3-pip libatlas-base-dev libopenjp2-7 libtiff5 -y
sudo pip3 install -r requirements.txt

sudo bash -c 'echo "maxsize 1M" >> /etc/logrotate.conf'

sudo bash -c 'cat >/etc/rc.local <<EOL
#!/bin/sh -e
echo "Starting Smart Camera Trap"
(
    cd /home/smart-camera-trap
    python3 -u main.py 2>&1 | logger -p user.info &
)
EOL'

sudo bash -c 'cat >/etc/wpa_supplicant/wpa_supplicant.conf <<EOL
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1 
country=NL
autoscan=periodic:3

network={
    ssid="ez Share"
    psk="88888888"
}
EOL'

echo "Done!"
echo "Reboot to apply changes"