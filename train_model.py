from ultralytics import YOLO
import helper


if __name__ == '__main__':
    # if a pre-trained custom model exists, load it instead
    model = YOLO(helper.find_last_best_model_path())

    # train the model
    model.train(data=helper.CONFIG_FILE, epochs=300)

