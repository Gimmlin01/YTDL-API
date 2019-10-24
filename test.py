import os

def get_secrets():
    api_key=os.environ.get('API_SECRET_KEY', False)
    secret_key=os.environ.get("SECRET_KEY", False)
    mysql_login=os.environ.get("MYSQL_LOGIN", False)
    return api_key,secret_key,mysql_login

if __name__ == '__main__':
    api_key,secret_key,mysql_login=get_secrets()
    if (api_key and secret_key and mysql_login):
        print(api_key,secret_key,mysql_login)
    else:
        print("No secret keys/logins found pleas export API_SECRET_KEY,SECRET_KEYm(30 bytes) and MYSQL_LOGIN(user:passwd)")
#app.config['api_secret_key'] = 'XH%GYO>.)j#8q=vaFk0oDXNiBmw3c7'
#app.config['SECRET_KEY'] = 'C_>UsHek|2Q@=J/AqLX3N_4&rK9Gcb'
#app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://mick:banzai01@localhost/ytdl?charset=utf8mb4'
