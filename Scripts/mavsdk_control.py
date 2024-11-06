from mavsdk import System
from mavsdk.offboard import Attitude
import asyncio
import time
import numpy as np

TARGET_ALT = 14.0
UP_THRUST = 0.52
DOWN_THRUST = 0.45
HOLD_THRUST = 0.55

IMAGE_WIDTH = 640
IMAGE_HEIGHT = 480
CENTER_X = IMAGE_WIDTH // 2
CENTER_Y = IMAGE_HEIGHT // 2


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
    magnitude = np.sqrt(diff_x ** 2 + diff_y ** 2)

    roll = diff_x * 12 + speed_x * 0.5
    pitch = diff_y  * 12 + speed_y * 0.5

    async for pos in drone.telemetry.position():
        curr_alt = pos.relative_altitude_m

        if curr_alt > TARGET_ALT:
            thrust = DOWN_THRUST
        elif curr_alt < TARGET_ALT:
            thrust = UP_THRUST
        else:
            thrust = HOLD_THRUST

        await set_rpyt(drone, roll, pitch, 0.0, thrust + 0.2 * thrust * magnitude)
        break


async def run():
    drone = System()
    await drone.connect(system_address="udp://:14540")

    await drone.action.arm()

    await set_rpyt(drone, 0.1, -0.2, 0.0, UP_THRUST)
    await drone.offboard.start()

    async for pos in drone.telemetry.position():
        curr_alt = pos.relative_altitude_m

        if curr_alt < TARGET_ALT:
            await set_rpyt(drone, 0.0, 0.0, 0.0, UP_THRUST)
        else:
            print("Target altitude reached.")
            await set_rpyt(drone, 0.0, 0.0, 0.0, DOWN_THRUST)
            break

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