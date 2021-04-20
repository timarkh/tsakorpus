pybabel extract -F babel.cfg -o messages.pot --no-wrap .
pybabel update -i messages.pot -d translations_pybabel --no-wrap