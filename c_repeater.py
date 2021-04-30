# Copyright (C) 2021 Ludger Hellerhoff, ludger@booker-hellerhoff.de
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 3
# of the License, or (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  
# See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.

from argparse import ArgumentParser
from ipaddress import ip_network, ip_address
from os import path, mkdir
from sys import platform
from autobahn.asyncio.websocket import WebSocketClientFactory
from autobahn.asyncio.websocket import WebSocketClientProtocol
import socket
import asyncio
import json
import subprocess

def checkport(ip, port):
  sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  sock.settimeout(0.2)
  result = sock.connect_ex((ip, port))
  if result == 0:
    try:      
      return(socket.gethostbyaddr(ip)[0])
    except socket.herror:
      return(None)
  else:
    return(None)

port_dict = {
  80 : 'http',
  443 : 'https',
  554 : 'rtsp',
  8554 : 'rtsp8',
  1935 : 'rtmp',
}

cam_task_register = {}

cfg_file = open('c_repeater.cfg', 'r')
lines = [line.rstrip() for line in cfg_file]
rep_id = lines[0]
password = lines[1]

parser = ArgumentParser('CAM-AI Repeater')
parser.add_argument('-u', '--url', dest='url',
  #default='wss://booker-hellerhoff.de:10443/ws/repeater/',
  #default='wss://django.cam-ai.de:443/ws/repeater/',
  default='ws://localhost:8000/ws/repeater/',
  help='Websocket-Url of the CAM-AI server')
parser.add_argument('-m', '--mask', dest='mask',
  default='255.255.255.0',
  help='Subnet mask of the network')
args = parser.parse_args()
strings = args.url.split('/')
if strings[0] == 'ws:':
  use_ssl = False
elif strings[0] == 'wss:':
  use_ssl = True
else:
  use_ssl = False
servername = strings[2]
if ':' in servername:
  servername = servername.split(':')
  use_port = int(servername[1])
  servername = servername[0]
else:
  use_port = 80

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
try:
  s.connect(('10.255.255.255', 1))
  my_ip = s.getsockname()[0]
except Exception:
  my_ip = '127.0.0.1'
finally:
  s.close()
my_net = ip_network(my_ip+'/'+args.mask, strict=False)
my_ip = ip_address(my_ip)
print('My own IP:', my_ip)
print('Subnet mask:', args.mask)
print('This network:', my_net)
print('Connecting to', args.url)

class MyClientProtocol(WebSocketClientProtocol):

  def onOpen(self):
    self.sendMessage(('rep_id:'+rep_id).encode())
    self.sendMessage(('passwo:'+password).encode())

  def onMessage(self, payload, isBinary):
    payload = payload.decode()
    command = payload[:7]
    params = payload[7:]
    #print(command, '>>>', params, '<---')
    if command == 'collip:':
      hostlist = list(my_net.hosts())
      for i in range(len(hostlist)):
        if hostlist[i] != my_ip:
          portlist = []
          myhostname = None
          for port in port_dict:
            hostname = checkport(str(hostlist[i]), port)
            if hostname is not None:
              portlist.append(port)
              if myhostname is None:
                myhostname = hostname
          if myhostname is not None:
            self.sendMessage(('ipitem:'+json.dumps((myhostname, str(hostlist[i]), portlist))).encode())
          else:
            self.sendMessage(('ticker:'+str(i+1)+'/'+str(len(hostlist))).encode())
      self.sendMessage('ipdone:'.encode())
    elif command == 'token_:':
      self.token = params
    elif command == 'ffprob:':
      if not path.exists('fifo'):
        mkdir('fifo')
      tempfilename = params.split('/')[2]
      cmdline='ffprobe -v warning -show_streams -of json -i "'+params+'" > '
      if (platform.startswith('win')):
        tempfilename = 'fifo\\'+tempfilename+'.json'
        cmdline='ffmpeg\\bin\\'+cmdline+'"'+tempfilename+'"'
      else:
        tempfilename = 'fifo/'+tempfilename+'.json'
        cmdline='exec '+cmdline+'"'+tempfilename+'"'
      subprocess.run(cmdline, shell=True)
      with open(tempfilename, 'r') as file:
        result = (params, file.read())
        #print(json.loads(result[1]))
      self.sendMessage(('ffpres:'+json.dumps(result)).encode())
    elif command == 'hostco:':
      params = json.loads(params)
      if use_ssl:
        ssl_code = '1'
      else:
        ssl_code = '0'
      if platform.startswith('win') and path.exists('c_repeater_cam.exe'):
        programname = 'c_repeater_cam.exe'
      else:
        programname = 'python c_repeater_cam.py'
      cmdline = (programname+' -r '+str(rep_id)+' -c '+str(params[0])
        +' -u "'+params[1]+'" -w "'+args.url+'" -s "'+servername+'" -p '+str(use_port)+' -t '+self.token+' -l '+ssl_code)
      if (not platform.startswith('win')):
        cmdline='exec '+cmdline
      cam_task_register[params[0]] = subprocess.Popen(cmdline, shell=True)

#print(args.url, servername, use_port, use_ssl)
factory = WebSocketClientFactory(args.url)
factory.protocol = MyClientProtocol
loop = asyncio.get_event_loop()
coro = loop.create_connection(factory, servername, use_port, ssl=use_ssl)
loop.run_until_complete(coro)
loop.run_forever()
loop.close()
