from app import app

@app.route('/flask/hello')
def home():
	return 'Hello, world!'