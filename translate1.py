from translate import Translator
import json

with open("trans_size.json", "r") as f:
    data = json.load(f)

for j in data:
    print(len(j['sizes']))
    for i in j['sizes']:
        translator= Translator(from_lang="french",to_lang="english")
        try:
            translation = translator.translate(i['title'])
            print( i['id'] ,translation)
            i['title'] = translation
        except:
            print(i, 'failed')
with open('trans_size.json', 'w') as json_file:
    # Use json.dump to save the object as JSON
    json.dump(data, json_file, indent=4)

