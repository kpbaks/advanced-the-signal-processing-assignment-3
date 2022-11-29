#!/usr/bin/env python

import os
import sys
import argparse
import tempfile
import subprocess
import logging
import re
from typing import Optional


import nbformat # pip install nbformat




DEFAULT_SILICON_ARGS: str = " ".join([
    "--theme=Github",
    "--no-line-number",

    "--no-window-controls",
    "--language=python",
    # "--font='JetBrainsMono Nerd Font Mono'"
])

DEFAULT_OUTPUT_FORMAT: str = "%f_%i_%s_%e.png"

if __name__ == '__main__':
    # check if silicon is installed
    try:
        subprocess.check_output(['silicon', '--help'])
    except FileNotFoundError:
        print('silicon not found. Please install it first.')
        sys.exit(1)

    # create logger
    logger = logging.getLogger('extract_code_snippets_from_ipynb_and_generate_images_with_silicon')



    parser = argparse.ArgumentParser()
    parser.add_argument('notebook', type=str, help='path to the notebook')
    parser.add_argument('output_dir', type=str, help='path to the output directory')
    parser.add_argument('--silicon-args', type=str, nargs='?', help='arguments to pass to silicon')
    parser.add_argument('output_format', type=str, nargs='?', help='output format: %i = snippet id, %c = cell number, %f = filename without extension, %s = line start, %e = line end')
    parser.add_argument('-V', '--verbose', action='store_true', help='increase output verbosity')
    args = parser.parse_args()

    # check if output directory exists
    if not os.path.isdir(args.output_dir):
        print('output directory does not exist')
        sys.exit(1)

    # set logging level
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)
    
    # log the loglevel
    logger.debug('loglevel: %s', logging.getLevelName(logger.getEffectiveLevel()))


    with open(args.notebook) as f:
        nb = nbformat.read(f, as_version=4)

    if args.silicon_args is None:
        args.silicon_args = DEFAULT_SILICON_ARGS

    if args.output_format is None:
        args.output_format = DEFAULT_OUTPUT_FORMAT

    code_snippets = []

    start_delimiter_regex = re.compile(r'^\s*#\s*silicon: start\s*\((.+)\)\s*$')
    end_delimiter_regex = re.compile(r'^\s*#\s*silicon: end\s*$')

    for cell_id, cell in enumerate(nb.cells):
        if cell.cell_type == 'code':
            # iterate over the lines in the cell, and select the interval
            # beginning with `# silicon: start` and ending with `# silicon: end`
            start: Optional[int] = None
            end: Optional[int] = None
            output_filename: Optional[str] = None
            
            for i, line in enumerate(cell.source.splitlines()):
                if (capture := start_delimiter_regex.match(line)) is not None:
                    start = i + 1 # skip the line with `# silicon: start`
                    output_filename = capture.group(1)

                elif end_delimiter_regex.match(line) is not None:
                    end = i - 1 # skip the line with `# silicon: end`

                # there might be more than one `# silicon: start` or `# silicon: end`
                # per cell, so we need to reset the start and end indices
                if start is not None and end is not None:
                    code_snippets.append({
                        'start': start,
                        'end': end,
                        'lines' : cell.source.splitlines()[start:end + 1],
                        'cell_id': cell_id,
                        'snippet_id': len(code_snippets)
                        'output_filename': output_filename
                    })
                    start = None
                    end = None
                    output_filename = None


    for i, code_snippet in enumerate(code_snippets):
        # create temporary file with the code snippet
        lines = code_snippet['lines']
        start = code_snippet['start']
        end = code_snippet['end']
        with tempfile.NamedTemporaryFile(mode='w', delete=True) as tmp_file:    
            tmp_file.write('\n'.join(lines))
            tmp_file.flush()

            # run silicon on the temporary file
            # generate the image in the output directory

            output_filename = args.output_format
            for placeholder, replacement in [
                ('%f', os.path.basename(args.notebook)), # filename without extension
                ('%c', str(code_snippet['cell_id'])), # cell number
                ('%s', str(start)),
                ('%e', str(end)),
                ('%i', str(code_snippet['snippet_id'])) # snippet id
            ]:
                output_filename = output_filename.replace(placeholder, replacement)

            print (output_filename)

            output_file = os.path.join(args.output_dir, output_filename)
            
            print(f'generating image for snippet {i} in cell {code_snippet["cell_id"]} from line {start} to line {end} in file {args.notebook} to {output_file}')
            cmd = 'silicon {} {} --output {}'.format(args.silicon_args, tmp_file.name, output_file)
            logger.debug(cmd.split())
            print(cmd)

            try:
                subprocess.check_output(cmd.split())
            except subprocess.CalledProcessError as e:
                print('error while running silicon: {}'.format(e))
                sys.exit(1)


print('done :D')
sys.exit(0)

            