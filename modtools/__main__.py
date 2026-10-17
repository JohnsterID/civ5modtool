import sys


def main():
    argv = sys.argv[1:]
    if argv[:1] == ["--gui"]:  # also accepted: modtools --gui
        argv = ["gui"] + argv[1:]
    from .cli.main import main as cli_main
    return cli_main(argv)


if __name__ == '__main__':
    sys.exit(main())
