#!/usr/bin/python
# -!- coding: utf-8 -!-
#
# Copyright 2016 Hector Martin <marcan@marcan.st>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import base64, msgpack, hashlib, random, urllib2, time
from Crypto.Cipher import AES
from Crypto.Util import Padding

from secrets import VIEWER_ID_KEY, SID_KEY

def decrypt_cbc(s, iv, key):
    aes = AES.new(key, AES.MODE_CBC, iv)
    return Padding.unpad(aes.decrypt(s), 16)

def encrypt_cbc(s, iv, key):
    aes = AES.new(key, AES.MODE_CBC, iv)
    return aes.encrypt(Padding.pad(s, 16))

class ApiClient(object):
    BASE = "https://apis.game.starlight-stage.jp"
    def __init__(self, user, viewer_id, udid, res_ver="10051210"):
        self.user = user
        self.viewer_id = viewer_id
        self.udid = udid
        self.sid = None
        self.res_ver = res_ver

    def lolfuscate(self, s):
        return "%04x" % len(s) + "".join(
            "%02d" % random.randrange(100) +
            chr(ord(c) + 10) + "%d" % random.randrange(10)
            for c in s) + "%032d" % random.randrange(10**32)

    def unlolfuscate(self, s):
        return "".join(chr(ord(c) - 10) for c in s[6::4][:int(s[:4], 16)])

    def call(self, path, args):
        vid_iv = "%016d" % random.randrange(10**16)
        args["timezone"] = "09:00:00"
        args["viewer_id"] = vid_iv + base64.b64encode(
            encrypt_cbc(str(self.viewer_id), vid_iv,
                        VIEWER_ID_KEY))
        plain = base64.b64encode(msgpack.packb(args))
        # I don't even
        key = base64.b64encode("".join("%x" % random.randrange(65536) for i in xrange(32)))[:32]
        msg_iv = self.udid.replace("-","").decode("hex")
        body = base64.b64encode(encrypt_cbc(plain, msg_iv, key) + key)
        sid = self.sid if self.sid else str(self.viewer_id) + self.udid
        headers = {
            "PARAM": hashlib.sha1(self.udid + str(self.viewer_id) + path + plain).hexdigest(),
            "KEYCHAIN": "",
            "USER-ID": self.lolfuscate(str(self.user)),
            "CARRIER": "google",
            "UDID": self.lolfuscate(self.udid),
            "APP-VER": "9.9.9",
            "RES-VER": str(self.res_ver),
            "IDFA": "",
            "PROCESSOR-TYPE": "ARMv7 VFPv3 NEON",
            "IP-ADDRESS": "127.0.0.1",
            "DEVICE-NAME": "Nexus 42",
            "X-Unity-Version": "2017.4.2f2",
            "SID": hashlib.md5(sid + SID_KEY).hexdigest(),
            "GRAPHICS-DEVICE-NAME": "3dfx Voodoo2 (TM)",
            "DEVICE-ID": hashlib.md5("Totally a real Android").hexdigest(),
            "PLATFORM-OS-VERSION": "Android OS 13.3.7 / API-42 (XYZZ1Y/74726f6c6c)",
            "DEVICE": "2",
            "Content-Type": "application/x-www-form-urlencoded", # lies
            "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 13.3.7; Nexus 42 Build/XYZZ1Y)",
        }
        for i in range(3):
            try:
                req = urllib2.Request(self.BASE + path, body, headers)
                reply = urllib2.urlopen(req).read()
            except urllib2.URLError as e:
                if i >= 2:
                    raise
                else:
                    continue
        reply = base64.b64decode(reply)
        plain = decrypt_cbc(reply[:-32], msg_iv, reply[-32:]).split("\0")[0]
        msg = msgpack.unpackb(base64.b64decode(plain))
        try:
            self.sid = msg["data_headers"]["sid"]
        except:
            pass
        return msg

if __name__ == "__main__":
    import sys, pprint
    from account import user_id, viewer_id, udid
    client = ApiClient(user_id, viewer_id, udid)
    args = {
        "campaign_data": "",
        "campaign_user": 1337,
        "campaign_sign": hashlib.md5("All your APIs are belong to us").hexdigest(),
        "app_type": 0,
    }
    print client.call("/load/check", args)
    pprint.pprint(client.call("/load/index", args))
    pprint.pprint(client.call("/profile/get_profile", {"friend_id": int(sys.argv[1])}))
