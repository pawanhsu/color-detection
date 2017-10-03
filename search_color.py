#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__        import division
import os
import sys
import cv2
import json
import numpy as np
from matplotlib.colors import hsv_to_rgb
from PIL               import Image
from importlib         import *
from collections       import deque
from config            import *
from image_process.auto_white_balance import auto_white_balance
from image_process.lamp_filter        import lamp_filter
from image_process.crop_aspect_ratio  import crop_aspect_ratio
from image_process.get_roi            import get_roi
from apscheduler.scheduler            import Scheduler
import datetime

sched = Scheduler()
sched.start()

class Search_Color:

    def __init__(self, auto_update_status = True):
        """ class instance initialization """
        self.cls_has_night  = cls_has_night
        self.detect_cls     = detect_cls
        self.isNight        = True
        self.imgcache       = { cls: deque() for cls in self.detect_cls}
        self.profile        = {}
        for cls in detect_cls:
            with open(os.path.join('profile', cls + '_color_profile.json')) as profile:
                self.profile[cls] = json.load(profile)
        if auto_update_status:
            sched.add_interval_job(self.update_status, seconds = 2)


    def update_status(self):
        # to be called every half hour
        print('called')

    def detectDark(img,ratio):
        hsv = cv2.cvtColor(img,cv2.COLOR_BGR2HSV)
        h,s,v = cv2.split(hsv)
        hei,wid,chan = hsv.shape
        return (np.sum(v)/(hei*wid*255)) < ratio

    def color_detection(self, frame_in, detect_type = 'car'):

        if detect_type in self.cls_has_night:
            if len(self.imgcache) == 30:
                self.imgcache[detect_type].pop()
            self.imgcache[detect_type].append(frame_in)

        status = ('night' if self.isNight else 'day')

        cur_profile          = self.profile[detect_type]
        color_to_be_detected = cur_profile['color_to_be_detected']

        if detect_type in cls_has_night:
            cur_profile = cur_profile[status]

        if detect_type in do_crop_aspect_ratio:
            frame_in    = crop_aspect_ratio(frame_in,True)

        if detect_type in do_white_balance[status]:
            frame_in    = auto_white_balance(frame_in)

        res = [False] * len(color_to_be_detected)

        # loop over all the color to be detected
        for (idx, color) in enumerate(color_to_be_detected):

            if detect_type in do_lamp_filter:
                filtratio = cur_profile['filtratio'][color]
                (frame, lightMask) = lamp_filter(frame_in, filtratio)

            if detect_type in do_get_roi:
                roi_scale = cur_profile['roi_scale']
                if self.isNight:
                    roi_scale = roi_scale[color]
                frame = get_roi(frame, roi_scale)

                blockedPxl = sum(np.count_nonzero(e) for e in lightMask)
            else:
                frame = frame_in
                blockedPxl = 0

            (src_height, src_width, src_channels) = frame.shape
            max_value = (src_height * src_width - blockedPxl) * 255
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

            color_boundaries = cur_profile['range'][color]
            assert len(color_boundaries) % 2 == 0, '[DEBUG MSG]: Each boundary must have a lower/upper pair'

            mask = 0
            # loop over each boundary pair for this color
            for (lower, upper) in zip(color_boundaries[0::2],color_boundaries[1::2]):
                # detecting...
                mask = mask + cv2.inRange(hsv, np.array(lower),np.array(upper))

            if float(max_value) != 0:
                Val = float(mask.sum()) / float(max_value)
            else:
                Val = 0

            if round(Val,2) >= cur_profile['threshold'][color]:
                res[idx] = True
        return res


if __name__ == '__main__':
    search_color = Search_Color()
    img = cv2.imread('test2.jpg')
    print search_color.color_detection(img,'car')
