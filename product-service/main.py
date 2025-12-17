from flask import Flask

app = Flask(__name__)

# Basic route
@app.route('/')
def home():
    return {"message": "product-service"}


if __name__ == '__main__':
    # Debug mode for development
    app.run(debug=True, host='0.0.0.0', port=5001)