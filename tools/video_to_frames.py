import cv2
import os 
import argparse
import multiprocessing



def crop_center(image, crop_ratio=1.0):
    if crop_ratio <= 0 or crop_ratio > 1:
        raise ValueError("Crop ratio must be between 0 and 1")

    height, width = image.shape[:2]
    new_height, new_width = int(height * crop_ratio), int(width * crop_ratio)

    # Calculate the starting points (top-left corner) of the crop
    start_x = width // 2 - new_width // 2
    start_y = height // 2 - new_height // 2

    # Crop and return the image
    return image[start_y:start_y + new_height, start_x:start_x + new_width]



def extract_video(video_path: str, out_dir: str, crop_ratio=1.0):
    os.makedirs(out_dir, exist_ok=True)
    cap = cv2.VideoCapture(video_path)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    for idx in range(total_frames):
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        # Read the frame
        success, frame = cap.read()
        if success:
            # Save the frame as an image file
            if crop_ratio != 1.0:
                frame = crop_center(image=frame, crop_ratio=crop_ratio)

            cv2.imwrite(os.path.join(out_dir, "{:04d}".format(idx) + ".jpg"), frame)
        else:
            print("Error: Unable to read the frame: ", idx)
            break

    cap.release()


def process_test_case(testcase):
    extract_video(testcase["path"], testcase["out_dir"])


if __name__ == "__main__":

    # Set up argument parser
    parser = argparse.ArgumentParser(description='Process videos.')
    parser.add_argument('--input_dir', type=str, help='Root directory of the videos')
    parser.add_argument('--output_dir', type=str, help='Directory to store results')
    parser.add_argument('--crop_ratio', type=float, default=1.0, help='Crop from center')
    parser.add_argument('--threads', type=int, default=8, help='Threads')



    # Parse arguments
    args = parser.parse_args()
    input_dir = args.input_dir
    output_dir = args.output_dir


    testcases = []
    for s in os.listdir(input_dir):
        sub = os.path.join(input_dir, s)
        if not os.path.isdir(sub):
            continue
        testcases.append({
            "name": s, 
            "path": os.path.join(input_dir, s, "video.mp4"),
            "out_dir": os.path.join(output_dir, s),
            })


    # # Number of processes in the pool
    num_processes = args.threads  # Adjust this number based on your requirement

    # Create a pool of workers and distribute the test cases
    with multiprocessing.Pool(num_processes) as pool:
        results = pool.map(process_test_case, testcases)


# python tools/video_to_frames.py --input_dir=testdata/showreel/2k-video/Birdhouses --output_dir=testdata/showreel/2k-frames/Birdhouses