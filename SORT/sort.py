"""
As implemented in https://github.com/abewley/sort but with some modifications
"""

from __future__ import print_function

import utils.sort_utils as utils
import numpy as np
from SORT.correlation_tracker import CorrelationTracker
from SORT.data_association import associate_detections_to_trackers
from SORT.kalman_tracker import KalmanBoxTracker



class Sort:

    def __init__(self, max_age=1, min_hits=3, use_dlib=False):
        """
        Sets key parameters for SORT
        """
        self.max_age = max_age
        self.min_hits = min_hits
        self.trackers = []
        self.frame_count = 0

        self.use_dlib = use_dlib

    def update(self, dets, img_size, root_dic, addtional_attribute_list, img=None):
        """
        Params:
          dets - a numpy array of detections in the format [[x,y,w,h,score],[x,y,w,h,score],...]
        Requires: this method must be called once for each frame even with empty detections.
        Returns the a similar array, where the last column is the object ID.

        NOTE:as in practical realtime MOT, the detector doesn't run on every single frame
        """
        self.frame_count += 1
        #time_dict = dict()
        # get predicted locations from existing trackers.
        trks = np.zeros((len(self.trackers), 5))
        to_del = []
        ret = []
        for t, trk in enumerate(trks):
            pos = self.trackers[t].predict(img)  # for kal!
            # print(pos)
            trk[:] = [pos[0], pos[1], pos[2], pos[3], 0]
            if (np.any(np.isnan(pos))):
                to_del.append(t)
        trks = np.ma.compress_rows(np.ma.masked_invalid(trks))
        for t in reversed(to_del):
            self.trackers.pop(t)
        if dets != []:
            matched, unmatched_dets, unmatched_trks = associate_detections_to_trackers(dets, trks)

            # update matched trackers with assigned detections
            for t, trk in enumerate(self.trackers):
                if (t not in unmatched_trks):
                    d = matched[np.where(matched[:, 1] == t)[0], 0]
                    trk.update(dets[d, :][0], img)  ## for dlib re-intialize the trackers ?!
                    trk.face_addtional_attribute.append(addtional_attribute_list[d[0]])

            # create and initialise new trackers for unmatched detections
            for i in unmatched_dets:
                if not self.use_dlib:
                    trk = KalmanBoxTracker(dets[i, :])
                    trk.face_addtional_attribute.append(addtional_attribute_list[i])
                    
                else:
                    trk = CorrelationTracker(dets[i, :], img)
                self.trackers.append(trk)

        i = len(self.trackers)
        for trk in reversed(self.trackers):
            if dets == []:
                trk.update([], img)
            d = trk.get_state()
            if ((trk.time_since_update < 1) and (trk.hit_streak >= self.min_hits or self.frame_count <= self.min_hits)):
                ret.append(np.concatenate((d, [trk.id + 1])).reshape(1, -1))  # +1 as MOT benchmark requires positive
            i -= 1
            # remove dead tracklet
            if (trk.time_since_update >= self.max_age or d[2] < 0 or d[3] < 0 or d[0] > img_size[1] or d[1] > img_size[0]):
               
                if (len(trk.face_addtional_attribute) >= 5):
                    utils.save_to_file(root_dic, trk)
                    #time_dict.update({trk.id : self.frame_count})
                    with open('tracker_saved_greater_5.txt', 'a+') as f:
                         f.write(str(trk.id)+'.'+ str(self.frame_count) + "\n")

                self.trackers.pop(i)
        if (len(ret) > 0):
            return np.concatenate(ret)
        return np.empty((0, 5))
