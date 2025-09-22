import sys
import argparse

def main():
    # Check if --gui is in the arguments
    if '--gui' in sys.argv:
        from .gui.main import main as gui_main
        return gui_main()
    else:
        from .cli.main import main as cli_main
        return cli_main()

if __name__ == '__main__':
    sys.exit(main())