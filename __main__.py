import sys
import argparse

def main():
    parser = argparse.ArgumentParser(description='Civilization V Mod Tools')
    parser.add_argument('--gui', action='store_true', help='Launch GUI interface')
    
    # Only parse the --gui argument first
    args, remaining = parser.parse_known_args()

    if args.gui:
        from .gui.main import main as gui_main
        return gui_main()
    else:
        from .cli.main import main as cli_main
        return cli_main(remaining)

if __name__ == '__main__':
    sys.exit(main())