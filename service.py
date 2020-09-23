from azure.cognitiveservices.vision.computervision import ComputerVisionClient
from azure.cognitiveservices.vision.computervision.models\
    import OperationStatusCodes, Line
from msrest.authentication import CognitiveServicesCredentials
from pprint import pprint

import os
import time

ENV_CV_SUBSCRIPTION_KEY = 'COMPUTER_VISION_SUBSCRIPTION_KEY'
ENV_CV_ENDPOINT = 'COMPUTER_VISION_ENDPOINT'

TEST_SCOREBOARD_IMAGE = 'https://i.stack.imgur.com/i5jSA.jpg'


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
    model for text item found from read result
    """

    def __init__(self, line: Line):
        self.text = line.text
        self.bounding_box = self._parse_bounding_box_arr(line.bounding_box)

        self.left_edge_center = Vec2.midpoint(
            self.bounding_box.bottom_left,
            self.bounding_box.top_left
        )

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

    def get_text_hist_dict(self) -> dict:
        """
        get the histogram dictionary of x, y coordinates for text results
        """
        # TODO: This probably needs to be moved into a scoreboard class
        res = dict()
        for item in self.text_items:
            # TODO: Figure out of it is a left anchored or center-anchored text
            #  Hint: if the text contains only numerals, it is center anchored
            #        otherwise, it is left anchored
            x = hist(item.left_edge_center.x, 20)
            y = hist(item.left_edge_center.y, 20)
            if x not in res:
                res[x] = dict()
            if y not in res[x]:
                res[x][y] = list()

            res[x][y].append(item)

        return res

    def print_read_info(self):
        for item in self.text_items:
            print("Item Text:", "'" + item.text + "'")
            print("    Corner Anchor:  x:", item.bounding_box.top_left.x,
                  "y:", item.bounding_box.top_left.y)
            print("    Bottom Anchor:  x:", item.bounding_box.bottom_left.x,
                  "y:", item.bounding_box.bottom_left.y)
            print("    Left Anchor:    x:", item.left_edge_center.x, "y:",
                  item.left_edge_center.y)
            print()

    def print_hist_dict(self):
        text_items = self.get_text_hist_dict()

        for x, ys in text_items.items():
            print("x:", x)
            for y, row_items in ys.items():
                print("  y:", y)
                for text_item in row_items:
                    print("    ", text_item.text)


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


def read_image_text(client: ComputerVisionClient, remote_url: str):
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


def main():
    client = _authenticate()

    # Call OCR API to get text readings and bounds
    image_text = read_image_text(client, TEST_SCOREBOARD_IMAGE)
    # Parse image results and build dict of entries
    ir = ImageResult(image_text)
    ir.print_hist_dict()
    # ir.print_read_info()


if __name__ == "__main__":
    main()
