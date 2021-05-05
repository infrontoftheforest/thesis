#!/usr/bin/env python3
from pprint import pprint
import numpy as np
import matplotlib as mpl
mpl.use('pdf')
import matplotlib.pyplot as plt

def jacobi(A,b,N=25,x=None):
    """Solves the equation Ax=b via the Jacobi iterative method."""
    # Create an initial guess if needed
    if x is None:
        x = np.zeros(len(A[0]))

    # Create a vector of the diagonal elements of A
    # and subtract them from A
    D = np.diag(A)
    R = A - np.diagflat(D)

    # Iterate for N times
    omega = 2./3
    for i in range(N):
        #  x = (b - np.dot(R,x)) / D
        x = omega*(b - np.dot(R,x)) / D + (1-omega)*x
    return x

n = 50

h = 1/n
A = (1/h**2)*(np.diag(np.full(n-1,-2))+np.diag(np.ones(n-2),1)+np.diag(np.ones(n-2),-1))
b = np.array([0]*(n-1), dtype=float)
j = np.linspace(1, n-1, n-1)
# pts = np.linspace(0, 1, n)
pts = np.linspace(h, 1 - h, (n-1))
k1 = 1 # wavenumber
k2 = n//4 # wavenumber
k3 = n//2 # wavenumber
k4 = n-1 # wavenumber

x_k1 = np.sin(k1*j*np.pi/n)
x_k2 = np.sin(k2*j*np.pi/n)
x_k3 = np.sin(k3*j*np.pi/n)
x_k4 = np.sin(k4*j*np.pi/n)
# guess = pts/n

# A = np.array([[2.0,1.0],[5.0,7.0]])
# b = np.array([11.0,13.0])
# guess = np.array([1.0,1.0])

N = 1000
ts = [0, 10, 100, 1000]
ts = [0, 10, 100]
x1 = []
x2 = []
x3 = []
x4 = []
for i, t in enumerate(ts):
    x1.append([0])
    x2.append([0])
    x3.append([0])
    x4.append([0])
    x1[i].extend(jacobi(A,b,N=t,x=x_k1))
    x2[i].extend(jacobi(A,b,N=t,x=x_k2))
    x3[i].extend(jacobi(A,b,N=t,x=x_k3))
    x4[i].extend(jacobi(A,b,N=t,x=x_k4))
    x1[i].extend([0])
    x2[i].extend([0])
    x3[i].extend([0])
    x4[i].extend([0])

temp = [0]
temp.extend(pts)
temp.extend([1])
pts = temp

#print("A:")
#pprint(A)
#
#print("b:")
#pprint(b)
#
#print("j/n:")
#pprint(j/(n))

#print("x:")
#pprint(sol)

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
height = 5.0

markersize=2
fig, axes = plt.subplots(len(ts), 3, constrained_layout = True)
for i, t in enumerate(ts):
    (ax1, ax2, ax3) = axes[i]
    ax1.plot(pts, x1[i], marker='.', markersize=markersize)
    ax1.set_xlim(left=0, right=1)
    ax1.set_ylim(bottom=-1, top=1)
    #  ax1.legend()
    ax2.plot(pts, x2[i], marker='.', markersize=markersize)
    ax2.set_xlim(left=0, right=1)
    ax2.set_xlim(left=0, right=1)
    ax2.set_ylim(bottom=-1, top=1)
    # ax2.legend()
    ax3.plot(pts, x4[i], marker='.', markersize=markersize)
    ax3.set_xlim(left=0, right=1)
    ax3.set_ylim(bottom=-1, top=1)
    #  ax3.legend()
    if (t == ts[-1]):
        ax1.set(xlabel='$\Omega_h$')
        ax2.set(xlabel='$\Omega_h$')
        ax3.set(xlabel='$\Omega_h$')
    ax1.set(ylabel='$\mathbf{u}_h$')

cols = ['k = {}'.format(col) for col in [k1, k2, k4]]
rows = ['m = {}'.format(row) for row in ['0', '10', '100']]

for ax, col in zip(axes[0], cols):
    ax.set_title(col)

#  for ax, row in zip(axes[:,0], rows):
    #  ax.set_ylabel(row, rotation=0)#, size='large')
pad = 5 # in points

for ax, row in zip(axes[:,0], rows):
    ax.annotate(row, xy=(0, 0.5), xytext=(-ax.yaxis.labelpad - pad, 0),
                xycoords=ax.yaxis.label, textcoords='offset points',
                size='large', ha='right', va='center')



plt.show()
save_str = 'jacobi.pdf'
fig.set_size_inches(width, height)
fig.savefig(save_str)

#fig, ax = plt.subplots()
#ax.plot(pts, sol_1, pts, sol_2, pts, sol_3, pts, sol_4, marker='o')
#  ax.plot(pts, sol_1, marker='o', label=f'k = {k1}')
#  ax.plot(pts, sol_2, marker='o', label=f'k = {k2}')
#  #ax.plot(pts, sol_3, marker='o', label=f'k = {k3}')
#  ax.plot(pts, sol_4, marker='o', label=f'k = {k4}')
#  # ax.plot(pts, x_k1, pts, x_k2, pts, x_k3, pts, x_k4, marker='o')

