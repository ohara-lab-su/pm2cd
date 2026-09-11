import time

from pm2cd.pm2cd_ctrl import PM2CD


IP_ADDRESS = "10.170.10.62"
PORT = 7777
MOTOR = 0


def main() -> None:
    pm2cd = PM2CD(
        ip_address=IP_ADDRESS,
        port=PORT,
    )

    try:
        print("[INFO] remote")
        print(pm2cd.remote())

        print("[INFO] motor setting")
        print(pm2cd.get_motor_setting(MOTOR))

        print("[INFO] status before")
        print(pm2cd.get_status(MOTOR))

        print("[INFO] position before")
        print(pm2cd.get_position(MOTOR))

        print("[INFO] jog cw")
        print(pm2cd.jog(MOTOR, "cw"))

        time.sleep(0.5)

        print("[INFO] status after")
        print(pm2cd.get_status(MOTOR))

        print("[INFO] position after")
        print(pm2cd.get_position(MOTOR))

    finally:
        pm2cd.disconnect()


if __name__ == "__main__":
    main()
