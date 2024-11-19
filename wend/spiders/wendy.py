import scrapy
from scrapy import Request
from scrapy.http import Response
import json
from datetime import datetime

class WendySpider(scrapy.Spider):
    name = "wendy"
    allowed_domains = ["locations.wendys.com"]
    start_urls = ["https://locations.wendys.com/united-states"]

    def parse(self, response: Response):
        states =  response.xpath('//div[contains(@class, "Directory-content")]//ul[contains(@class, "Directory-listLinks")]//li[contains(@class, "Directory-listItem")]//a/@href').getall()
        yield from response.follow_all(states, self.parse_state)
        
    def parse_state(self, response: Response):
        cities = response.xpath('//div[contains(@class, "Directory-content")]//ul[contains(@class, "Directory-listLinks")]//li[contains(@class, "Directory-listItem")]//a/@href').getall()
        yield from response.follow_all(cities, self.parse_city)
        
    def parse_city(self, response: Response):
        is_store_page = response.xpath('//h1[contains(@class, "HeroBanner-title Heading--lead")]')
        if is_store_page:
            yield from self.parse_store(response)
        else:
            stores = response.xpath('//a[contains(@class, "Teaser-titleLink Link--big")]/@href').getall()
            yield from response.follow_all(stores, self.parse_store)
    def geo_loc(self, response):
        geo_dict = {}
        geo = response.xpath('//meta[@name="geo.position"]/@content').get().split(';')
        if geo:
            geo_dict = {
                "type" : "Point",
                "coordinates" : geo
            }
        else:
            self.logger.info("no location found!")

        return geo_dict
    def day_hour(self, response): 
        days = response.xpath('//div[contains(@class, "c-location-hours-details-wrapper js-location-hours")]/@data-days').get()
        hours_dict = {}
        if days:
            days = json.loads(days)
            for day in days:
                if day['intervals']:
                    day_name = day["day"].lower()
                    interval = day['intervals'][0]
                    hours_dict[day_name] = [
                        {
                        "open" : datetime.strptime(str(interval.get('start')).zfill(4), "%H%M").strftime("%I:%M %p"),
                        "close" : datetime.strptime(str(interval.get('end')).zfill(4), "%H%M").strftime("%I:%M %p")
                        }
                    ]
        else:
            self.logger.info("no json time found!")
        return hours_dict
            
    def parse_store(self, response: Response):
        geo_dict = self.geo_loc(response)
        hours_dict = self.day_hour(response)
        phone_number = response.xpath('//div[contains(@class, "c-phone-number c-phone-main-number")]/a/text()').get()
        services = response.xpath('//ul[contains(@class, "LocationInfo-serviceList")]//li[@class="LocationInfo-service"]//span[contains(@class, "LocationInfo-serviceText")]/text()').getall()
        address = response.xpath('//div[contains(@class, "c-AddressRow")]/span/text()').get().strip()
        address_2 = response.xpath('//div[contains(@class, "c-AddressRow")]//span[contains(@class, "c-address-city")]/text()').get()
        address_3 = response.xpath('//div[contains(@class, "c-AddressRow")]//abbr[contains(@class, "c-address-state")]/text()').get()
        address_4 = response.xpath('//div[contains(@class, "c-AddressRow")]//span[contains(@class, "c-address-postal-code")]/text()').get()
        yield{
            'name' : response.xpath('//div[contains(@class, "HeroBanner-container l-container")]//div[contains(@class, "HeroBanner-content")]//div[contains(@class, "HeroBanner-left")]//h1/text()').get(),
            'phone' : phone_number,
            'location' : geo_dict,
            'address' : f"{address}, {address_2}, {address_3}, {address_4} ",
            'services' : services,
            'url' : response.url,
            'hours' : hours_dict
            
        }
        
