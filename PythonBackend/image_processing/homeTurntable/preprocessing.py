import cv2
import numpy as np
from GeneralProc.logger import logger
import globals


def preprocess(image, scale_percent):
    """Resize the image for faster processing.
        Input: Grayscale image
        Output: Scaled image"""


    try:
        image=cv2.resize(image, None, fx=scale_percent / 100, fy=scale_percent / 100, interpolation=cv2.INTER_AREA)
        return image, None
    except cv2.error as e:
        logger.error("E2011")
        return None, "E2011"



def rotate_image(image, angle):
    """Rotate an image by a given angle around its center.
        Input: Scaled Grayscale image, angle of rotation
        Output: Rotated image"""
    try:
        center = (image.shape[1] // 2, image.shape[0] // 2)
        rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1)
        return cv2.warpAffine(image, rotation_matrix, (image.shape[1], image.shape[0]))
    except:
        return None


def crop_second_two_thirds(image):
    print(globals.x_end)
    try:
        cropped_image = image[:, :globals.x_end]
        return cropped_image, None
    except:
        return None, "E2211"