import requests
import json
from bs4 import BeautifulSoup


def getVintedProducts(
    pref,
    filters=[
        "brand",
        "size",
        "price",
        "condition",
    ],
):
    url = "https://www.vinted.com/catalog?order=newest_first"
    print("pref: ",pref)
    extras = ''
    if pref:
        try:
            if pref['catalog']:
                for i in pref['catalog']:
                    url += "&catalog[]=" + i
        except:
            print('catalog error')
        try:
            if pref['size_ids']:
                for i in pref['size_ids']:
                    url += "&size_id[]=" + i
        except:
            print('size error')
        try:
            if pref['brand_ids']:
                for i in pref['brand_ids']:
                    url += "&brand_id[]=" + i
        except:
            print('brand error')
        try:
            if pref['price range']:
                url+=f"&price_from={pref['price range']['min']}&currency={pref['price range']['currency']}&price_to={pref['price range']['max']}"
        except:
            print('price error')
    print(url)
    response = requests.get(url)

    html = response.content
    # Parse HTML using Beautiful Soup
    soup = BeautifulSoup(html, "html.parser")

    # Find all elements with class "my-class"
    elements = soup.find_all(attrs={"data-js-react-on-rails-store": "MainStore"})

    # Extract JSON data from each element
    json_data = []
    for element in elements:
        data = element.text
        # print(element)
        if data:
            json_data.append(json.loads(data))
    return json_data[0]["items"]["catalogItems"]["byId"]
