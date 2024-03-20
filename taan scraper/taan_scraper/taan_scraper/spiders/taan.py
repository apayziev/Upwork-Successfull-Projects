import scrapy
import pandas as pd

class TaanSpider(scrapy.Spider):
    name = "taan"
    allowed_domains = ["www.taan.org.np"]
    start_urls = ["https://www.taan.org.np/members"]
    lower_alphabet_letters = [chr(i) for i in range(97, 123)]
    all_member_data = []


    def start_requests(self):
        """" This function will generate the urls for each letter of the alphabet and call the parse_members function"""
        for letter in self.lower_alphabet_letters:
            url = f"https://www.taan.org.np/members?l={letter}"
            yield scrapy.Request(url, callback=self.parse_members)  
        yield scrapy.Request(url, callback=self.parse_members)


    def parse_members(self, response):
        """This function will extract the member urls from the page and call the parse_member_info function"""
        letter = response.url.split("=")[-1]
        members = response.xpath('//*[contains(concat( " ", @class, " " ), concat( " ", "news-list", " " ))]//a')
        for member in members:
            member_url = member.xpath('.//@href').get()
            yield scrapy.Request(member_url, callback=self.parse_member_info, meta={'letter': letter})

    def extract_member_info(self, response):
        """This function will extract the member details from the page"""
        member_detail_list  = response.xpath('//ul[@class="list-group small"]')
        for row_item in member_detail_list:
            member_info = {}
            try:
                organization_name = row_item.xpath('.//li[1]/text()[normalize-space()]').get().replace(":", "").strip()
            except AttributeError:
                organization_name = None
            try:
                reg_number = row_item.xpath('.//li[2]/text()[normalize-space()]').get().replace(":", "").strip()
            except AttributeError:
                reg_number = None
            try:
                vat_number = row_item.xpath('.//li[3]/text()[normalize-space()]').get().replace(":", "").strip()
            except AttributeError:
                vat_number = None
            try:
                address = row_item.xpath('.//li[4]/text()[normalize-space()]').get().replace(":", "").strip()
            except AttributeError:
                address = None
            try:
                country = row_item.xpath('.//li[5]/text()[normalize-space()]').get().replace(":", "").strip()
            except AttributeError:
                country = None
            try:
                website_url = row_item.xpath('.//li[6]/a/text()').get().strip()
            except AttributeError:
                website_url = None
            try:
                email = row_item.xpath('.//li[7]/a/text()').get().strip()
            except AttributeError:
                email = None
            try:
                telephone_number = row_item.xpath('.//li[8]/text()[normalize-space()]').get().replace(":", "").strip()
            except AttributeError:
                telephone_number = None
            try:
                mobile_number = row_item.xpath('.//li[9]/text()[normalize-space()]').get().replace(":", "").strip()
            except AttributeError:
                mobile_number = None
            try:
                fax = row_item.xpath('.//li[10]/text()[normalize-space()]').get().replace(":", "").strip()
            except AttributeError:
                fax = None
            try:
                po_box = row_item.xpath('.//li[11]/text()[normalize-space()]').get().replace(":", "").strip()
            except AttributeError:
                po_box = None
            try:
                key_person = row_item.xpath('.//li[12]/text()[normalize-space()]').get().replace(":", "").strip()
            except AttributeError:
                key_person = None
            try:
                establishment_date = row_item.xpath('.//li[13]/text()[normalize-space()]').get().replace(":", "").strip()
            except AttributeError:
                establishment_date = None
            member_url = response.url
            
            member_info = {
                "Member_url": member_url,
                "Letter": response.meta['letter'],
                "Organization Name": organization_name,
                "Reg. No": reg_number,
                "Vat No": vat_number,
                "Address": address,
                "Country": country,
                "Website URL": website_url,
                "Email": email,
                "Telephone number": telephone_number,
                "Mobile number": mobile_number,
                "Fax": fax,
                "Po Box": po_box,
                "Key Person": key_person,
                "Establishment Date": establishment_date
            }

            return member_info

    def parse_member_info(self, response):
        """This function will call the extract_member_info function and append the member details to all_member_data list"""
        member_info = self.extract_member_info(response)
        self.all_member_data.append(member_info)

    
    def closed(self, reason):
        """This function will call the save_to_excel function"""
        df = pd.DataFrame(self.all_member_data)
        self.save_to_excel(df)


    def save_to_excel(self, df):
        """This function will save the member details to an excel file"""
        df.to_excel("taan_members.xlsx", index=False)
        self.log("Saved file taan_members.xlsx")
        
            

