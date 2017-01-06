import pytest

# from pyvirtualdisplay import Display

# NOTIFY_URL = 'https://notify:oNe_l0g1nTOrUle!@admin-ags.notify.works'
# REPEAT_COUNT = 10
NOTIFY_URL = 'http://localhost:6012/'
REPEAT_COUNT = 1


@pytest.mark.parametrize('exec_count', range(REPEAT_COUNT))
def test_click_to_ags_sign_in(selenium, exec_count):
    # display = Display(visible=0, size=(1024, 768))
    # display.start()

    print(exec_count)

    selenium.get(NOTIFY_URL)
    selenium.find_element_by_xpath(
        '//*[@id="proposition-links"]/li[1]/a').click()
    assert 'Do you know your work email?' in selenium.find_element_by_xpath(
        '//*[@id="content"]/h1').text

    # display.stop()
