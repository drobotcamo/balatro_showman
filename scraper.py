
with open("htmls\Booster Packs _ Balatro Wiki _ Fandom.htm", 'rb') as sourceFile:
    lines = sourceFile.readlines()

with open("booster.txt", "w+") as outputFile:

    findString = 'meless"><a href="'

    def writer(readableLine: str, start_index):
        if start_index > -1:
            start_index = start_index + len(findString)
            if start_index > 9:
                endIndex = readableLine.find('"', start_index)
                outputFile.write('"' + readableLine[start_index:endIndex] + '",\n')

            nextIndex = readableLine[endIndex:].find(findString)
            if nextIndex > -1:
                writer(readableLine[endIndex:], nextIndex)

        else:
            return -1


    findString = 'meless"><a href="'

    for line in lines:
        readableLine = line.decode("utf-8")
        start_index = readableLine.find(findString)
        writer(readableLine, start_index)


