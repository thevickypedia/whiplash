from logging import basicConfig, getLogger, INFO
from os import environ

from boto3 import client
from bs4 import BeautifulSoup
from requests import get
from requests_html import HTMLSession


# noinspection PyUnresolvedReferences
def amazon(asin):
    url = f'https://www.amazon.com/dp/{asin}/'
    session = HTMLSession()
    response = session.get(url)
    response.html.render()

    title = response.html.xpath('//*[@id="productTitle"]', first=True).text
    logger.info(f' Title: {title}')

    avail_check = response.html.xpath('//*[@id="availability"]', first=True)
    if 'Currently unavailable.' in avail_check.text:
        availability = 'Currently Unavailable'
    elif 'In Stock.' in avail_check.text:
        availability = 'In Stock'
    elif 'in stock' in avail_check.text:
        availability = avail_check.text
    else:
        availability = 'Unknown'
    logger.info(f' Availability: {availability}')

    price = response.html.xpath('//*[@id="priceblock_ourprice"]', first=True)
    if price:
        price = price.text
        logger.info(f' Price: {price}')

    prime_check = response.html.xpath('//*[@id="creturns-return-policy-separator"]', first=True)
    if prime_check and prime_check.text == '&':
        prime = 'True'
    else:
        prime = 'False'
    logger.info(f' Prime: {prime}')

    if price:
        return f'Title: {title}\nAvailability: {availability}\nPrice: {price}\nPrime: {prime}\nURL: {url}'
    else:
        return f'Title: {title}\nAvailability: {availability}\nPrice: {price}\nPrime: {prime}'


def walmart(product_id):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/58.0.3029.110 Safari/537.3'}
    url = f'https://www.walmart.com/ip/{product_id}'
    response = get(url=url, headers=headers).text
    soup = BeautifulSoup(response, 'lxml')

    raw_name = soup.find_all('h1', {'class': 'prod-ProductTitle prod-productTitle-buyBox font-bold'})[0]
    title = raw_name.text.strip()
    logger.info(f' Title: {title}')

    raw_price = soup.find_all('span', {'class': 'price display-inline-block arrange-fit price price--stylized'})[0]
    price = raw_price.find('span').text
    logger.info(f' Price: {price}')

    raw_avail = soup.find_all('section', {'class': 'prod-ProductCTA primaryProductCTA-marker'})[0]
    availability = raw_avail.find('button').find('span').text
    logger.info(f' Availability: {availability}')

    raw_delivery = soup.find_all('div', {'class': 'fulfillment-buy-box-update'})[0]
    fulfillment_box = raw_delivery.find_all('div')
    delivery_options = []
    for item in fulfillment_box:
        if (div := item.find('div')) and (options := div.find('span')):
            if (appender := options.text) and appender not in delivery_options:
                delivery_options.append(appender)
    delivery_options = ', '.join(delivery_options)
    logger.info(f' Delivery Options: {delivery_options}')

    return f'Title: {title}\nAvailability: {availability}\nPrice: {price}\n' \
           f'Delivery Options: {delivery_options}\nURL: {url}'


def notify(message):
    if (access_key := environ.get('ACCESS_KEY')) and (secret_key := environ.get('SECRET_KEY')):
        sns = client('sns', aws_access_key_id=access_key, aws_secret_access_key=secret_key)
    else:
        sns = client('sns')
    if not (phone_number := environ.get('PHONE')):
        logger.error('Phone number is not stored as ENV VAR to kick off notifications.')
    else:
        response = sns.publish(PhoneNumber=phone_number, Message=message)
        if response.get('ResponseMetadata').get('HTTPStatusCode') == 200:
            logger.info('Notification has been sent.')
        else:
            logger.error(f'Unable to send notification.\n{response}')


if __name__ == '__main__':
    getLogger(name='pyppeteer.launcher').propagate = False
    basicConfig(format='%(asctime)s - %(levelname)s - %(funcName)s - Line: %(lineno)d - %(message)s', level=INFO)
    logger = getLogger(__name__)
    status = amazon(asin='B08KTPHGPP')
    notify(message=status)
    status = walmart(product_id='427810711')
    notify(message=status)
