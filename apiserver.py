#!/usr/bin/python3
# -*- coding: utf-8 -*-


from flask import Flask, abort, request, jsonify, g, url_for,send_file,Response
from flask_httpauth import HTTPBasicAuth
import os,urllib.parse,MySqlHandler
from YTDL import Song,Downloader
import mimetypes
import os
import re

def get_secrets():
    api_key=os.environ.get('API_SECRET_KEY', False)
    secret_key=os.environ.get("SECRET_KEY", False)
    mysql_login=os.environ.get("MYSQL_LOGIN", False)
    return api_key,secret_key,mysql_login

def create_app():
    app = Flask(__name__)
    api_key,secret_key,mysql_login=get_secrets()
    if (api_key and secret_key and mysql_login):
        app.config["api_version"]=0.2
        app.config["app_version"]=0.31
        app.config["Download_Folder"]="/opt/ytdl"
        app.config["apk_path"]="/opt/ytdl/apk/YTDL-v"
        app.config['api_secret_key'] = api_key
        app.config['SECRET_KEY'] = secret_key
        app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://'+mysql_login+'@localhost/ytdl?charset=utf8mb4'
        app.config['SQLALCHEMY_COMMIT_ON_TEARDOWN'] = True
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        app.config["use_x_sendfile"]=True
        return app
    else:
        print("No secret keys/logins found pleas export API_SECRET_KEY,SECRET_KEYm(30 bytes) and MYSQL_LOGIN(user:passwd)")
        raise SystemExit(0)



app=create_app()
from models import db,User
# extensions
with app.app_context():
    db.init_app(app)
    db.create_all()
auth = HTTPBasicAuth()
sql=MySqlHandler.MySqlHandler(get_secrets()[2])


@auth.verify_password
def verify_password(username_or_token, password):
    # first try to authenticate by token
    user = User.verify_auth_token(username_or_token)
    if not user:
        # try to authenticate with username/password
        user = User.query.filter_by(username=username_or_token).first()
        if not user or not user.verify_password(password):
            return False
    g.user = user
    return True


@app.route('/downloads', methods=['POST'])
@auth.login_required
def postDownload():
    try:
        json = request.get_json()
        s=Song(json=json)
        dl_id=Downloader(url=s.url,conv=s.conv).start()
        return jsonify(Song(dl_id=dl_id).toJson())
    except Exception as e:
        print(e)
        abort(400)

@app.route('/downloads/<id_get>', methods=['GET'])
@auth.login_required
def getSpecificDownload(id_get=None):
    try:
        files=sql.selectRow(dl_id=id_get)
        if len(files)!=1:
            abort(400)
        f=files[0]
        status=f[3]
        dl_id=f[0]
        if status!=100:
            abort(400)
        filename=f[2]
        return send_file_partial(filename)
    except Exception as e:
        print(e)
        abort(400)

@app.route('/status', methods=['GET'])
@auth.login_required
def getStatus():
    try:
        offset = request.args.get('offset', default = 0, type = int)
        limit = request.args.get('limit', default = -1, type = int)
        files=sql.selectRow(offset=offset,limit=limit)
        output=[]
        for f in files:
            filename=None
            if f[2]!=None:
                filename=f[2]
            output.append(Song(dl_id=f[0],url=f[1],filename=os.path.basename(filename),status=f[3]).toJson())
        return jsonify(output)
    except Exception as e:
        print(e)
        abort(400)

@app.route('/status/<id_get>', methods=['GET'])
@auth.login_required
def getSpecificStatus(id_get=None):
    try:
        files=sql.selectRow(dl_id=id_get)
        if len(files)==1:
            f=files[0]
            status=f[3]
            dl_id=f[0]
            if status==100:
                filename=f[2]
                song=Song(dl_id=dl_id,status=status,filename=os.path.basename(filename))
            elif status==-1:
                abort(400)
            else:
                song=Song(dl_id=dl_id,status=status)
        else:
            abort(400)
            print (files)
        print(f[3])
        return jsonify(song.toJson())
    except Exception as e:
        print(e)
        abort(400)

@app.route('/users', methods=['POST'])
def new_user():
    try:
        username = request.json.get('username')
        password = request.json.get('password')
        api_key = request.json.get('api_key')
        if api_key != app.config["api_secret_key"]:
            abort(401)
        print(username,password)
        if username is None or password is None:
            abort(400)    # missing arguments
        print(User.query.filter_by(username=username).first())
        if User.query.filter_by(username=username).first() is not None:
            abort(410)    # existing user
        user = User(username=username)
        user.hash_password(password)
        db.session.add(user)
        db.session.commit()
        return jsonify({'username': user.username}), 201
    except Exception as e:
        print(e)
        abort(400)

@app.route('/token')
@auth.login_required
def get_auth_token():
    duration=5
    token = g.user.generate_auth_token(60)
    return jsonify({'token': token.decode('ascii'), 'duration': duration})

@app.route('/update/<version>')
def get_update(version):
    return send_file_partial(app.config["apk_path"]+version+".apk")


@app.route('/update')
def check_update():
    return str(app.config["app_version"])

@app.route('/update/newest')
def get_newest_update():
    return send_file(app.config["apk_path"]+str(app.config["app_version"])+".apk",as_attachment=True)

@app.route('/')
def get_mainPage():
    return send_file(app.config["apk_path"]+str(app.config["app_version"])+".apk",as_attachment=True)


def getUrl(filepath):
    return "https://yoxcu.de/"+urllib.parse.quote(filepath[8:])


def send_file_partial(path):
    """
        Simple wrapper around send_file which handles HTTP 206 Partial Content
        (byte ranges)
        TODO: handle all send_file args, mirror send_file's error handling
        (if it has any)
    """
    range_header = request.headers.get('Range', None)
    if not range_header: return send_file(path)

    size = os.path.getsize(path)
    byte1, byte2 = 0, None

    m = re.search('(\d+)-(\d*)', range_header)
    g = m.groups()

    if g[0]: byte1 = int(g[0])
    if g[1]: byte2 = int(g[1])

    length = size - byte1
    if byte2 is not None:
        length = byte2+1 - byte1

    data = None
    with open(path, 'rb') as f:
        f.seek(byte1)
        data = f.read(length)

    rv = Response(data,
        206,
        mimetype=mimetypes.guess_type(path)[0],
        direct_passthrough=True)
    rv.headers.add('Content-Range', 'bytes {0}-{1}/{2}'.format(byte1, byte1 + length - 1, size))

    return rv


if __name__ == '__main__':
    os.chdir(app.config["Download_Folder"])
    context = ('/etc/letsencrypt/live/yoxcu.de/fullchain.pem', '/etc/letsencrypt/live/yoxcu.de/privkey.pem')
    app.run(port=31415, host="0.0.0.0",ssl_context=context)
