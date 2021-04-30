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
from sys import platform
from autobahn.asyncio.websocket import WebSocketClientFactory
from autobahn.asyncio.websocket import WebSocketClientProtocol
from multiprocessing import Process
import asyncio
import subprocess

from time import sleep

class MyClientProtocol(WebSocketClientProtocol):

  async def periodic(self):
    while True:
      if self.ready_to_receive:
        #in_bytes = self.worker_proc.stdout.read(65536)
        in_bytes = self.worker_proc.stdout.read(16384)
        rep_nr_bin = str(args.rep).zfill(6).encode()
        cam_nr_bin = str(args.cam).zfill(6).encode()
        token_bin = args.token.encode()
        self.sendMessage(rep_nr_bin+cam_nr_bin+token_bin+in_bytes, isBinary=True)
        self.ready_to_receive = False
      await asyncio.sleep(0.01)

  def stop(self):
    self.task.cancel()

  def onOpen(self):
    #loop.call_later(60, self.stop)
    self.task = loop.create_task(self.periodic())
    self.ready_to_receive = True
    inparams = '-v warning'
    outparams = '-c copy -f ismv -an'
    cmdline = 'ffmpeg '+inparams+' -i "'+args.url+'" '+outparams+' pipe:'
    if (platform.startswith('win')):
      cmdline='ffmpeg\\bin\\'+cmdline
    else:
      cmdline='exec '+cmdline
    self.worker_proc = subprocess.Popen(cmdline, stdout=subprocess.PIPE, shell=True)

  def onMessage(self, payload, isBinary):
    payload = payload.decode()
    command = payload[:7]
    params = payload[7:]
    #print(command, '>>>', params, '<---')
    if command == 'readyr:':
      self.ready_to_receive = True

parser = ArgumentParser('Repeater CAM Module')
parser.add_argument('-r', '--rep', dest='rep', type=int)
parser.add_argument('-c', '--cam', dest='cam', type=int)
parser.add_argument('-u', '--url', dest='url')
parser.add_argument('-w', '--ws_url', dest='ws_url')
parser.add_argument('-s', '--servername', dest='servername')
parser.add_argument('-p', '--port', dest='port', type=int)
parser.add_argument('-t', '--token', dest='token')
parser.add_argument('-l', '--ssl', dest='ssl', type=int)
args = parser.parse_args()
ws_url = args.ws_url+'data/'
use_ssl = args.ssl == 1

factory = WebSocketClientFactory(ws_url)
factory.protocol = MyClientProtocol
loop = asyncio.get_event_loop()
coro = loop.create_connection(factory, args.servername, args.port, ssl=use_ssl)
loop.run_until_complete(coro)
loop.run_forever()
loop.close()
