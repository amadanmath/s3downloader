import requests



# https://github.com/Hipo/university-domains-list-api
university_checker = 'http://universities.hipolabs.com/search?domain={domain}'

def check_email(email):
    try:
        domain = email.split('@')[1]
        r = requests.get(university_checker.format(domain=domain))
        result = r.json()
        if result:
            return True
    except Exception:
        logger.exception("Error in university checker")
    return False


