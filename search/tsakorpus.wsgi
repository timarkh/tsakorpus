import sys
# sys.path.insert(0, '.../')
# sys.path.insert(0, '.../app/')

from web_app import app as application, get_locale as app_get_locale
from flask_babel import Babel

babel = Babel(application)
babelOldVersion = ('localeselector' in Babel.__dict__)  # Apparently, before 3.0

if babelOldVersion:
    @babel.localeselector
    def get_locale():
        return app_get_locale()
    babel.init_app(application)
else:
    def get_locale():
        return app_get_locale()
    babel.init_app(application, locale_selector=get_locale)


if __name__ == "__main__":
    application.run(port=7342, host='0.0.0.0',
                    debug=True, use_reloader=False)
