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

        print("[INFO] limit switch setting")
        print(pm2cd.get_limit_switch_setting(MOTOR))

        print("[INFO] motor setting")
        print(pm2cd.get_motor_setting(MOTOR))

        print("[INFO] status")
        status = pm2cd.get_status(MOTOR)
        print(status)

        if status is not None:
            print(f"[INFO] ls_status: 0x{status.ls_status:X}")
            print(f"[INFO] CW LS : {bool(status.ls_status & 0x01)}")
            print(f"[INFO] CCW LS: {bool(status.ls_status & 0x02)}")
            print(f"[INFO] HP LS : {bool(status.ls_status & 0x04)}")

        print("[INFO] position")
        print(pm2cd.get_position(MOTOR))

    finally:
        pm2cd.disconnect()


if __name__ == "__main__":
    main()
