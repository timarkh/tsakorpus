import sys
# sys.path.insert(0, '.../')
# sys.path.insert(0, '.../app/')

from web_app import app as application

if __name__ == "__main__":
    application.run(port=7342, host='0.0.0.0', debug=True)