login_button_xpath = '//*[contains(concat( " ", @class, " " ), concat( " ", "spectrum-Button--overBackground", " " ))]'

email_input_xpath = '//*[(@id = "EmailPage-EmailField")]'
email_continue_button_xpath = '//*[contains(concat( " ", @class, " " ), concat( " ", "SpinnerButton--right", " " ))]'

verification_form_xpath = '//*[contains(concat( " ", @class, " " ), concat( " ", "Page__spinner-btn", " " ))]'

password_form_xpath = '//*[contains(concat( " ", @class, " " ), concat( " ", "CardLayout-Container PasswordPage", " " ))] | //*[(@id = "PasswordPage-PasswordField")]'
password_input_xpath = '//*[(@id = "PasswordPage-PasswordField")]'
password_continue_button_xpath = '//*[contains(concat( " ", @class, " " ), concat( " ", "spectrum-Button--cta", " " ))]'

mixamo_home_page_xpath = '//*[contains(concat( " ", @class, " " ), concat( " ", "thumbnails-md", " " ))]//div'
animation_xpath = "//div[contains(@class, 'product-animation') or contains(@class, 'product-animation-pack')]"
animation_title_xpath = ".//*[contains(concat(' ', @class, ' '), concat(' ', 'text-capitalize', ' '))]"
animation_description_xpath = ".//ul[contains(@class, 'product-metadata')]/li"
animation_gif_url_xpath = './/img'

next_page_button_xpath = '//*[contains(@class, "fa-angle-right") and not(contains(@class, "disabled"))]'

directory_name = "animations"