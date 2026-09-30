"""命令行入口：跑每日重置样例。"""

import argparse

from .core import DAY_MS, Resets


def build_parser():
    parser = argparse.ArgumentParser(prog="daily-reset", description="每日重置")
    parser.add_argument("--sample", default="rollover", help="rollover / catchup / idempotent / scale")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.sample == "rollover":
        resets = Resets(480)
        resets.due("p", 0)
        # UTC 还是第 0 天，服务器时区（+8）已经翻到第 1 天。
        result = resets.due("p", 57600000)
        print("day=%d granted=%d" % (resets.state["p"]["day"], result["granted"]))
    elif args.sample == "catchup":
        resets = Resets(480)
        resets.due("p", 0)
        result = resets.due("p", 1000 * DAY_MS)
        print("granted=%d missed=%d steps=%d" % (result["granted"], result["missed"], resets.steps_count()))
    elif args.sample == "idempotent":
        resets = Resets(480)
        resets.due("p", 1000)
        resets.due("p", 2000)
        print("granted_total=%d" % resets.granted_total("p"))
    elif args.sample == "scale":
        resets = Resets(480)
        for index in range(2000):
            player = "p-%d" % index
            resets.due(player, 0)
            resets.due(player, 1000 * DAY_MS)
        print("steps=%d" % resets.steps_count())
    else:
        raise SystemExit("需要 --sample rollover|catchup|idempotent|scale")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
