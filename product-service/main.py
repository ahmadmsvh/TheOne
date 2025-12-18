from flask import Flask

app = Flask(__name__)

# Basic route
@app.route('/')
def home():
    return {"message": "product-service-running"}


if __name__ == '__main__':
    # Debug mode for development
    app.run(debug=True, use_reloader=True, host='0.0.0.0', port=5001)