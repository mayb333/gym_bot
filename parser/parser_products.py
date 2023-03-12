import requests
import json
from bs4 import BeautifulSoup


URL = 'http://natural-body.ru/tablitsa-kaloriynosti-produktov-bzhu'


def parse(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'lxml')
    tags = soup.find('div', class_='entry').find_all(['p', 'table'])

    categories_to_skip = ['Хлеб, хлебобулочные изделия, мука', 'Масло, жиры, маргарин', 'Колбаса и колбасные изделия',
                          'Мясные копченые продукты', 'Кондитерские изделия и сладости', ]

    parsed_data = {}
    for tag in tags:
        try:
            table_name = tag.find('span').find('strong').text[:-1]

            # check if there's a category I don't need and skip it
            if table_name in categories_to_skip:
                continue

            table = tag.find_next('table', class_='tbl').find('tbody').find_all('tr')
            parsed_data[table_name] = []
            for product in table[1:]:
                td_tags = product.find_all('td')
                product_info = []
                for td in td_tags:
                    product_info.append(td.text)

                item = {
                    'название': product_info[0].lower(),
                    'белки': '.'.join(product_info[2].strip().split(',')),
                    'жиры': '.'.join(product_info[3].strip().split(',')),
                    'углеводы': '.'.join(product_info[4].strip().split(',')),
                    'ккал': '.'.join(product_info[5].strip().split(',')),
                }
                parsed_data[table_name].append(item)
        except Exception:
            continue

    print(len(parsed_data.keys()))
    return parsed_data


def dump_to_json(data, filename):
    data = json.dumps(data)
    data = json.loads(str(data))

    with open(filename, 'w', encoding='utf-8') as file:
        json.dump(data, file, indent=4, ensure_ascii=False)


def get_from_json(filename):
    with open(filename, 'r', encoding='utf-8') as file:
        data = json.load(file)

    print(data.keys())


def main():
    data = parse(URL)
    dump_to_json(data=data, filename='proteins_data.json')
    # get_from_json('proteins_data.json')


if __name__ == '__main__':
    main()