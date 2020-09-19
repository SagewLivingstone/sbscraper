from azure.cognitiveservices.computervision import ComputerVisionClient
# from azure.cognitiveservices.computervision.models import OperationStatusCodes, VisualFeatureTypes
from msrest.authentication import CognitiveServicesCredentials

# import os
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


def main():
    client = _authenticate()

    remote_image_url = "https://raw.githubusercontent.com/Azure-Samples/cognitive-services-sample-data-files/master/ComputerVision/Images/landmark.jpg"

    


if __name__ == "main":
    main()
