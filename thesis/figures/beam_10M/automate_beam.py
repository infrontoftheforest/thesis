#!/usr/bin/env python3

import itertools
from pathlib import Path
import shutil
import re
import subprocess
import argparse
import os
import sys
from socket import gethostname

SCENARIO_PREFIX = 'beam'
PRE_EXODUS = '/home/ryan/wdir/tartaros_build/pre_exodus'
TARTAROS = '/home/ryan/wdir/tartaros_build/tartaros-release'
POST_ENSIGHT = '/home/ryan/wdir/tartaros_build/post_drt_ensight'
CUBIT = '/mhpc/programs64/cubit-13.2/cubit'


def replace_value_in_file(filename, value, replace_regex, section_regex=None):
    '''replace_regex is a regex with 3 groups. The first and last remain
    unchanged, while the second contains the value to be replaced.

    If section_regex is provided, lines are skipped until after a line
    matches that regex
    '''
    edited_line = None
    editing_lines = True
    if section_regex is not None:
        section_found = False
    else:
        section_found = True

    with open(filename, 'r') as f:
        lines = f.readlines()
    with open(filename, 'w') as f:
        for line in lines:
            if editing_lines:
                if not section_found:
                    # skip editing lines until section_regex is found
                    m = re.match(section_regex, line)
                    if m:
                        section_found = True
                else:
                    # change the match for m.group(2) to value
                    m = re.match(replace_regex, line)
                    if m:
                        line = m.group(1) + str(float(value)) + m.group(3) + '\n'
                        edited_line = line
                        editing_lines = False

            f.write(line)
    return edited_line


def edit_neumann_bc(bc_file, force_value):
    section_regex = r'^sectionname="DESIGN SURF NEUMANN CONDITIONS"'
    description_regex = r'(^description.*VAL\s+.*?\s+)(.*?)(\s+.*)'
    edited_line = replace_value_in_file(bc_file, force_value, description_regex, section_regex)
    return edited_line


def edit_poissons_ratio(head_file, poissons_ratio):
    material_regex = r'(^MAT.*?NUE\s+)(\S+)(.*$)'
    edited_line = replace_value_in_file(head_file, poissons_ratio, material_regex)
    return edited_line


def run_cubit(jou_file, overwrite=False):
    # cubit -nographics -nojournal -batch -workingdir str(dir_path) jou_file
    if not overwrite and Path(jou_file).with_suffix('.e').exists():
        print('INFO --     Skipping')
        return 0
    dir_path = Path(jou_file).parent
    cmd = [
        CUBIT,
        '-nographics',
        '-nojournal',
        '-batch',
        '-workingdir', str(dir_path),
        jou_file,
    ]
    print('INFO -- Command:')
    print(' '.join(cmd))
    result = subprocess.run(cmd)
    return result


def run_pre_exodus(bc_file, head_file, exodus_file, dat_file, overwrite=False):
    if not overwrite and Path(dat_file).exists():
        print('INFO --     Skipping')
        return 0
    cmd = [
        PRE_EXODUS,
        f'--exo={exodus_file}',
        f'--bc={bc_file}',
        f'--head={head_file}',
        f'--dat={dat_file}'
    ]
    print('INFO -- Command:')
    print(' '.join(cmd))
    result = subprocess.run(cmd)
    return result.returncode


def run_tartaros(dat_file, output_files, num_procs=1, overwrite=False):
    # change cwd because tartaros outputs in cwd
    cwd = str(Path(dat_file).parent)
    log_file = str(Path(dat_file).with_suffix('.txt'))
    if not overwrite and Path(log_file).exists():
        print('INFO --     Skipping')
        return 0
    # only the filename because the cwd gets changed
    dat_file = str(Path(dat_file).name)

    # setup tee to read from tartaros
    tee = subprocess.Popen(['tee', log_file], stdin=subprocess.PIPE)
    # TODO: make another tee object for the std error?

    # run tartaros and pipe to tee
    print('INFO -- cwd:')
    print(cwd)
    cmd = ['mpirun', '-np', str(num_procs), TARTAROS, dat_file, output_files]
    print('INFO -- Command:')
    print(' '.join(cmd))
    tartaros = subprocess.Popen(cmd, cwd=cwd, stdout=tee.stdin)

    try:
        tartaros.wait()
        tee.stdin.close()
    except KeyboardInterrupt:
        # can't use .terminate() because mpi doesn't want to be killed like that
        SIGINT = 2
        os.kill(tartaros.pid, SIGINT)
        tee.terminate()
        raise

    return tartaros.returncode


def run_post_ensight(dir_path, output_files):
    cwd = str(str(dir_path))
    print('INFO -- cwd:')
    print(cwd)
    cmd = [POST_ENSIGHT, f'--file={output_files}']
    print('INFO -- Command:')
    print(' '.join(cmd))
    result = subprocess.run(cmd, cwd=cwd)
    return result.returncode


def get_num_nodes(output_file):
    numele = None
    numnodes_str = r'^numnode (?P<numnode>\d+) nblock \d+ bsize \d+'
    with open(output_file, 'r') as f:
        for line in f:
            m = re.match(numnodes_str, line)
            if m:
                numele = int(m.group('numnode'))
                break
    return numele


def get_num_ele(output_file):
    numele_str = r'^numele (?P<numele>\d+) nblock \d+ bsize \d+'
    with open(output_file, 'r') as f:
        for line in f:
            m = re.match(numele_str, line)
            if m:
                numele = int(m.group('numele'))
                break
    return numele


def get_mean_gmres_iters(output_file):
    iterations_str = r'^\s+total iterations: (?P<iters>\d+)'
    total_iters = 0
    solves = 0.0
    with open(output_file, 'r') as f:
        for line in f:
            m = re.match(iterations_str, line)
            if m:
                iters = int(m.group('iters'))
                total_iters += iters
                solves += 1.0
    return float(total_iters)/solves


def get_total_gmres_iters(output_file):
    iterations_str = r'^\s+total iterations: (?P<iters>\d+)'
    total_iters = 0
    with open(output_file, 'r') as f:
        for line in f:
            m = re.match(iterations_str, line)
            if m:
                iters = int(m.group('iters'))
                total_iters += iters
    return total_iters


def get_lin_solve_time(output_file, num_procs):
    if num_procs == 1:
        setup_string = r'LINALG::Solver:\s+1\)\s+Setup\s+(?P<time>\S+)\s+\((?P<calls>\d+)\)'
        create_preconditioner_string = r'LINALG::Solver:\s+1.1\)\s+CreatePreconditioner\s+(?P<time>\S+)\s+\((?P<calls>\d+)\)'
        solve_string = r'LINALG::Solver:\s+2\)\s+Solve\s+(?P<time>\S+)\s+\((?P<calls>\d+)\)'
    else:
        setup_string = r'LINALG::Solver:\s+1\)\s+Setup\s+\S+\s+\(\d+\)\s+(?P<time>\S+)\s+\((?P<calls>\d+)\)'
        create_preconditioner_string = r'LINALG::Solver:\s+1.1\)\s+CreatePreconditioner\s+\S+\s+\(\d+\)\s+(?P<time>\S+)\s+\((?P<calls>\d+)\)'
        solve_string = r'LINALG::Solver:\s+2\)\s+Solve\s+\S+\s+\(\d+\)\s+(?P<time>\S+)\s+\((?P<calls>\d+)\)'

    lin_solve_time = 0.0
    with open(output_file, 'r') as f:
        for line in f:
            # m = re.match(setup_string, line)
            # if m:
                # time = float(m.group('time'))
                # calls = int(m.group('calls'))
                # lin_solve_time += time/calls
                # print(time)
                # print(calls)
                # continue
            # m = re.match(create_preconditioner_string, line)
            # if m:
                # time = float(m.group('time'))
                # calls = int(m.group('calls'))
                # lin_solve_time += time/calls
                # print(m.group('time'))
                # print(m.group('calls'))
                # continue
            m = re.match(solve_string, line)
            if m:
                time = float(m.group('time'))
                calls = int(m.group('calls'))
                lin_solve_time += time/calls
                print(m.group('time'))
                print(m.group('calls'))
                continue

    return lin_solve_time


# print(get_lin_solve_time('muelu/ele_20000/beam_ratio_10_ele_20000.txt', 2))
# print(get_total_gmres_iters('muelu/ele_20000/beam_ratio_10_ele_20000.txt'))

if __name__ == "__main__":
# if False:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-s', '--setup',
        help='setup files by creating dirs and running pre_exodus',
        action='store_true',
        default=False,
    )
    parser.add_argument(
        '-r', '--run',
        help='run tartaros with .dat files',
        action='store_true',
        default=False,
    )
    parser.add_argument(
        '-p', '--process',
        help='post-process output files with post_drt_ensight',
        action='store_true',
        default=False,
    )
    parser.add_argument(
        '-o', '--overwrite',
        help='overwrite files if step already completed',
        action='store_true',
        default=False,
    )
    parser.add_argument(
        '-t', '--plot',
        help='plot performance graphs',
        action='store_true',
        default=False,
    )
    args = parser.parse_args()

    preconditioners = ("muelu",)
    # preconditioners = ("superlu",)
    # preconditioners = ("muelu", "superlu")
    # ratios = (10**x for x in range(1, 4)) # length to height, decreasing thickness
    # ratios = tuple(10**x for x in range(1, 3)) # length to height, decreasing thickness
    # ratios = (10**x for x in range(1, 2)) # length to height, decreasing thickness
    ratios = (10,)
    # ratios = (100,)

    # TODO: run 10**6 only on rechenknecht
    elements = (10**x for x in range(4, 7))
    elements = range(10000, 410000, 10000)
    elements = range(330000, 3300001, 330000)
    # elements = (10**x for x in range(4, 6))
    # elements = (10000,)

    # elements_per_core = 10**4
    elements_per_core = 330000
    max_cores = 40
    elements_to_proc = ((x, int(min(max_cores, x/elements_per_core))) for x in elements)

    # poissons_ratios = (0.3, 0.4, 0.49)

    # combinations = list(itertools.product(preconditioners, ratios, elements_to_proc, poissons_ratios))
    combinations = list(itertools.product(preconditioners, ratios, elements_to_proc))
    output_file_format = SCENARIO_PREFIX + '_ratio_{0}_ele_{1}'

    # Setup
    if args.setup:
        for preconditioner, ratio, (element, num_proc) in combinations:
            print(f'INFO -- Setting up preconditioner={preconditioner}')
            print(f'INFO --            ratio={ratio}')
            print(f'INFO --            element={element}')
            print(f'INFO --            num_proc={num_proc}')

            # make dirs if not existing
            # dir_path = Path(f'{preconditioner}', f'ratio_{ratio}', f'ele_{element}', f'nue_{poissons_ratio}')
            dir_path = Path(f'{preconditioner}', f'ratio_{ratio}', f'ele_{element}')
            # dir_path = Path(f'{preconditioner}', f'ele_{element}')
            # dir_path = Path(f'ele_{element}')
            print(f'INFO -- making directory: {str(dir_path)}')
            dir_path.mkdir(parents=True, exist_ok=True)

            # move the .e files to the right dir
            exodus_path = Path('exodus', f'ratio_{ratio}', f'ele_{element}')
            exodus_file = output_file_format.format(ratio, element) + '.e'
            # need full path to dir_path and exodus_file since not copying anymore
            exodus_file = str(Path(exodus_path, exodus_file))
            jou_file = output_file_format.format(ratio, element) + '.jou'
            jou_file = str(Path(exodus_path, jou_file).resolve())
            # run cubit -nographics -nojournal -workingdir str(dir_path) -input jou_file
            print(f'INFO -- Running cubit with {jou_file}')
            run_cubit(jou_file, overwrite=args.overwrite)

            # print(f'INFO -- moving {exodus_file} to {str(dir_path)}')
            # exodus_file = shutil.copy2(exodus_file, str(dir_path))

            # update beam.bc (use correct force for neumann)
            base_bc_file = SCENARIO_PREFIX + '.bc'
            bc_file = shutil.copy2(base_bc_file, str(dir_path))
            force = -10**3/(ratio**3)
            print(f'INFO -- Changing the y-force in {bc_file} to {force}')
            edited_line = edit_neumann_bc(bc_file, force)
            print(edited_line.strip())

            base_head_file = SCENARIO_PREFIX + '_' + preconditioner + '.head'
            # base_head_file = SCENARIO_PREFIX + '.head'
            head_file = shutil.copy2(base_head_file, str(dir_path))

            # # update beam.head (using correct material ratio)
            # print(f'INFO -- Changing Poisson\'s ratio in {head_file} to {poissons_ratio}')
            # edited_line = edit_poissons_ratio(head_file, poissons_ratio)
            # print(edited_line.strip())

            # run pre_exodus to generate .dat file
            # dat_file = Path(exodus_file).with_suffix('.dat')
            dat_file = output_file_format.format(ratio, element) + '.dat'
            dat_file = Path(dir_path, dat_file)
            print(f'INFO -- Running pre_exodus with {exodus_file}')
            retcode = run_pre_exodus(bc_file, head_file, exodus_file, str(dat_file), overwrite=args.overwrite)
            print(f'INFO -- pre_exodus return code = {retcode}')
            if retcode != 0:
                sys.exit(retcode)

    # Run
    if args.run:
        for preconditioner, ratio, (element, num_proc) in combinations:
            if num_proc > 10 and gethostname() != 'rechenknecht':
                continue # only run 40 procs on rechenknecht
            print(f'INFO -- Running preconditioner={preconditioner}')
            print(f'INFO --         ratio={ratio}')
            print(f'INFO --         element={element}')
            print(f'INFO --         num_proc={num_proc}')

            # dir_path = Path(f'ele_{element}')
            dir_path = Path(f'{preconditioner}', f'ratio_{ratio}', f'ele_{element}')
            output_files = output_file_format.format(ratio, element)
            dat_file = Path(dir_path, output_files).with_suffix('.dat')

            # run simulation with correct processors
            print(f'INFO -- Running tartaros with {str(dat_file)}')
            retcode = run_tartaros(dat_file, output_files, num_proc, overwrite=args.overwrite)
            print(f'tartaros return code = {retcode}')
            if retcode != 0:
                sys.exit(retcode)

    # Post-Process
    if args.process:
        for preconditioner, ratio, (element, num_proc) in combinations:
            print(f'INFO -- Post-Processing preconditioner={preconditioner}')
            print(f'INFO --                 ratio={ratio}')
            print(f'INFO --                 element={element}')
            print(f'INFO --                 num_proc={num_proc}')
            dir_path = Path(f'{preconditioner}', f'ratio_{ratio}', f'ele_{element}')
            # dir_path = Path(f'ele_{element}')
            output_files = output_file_format.format(ratio, element)
            # run post_drt_ensight
            print(f'INFO -- Running post_drt_ensight in {str(dir_path)}')
            print(output_files)
            retcode = run_post_ensight(dir_path, output_files)
            print(f'INFO -- post_drt_ensight return code = {retcode}')
            if retcode != 0:
                sys.exit(retcode)

    # Plot
    if args.plot:
        import numpy as np
        import matplotlib as mpl
        mpl.use('pdf')
        import matplotlib.pyplot as plt

        # read data
        # elems = {precond : { ratio: [] for ratio in ratios } for precond in preconditioners }
        elems = {precond : { ratio: [] for ratio in list(ratios) } for precond in preconditioners }
        print(list(ratios))
        print(preconditioners)
        print(elems)
        # lin_solve_time = {precond : { ratio: [] } for ratio in ratios for precond in preconditioners}
        lin_solve_time = {precond : { ratio: [] for ratio in list(ratios) } for precond in preconditioners }
        solve_time = False
        for preconditioner, ratio, (element, num_proc) in combinations:
            print(f'INFO -- Plotting preconditioner={preconditioner}')
            print(f'INFO --          ratio={ratio}')
            print(f'INFO --          element={element}')
            print(f'INFO --          num_proc={num_proc}')

            dir_path = Path(f'{preconditioner}', f'ratio_{ratio}', f'ele_{element}')
            output_file = Path(dir_path, output_file_format.format(ratio, element) + '.txt')
            if not output_file.exists():
                print('        Not found. Skipping.')
                continue
            # elems[preconditioner].append(element)
            num_nodes = get_num_nodes(output_file)
            if num_nodes is None: continue
            num_dofs = 3*num_nodes
            elems[preconditioner][ratio].append(num_dofs)
            if solve_time:
                lin_solve_time[preconditioner][ratio].append(get_lin_solve_time(str(output_file), num_proc))
            else:
                # lin_solve_time[preconditioner][ratio].append(get_total_gmres_iters(str(output_file)))
                lin_solve_time[preconditioner][ratio].append(get_mean_gmres_iters(str(output_file)))

        # render plot
        plt.style.use(['science', 'grid', 'ieee'])

        # should be 10.91? idk
        caption_font_size = 10
        plt.rc('font', family='serif', serif='Times')
        plt.rc('text', usetex=True)
        plt.rc('xtick', labelsize=caption_font_size)
        plt.rc('ytick', labelsize=caption_font_size)
        plt.rc('axes', labelsize=caption_font_size)


        width = 5.997
        height = width / 1.618
        height = 3.3

        fig, ax = plt.subplots()
        #fig.subplots_adjust(left=.15, bottom=.16, right=.99, top=.97)
        # fig.subplots_adjust(left=.07, bottom=.1, right=0.96, top=.97) #font 8
        fig.subplots_adjust(left=.08, bottom=.12, right=0.95, top=.97) #font 10
        #fig = plt.figure()
        #ax = fig.add_subplot(111)

        precond_to_str = {'muelu' : 'MueLu', 'superlu' : 'SuperLU'}

        for precond in preconditioners:
            for ratio in ratios:
                # ax.plot(elems[precond][ratio], lin_solve_time[precond][ratio], marker='o', label=precond)
                # ax.plot(elems[precond][ratio], lin_solve_time[precond][ratio], marker='o', label=f'Beam Ratio {ratio}')
                ax.plot(elems[precond][ratio], lin_solve_time[precond][ratio], marker='o', markersize=3)
        # if len(preconditioners) > 1:
        if len(ratios) > 1:
            ax.legend()

        if solve_time:
            ax.set(xlabel='Degrees of Freedom', ylabel='Mean Linear Solve Time (s)')
        else:
            ax.set(xlabel='Degrees of Freedom', ylabel='Mean GMRES Iterations')
        plt.ticklabel_format(style='sci', axis='x', scilimits=(0,0))
        if len(preconditioners) > 1:
            title_str = 'Beam FE Scaling (Tartaros)'
            ax.set_yscale('log')
        else:
            if preconditioner == 'muelu':
                title_str = 'AMG Preconditioned Krylov (Muelu + Aztec)'
            elif preconditioner == 'superlu':
                title_str = 'SuperLU'
        # ax.set_title(f'{title_str} (~1M DOF/processor)')
        ax.set_xlim(left=0)
        ax.set_ylim(bottom=0)
        # ax.set_ylim(top=15)

        if len(preconditioners) > 1:
            save_str = f'ratio_{ratio}_prec_beam_scaling.pdf'
        else:
            if solve_time:
                if len(ratios) > 1:
                    save_str = f'{preconditioner}_beam_scaling.pdf'
                else:
                    save_str = f'{preconditioner}_ratio_{ratio}_beam_scaling.pdf'
            else:
                if len(ratios) > 1:
                    save_str = f'{preconditioner}_gmres_iters.pdf'
                else:
                    save_str = f'{preconditioner}_ratio_{ratio}_gmres_iters.pdf'
        print(f'Saving to {save_str}')
        fig.set_size_inches(width, height)
        plt.savefig(save_str)
        plt.show()

