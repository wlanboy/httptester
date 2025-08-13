## nmcli bridge + vlan
```
nmcli con add type bridge ifname enx6c1ff706116 con-name enx6c1ff706116 connection.autoconnect yes

nmcli con add type vlan con-name enx6c1ff706116.10 dev enx6c1ff706116 id 10 master enx6c1ff706116 connection.autoconnect yes

nmcli connection
nmcli device

nmcli -f bridge con delete enx6c1ff706116
```

## ip vlan + net
```
ip link add link enx6c1ff7061161 name enx6c1ff7061161.10 type vlan id 10
ip -details addr show
ip addr add 192.168.1.1/24 brd 192.168.1.255 dev enx6c1ff7061161.10
ip link set dev enx6c1ff7061161.10 up
```

## add route to metallb subnet
```
sudo ip route add 172.18.0.0/24 via 192.168.178.88 dev eno1
```