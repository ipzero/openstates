import datetime

from fiftystates.scrape.nj import metadata
from fiftystates.scrape.nv.utils import chamber_name
from fiftystates.scrape.bills import BillScraper, Bill
from fiftystates.scrape.votes import VoteScraper, Vote

import lxml.etree

class NJBillScraper(BillScraper):
    state = 'nj'

    def scrape(self, chamber, year):

        if year < 1996:
            raise NoDataForPeriod(year)
        elif year == 1996:
            year_abr = 9697
        elif year == 1998:
            year_abr = 9899
        else:
            year_abr = year

        session = (int(year) - 2010) + 214
        self.scrape_bill_pages(year, session, year_abr)

    def scrape_bill_pages(self, year, session, year_abr):

        year_url = 'http://www.njleg.state.nj.us/bills/bills0001.asp'
        year_body = 'DBNAME=LIS%s' % (year_abr)
        bill_list_url = 'http://www.njleg.state.nj.us/bills/BillsByNumber.asp'
        first_body = 'SearchText=&SubmitSearch=Find&GoToPage=1&MoveRec=&DocumentText=&Search=&NewSearch=&ClearSearch=&SearchBy'
        with self.urlopen(year_url, 'POST', year_body) as year_page:
            with self.urlopen(bill_list_url, 'POST', first_body) as first_bill_page:
                root = lxml.etree.fromstring(first_bill_page, lxml.etree.HTMLParser())
                num_pages = root.xpath('string(//table/tr[1]/td[4]/div/font/b/font)').split()[-1]
                num_pages = int(num_pages)
                self.scrape_bills_number(session, first_bill_page, year)
                #print num_pages


    def scrape_bills_number(self, session, page, year):
        bills = []        
        root = lxml.etree.fromstring(page, lxml.etree.HTMLParser())
        count = 1
        for mr in root.xpath('//table/tr/td[1]/a/font'):
            bill_number = mr.xpath('string()').split()[0]
            title = ""
            title_path = 'string(//tr[4]/td/table/tr[%s]/td[2]/font)' % (count)
            title_parts = root.xpath(title_path).split()
            for part in title_parts:
                title = title + part + " "
            title = title[0: len(title) - 1]
            bill_object = [bill_number, title]
            bills.append(bill_object)
            count = count + 4
        for bill in bills:
            self.scrape_info(session, bill, year)

    def scrape_info(self, session, bill_number, year):
        bill_view_url = 'http://www.njleg.state.nj.us/bills/BillView.asp'
        bill_id = bill_number[0]
        bill_view_body = 'BillNumber=%s++++&LastSession=' % bill_number[0]
        with self.urlopen(bill_view_url, 'POST', bill_view_body) as bill_view_page:
            root = lxml.etree.fromstring(bill_view_page, lxml.etree.HTMLParser())
            title = bill_number[1]
            if bill_id[0] == 'A':
                chamber = 'General Assembly'
            elif bill_number[0][0] == 'S':
                chamber = 'Senate'
            bill = Bill(session, chamber, bill_id, title)

            #Grabbing sponsors
            sponsorship = root.xpath('string(//tr[1]/td[1]/div/font[3])').split()
            primary_count = sponsorship.count('Primary')
            sponsor_count = 1
            #Special case
            if session == 214 and bill_id == 'A101':
                sponsorship = root.xpath('string(//tr[1]/td[1]/div/font[5])').split()
                primary_count = sponsorship.count('Primary')
            #End special case
            for sp in root.xpath('//tr[1]/td[1]/div/font/a/font'):
                sponsor = sp.xpath('string()').split()
                if len(sponsor) == 3:
                    leg = sponsor[1] + " " + sponsor[2] + " " + sponsor[0]
                    leg = leg[0: len(leg) - 1]
                elif len(sponsor) == 2:
                    leg = sponsor[1] + " " + sponsor[0]
                    leg = leg[0: len(leg) - 1]

                if sponsor_count <= primary_count:
                    sponsor_type = 'Primary'
                if sponsor_count > primary_count:
                    sponsor_type = 'Co-sponsor'

                bill.add_sponsor(sponsor_type, leg)
                sponsor_count = sponsor_count + 1

            #Actions
            #Make a new action for everything behind a "BRWASHERE"
            action_page = bill_view_page
            action_page = action_page.replace('<br>', '\nBRWASHERE\n')
            roo = lxml.etree.fromstring(action_page, lxml.etree.HTMLParser())
            block_o_actions = roo.xpath('string(//tr[4]/td/font[1])').split()
            action_part_count = 0
            date = ''
            action_name = ''
            intro_count = 0
            year_insert1 = '/%s' % (year)
            year_insert2 = '/%s' % (int(year) + 1)
            for action_part in block_o_actions:
                if (action_part_count == 0) or (year_insert1 in action_part) or (year_insert2 in action_part):
                    date = action_part
                elif action_part != 'BRWASHERE':
                    action_name = action_name + action_part + " "
                elif action_part == 'BRWASHERE':
                    if len(action_name) > 0:
                        action = action_name[0: len(action_name) - 1]
                        if action.split()[0] != 'Introduced':
                            bill.add_action(chamber, action, date)
                            print date, '\t', action
                    action_name = ''
                action_part_count = action_part_count + 1
            print '\n'

            #self.save_bill(bill)
