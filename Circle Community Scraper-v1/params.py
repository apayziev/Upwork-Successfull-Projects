# Base URLs
BASE_URL = "https://curriculum.founder.university"
LOGIN_URL = "https://login.circle.so/sign_in?request_host=curriculum.founder.university#email"

# Login Page XPaths
EMAIL_INPUT_XPATH = '//*[(@id = "user_email")]'
PASSWORD_INPUT_XPATH = '//*[(@id = "user_password")]'
SIGN_IN_BUTTON_XPATH = "//form[@action='/sign_in?']//button[contains(text(), 'Sign In')]"

# XPath Selectors for Member Profiles
# XPath Selectors
MEMBER_XPATHS = {
    'full_name': "//span[@data-testid='member-name']",
    'role': "//span[@data-testid='member-headline']",
    'social_links': "//div[contains(@class, 'profile-drawer__about__heading') and contains(text(), 'Social')]/following-sibling::div[contains(@class, 'profile-drawer__about__block')]"
}
