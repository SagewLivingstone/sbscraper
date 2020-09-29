from azure.cognitiveservices.vision.computervision import ComputerVisionClient
from azure.cognitiveservices.vision.computervision.models\
    import OperationStatusCodes, Line
from msrest.authentication import CognitiveServicesCredentials
from pprint import pprint

import os
import re
import time

ENV_CV_SUBSCRIPTION_KEY = 'COMPUTER_VISION_SUBSCRIPTION_KEY'
ENV_CV_ENDPOINT = 'COMPUTER_VISION_ENDPOINT'

TEST_SCOREBOARD_IMAGE = 'https://i.stack.imgur.com/i5jSA.jpg'

SIEGE_NUMERAL_EXP = r"^[Oo\d]{0,4}$"
SIEGE_NAME_EXP = r"^(?=.{3,15}$)(?![_.0-9-])[a-zA-Z0-9._-]+$"


def hist(a: float, r: float) -> float:
    """
    return the bucket number of the parameter a and range width r
    """
    return r*(round(a / r))


class Vec2():
    """
    2D vector
    """

    def __init__(self,
                 x: float,
                 y: float):
        self.x = x
        self.y = y

    @staticmethod
    def midpoint(a, b):
        """
        return midpoint of 2 vectors
        """
        return Vec2(
            (a.x + b.x) / 2,
            (a.y + b.y) / 2
        )


class BoundingBox():
    """
    image result bounding box
    """

    def __init__(self, vec2_arr: list):
        self.top_left = vec2_arr[0]
        self.top_right = vec2_arr[1]
        self.bottom_right = vec2_arr[2]
        self.bottom_left = vec2_arr[3]


class TextItem():
    """
    model for text item found from image read result
    """

    def __init__(self, line: Line):
        self.text = self._get_cleansed_text(line.text)
        self.bounding_box = self._parse_bounding_box_arr(line.bounding_box)

        self.left_anchor = Vec2.midpoint(
            self.bounding_box.bottom_left,
            self.bounding_box.top_left
        )

        self.center_anchor = Vec2.midpoint(
            Vec2.midpoint(
                self.bounding_box.bottom_left,
                self.bounding_box.top_left
            ),
            Vec2.midpoint(
                self.bounding_box.bottom_right,
                self.bounding_box.top_right
            )
        )

        self._get_text_type()
    
    @staticmethod
    def _get_cleansed_text(text: str) -> str:
        text = text.replace('?', '')
        if text.count(" ") <= 2:
            text = text.replace(' ', '')
        return text

    def _get_text_type(self):
        numeral = re.match(SIEGE_NUMERAL_EXP, self.text)
        name = re.match(SIEGE_NAME_EXP, self.text)

        if numeral and name:
            # Both??? ... do sanity check later
            self.type = 'mix'
            self.anchor = self.left_anchor
        elif numeral:
            self.type = 'numeral'
            self.anchor = self.center_anchor
        elif name:
            self.type = 'name'
            self.anchor = self.left_anchor
        else:
            self.type = 'neither'
            self.anchor = self.left_anchor

    @staticmethod
    def _parse_bounding_box_arr(bounding_box: list) -> BoundingBox:
        parsed = list()
        try:
            for i in range(0, 8, 2):
                parsed.append(
                    Vec2(bounding_box[i], bounding_box[i+1])
                )
        except KeyError:
            return None

        return BoundingBox(parsed)


class ImageResult():
    """
    object that hold methods for parsed image result from Azure OCR API
    """

    def __init__(self, image_text):
        self.text_items = list()

        if image_text:
            for read_result in image_text.analyze_result.read_results:
                for line in read_result.lines:
                    # Add entry for text item
                    self.text_items.append(TextItem(line))

    def print_read_info(self):
        for item in self.text_items:
            print("Item Text:", "'" + item.text + "'")
            print("    Corner Anchor:  x:", item.bounding_box.top_left.x,
                  "y:", item.bounding_box.top_left.y)
            print("    Bottom Anchor:  x:", item.bounding_box.bottom_left.x,
                  "y:", item.bounding_box.bottom_left.y)
            print("    Left Anchor:    x:", item.left_anchor.x, "y:",
                  item.left_anchor.y)
            print()


class Parser():
    def __init__(self,
                 client: ComputerVisionClient = None,
                 url: str = None):
        self._client = client
        self._url = url
        if client and url:
            self.parse_image(client, url)

    def parse_image(self, client, url):
        self._image_text = self.read_image_text(client, url)
        self._result = ImageResult(self._image_text)

    def read_image_text(self, client: ComputerVisionClient, remote_url: str):
        """
        read text from an image using the Azure OCR Read API
        """
        print(f"Calling read API on {remote_url}")

        read_result = client.read(remote_url, raw=True)

        operation_location_remote = read_result.headers['Operation-Location']
        operation_id = operation_location_remote.split('/')[-1]

        # GET method for read results
        while True:
            read_operation_result = client.get_read_result(operation_id)
            if read_operation_result.status not in [
                OperationStatusCodes.not_started,
                    OperationStatusCodes.running]:
                break
            time.sleep(1)  # Re-check every second

        return read_operation_result if read_operation_result.status ==\
            OperationStatusCodes.succeeded else None

    def get_text_hist_dict(self) -> dict:
        """
        get the histogram dictionary of x, y coordinates for text results
        """
        # TODO: This probably needs to be moved into a scoreboard class
        res = dict()
        for item in self._result.text_items:
            # Figure out of it is a left anchored or center-anchored text
            x = hist(item.anchor.x, 60)
            y = hist(item.anchor.y, 30)

            if x not in res:
                res[x] = dict()
            if y not in res[x]:
                res[x][y] = list()

            res[x][y].append(item)

        return res

    def print_hist_dict(self):
        text_items = self.get_text_hist_dict()

        for x, ys in text_items.items():
            print("x:", x)
            for y, row_items in ys.items():
                print("  y:", y)
                for text_item in row_items:
                    print("    ", text_item.text)

    def parse_siege_scoreboard(self):
        """
        new attempt at parsing the scoreboard
        """
        # Get all the possible name candidates in the results
        name_cand = []
        for item in self._result.text_items:
            print(f" Found {item.text} at x: {item.anchor.x}")
            if item.type == 'name':
                name_cand.append(item)
        name_cand.sort(key=lambda i: i.anchor.x)

        print('-----------------')
        print("Found these player candidates")
        for item in name_cand:
            print(f"x: {item.anchor.x} : {item.text}")
        print("------------------")

        # Find a continuous subset where 6+ are in a column within an error range
        # TODO: Comment the fuck outa this
        # TODO: Move this to a get_players function
        result = []
        TOLERANCE = 1.15
        SECONDARY_TOLERANCE = 1.05
        subset_length = 6  # This is a const
        for i in range(0, len(name_cand) - (subset_length-1)):
            subset_failed = False
            subset = name_cand[i:i+subset_length]
            col_x = subset[0].anchor.x
            for item in subset:
                if item.anchor.x >= TOLERANCE*col_x:
                    subset_failed = True
                    break

            if not subset_failed:
                print('--------------')
                print("This subset didn't fail, adding extras:")
                for item in subset:
                    print(item.text)
                result = subset
                col_x = name_cand[i+subset_length-1].anchor.x
                for j in range(i+subset_length, len(name_cand)):
                    if name_cand[j].anchor.x < SECONDARY_TOLERANCE*col_x:
                        result.append(name_cand[j])
                        print(f"Adding: {name_cand[j].text}")
                        col_x = name_cand[j].anchor.x
                    else:
                        print(f"Failed at: {name_cand[j].text}")
                        break
                break
        print('-----------')
        print(f"Got {len(result)} players")
        for res in result:
            print(res.text)

    def parse_siege_scoreboard_old(self):
        # Algorithm overview:
        hist = self.get_text_hist_dict()

        # 1. find all the usernames, validate that there's at least 6~7
        stat_cols = {}
        names = {}
        for x, ys in hist.items():
            if len(ys) > 6:
                # This could be considered a 'column', check for names
                name_count = 0
                numeral_count = 0
                neither_count = 0
                for y, items in ys.items():
                    # Check if this is a name
                    for item in items:
                        if item.type == 'name':
                            name_count += 1
                        if item.type == 'numeral':
                            numeral_count += 1
                        if item.type == 'neither':
                            neither_count += 1
                
                # Now, determine what kind of column this is
                if name_count > 6:
                    # This is the name column
                    names = ys
                    continue
                elif numeral_count > 6:
                    stat_cols[x] = ys
                    continue

                # maybe debug 'neither' and 'both' later

        print(f"Found {len(stat_cols)} stat columns")
        if len(stat_cols) == 5:
            # Ok we got 5 stat columns, so far so good
            # now figure out which column is which
            keys = sorted(stat_cols.keys())
            points_col = stat_cols[keys[0]]
            kills_col = stat_cols[keys[1]]
            assists_col = stat_cols[keys[2]]
            deaths_col = stat_cols[keys[3]]
            ping_col = stat_cols[keys[4]]
        
        # TODO !!!!!!!!!!!!!!!1
        """
        note: histogramming isn't gonna work if values land right on
        the edge of a bucket. aka, we need a better way to find values
        in a semi-grid

        maybe look into ocr chart-detecting methods online
        congregating around averages?
        """
        
        for y, player in names.items():
            if len(player) == 1:
                player = player[0].text
            else:
                return  # this is a problem...
            
            try:
                for score in points_col[y]:
                    if score.type == 'numeral':
                        points = score.text
                        break
            except KeyError:
                print(f"Could not find points for {player} at {y}")
                for cy, scores in points_col.items():
                    for score in scores:
                        print(f"  {cy} = {score.text}")
                continue
            try:
                for kill in kills_col[y]:
                    if kill.type == 'numeral':
                        kills = kill.text
                        break
            except KeyError:
                print(f"Could not find kills for {player} at {y}")
                continu
            print(f"Player {player} :  {points} | {kills}")

        self.print_hist_dict()
            
        # for x, col in stat_cols.items():
        #     print("Found column:")
        #     for y, items in col.items():
        #         for item in items:
        #             print(f"    : {item.text}")

        # 2. find each stat column with same # of entries as players, save as a guess
        # 3. for each stat, try to find the player that matches it and save to sb object

        # 4. find score to the left of player names
        # 5. find map name right above mode


def _authenticate() -> ComputerVisionClient:
    try:
        subscription_key = os.environ[ENV_CV_SUBSCRIPTION_KEY]
    except KeyError as e:
        print(f'Error getting environment variable {ENV_CV_SUBSCRIPTION_KEY}')
        raise e

    try:
        endpoint = os.environ[ENV_CV_ENDPOINT]
    except KeyError as e:
        print(f'Error getting environment variable {ENV_CV_ENDPOINT}')
        raise e

    return ComputerVisionClient(
        endpoint,
        CognitiveServicesCredentials(subscription_key)
    )


def describe_image(client: ComputerVisionClient, remote_url: str):
    """
    Describe image contents - remote
    """
    print(f"Calling description API for image {remote_url}")

    description_results = client.describe_image(remote_url)

    print("Recieved image description:")
    if (len(description_results.captions) == 0):
        print("No description received")
    else:
        for caption in description_results.captions:
            print(f"'{caption.text}' with confidence:\
                  {caption.confidence * 100}")


def get_image_category(client: ComputerVisionClient, remote_url: str):
    """
    Get image categorization - remote
    """
    print(f"Calling categorization API for image {remote_url}")

    remote_image_features = ["categories"]

    categorize_results_remote = client.analyze_image(remote_url,
                                                     remote_image_features)

    print("Categories from image:")
    if (len(categorize_results_remote.categories) == 0):
        print("No categories detected")
    else:
        for category in categorize_results_remote.categories:
            print(f"{category.name} with confidence {category.score * 100}")


def main():
    client = _authenticate()

    # Call OCR API to get text readings and bounds
    image = "https://i.stack.imgur.com/i5jSA.jpg"
    p = Parser(client, image)
    p.parse_siege_scoreboard()
    # p._result.print_hist_dict()
    # image_text = read_image_text(client, TEST_SCOREBOARD_IMAGE)
    # Parse image results and build dict of entries
    # ir = ImageResult(image_text)
    # ir.print_hist_dict()

    # ir.print_read_info()


if __name__ == "__main__":
    main()
