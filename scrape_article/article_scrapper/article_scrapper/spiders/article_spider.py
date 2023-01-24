import scrapy
import html2text
from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from datetime import datetime

class ArticleSpider(CrawlSpider):
    name = 'article'
    start_urls = ['https://helpdesk.revelator.com/support/home']
    rules = (
        Rule(LinkExtractor(allow='folders', deny='articles',), follow=True),
        Rule(LinkExtractor(allow='articles'), callback='parse_item',)
    )
    
    def parse_item(self, response):
        article_id = response.url.split("/")[-1]
        article_title = response.css("h2.heading::text").get().strip()
        
        article_body = response.css("#article-body").extract()
        h = html2text.HTML2Text()
        h.ignore_links = True
        h.ignore_images = True
        
        content = h.handle(article_body[0])

        breadcrumb = response.css(".breadcrumb a::text").extract()

        page_url = response.url

        modified_on = response.css(".heading+ p::text").extract_first()
        date_object = datetime.strptime(
            modified_on, "Modified on: %a, %d %b, %Y at %I:%M %p"
        )
        modified_on = date_object.date()
       
        related_articles_url = f"https://helpdesk.revelator.com/support/search/articles/{article_id}/related_articles?container=related_articles&limit=10"
        
        yield scrapy.Request(
            related_articles_url,
            callback=self.parse_related_articles,
            meta={
                "article_title": article_title,
                "content": content,
                "breadcrumb": breadcrumb,
                "page_url": page_url,
                "modified_on": modified_on,
            },
        )
    
    def parse_related_articles(self, response):
        self.logger.info("Visited %s", response.url)

        article_title = response.meta["article_title"]
        content = response.meta["content"]
        breadcrumb = response.meta["breadcrumb"]
        page_url = response.meta["page_url"]
        related_articles = response.css("a::text").extract()
        modified_on = response.meta["modified_on"]


        yield {
            "article_title": article_title,
            "content": content,
            "breadcrumb": breadcrumb,
            "page_url": page_url,
            "related_articles": related_articles,
            "modified_on": modified_on,
        }
