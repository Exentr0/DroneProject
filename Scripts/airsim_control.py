import airsim
import cv2
import numpy as np


def run():
    c = airsim.MultirotorClient(ip="172.31.160.1")
    c.confirmConnection()
    c.enableApiControl(True)

    cam_pos = airsim.Pose()
    cam_pos.position = airsim.Vector3r(0, 0, 0)
    local_cam_rot = airsim.to_quaternion(-np.pi / 2, 0, 0)

    while True:
        drone_pos = c.simGetVehiclePose()
        drone_orientation = drone_pos.orientation

        inv_orientation = airsim.Quaternionr(
            -drone_orientation.x_val,
            -drone_orientation.y_val,
            -drone_orientation.z_val,
            drone_orientation.w_val
        )

        cam_pos.orientation = inv_orientation * local_cam_rot
        c.simSetCameraPose("Front", cam_pos)

        res = c.simGetImages([airsim.ImageRequest("Front", airsim.ImageType.Scene, False, False)])
        img1d = np.frombuffer(res[0].image_data_uint8, dtype=np.uint8)
        img_rgb = img1d.reshape(res[0].height, res[0].width, 3)

        img_copy = np.copy(img_rgb)

        img_gray = cv2.cvtColor(img_copy, cv2.COLOR_BGR2GRAY)

        img_blur = cv2.GaussianBlur(img_gray, (9, 9), 2)

        circles = cv2.HoughCircles(
            img_blur,
            cv2.HOUGH_GRADIENT,
            dp=1.2,
            minDist=500,
            param1=100,
            param2=30,
            minRadius=30,
            maxRadius=1000
        )

        if circles is not None:
            circles = np.round(circles[0, :]).astype("int")
            with open("circle_position.txt", "w") as f:
                x, y, _ = circles[0]
                f.write(f"{x},{y}\n")
            for (x, y, r) in circles:
                cv2.circle(img_copy, (x, y), r, (0, 255, 0), 4)
                cv2.circle(img_copy, (x, y), 2, (0, 0, 255), 3)
        else:
            with open("circle_position.txt", "w") as f:
                f.write("-1,-1\n")

        cv2.imshow("Drone Cam - Circle Detection", img_copy)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cv2.destroyAllWindows()


if __name__ == "__main__":
    run()
