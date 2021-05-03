#!/usr/bin/python3

import re
import subprocess
from pathlib import Path
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt


SOLVER = '/home/ryan/pytartaros/applications/topology_optimization/topopt.py'


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


def run_solver(output_path):
    # setup tee to read from process
    log_file = str(Path(output_path, f'results.txt'))
    tee = subprocess.Popen(['tee', log_file], stdin=subprocess.PIPE)

    cmd = [
        SOLVER,
    ]
    cmd = [str(x) for x in cmd]
    print('INFO -- Command:')
    print(' '.join(cmd))
    result = subprocess.run(cmd, stdout=tee.stdin)
    return result.returncode

# run_solver('test')

# regexes
thickness_regex = r"^(\s+mesher_params\['thickness'\]\s*=\s*)(?P<value>\S+)" 
ele_rad_regex = r"^(\s+mesher_params\['ele_rad'\]\s*=\s*)(?P<value>\S+)"
ele_cir_regex = r"^(\s+mesher_params\['ele_cir'\]\s*=\s*)(?P<value>\S+)"
ele_axi_regex = r"^(\s+mesher_params\['ele_axi'\]\s*=\s*)(?P<value>\S+)"
load_regex = r"^(\s+dat_params\['load'\]\s*=\s*)(?P<value>\S+)"
procs_regex = r"^(\s+num_procs\s*=\s*)(?P<value>\S+)"

# parameters
thicknesses = (0.25, 2.5, 5.0, 7.5, 10.0, 12.5)
loads = (-192.0, -2002.5, -4675.0, -8500.0, -13950.0, -21500.0)
ele_rads = ( 2,  4,  8,  16,  32)
ele_cirs = (20, 40, 80, 160, 320)
ele_axis = (20, 40, 80, 160, 320)


def replace_value_in_file(filename, value, replace_regex):
    with open('topopt.py', 'r') as f:
        lines = f.readlines()
    with open('topopt.py', 'w') as f:
        for line in lines: 
            m = re.match(replace_regex, line)
            if m:
                line = m.group(1) + str(float(value)) + '\n'
            f.write(line)

# for thickness, load in zip(thicknesses, loads):
for ele_rad, ele_cir, ele_axi in zip(ele_rads, ele_cirs, ele_axis):
    ele = ele_rad*ele_cir*ele_axi
    print(ele)

num_procs = 20
for ele_rad, ele_cir, ele_axi in zip(ele_rads, ele_cirs, ele_axis):
    for thickness, load in zip(thicknesses, loads):
        # make directory
        ele = ele_rad*ele_cir*ele_axi
        dir_path = Path('results', f'thickness_{thickness}', f'ele_{ele}')
        dir_path.mkdir(parents=True, exist_ok=True)

        # edit lines in topopt.py
        replace_value_in_file('topopt.py', load, load_regex)
        replace_value_in_file('topopt.py', ele_rad, ele_rad_regex)
        replace_value_in_file('topopt.py', ele_cir, ele_cir_regex)
        replace_value_in_file('topopt.py', ele_axi, ele_axi_regex)

        # run the sim
        run_solver(dir_path)

