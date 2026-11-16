import argparse
import json
import sqlite3
import sys
from .catalog import import_json
from .unified import search_resources as search


def main():
    parser = argparse.ArgumentParser(description='Catálogo bibliográfico local')
    commands = parser.add_subparsers(dest='command', required=True)
    importer = commands.add_parser('import-json')
    importer.add_argument('input')
    importer.add_argument('--db', required=True)
    importer.add_argument('--source', default='zotero', help='Identificador de biblioteca de origen')
    finder = commands.add_parser('search')
    finder.add_argument('query')
    finder.add_argument('--db', required=True)
    finder.add_argument('--limit', type=int, default=20)
    interface = commands.add_parser('gui', help='Abrir la interfaz local')
    interface.add_argument('--db', help='Catálogo PKM existente (opcional)')
    args = parser.parse_args()
    if args.command == 'gui':
        from .gui import launch
        launch(args.db)
        return 0
    try:
        result = (import_json(args.db, args.input, args.source) if args.command == 'import-json'
                  else search(args.db, args.query, args.limit))
    except (OSError, ValueError, sqlite3.Error) as error:
        print(f'Error: {error}', file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
