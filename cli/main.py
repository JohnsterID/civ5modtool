import argparse
import sys
from pathlib import Path
import logging
from ..core.models import ModProject

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Civilization V Mod Tools')
    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Convert modinfo to civ5proj
    modinfo_to_proj = subparsers.add_parser('modinfo2proj', help='Convert .modinfo to .civ5proj')
    modinfo_to_proj.add_argument('modinfo', type=str, help='Path to .modinfo file')
    modinfo_to_proj.add_argument('--output', '-o', type=str, help='Output .civ5proj path')
    modinfo_to_proj.add_argument('--no-solution', action='store_true', help='Do not create/update .civ5sln file')

    # Convert civ5proj to modinfo
    proj_to_modinfo = subparsers.add_parser('proj2modinfo', help='Convert .civ5proj to .modinfo')
    proj_to_modinfo.add_argument('civ5proj', type=str, help='Path to .civ5proj file')
    proj_to_modinfo.add_argument('--output', '-o', type=str, help='Output .modinfo path')

    # Validate files
    validate = subparsers.add_parser('validate', help='Validate mod files')
    validate.add_argument('file', type=str, help='Path to .modinfo or .civ5proj file')

    # Update MD5 hashes
    update_md5 = subparsers.add_parser('update-md5', help='Update MD5 hashes in .modinfo')
    update_md5.add_argument('modinfo', type=str, help='Path to .modinfo file')
    update_md5.add_argument('--output', '-o', type=str, help='Output .modinfo path')

    return parser

def main(argv=None):
    parser = create_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return

    try:
        if args.command == 'modinfo2proj':
            input_path = Path(args.modinfo)
            if not input_path.exists():
                logger.error(f"Input file not found: {input_path}")
                return 1

            project = ModProject.from_modinfo(input_path)
            
            output_path = Path(args.output) if args.output else input_path.with_suffix('.civ5proj')
            project.write_civ5proj(output_path, create_solution=not args.no_solution)
            logger.info(f"Successfully converted {input_path} to {output_path}")
            if not args.no_solution:
                logger.info(f"Created/updated solution file: {output_path.with_suffix('.civ5sln')}")

        elif args.command == 'proj2modinfo':
            input_path = Path(args.civ5proj)
            if not input_path.exists():
                logger.error(f"Input file not found: {input_path}")
                return 1

            project = ModProject.from_civ5proj(input_path)
            
            output_path = Path(args.output) if args.output else input_path.with_suffix('.modinfo')
            project.write_modinfo(output_path, input_path.parent)
            logger.info(f"Successfully converted {input_path} to {output_path}")

        elif args.command == 'validate':
            input_path = Path(args.file)
            if not input_path.exists():
                logger.error(f"Input file not found: {input_path}")
                return 1

            # Try to load the file to validate it
            if input_path.suffix.lower() == '.modinfo':
                project = ModProject.from_modinfo(input_path)
                logger.info(f"Successfully validated {input_path} as .modinfo")
            elif input_path.suffix.lower() == '.civ5proj':
                project = ModProject.from_civ5proj(input_path)
                logger.info(f"Successfully validated {input_path} as .civ5proj")
            else:
                logger.error(f"Unsupported file type: {input_path.suffix}")
                return 1

        elif args.command == 'update-md5':
            input_path = Path(args.modinfo)
            if not input_path.exists():
                logger.error(f"Input file not found: {input_path}")
                return 1

            project = ModProject.from_modinfo(input_path)
            
            # Update MD5 hashes
            output_path = Path(args.output) if args.output else input_path
            project.write_modinfo(output_path, input_path.parent)
            logger.info(f"Successfully updated MD5 hashes in {output_path}")

        return 0

    except Exception as e:
        logger.error(f"Error: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(main())