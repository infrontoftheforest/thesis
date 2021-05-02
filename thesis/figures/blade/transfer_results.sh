#!/bin/bash
for size in 2 4 8 16 32 64; do
    mkdir -p $(pwd)/small${size}
    for procs in 1 2 4 8; do
        scp blue07:/home/ryan/wdir/input_files/blade_klaus_scaling/small${size}/small${size}_procs_${procs}_results.txt $(pwd)/small${size}/small${size}_procs_${procs}_results.txt 
    done
done

