from sms.config import connex_app

connex_app.add_api('swagger.yaml')
app = connex_app.app

if __name__ == '__main__':
    connex_app.run(debug=True, port=1807)
