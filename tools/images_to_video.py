import cv2
import os
import argparse

def images_to_video(input_dir: str, output_file: str, fps: int): 
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    images = [img for img in os.listdir(input_dir) if img.endswith(".png")]
    images.sort()  # Sort the images if needed

    frame = cv2.imread(os.path.join(input_dir, images[0]))
    height, width, _ = frame.shape

    video = cv2.VideoWriter(output_file, cv2.VideoWriter_fourcc(*'mp4v'), fps, (width,height))

    for image in images:
        video.write(cv2.imread(os.path.join(input_dir, image)))

    cv2.destroyAllWindows()
    video.release()



if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="images to video",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--input_dir",
        type=str,
        required=True,
        help="Output folder to store the final video and intermediate outputs.",
    )
    parser.add_argument(
        "--fps",
        type=int,
        default=24,
        required=False,
        help="fps",
    )
    parser.add_argument(
        "--output_file",
        type=str,
        required=False,
        default="./video.mp4",
        help="mp4 filename",
    )
    
    args = parser.parse_args()

    images_to_video(input_dir=args.input_dir, output_file=args.output_file, fps=args.fps)
