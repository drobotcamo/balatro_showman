import json

names_to_img_urls = {}

with open("./jokers.txt", "r") as f:
    line = f.readline()
    while line:
        segments = line.split('/')
        print(segments[7])
        name = segments[7]
        names_to_img_urls[name[0:-4].replace('_', ' ')] = line[1:-3]
        line = f.readline()

with open("./joker_images.json", "w") as f:
    json.dump(names_to_img_urls, f, indent=4)
