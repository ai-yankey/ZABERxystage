"""
Basic Zaber XY stage controller for X-ADR250B100B-SAE53D12-style 2-axis stages.

Designed to be importable later by a larger experiment controller that also
handles an Edinburgh spectrometer and a Zaber cooling stage.

Examples:
    python zaber_xy_stage.py --port COM3 status
    python zaber_xy_stage.py --port COM3 home
    python zaber_xy_stage.py --port COM3 move-abs --x 10 --y 20
    python zaber_xy_stage.py --port COM3 move-rel --dx 1 --dy -1
    python zaber_xy_stage.py --port COM3 stop
"""

''' move-abs and move-rel need to be slowed'''

'''pip install --upgrade zaber-motion'''



import argparse
from dataclasses import dataclass
from typing import Optional, Tuple

from zaber_motion import Units
from zaber_motion.ascii import Connection, AxisGroup


MM = Units.LENGTH_MILLIMETRES
MM_PER_S = Units.VELOCITY_MILLIMETRES_PER_SECOND


@dataclass
class XYPosition:
    x_mm: float
    y_mm: float


class ZaberXYStage:
    """
    Thin wrapper around a 2-axis Zaber ASCII device.

    Assumptions:
    - One Zaber device controls both X and Y axes.
    - Axis 1 = X, Axis 2 = Y.
    - Positions are handled in millimetres.
    """

    def __init__(
        self,
        port: str,
        device_index: int = 0,
        x_axis_number: int = 1,
        y_axis_number: int = 2,
        min_x_mm: Optional[float] = 0.0,
        max_x_mm: Optional[float] = None,
        min_y_mm: Optional[float] = 0.0,
        max_y_mm: Optional[float] = None,
    ):
        self.port = port
        self.device_index = device_index
        self.x_axis_number = x_axis_number
        self.y_axis_number = y_axis_number

        self.min_x_mm = min_x_mm
        self.max_x_mm = max_x_mm
        self.min_y_mm = min_y_mm
        self.max_y_mm = max_y_mm

        self.connection = None
        self.device = None
        self.x_axis = None
        self.y_axis = None
        self.xy_group = None

    def __enter__(self) -> "ZaberXYStage":
        self.connect()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def connect(self) -> None:
        self.connection = Connection.open_serial_port(self.port)
        self.connection.enable_alerts()

        devices = self.connection.detect_devices()
        if len(devices) == 0:
            raise RuntimeError(f"No Zaber devices found on {self.port}")

        if self.device_index >= len(devices):
            raise IndexError(
                f"device_index={self.device_index} but only {len(devices)} device(s) found"
            )

        self.device = devices[self.device_index]
        self.x_axis = self.device.get_axis(self.x_axis_number)
        self.y_axis = self.device.get_axis(self.y_axis_number)
        self.xy_group = AxisGroup([self.x_axis, self.y_axis])

    def close(self) -> None:
        if self.connection is not None:
            self.connection.close()
        self.connection = None

    def _require_connected(self) -> None:
        if self.connection is None or self.x_axis is None or self.y_axis is None:
            raise RuntimeError("Stage is not connected. Use connect() or a with-block.")

    def _check_xy_limits(self, x_mm: float, y_mm: float) -> None:
        if self.min_x_mm is not None and x_mm < self.min_x_mm:
            raise ValueError(f"x={x_mm} mm is below min_x_mm={self.min_x_mm}")
        if self.max_x_mm is not None and x_mm > self.max_x_mm:
            raise ValueError(f"x={x_mm} mm is above max_x_mm={self.max_x_mm}")
        if self.min_y_mm is not None and y_mm < self.min_y_mm:
            raise ValueError(f"y={y_mm} mm is below min_y_mm={self.min_y_mm}")
        if self.max_y_mm is not None and y_mm > self.max_y_mm:
            raise ValueError(f"y={y_mm} mm is above max_y_mm={self.max_y_mm}")

    def print_identity(self) -> None:
        self._require_connected()
        print(f"Device: {self.device}")
        print(f"X axis: {self.x_axis}")
        print(f"Y axis: {self.y_axis}")

    def home(self) -> None:
        self._require_connected()
        self.xy_group.home()

    def is_homed(self) -> bool:
        self._require_connected()
        return self.xy_group.is_homed()

    def position(self) -> XYPosition:
        self._require_connected()
        x, y = self.xy_group.get_position(MM)
        return XYPosition(x_mm=x, y_mm=y)




    # def move_absolute(
    #     self,
    #     x_mm: float,
    #     y_mm: float,
    #     velocity_mm_s: Optional[float] = None,
    # ) -> XYPosition:
    #     self._require_connected()
    #     self._check_xy_limits(x_mm, y_mm)

    #     if velocity_mm_s is None:
    #         self.x_axis.move_absolute(x_mm, MM, wait_until_idle=False)
    #         self.y_axis.move_absolute(y_mm, MM, wait_until_idle=False)
    #         self.xy_group.wait_until_idle()
    #     else:
    #         self.x_axis.move_absolute(
    #             x_mm,
    #             MM,
    #             wait_until_idle=False,
    #             velocity=velocity_mm_s,
    #             velocity_unit=MM_PER_S,
    #         )
    #         self.y_axis.move_absolute(
    #             y_mm,
    #             MM,
    #             wait_until_idle=False,
    #             velocity=velocity_mm_s,
    #             velocity_unit=MM_PER_S,
    #         )
    #         self.xy_group.wait_until_idle()
    #     return self.position()
    




    def move_absolute(
        self,
        x_mm: float,
        y_mm: float,
        velocity_mm_s: Optional[float] = None,
    ) -> XYPosition:

        self._require_connected()
        self._check_xy_limits(x_mm, y_mm)

        if velocity_mm_s is None:
            velocity_mm_s = 5  # Default speed (mm/s)

        self.x_axis.move_absolute(
            x_mm,
            MM,
            wait_until_idle=False,
            velocity=velocity_mm_s,
            velocity_unit=MM_PER_S,
        )

        self.y_axis.move_absolute(
            y_mm,
            MM,
            wait_until_idle=False,
            velocity=velocity_mm_s,
            velocity_unit=MM_PER_S,
        )

        self.xy_group.wait_until_idle()
        return self.position()
    


    def move_relative(
        self,
        dx_mm: float,
        dy_mm: float,
        velocity_mm_s: Optional[float] = None,
    ) -> XYPosition:

        self._require_connected()

        current = self.position()
        target_x = current.x_mm + dx_mm
        target_y = current.y_mm + dy_mm

        self._check_xy_limits(target_x, target_y)

        if velocity_mm_s is None:
            velocity_mm_s = 5  # Default speed (mm/s)

        self.x_axis.move_relative(
            dx_mm,
            MM,
            wait_until_idle=False,
            velocity=velocity_mm_s,
            velocity_unit=MM_PER_S,
        )

        self.y_axis.move_relative(
            dy_mm,
            MM,
            wait_until_idle=False,
            velocity=velocity_mm_s,
            velocity_unit=MM_PER_S,
        )

        self.xy_group.wait_until_idle()

        return self.position()








    # def move_relative(
    #     self,
    #     dx_mm: float,
    #     dy_mm: float,
    #     velocity_mm_s: Optional[float] = None,
    # ) -> XYPosition:
    #     current = self.position()
    #     target_x = current.x_mm + dx_mm
    #     target_y = current.y_mm + dy_mm
    #     self._check_xy_limits(target_x, target_y)

    #     if velocity_mm_s is None:
    #         self.x_axis.move_relative(dx_mm, MM, wait_until_idle=False)
    #         self.y_axis.move_relative(dy_mm, MM, wait_until_idle=False)
    #         self.xy_group.wait_until_idle()
    #     else:
    #         self.x_axis.move_relative(
    #             dx_mm,
    #             MM,
    #             wait_until_idle=False,
    #             velocity=velocity_mm_s,
    #             velocity_unit=MM_PER_S,
    #         )
    #         self.y_axis.move_relative(
    #             dy_mm,
    #             MM,
    #             wait_until_idle=False,
    #             velocity=velocity_mm_s,
    #             velocity_unit=MM_PER_S,
    #         )
    #         self.xy_group.wait_until_idle()

    #     return self.position()

    def stop(self) -> None:
        self._require_connected()
        self.xy_group.stop()

    def set_maxspeed(self, speed_mm_s: float) -> None:
        self._require_connected()
        self.x_axis.settings.set("maxspeed", speed_mm_s, MM_PER_S)
        self.y_axis.settings.set("maxspeed", speed_mm_s, MM_PER_S)

    def get_maxspeed(self) -> Tuple[float, float]:
        self._require_connected()
        return (
            self.x_axis.settings.get("maxspeed", MM_PER_S),
            self.y_axis.settings.get("maxspeed", MM_PER_S),
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Control a Zaber XY stage.")
    parser.add_argument("--port", required=True, help="Serial port, e.g. COM3 or /dev/ttyUSB0")
    parser.add_argument("--device-index", type=int, default=0)
    parser.add_argument("--max-x", type=float, default=None, help="Optional software X limit in mm")
    parser.add_argument("--max-y", type=float, default=None, help="Optional software Y limit in mm")

    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status")
    sub.add_parser("home")
    sub.add_parser("stop")

    p_abs = sub.add_parser("move-abs")
    p_abs.add_argument("--x", type=float, required=True)
    p_abs.add_argument("--y", type=float, required=True)
    p_abs.add_argument("--velocity", type=float, default=None)

    p_rel = sub.add_parser("move-rel")
    p_rel.add_argument("--dx", type=float, required=True)
    p_rel.add_argument("--dy", type=float, required=True)
    p_rel.add_argument("--velocity", type=float, default=None)

    p_speed = sub.add_parser("set-maxspeed")
    p_speed.add_argument("--speed", type=float, required=True)

    return parser


def main() -> None:
    args = build_parser().parse_args()

    with ZaberXYStage(
        port=args.port,
        device_index=args.device_index,
        max_x_mm=args.max_x,
        max_y_mm=args.max_y,
    ) as stage:
        if args.command == "status":
            stage.print_identity()
            print("Homed:", stage.is_homed())
            print("Position:", stage.position())
            # print("Maxspeed X/Y [mm/s]:", stage.get_maxspeed())

        elif args.command == "home":
            stage.home()
            print("Homed. Position:", stage.position())

        elif args.command == "move-abs":
            pos = stage.move_absolute(args.x, args.y, args.velocity)
            print("Moved to:", pos)

        elif args.command == "move-rel":
            pos = stage.move_relative(args.dx, args.dy, args.velocity)
            print("Moved to:", pos)

        elif args.command == "set-maxspeed":
            stage.set_maxspeed(args.speed)
            print("Maxspeed X/Y [mm/s]:", stage.get_maxspeed())

        elif args.command == "stop":
            stage.stop()
            print("Stop command sent.")


if __name__ == "__main__":
    main()