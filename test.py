import socket
hostname = socket.gethostname()
IPAddr = socket.gethostbyname(hostname)

print("Your Computer Name is:" + hostname)
print("Your Computer IP Address is:" + IPAddr)

from urllib.request import urlopen
import re as r

def getIP():
    d = str(urlopen('http://checkip.dyndns.com/')
            .read())

    return r.compile(r'Address: (\d+\.\d+\.\d+\.\d+)').search(d).group(1)

print(getIP())