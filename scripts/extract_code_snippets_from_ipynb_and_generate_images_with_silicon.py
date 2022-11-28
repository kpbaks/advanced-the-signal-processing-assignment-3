#!/usr/bin/env python

import os
import sys
import argparse
import tempfile
import subprocess

import nbformat


DEFAULT_SILICON_ARGS: str = [
    "--theme=Github",
    "--no-window-controls",
    "--font='JetBrainsMono Nerd Font Mono'"
].join(" ")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('notebook', type=str, help='path to the notebook')
    parser.add_argument('output-dir', type=str, help='path to the output directory')
    parser.add_argument('silicon-args', type=str, nargs='?', help='arguments to pass to silicon')
    args = parser.parse_args()

    # check if silicon is installed
    try:
        subprocess.check_output(['silicon', '--help'])
    except FileNotFoundError:
        print('silicon not found. Please install it first.')
        sys.exit(1)


    with open(args.notebook) as f:
        nb = nbformat.read(f, as_version=4)

    if args.silicon_args is None:
        args.silicon_args = DEFAULT_SILICON_ARGS

    code_snippets = []

    for cell in nb.cells:
        if cell.cell_type == 'code':
            # iterate over the lines in the cell, and select the interval
            # beginning with `# silicon: start` and ending with `# silicon: end`
            start = None
            end = None
            for i, line in enumerate(cell.source.splitlines()):
                if line == '# silicon: start':
                    start = i + 1 # skip the line with `# silicon: start`
                elif line == '# silicon: end':
                    end = i - 1 # skip the line with `# silicon: end`
                    break
                
                # there might be more than one `# silicon: start` or `# silicon: end`
                # per cell, so we need to reset the start and end indices
                if start is not None and end is not None:
                    code_snippets.append({
                        'start': start,
                        'end': end,
                        'lines' : cell.source.splitlines()[start:end]
                    })
                    start = None
                    end = None


    for i, code_snippet in enumerate(code_snippets):
        # create temporary file with the code snippet
        lines = code_snippet['lines']
        start = code_snippet['start']
        end = code_snippet['end']
        with tempfile.NamedTemporaryFile(mode='w', delete=True) as f:    
            f.write('\n'.join(lines))
            f.flush()

            # run silicon on the temporary file
            # generate the image in the output directory
            output_file = os.path.join(args.output_dir, f'{args.notebook}_start_{start}_end_{end}.png')
            cmd = 'silicon {} {} --output {}'.format(args.silicon_args, f.name, output_file)

            try:
                subprocess.check_output(cmd.split())
            except subprocess.CalledProcessError as e:
                print('error while running silicon: {}'.format(e))
                sys.exit(1)


print('done :D')
sys.exit(0)

            