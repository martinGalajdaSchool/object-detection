from models.yolov3.constants import PathConstants
from keras.models import load_model
from utils.non_max_suppression import non_max_suppression
from utils.math import sigmoid
import time

import numpy as np

ANCHORS = np.array([
    [[116, 90], [156, 198], [373, 326]],
    [[30, 61], [62, 45], [59, 119]],
    [[10, 13], [16, 30], [33, 23]]
])

MODEL_WIDTH, MODEL_HEIGHT = (608, 608)


def restore_model(path_to_model = PathConstants.YOLOV3_MODEL_OPENIMAGES_OUT_PATH):
    return load_model(path_to_model)


def infer_objects_in_image(
    *,
    image: np.array,
    path_to_model=PathConstants.YOLOV3_MODEL_OPENIMAGES_OUT_PATH,
    orig_image_height: int,
    orig_image_width: int,
    detection_prob_treshold= 0.5,
    model = None
):
    yolov3fully_conv = restore_model(path_to_model) if model is None else model

    start_predict = time.time()
    predicted = yolov3fully_conv.predict(image / 255.)
    end_predict = time.time()
    print(f'YOLOv3 predict took {end_predict - start_predict} seconds.')

    detected_objects = []
    detected_classes = []
    detected_scores_all_classes = []

    for anchor_idx, yolo_predicted in enumerate(predicted):
        num_of_grid_cols, num_of_grid_rows, num_of_anchors = yolo_predicted.shape[1], yolo_predicted.shape[2], 3
        np_arr_predicted = yolo_predicted.reshape((1, num_of_grid_cols, num_of_grid_rows, num_of_anchors, -1))

        curr_detected_objects, curr_detected_classes, curr_detected_scores_all_classes = _detect_objects(
            orig_image_height=orig_image_height,
            orig_image_width=orig_image_width,
            yolo_predicted=np_arr_predicted,
            anchor_start_idx=anchor_idx,
            prob_treshold=detection_prob_treshold
        )

        detected_objects += curr_detected_objects
        detected_classes += curr_detected_classes
        detected_scores_all_classes += curr_detected_scores_all_classes

    return detected_objects, detected_classes, detected_scores_all_classes


def get_corrected_boxes(*, box_width, box_height, box_x, box_y, orig_image_shape, model_image_shape):
    orig_image_w, orig_image_h = orig_image_shape
    model_w, model_h = model_image_shape

    if float(model_w / orig_image_w) < float(model_h / orig_image_h):
        new_w = model_w
        new_h = float(orig_image_h * model_w) / orig_image_w
    else:
        new_h = model_h
        new_w = float(orig_image_w * model_h) / orig_image_h

    box_x = (box_x - (((model_w - new_w)/2.0)/model_w)) / float(new_w/model_w)
    box_y = (box_y - (((model_h - new_h)/2.0)/model_h)) / float(new_h/model_h)

    box_width *= model_w/new_w
    box_height *= model_h/new_h

    left = (box_x - (box_width/2.)) * orig_image_w
    right = (box_x + (box_width/2.)) * orig_image_w
    top = (box_y - (box_height/2.)) * orig_image_h
    bottom = (box_y + (box_height/2.)) * orig_image_h

    output_box = [
        int(left),
        int(top),
        int(right),
        int(bottom)
    ]

    return output_box


def _detect_objects(
    *,
    orig_image_width: int,
    orig_image_height: int,
    yolo_predicted: np.array,
    anchor_start_idx: int,
    prob_treshold: float,
    nms_iou_tresh = 0.5
):
    box_candidates = []
    box_scores = []
    box_classes = []

    num_of_grid_cols, num_of_grid_rows = yolo_predicted.shape[1], yolo_predicted.shape[2]

    for col_idx, cell_grid in enumerate(yolo_predicted[0]):
        for row_idx, cell in enumerate(cell_grid):
            for anchor_idx, box in enumerate(cell):
                prob_obj = sigmoid(box[4])

                class_probs = list(map(lambda x: sigmoid(x), box[5:]))

                prob_chosen_class = prob_obj * np.array(class_probs)
                detected_classes_idx = np.where(prob_chosen_class > prob_treshold)[0]

                if len(detected_classes_idx) > 0:
                    box_center_x = (row_idx + sigmoid(box[0])) / num_of_grid_rows
                    box_center_y = (col_idx + sigmoid(box[1])) / num_of_grid_cols

                    width_feat = box[2]
                    height_feat = box[3]

                    grid_cell_width = (np.exp(width_feat) * ANCHORS[anchor_start_idx][anchor_idx][0]) / MODEL_WIDTH
                    grid_cell_height = (np.exp(height_feat) * ANCHORS[anchor_start_idx][anchor_idx][1]) / MODEL_HEIGHT

                    box_left_x, box_left_y, box_right_x, box_right_y = get_corrected_boxes(
                        box_width=grid_cell_width,
                        box_height=grid_cell_height,
                        box_x=box_center_x,
                        box_y=box_center_y,
                        orig_image_shape=(orig_image_width, orig_image_height),
                        model_image_shape=(MODEL_WIDTH, MODEL_HEIGHT))

                    for i in detected_classes_idx:
                        detected_class_idx = i
                        box_candidates.append([
                            box_left_x,
                            box_left_y,
                            box_right_x,
                            box_right_y
                        ])

                        box_classes.append(detected_class_idx)
                        box_scores.append(prob_chosen_class[i])

    chosen_box_indices = non_max_suppression(box_candidates, box_scores, box_classes, nms_iou_tresh)

    picked_boxes = [box_candidates[i] for i in chosen_box_indices]
    picked_classes = [box_classes[i] for i in chosen_box_indices]
    picked_scores = [box_scores[i] for i in chosen_box_indices]

    return picked_boxes, picked_classes, picked_scores
