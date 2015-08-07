import re

from nose.tools import eq_, ok_
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException

from airmozilla.base.tests.testbase import DjangoLiveServerTestCase


class CalendarLiveServerTestCase(DjangoLiveServerTestCase):

    def is_element_present(self, how, what):
        try:
            self.driver.find_element(by=how, value=what)
        except NoSuchElementException:
            return False
        return True

    def test_persistent_week_start(self):
        driver = self.driver
        driver.get(self.base_url)
        driver.find_element_by_link_text("CALENDAR").click()
        eq_("Mon", driver.find_element_by_xpath("//th").text)
        driver.find_element_by_id("startsOnMonday").click()
        eq_("Sun", driver.find_element_by_xpath("//th").text)
        driver.refresh()
        eq_("Sun", driver.find_element_by_xpath("//th").text)
        ok_(not driver.find_element_by_id("startsOnMonday").is_selected())
        driver.find_element_by_xpath("(//button[@type='button'])[5]").click()
        ok_(re.match("Sun", driver.find_element_by_xpath("//th[2]").text))

    def test_persistent_calendar_view(self):
        driver = self.driver
        driver.get(self.base_url)
        driver.find_element_by_link_text("CALENDAR").click()
        driver.find_element_by_xpath("(//button[@type='button'])[5]").click()
        ok_(self.is_element_present(By.CSS_SELECTOR, ".fc-agendaWeek-view"))
        driver.refresh()
        ok_(self.is_element_present(By.CSS_SELECTOR, ".fc-agendaWeek-view"))
        driver.find_element_by_xpath("(//button[@type='button'])[6]").click()
        ok_(self.is_element_present(By.CSS_SELECTOR, ".fc-agendaDay-view"))
        driver.refresh()
        ok_(self.is_element_present(By.CSS_SELECTOR, ".fc-agendaDay-view"))
        driver.find_element_by_xpath("(//button[@type='button'])[4]").click()
        ok_(self.is_element_present(By.CSS_SELECTOR, ".fc-month-view"))
        driver.refresh()
        ok_(self.is_element_present(By.CSS_SELECTOR, ".fc-month-view"))
