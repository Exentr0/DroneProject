from mavsdk import System
from mavsdk.offboard import Attitude
import asyncio
import time

# Constants
TARGET_ALT = 14.0
IMAGE_WIDTH = 640
IMAGE_HEIGHT = 480
CENTER_X = IMAGE_WIDTH // 2
CENTER_Y = IMAGE_HEIGHT // 2

class PDController:
    def __init__(self, kp, kd):
        self.kp = kp
        self.kd = kd
        self.prev_error = 0

    def update(self, error, delta_time):
        derivative = (error - self.prev_error) / delta_time if delta_time > 0 else 0
        self.prev_error = error
        return self.kp * error + self.kd * derivative


altitude_controller = PDController(kp=0.01, kd=0.1)

async def check_for_circle():
    try:
        with open("circle_position.txt", "r") as f:
            data = f.read().strip()
            x, y = map(int, data.split(","))
            return x, y
    except Exception as e:
        print(f"Error reading circle data: {e}")
        return -1, -1

async def wait_for_circle():
    while True:
        x, y = await check_for_circle()
        if x != -1 and y != -1:
            return x, y
        await asyncio.sleep(0.1)

async def set_rpyt(drone, roll, pitch, yaw, thrust):
    attitude = Attitude(roll, pitch, yaw, thrust)
    await drone.offboard.set_attitude(attitude)

async def adjust_to_circle(drone, x, y, speed_x, speed_y):
    diff_x = (x - CENTER_X) / IMAGE_WIDTH
    diff_y = (y - CENTER_Y) / IMAGE_HEIGHT

    roll = diff_x * 12 + speed_x * 0.5
    pitch = diff_y * 12 + speed_y * 0.5

    async for pos in drone.telemetry.position():
        curr_alt = pos.relative_altitude_m
        error = TARGET_ALT - curr_alt
        delta_time = 0.1

        # Adjust thrust using the PID controller
        thrust = 0.5 + altitude_controller.update(error, delta_time)
        thrust = max(0.0, min(1.0, thrust))  # Clamp thrust between 0 and 1

        await set_rpyt(drone, roll, pitch, 0.0, thrust)
        break

async def run():
    drone = System()
    await drone.connect(system_address="udp://:14540")

    await drone.action.arm()

    await set_rpyt(drone, 0.0, 0.0, 0.0, 0.55)
    await drone.offboard.start()

    # Takeoff loop using PD control to reach target altitude
    while True:
        async for pos in drone.telemetry.position():
            curr_alt = pos.relative_altitude_m
            error = TARGET_ALT - curr_alt
            delta_time = 0.1

            thrust = 0.5 + altitude_controller.update(error, delta_time)
            thrust = max(0.0, min(1.0, thrust))

            await set_rpyt(drone, 0.0, 0.0, 0.0, thrust)

            if abs(error) < 0.1:
                print("Target altitude reached.")
                break
        break

    # Main loop to adjust to the circle position
    while True:
        x, y = await wait_for_circle()
        start_time = time.time()
        await asyncio.sleep(0.3)
        x_new, y_new = await wait_for_circle()
        t = (time.time() - start_time) * 1000

        speed_x = (x_new - x) * 350 / t
        speed_y = (y_new - y) * 350 / t

        await adjust_to_circle(drone, x_new, y_new, speed_x, speed_y)

if __name__ == "__main__":
    asyncio.run(run())
