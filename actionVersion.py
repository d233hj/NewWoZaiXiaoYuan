import requests
import json
import yagmail
import re
import os
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from base64 import b64encode
import urllib.parse


def MsgSend(message_title, message_info):
    if os.environ['mail_address']:
        mail = yagmail.SMTP(os.environ['mail_address'],
                            os.environ['mail_password'], os.environ['mail_host'])
        try:
            mail.send(os.environ['receive_mail'], message_title, message_info)
        except Exception as e:
            print("推送出错！", str(e))
    if os.environ['sct_ftqq']:
        try:
            requests.get(f'https://sctapi.ftqq.com/{os.environ["sct_ftqq"]}.send?{urllib.parse.urlencode({"title":message_title, "desp":message_info})}')
        except Exception as e:
            print("推送出错！", str(e))

def encrypt(t, e):
    t = str(t)
    key = e.encode('utf-8')
    cipher = AES.new(key, AES.MODE_ECB)
    padded_text = pad(t.encode('utf-8'), AES.block_size)
    encrypted_text = cipher.encrypt(padded_text)
    return b64encode(encrypted_text).decode('utf-8')


def Login(headers, username, password):
    headers00 = {
        "accept": "application/json, text/plain, */*",
        "user-agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1 Edg/119.0.0.0"}
    url00 = "https://gw.wozaixiaoyuan.com/basicinfo/mobile/login/getSchoolList"
    response00 = requests.get(url00, headers=headers00)
    school_data = json.loads(response00.text)['data']

    def find_school_id(school_name, data):
        for school in data:
            if school['name'] == school_name:
                return school['id']
        return None
    school = os.environ["school_name"]
    school_id = find_school_id(school, school_data)
    key = (str(username) + "0000000000000000")[:16]
    encrypted_text = encrypt(password, key)
    login_url = 'https://gw.wozaixiaoyuan.com/basicinfo/mobile/login/username'
    params = {
        "schoolId": school_id,
        "username": username,
        "password": encrypted_text
    }
    login_req = requests.post(login_url, params=params, headers=headers)
    print(login_req.text)
    text = json.loads(login_req.text)
    if text['code'] == 0:
        print(f"{username}账号登陆成功！")
        set_cookie = login_req.headers['Set-Cookie']
        jws = re.search(r'JWSESSION=(.*?);', str(set_cookie)).group(1)
        return jws
    else:
        print(f"{username}登陆失败，请检查账号密码！")
        return False


def GetUnDo(headers, username):
    url = 'https://gw.wozaixiaoyuan.com/health/mobile/health/getBatch'
    res = requests.get(url, headers=headers)
    lists = json.loads(res.text)['data']
    for list in lists['list']:
        if list['state'] == 1 and list['type'] == 0:
            return list['id']
    print(f"{username}未找到未打卡项目！")
    MsgSend(f"{username}未找到未打卡项目！", f"{username}未找到未打卡项目！")
    return False


def GetPunchData(headers, username, batch, location, tencentKey):
    PunchData = {}
    locationType_url = 'https://gw.wozaixiaoyuan.com/health/mobile/health/getForm?batch='+ batch
    res = requests.get(locationType_url, headers=headers)
    locationType = json.loads(res.text)['data']['locationType']
    PunchData.update({"type": 0, "locationMode": 0, "locationType": locationType})
    geocode = requests.get("https://apis.map.qq.com/ws/geocoder/v1", params={"address": location, "key": tencentKey})
    geocode_data = json.loads(geocode.text)
    if geocode_data['status'] == 0:
        reverseGeocode = requests.get("https://apis.map.qq.com/ws/geocoder/v1", params={"location": f"{geocode_data['result']['location']['lat']},{geocode_data['result']['location']['lng']}", "key": tencentKey})
        reverseGeocode_data = json.loads(reverseGeocode.text)
        if reverseGeocode_data['status'] == 0:
            PunchData.update({"location": reverseGeocode_data['result']['ad_info']['name'].replace(",", "/") + '/' + reverseGeocode_data['result']['address_reference']['town']['title'] + '/' + reverseGeocode_data['result']['address_reference']['landmark_l1']['title'] + '/156' +  reverseGeocode_data['result']['ad_info']['adcode'] + '/' + reverseGeocode_data['result']['ad_info']['city_code'] + '/' + reverseGeocode_data['result']['address_reference']['town']['id'] + '/' + str(geocode_data['result']['location']['lng']) + '/' + str(geocode_data['result']['location']['lat'])})
            return PunchData


def Punch(headers, batch, punchData, username):
    url = 'https://gw.wozaixiaoyuan.com/health/mobile/health/save?batch='+batch
    res = requests.post(url, json=punchData, headers=headers)
    txt = json.loads(res.text)
    if txt['code'] == 0:
        print(f"{username}打卡成功！\n")
        MsgSend(f"{username} 打卡成功！", f"{username} 归寝打卡成功！")
        return True
    else:
        print(f"{username}打卡失败！{str(txt)}\n")
        MsgSend(f"{username} 打卡失败！", f"{username} 归寝打卡失败！" + str(res.text))
        return False


# 蓝牙签到模块开始 By Mudea661
def upload_blue_data(blue1, blue2, headers, id, signid):
    username = os.environ['wzxy_username']
    data = {
        "blue1": blue1,
        "blue2": list(blue2.values())
    }
    response = requests.post(
        url=f"https://gw.wozaixiaoyuan.com/dormSign/mobile/receive/doSignByDevice?id={id}&signId={signid}",
        headers=headers, data=json.dumps(data))
    if response.status_code == 200:
        response_data = response.json()
        if response_data.get("code") == 0:
            MsgSend(f"账号- {username} -蓝牙打卡成功！", f"账号- {username} -蓝牙打卡成功！")
            return 0
        else:
            MsgSend(f"账号- {username} -蓝牙打卡失败！", f"账号- {username} -蓝牙打卡失败！")
            return 1
    else:
        return 1


def doBluePunch(headers, username):
    # 获取签到日志
    sign_logs_url = "https://gw.wozaixiaoyuan.com/dormSign/mobile/receive/getMySignLogs"
    sign_logs_params = {
        "page": 1,
        "size": 10
    }
    try:
        response = requests.get(sign_logs_url, headers=headers, params=sign_logs_params)
        data_ids = response.json()
        location_id = data_ids["data"][0]["locationId"]
        sign_id = data_ids["data"][0]["signId"]
        major = data_ids["data"][0]["deviceList"][0]["major"]
        uuid = data_ids["data"][0]["deviceList"][0]["uuid"]
        blue1 = [uuid.replace("-", "") + str(major)]
        blue2 = {"UUID1": uuid}
    except:
        MsgSend(f"账号- {username} -获取签到列表出错！", f"账号- {username} -获取签到列表出错！")
        return 0
    return upload_blue_data(blue1, blue2, headers, location_id, sign_id)

# 蓝牙模块结束


def main():
    username = os.environ['wzxy_username']
    login_headers = {'User-Agent': 'Mozilla/5.0 (Linux; Android 10; WLZ-AN00 Build/HUAWEIWLZ-AN00; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/86.0.4240.99 XWEB/4343 MMWEBSDK/20220903 Mobile Safari/537.36 MMWEBID/4162 MicroMessenger/8.0.28.2240(0x28001C35) WeChat/arm64 Weixin NetType/WIFI Language/zh_CN ABI/arm64 miniProgram/wxce6d08f781975d91'}
    jws = Login(login_headers, username,
                             os.environ['wzxy_password'])
    if jws:
        headers = {
            'Host': 'gw.wozaixiaoyuan.com',
            'Connection': 'keep-alive',
            'Accept': 'application/json, text/plain, */*',
            'jwsession': jws,
            "cookie": f'JWSESSION={jws}',
            "cookie": f'JWSESSION={jws}',
            "cookie": f'WZXYSESSION={jws}',
            'User-Agent': 'Mozilla/5.0 (Linux; Android 10; WLZ-AN00 Build/HUAWEIWLZ-AN00; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/86.0.4240.99 XWEB/4343 MMWEBSDK/20220903 Mobile Safari/537.36 MMWEBID/4162 MicroMessenger/8.0.28.2240(0x28001C35) WeChat/arm64 Weixin NetType/WIFI Language/zh_CN ABI/arm64 miniProgram/wxce6d08f781975d91',
            'Content-Type': 'application/json;charset=UTF-8',
            'X-Requested-With': 'com.tencent.mm',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Dest': 'empty',
            'Referer': 'https://gw.wozaixiaoyuan.com/h5/mobile/health/0.3.7/health',
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7'
        }
        if os.environ['dorm_sign'] == 'yes':
            batch = GetUnDo(headers, username)
            if not batch:
                return False
            punchData = GetPunchData(headers, username, batch, os.environ['location'], os.environ['tencentKey'])
            Punch(headers, batch, punchData, username)
            return True
        if os.environ['blue_sign'] == 'yes':
            doBluePunch(headers, username)

    else:
        MsgSend(f"{username} 登陆失败！", f"{username} 登陆失败！")
        return False


if __name__ == "__main__":
    main()
