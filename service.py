from azure.cognitiveservices.vision.computervision import ComputerVisionClient
# from azure.cognitiveservices.vision.computervision.models import OperationStatusCodes, VisualFeatureTypes
from msrest.authentication import CognitiveServicesCredentials
from pprint import pprint

import os
# import sys
# import time

# from array import array
# from PIL import Image

ENV_CV_SUBSCRIPTION_KEY = 'COMPUTER_VISION_SUBSCRIPTION_KEY'
ENV_CV_ENDPOINT = 'COMPUTER_VISION_ENDPOINT'


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

    remote_image_url = "https://raw.githubusercontent.com/Azure-Samples/cognitive-services-sample-data-files/master/ComputerVision/Images/landmark.jpg"

    describe_image(client, remote_image_url)

    get_image_category(client, remote_image_url)

if __name__ == "__main__":
    main()
