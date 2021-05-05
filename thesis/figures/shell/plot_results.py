#!/usr/bin/env python3
import re
import subprocess
from pathlib import Path
import numpy as np
import matplotlib as mpl
mpl.use('pdf')
import matplotlib.pyplot as plt

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
# results/thickness_0.25/ele_409600/results.txt:LINALG::Solver:  2)   Solve                              3.481e+04 (300)         3.481e+04 (300)          3.481e+04 (300)          116 (300)
# results/thickness_0.25/ele_51200/results.txt:LINALG::Solver:  2)   Solve                              1592 (300)           3931 (300)          4282 (300)           13.1 (300)
# results/thickness_0.25/ele_6400/results.txt:LINALG::Solver:  2)   Solve                              48.6 (300)            84.85 (300)           142.5 (300)           0.2828 (300)
# results/thickness_0.25/ele_800/results.txt:LINALG::Solver:  2)   Solve                              13.6 (298)             25.39 (298)           42.89 (298)            0.08519 (298)

thicknesses = (0.25, 2.5, 5.0, 7.5, 10.0, 12.5)
loads = (-192.0, -2002.5, -4675.0, -8500.0, -13950.0*0.8, -21500.0)
ele_rads = ( 2,  4,  8, 10, 12, 14, 16)
ele_cirs = (20, 40, 80, 100, 120, 140, 160)
ele_axis = (20, 40, 80, 100, 120, 140, 160)


for ele_rad, ele_cir, ele_axi in zip(ele_rads, ele_cirs, ele_axis):
    ele = ele_rad*ele_cir*ele_axi
    print(ele)

dofs = {thickness : [] for thickness in thicknesses}
sol_times = {thickness : [] for thickness in thicknesses}
iters = {thickness : [] for thickness in thicknesses}


for thickness in thicknesses:
    for ele_rad, ele_cir, ele_axi in zip(ele_rads, ele_cirs, ele_axis):
        ele = ele_rad*ele_cir*ele_axi
        dir_path = Path('results', f'thickness_{thickness}', f'ele_{ele}')
        log_file = str(Path(dir_path, 'results.txt'))
        num_dofs = 3*get_num_nodes(log_file)
        sol_time = get_lin_solve_time(log_file, 20)
        num_iters = get_mean_gmres_iters(log_file)
        dofs[thickness].append(num_dofs)
        sol_times[thickness].append(sol_time)
        iters[thickness].append(num_iters)

plt.style.use(['science', 'grid', 'ieee'])
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
fig.subplots_adjust(left=.08, bottom=.12, right=0.95, top=.97) #font 10

for thickness in thicknesses:
    if thickness == 10.0:
        ax.plot(dofs[thickness][:-1], sol_times[thickness][:-1], color='gold', marker='o', label=f'{thickness} mm thickness', markersize=3)
    elif thickness == 12.5:
        ax.plot(dofs[thickness], sol_times[thickness], color='darkturquoise', linestyle='--', marker='o', label=f'{thickness} mm thickness', markersize=3)
    else:
        ax.plot(dofs[thickness], sol_times[thickness], marker='o', label=f'{thickness} mm thickness', markersize=3)

ax.legend()
ax.set(xlabel='Degrees of Freedom', ylabel='Mean Linear Solve Time (s)')
plt.ticklabel_format(style='sci', axis='x', scilimits=(0,0))
ax.set_xlim(left=0)
ax.set_ylim(bottom=0)
# ax.set_title(f'Small Blade Klaus Discretizations')
fig.set_size_inches(width, height)
plt.savefig('shell.pdf')
plt.show()

fig, ax = plt.subplots()
fig.subplots_adjust(left=.08, bottom=.12, right=0.95, top=.97) #font 10

for thickness in thicknesses:
    if thickness == 10.0:
        ax.plot(dofs[thickness][:-1], sol_times[thickness][:-1], color='gold', marker='o', label=f'{thickness} mm thickness', markersize=3)
    elif thickness == 12.5:
        ax.plot(dofs[thickness], iters[thickness], color='darkturquoise', linestyle='--', marker='o', label=f'{thickness} mm thickness', markersize=3)
    else:
        ax.plot(dofs[thickness], iters[thickness], marker='o', label=f'{thickness} mm thickness', markersize=3)

ax.legend()
ax.set(xlabel='Degrees of Freedom', ylabel='Mean GMRES iterations')
plt.ticklabel_format(style='sci', axis='x', scilimits=(0,0))
ax.set_xlim(left=0)
ax.set_ylim(bottom=0)
# ax.set_title(f'Small Blade Klaus Discretizations')
fig.set_size_inches(width, height)
plt.savefig('shell_iters.pdf')
plt.show()

#  nodes = [1323, 8450, 59049, 440657]
#  dofs = [x*3 for x in nodes]
#  times = [0.08519, 0.2828, 13.1, 116.0]

#  plt.style.use('seaborn')
#  fig = plt.figure()
#  ax = fig.add_subplot(111)

#  ax.plot(dofs, times, marker='o', label=f'0.25mm thickness')


#  ax.legend()
#  ax.set(xlabel='Degrees of Freedom', ylabel='Mean Linear Solve Time (s)')
#  ax.set_xlim(left=0)
#  ax.set_ylim(bottom=0)
#  ax.set_title(f'Cylidrical Shell Strong Scaling')
#  plt.savefig('shell_strong_scaling.png')
#  plt.show()
