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
    if pref:
        for i in pref:
            url += "&catalog[]=" + i

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
