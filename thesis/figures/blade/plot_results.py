#!/usr/bin/env python3

import re
import subprocess
from pathlib import Path
import numpy as np
import matplotlib as mpl
mpl.use('pdf')
import matplotlib.pyplot as plt

SOLVER = '/home/ryan/scratch/trilinos_testing/build/iterative_solver/iterative_solver'

def get_num_dofs(output_file):
    num_dofs = None
    num_dofs_str = r'^PID: 0, total_rows: (?P<num_dofs>\d+)'
    with open(output_file, 'r') as f:
        for line in f:
            m = re.match(num_dofs_str, line)
            if m:
                num_dofs = int(m.group('num_dofs'))
                break
    return num_dofs


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


def get_time(output_file):
    sol_time = None
    sol_time_str = r'^\s+Solution time:\s+(?P<sol_time>\S+)'
    with open(output_file, 'r') as f:
        for line in f:
            m = re.match(sol_time_str, line)
            if m:
                sol_time = float(m.group('sol_time'))
                break
    return sol_time


def run_solver(i, num_procs):
    # setup tee to read from process
    dir_path = Path(f'small{i}')
    log_file = str(Path(dir_path, f'small{i}_results.txt'))
    tee = subprocess.Popen(['tee', log_file], stdin=subprocess.PIPE)

    cmd = [
        'mpirun', '-np', num_procs,
        SOLVER, i
    ]
    cmd = [str(x) for x in cmd]
    print('INFO -- Command:')
    print(' '.join(cmd))
    result = subprocess.run(cmd, stdout=tee.stdin)
    return result.returncode

# TODO: run for 128 by changing to range(7)
procs = list(2**(i) for i in range(4))
sizes = list(2**(i+1) for i in range(6))


# for i in range(6):
#     j = 2**(i+1)
#     run_solver(j, 1)


# dofs = { size : { proc: [] for proc in procs } for size in sizes }
# sol_times = { size : { proc: [] for proc in procs } for size in sizes }

dofs = { proc : [] for proc in procs }
sol_times = { proc : [] for proc in procs }
iters = { proc : [] for proc in procs }

labels = [f'{i} Processors' for i in procs]

for proc in procs:
    for size in sizes:
        dir_path = Path(f'small{size}')
        log_file = str(Path(dir_path, f'small{size}_procs_{proc}_results.txt'))
        num_dofs = get_num_dofs(log_file)
        sol_time = get_time(log_file)
        num_iters = get_total_gmres_iters(log_file)
        dofs[proc].append(num_dofs)
        sol_times[proc].append(sol_time)
        iters[proc].append(num_iters)


# labels = ['small2', 'small4', 'small8', 'small16']
# procs = [[1, 2, 4, 8], [1, 2, 4, 8], [1, 2, 4], [1, 2, 4, 8]]
# times = [[17.7, 11.3, 4.18, 2.24], [26.8, 16.06, 9.76, 5.91], [53.88, 31.51, 17.77], [204.42, 99.04, 43.80, 40.67]]
#
size_to_dof = {}
for i, size in enumerate(sizes):
    size_to_dof[size] = dofs[2][i]
print(size_to_dof)

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

for proc in procs:
    ax.plot(dofs[proc], sol_times[proc], marker='o', label=f'{proc} Processors', markersize=3)


# for i, label in enumerate(labels):
#     ax.plot(procs[i], times[i], marker='o', label=label)
ax.legend()
ax.set(xlabel='Degrees of Freedom', ylabel='Linear Solve Time (s)')
plt.ticklabel_format(style='sci', axis='x', scilimits=(0,0))
ax.set_xlim(left=0)
ax.set_ylim(bottom=0)
# ax.set_title(f'Small Blade Klaus Discretizations')
fig.set_size_inches(width, height)
plt.savefig('blade_klaus_small.pdf')
plt.show()

fig, ax = plt.subplots()
fig.subplots_adjust(left=.08, bottom=.12, right=0.95, top=.97) #font 10

for proc in procs:
    ax.plot(dofs[proc], iters[proc], marker='o', label=f'{proc} Processors', markersize=3)


# for i, label in enumerate(labels):
#     ax.plot(procs[i], times[i], marker='o', label=label)
ax.legend()
ax.set(xlabel='Degrees of Freedom', ylabel='GMRES Iterations')
plt.ticklabel_format(style='sci', axis='x', scilimits=(0,0))
ax.set_xlim(left=0)
ax.set_ylim(bottom=0)
# ax.set_title(f'Small Blade Klaus Discretizations')
fig.set_size_inches(width, height)
plt.savefig('blade_klaus_small_iters.pdf')
plt.show()

## next figure
dofs = { size : [] for size in sizes }
sol_times = { size : [] for size in sizes }
iters = { size : [] for size in sizes }
# labels = [f'small{i}' for i in sizes]
for size in sizes:
    for proc in procs:
        dir_path = Path(f'small{size}')
        log_file = str(Path(dir_path, f'small{size}_procs_{proc}_results.txt'))
        num_dofs = get_num_dofs(log_file)
        sol_time = get_time(log_file)
        num_iters = get_total_gmres_iters(log_file)
        sol_times[size].append(sol_time)
        iters[size].append(num_iters)

# plt.style.use(['science', 'grid', 'high-vis'])
fig, ax = plt.subplots()
fig.subplots_adjust(left=.08, bottom=.12, right=0.95, top=.97) #font 10

for size in reversed(sizes):
    if size == 2:
        ax.plot(procs, sol_times[size], color='gold', marker='o', label=f'{size_to_dof[size]} DOF', markersize=3)
    elif size == 4:
        ax.plot(procs, sol_times[size], color='darkturquoise', linestyle='--', marker='o', label=f'{size_to_dof[size]} DOF', markersize=3)
    else:
        ax.plot(procs, sol_times[size], marker='o', label=f'{size_to_dof[size]} DOF', markersize=3)


# for i, label in enumerate(labels):
#     ax.plot(procs[i], times[i], marker='o', label=label)
ax.legend()
ax.set(xlabel='Processors', ylabel='Linear Solve Time (s)')
ax.set_xlim(left=0)
ax.set_ylim(bottom=0)
#ax.set_title(f'Small Blade Klaus Discretizations')
fig.set_size_inches(width, height)
plt.savefig('blade_klaus_small_sizes.pdf')
plt.show()

# ax.set(xlabel='Number of Processors', ylabel='Linear Solve Time (s)')
# ax.set_title(f'Small Blade Klaus Discretizations')
# ax.set_xlim(left=0)
# ax.set_ylim(bottom=0)
# plt.savefig('blade_klaus_small.png')
# plt.show()

